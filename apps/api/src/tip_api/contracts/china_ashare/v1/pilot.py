"""Immutable contracts for the bounded China A-share foundation pilot."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import date, datetime
from enum import StrEnum
from pathlib import PurePosixPath
from typing import Any, Literal

from pydantic import Field, field_validator, model_validator

from tip_api.contracts.china_ashare.v1.foundation import (
    MARKET_ID,
    ChinaAshareBoard,
    ChinaAshareExchange,
    FrozenContract,
)
from tip_api.contracts.common import normalize_required_string, normalize_utc_datetime


PILOT_PLAN_VERSION = "china-ashare-foundation-pilot-plan/1.0"
PILOT_MANIFEST_VERSION = "china-ashare-foundation-pilot-package/1.0"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_SOURCE_SECURITY_ID = re.compile(r"^(?:sh|sz|bj)\.[0-9]{6}$")
_LIFECYCLE_SUBJECT_KEY = re.compile(r"^(?:sse_issuer|szse_security)\.[0-9]{6}$")
_REASON_CODE = re.compile(r"^[a-z][a-z0-9_]*$")


class ChinaAsharePilotArtifactKind(StrEnum):
    OFFICIAL_CURRENT_INSTRUMENT = "official_current_instrument"
    BAOSTOCK_INSTRUMENT = "baostock_instrument"
    BAOSTOCK_SOURCE_STATE = "baostock_source_state"
    OFFICIAL_LIFECYCLE = "official_lifecycle"


class ChinaAsharePilotAnchorV1(FrozenContract):
    source_security_id: str
    exchange: ChinaAshareExchange
    board: ChinaAshareBoard
    scenario_tags: tuple[str, ...] = Field(min_length=1)

    @field_validator("source_security_id", mode="before")
    @classmethod
    def source_id_is_canonical(cls, value: str) -> str:
        normalized = normalize_required_string(
            value,
            field_name="source_security_id",
        ).lower()
        if not _SOURCE_SECURITY_ID.fullmatch(normalized):
            raise ValueError("source_security_id must use sh|sz|bj plus six digits")
        return normalized

    @field_validator("scenario_tags", mode="before")
    @classmethod
    def tags_are_canonical(cls, value: Any) -> tuple[str, ...]:
        return _canonical_reason_codes(value, field_name="scenario_tags")

    @model_validator(mode="after")
    def anchor_reconciles(self) -> "ChinaAsharePilotAnchorV1":
        prefix = self.source_security_id.split(".", maxsplit=1)[0]
        expected_exchange = {
            "sh": ChinaAshareExchange.SSE,
            "sz": ChinaAshareExchange.SZSE,
            "bj": ChinaAshareExchange.BSE,
        }[prefix]
        if self.exchange is not expected_exchange:
            raise ValueError("anchor exchange differs from source security ID")
        permitted_boards = {
            ChinaAshareExchange.SSE: {
                ChinaAshareBoard.SSE_MAIN,
                ChinaAshareBoard.STAR,
            },
            ChinaAshareExchange.SZSE: {
                ChinaAshareBoard.SZSE_MAIN,
                ChinaAshareBoard.CHINEXT,
            },
            ChinaAshareExchange.BSE: {ChinaAshareBoard.BSE},
        }
        if self.board not in permitted_boards[self.exchange]:
            raise ValueError("anchor board differs from exchange")
        return self


class ChinaAsharePilotPlanV1(FrozenContract):
    schema_version: Literal["1.0"] = "1.0"
    plan_version: Literal["china-ashare-foundation-pilot-plan/1.0"] = (
        PILOT_PLAN_VERSION
    )
    market_id: Literal["china_a_share"] = MARKET_ID
    planned_at: datetime
    official_reference_as_of_date: date
    baostock_snapshot_date: date
    history_start_date: date
    history_end_date: date
    anchors: tuple[ChinaAsharePilotAnchorV1, ...] = Field(min_length=5)
    lifecycle_subject_keys: tuple[str, ...] = Field(min_length=2)
    provider_ids: tuple[str, ...] = Field(min_length=2)
    maximum_source_requests: int = Field(ge=1, le=64)
    raw_upstream_payload_retained: Literal[False] = False
    canonical_apply_authorized: Literal[False] = False
    research_backtest_authorized: Literal[False] = False
    product_publication_authorized: Literal[False] = False
    deployment_authorized: Literal[False] = False
    logical_fingerprint: str

    @field_validator("planned_at")
    @classmethod
    def planned_time_is_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @field_validator(
        "official_reference_as_of_date",
        "baostock_snapshot_date",
        "history_start_date",
        "history_end_date",
        mode="before",
    )
    @classmethod
    def dates_are_dates(cls, value: Any) -> Any:
        if isinstance(value, datetime):
            raise ValueError("pilot date fields must not receive datetime values")
        return value

    @field_validator("anchors", mode="before")
    @classmethod
    def anchors_are_ordered(cls, value: Any) -> Any:
        if not isinstance(value, (tuple, list)):
            raise ValueError("anchors must be an ordered collection")
        return value

    @field_validator("lifecycle_subject_keys", mode="before")
    @classmethod
    def lifecycle_keys_are_canonical(cls, value: Any) -> tuple[str, ...]:
        if not isinstance(value, (tuple, list)):
            raise ValueError("lifecycle_subject_keys must be an ordered collection")
        normalized = tuple(
            sorted(
                {
                    normalize_required_string(
                        item,
                        field_name="lifecycle_subject_keys",
                    ).lower()
                    for item in value
                }
            )
        )
        if any(not _LIFECYCLE_SUBJECT_KEY.fullmatch(item) for item in normalized):
            raise ValueError("lifecycle_subject_keys contains an invalid key")
        return normalized

    @field_validator("provider_ids", mode="before")
    @classmethod
    def providers_are_canonical(cls, value: Any) -> tuple[str, ...]:
        if not isinstance(value, (tuple, list)):
            raise ValueError("provider_ids must be an ordered collection")
        normalized = tuple(
            sorted(
                {
                    normalize_required_string(item, field_name="provider_id").lower()
                    for item in value
                }
            )
        )
        return normalized

    @field_validator("logical_fingerprint")
    @classmethod
    def fingerprint_is_sha256(cls, value: str) -> str:
        return _sha(value, "logical_fingerprint")

    @model_validator(mode="after")
    def plan_reconciles(self) -> "ChinaAsharePilotPlanV1":
        if self.history_end_date < self.history_start_date:
            raise ValueError("pilot history interval is reversed")
        if self.history_end_date > self.baostock_snapshot_date:
            raise ValueError("pilot history cannot end after its BaoStock snapshot")
        anchor_ids = tuple(item.source_security_id for item in self.anchors)
        if anchor_ids != tuple(sorted(set(anchor_ids))):
            raise ValueError("pilot anchors must be unique and sorted")
        required_boards = {
            ChinaAshareBoard.SSE_MAIN,
            ChinaAshareBoard.STAR,
            ChinaAshareBoard.SZSE_MAIN,
            ChinaAshareBoard.CHINEXT,
            ChinaAshareBoard.BSE,
        }
        if {item.board for item in self.anchors} != required_boards:
            raise ValueError("pilot anchors must cover all five supported boards")
        if china_ashare_pilot_plan_fingerprint(self) != self.logical_fingerprint:
            raise ValueError("pilot plan fingerprint differs")
        return self


class ChinaAsharePilotReferenceQualityReportV1(FrozenContract):
    schema_version: Literal["1.0"] = "1.0"
    market_id: Literal["china_a_share"] = MARKET_ID
    plan_fingerprint: str
    evaluated_at: datetime
    planned_anchor_ids: tuple[str, ...]
    official_current_observed_ids: tuple[str, ...]
    baostock_snapshot_observed_ids: tuple[str, ...]
    lifecycle_target_keys: tuple[str, ...]
    lifecycle_observed_keys: tuple[str, ...]
    official_current_missing_ids: tuple[str, ...]
    baostock_snapshot_missing_ids: tuple[str, ...]
    lifecycle_missing_keys: tuple[str, ...]
    source_request_count: int = Field(ge=1)
    source_request_ceiling: int = Field(ge=1)
    reference_evidence_complete: bool
    stable_identity_adjudicated: Literal[False] = False
    daily_history_captured: Literal[False] = False
    adjustment_semantics_reconciled: Literal[False] = False
    research_backtest_authorized: Literal[False] = False
    canonical_apply_authorized: Literal[False] = False
    product_publication_authorized: Literal[False] = False
    deployment_authorized: Literal[False] = False
    reason_codes: tuple[str, ...] = Field(min_length=1)
    logical_fingerprint: str

    @field_validator("plan_fingerprint", "logical_fingerprint")
    @classmethod
    def fingerprints_are_sha256(cls, value: str, info: Any) -> str:
        return _sha(value, info.field_name)

    @field_validator("evaluated_at")
    @classmethod
    def evaluated_time_is_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @field_validator(
        "planned_anchor_ids",
        "official_current_observed_ids",
        "baostock_snapshot_observed_ids",
        "official_current_missing_ids",
        "baostock_snapshot_missing_ids",
        mode="before",
    )
    @classmethod
    def source_ids_are_canonical(cls, value: Any, info: Any) -> tuple[str, ...]:
        return _canonical_source_security_ids(value, field_name=info.field_name)

    @field_validator(
        "lifecycle_target_keys",
        "lifecycle_observed_keys",
        "lifecycle_missing_keys",
        mode="before",
    )
    @classmethod
    def lifecycle_keys_are_canonical(cls, value: Any, info: Any) -> tuple[str, ...]:
        if not isinstance(value, (tuple, list)):
            raise ValueError(f"{info.field_name} must be an ordered collection")
        normalized = tuple(
            sorted(
                {
                    normalize_required_string(item, field_name=info.field_name).lower()
                    for item in value
                }
            )
        )
        if any(not _LIFECYCLE_SUBJECT_KEY.fullmatch(item) for item in normalized):
            raise ValueError(f"{info.field_name} contains an invalid key")
        return normalized

    @field_validator("reason_codes", mode="before")
    @classmethod
    def reasons_are_canonical(cls, value: Any) -> tuple[str, ...]:
        return _canonical_reason_codes(value, field_name="reason_codes")

    @model_validator(mode="after")
    def report_reconciles(self) -> "ChinaAsharePilotReferenceQualityReportV1":
        planned = set(self.planned_anchor_ids)
        lifecycle_targets = set(self.lifecycle_target_keys)
        if set(self.official_current_missing_ids) != planned - set(
            self.official_current_observed_ids
        ):
            raise ValueError("official-current missing set differs")
        if set(self.baostock_snapshot_missing_ids) != planned - set(
            self.baostock_snapshot_observed_ids
        ):
            raise ValueError("BaoStock snapshot missing set differs")
        if set(self.lifecycle_missing_keys) != lifecycle_targets - set(
            self.lifecycle_observed_keys
        ):
            raise ValueError("lifecycle missing set differs")
        expected_complete = not (
            self.official_current_missing_ids or self.lifecycle_missing_keys
        )
        if self.reference_evidence_complete is not expected_complete:
            raise ValueError("reference evidence completeness differs")
        if self.source_request_count > self.source_request_ceiling:
            raise ValueError("pilot source request count exceeds its ceiling")
        if china_ashare_pilot_quality_report_fingerprint(self) != self.logical_fingerprint:
            raise ValueError("pilot quality report fingerprint differs")
        return self


class ChinaAsharePilotArtifactV1(FrozenContract):
    artifact_kind: ChinaAsharePilotArtifactKind
    relative_path: str
    row_count: int = Field(ge=0)
    byte_size: int = Field(ge=1)
    physical_sha256: str

    @field_validator("relative_path", mode="before")
    @classmethod
    def path_is_safe(cls, value: str) -> str:
        normalized = normalize_required_string(value, field_name="relative_path")
        path = PurePosixPath(normalized)
        if path.is_absolute() or ".." in path.parts or path.as_posix() != normalized:
            raise ValueError("artifact relative path is unsafe")
        if not normalized.startswith("normalized/") or not normalized.endswith(".json"):
            raise ValueError("pilot artifacts must use normalized JSON paths")
        return normalized

    @field_validator("physical_sha256")
    @classmethod
    def physical_hash_is_sha256(cls, value: str) -> str:
        return _sha(value, "physical_sha256")


class ChinaAsharePilotPackageManifestV1(FrozenContract):
    schema_version: Literal["1.0"] = "1.0"
    package_version: Literal["china-ashare-foundation-pilot-package/1.0"] = (
        PILOT_MANIFEST_VERSION
    )
    market_id: Literal["china_a_share"] = MARKET_ID
    plan_fingerprint: str
    created_at: datetime
    payload_layer: Literal["normalized_library_observations"] = (
        "normalized_library_observations"
    )
    raw_upstream_payload_retained: Literal[False] = False
    plan_document_sha256: str
    quality_report_sha256: str
    quality_report_fingerprint: str
    artifacts: tuple[ChinaAsharePilotArtifactV1, ...] = Field(min_length=1)
    canonical_apply_authorized: Literal[False] = False
    research_backtest_authorized: Literal[False] = False
    product_publication_authorized: Literal[False] = False
    deployment_authorized: Literal[False] = False
    logical_fingerprint: str

    @field_validator(
        "plan_fingerprint",
        "plan_document_sha256",
        "quality_report_sha256",
        "quality_report_fingerprint",
        "logical_fingerprint",
    )
    @classmethod
    def hashes_are_sha256(cls, value: str, info: Any) -> str:
        return _sha(value, info.field_name)

    @field_validator("created_at")
    @classmethod
    def created_time_is_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @model_validator(mode="after")
    def manifest_reconciles(self) -> "ChinaAsharePilotPackageManifestV1":
        keys = tuple(item.artifact_kind.value for item in self.artifacts)
        paths = tuple(item.relative_path for item in self.artifacts)
        if keys != tuple(sorted(set(keys))):
            raise ValueError("pilot artifact kinds must be unique and sorted")
        if len(paths) != len(set(paths)):
            raise ValueError("pilot artifact paths must be unique")
        if china_ashare_pilot_package_fingerprint(self) != self.logical_fingerprint:
            raise ValueError("pilot package fingerprint differs")
        return self


def build_china_ashare_pilot_plan(**values: Any) -> ChinaAsharePilotPlanV1:
    provisional = ChinaAsharePilotPlanV1.model_construct(
        **values,
        logical_fingerprint="0" * 64,
    )
    return ChinaAsharePilotPlanV1.model_validate(
        {
            **values,
            "logical_fingerprint": china_ashare_pilot_plan_fingerprint(provisional),
        }
    )


def build_china_ashare_pilot_quality_report(
    **values: Any,
) -> ChinaAsharePilotReferenceQualityReportV1:
    provisional = ChinaAsharePilotReferenceQualityReportV1.model_construct(
        **values,
        logical_fingerprint="0" * 64,
    )
    return ChinaAsharePilotReferenceQualityReportV1.model_validate(
        {
            **values,
            "logical_fingerprint": china_ashare_pilot_quality_report_fingerprint(
                provisional
            ),
        }
    )


def build_china_ashare_pilot_package_manifest(
    **values: Any,
) -> ChinaAsharePilotPackageManifestV1:
    provisional = ChinaAsharePilotPackageManifestV1.model_construct(
        **values,
        logical_fingerprint="0" * 64,
    )
    return ChinaAsharePilotPackageManifestV1.model_validate(
        {
            **values,
            "logical_fingerprint": china_ashare_pilot_package_fingerprint(provisional),
        }
    )


def china_ashare_pilot_plan_fingerprint(value: ChinaAsharePilotPlanV1) -> str:
    return _fingerprint(value.model_dump(mode="json", exclude={"logical_fingerprint"}))


def china_ashare_pilot_quality_report_fingerprint(
    value: ChinaAsharePilotReferenceQualityReportV1,
) -> str:
    return _fingerprint(value.model_dump(mode="json", exclude={"logical_fingerprint"}))


def china_ashare_pilot_package_fingerprint(
    value: ChinaAsharePilotPackageManifestV1,
) -> str:
    return _fingerprint(value.model_dump(mode="json", exclude={"logical_fingerprint"}))


def _canonical_source_security_ids(value: Any, *, field_name: str) -> tuple[str, ...]:
    if not isinstance(value, (tuple, list)):
        raise ValueError(f"{field_name} must be an ordered collection")
    normalized = tuple(
        sorted(
            {
                normalize_required_string(item, field_name=field_name).lower()
                for item in value
            }
        )
    )
    if any(not _SOURCE_SECURITY_ID.fullmatch(item) for item in normalized):
        raise ValueError(f"{field_name} contains an invalid source security ID")
    return normalized


def _canonical_reason_codes(value: Any, *, field_name: str) -> tuple[str, ...]:
    if not isinstance(value, (tuple, list)):
        raise ValueError(f"{field_name} must be an ordered collection")
    normalized = tuple(
        sorted(
            {
                normalize_required_string(item, field_name=field_name).lower()
                for item in value
            }
        )
    )
    if not normalized or any(not _REASON_CODE.fullmatch(item) for item in normalized):
        raise ValueError(f"{field_name} contains an invalid code")
    return normalized


def _fingerprint(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()


def _sha(value: str, field_name: str) -> str:
    normalized = normalize_required_string(value, field_name=field_name).lower()
    if not _SHA256.fullmatch(normalized):
        raise ValueError(f"{field_name} must be a lowercase SHA-256 digest")
    return normalized
