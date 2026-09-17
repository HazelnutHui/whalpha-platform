"""Stable research identity and listed-lifecycle contracts for China A-shares."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import date, datetime
from pathlib import PurePosixPath
from typing import Any, Literal
from urllib.parse import urlparse
from uuid import UUID, uuid5

from pydantic import Field, field_validator, model_validator

from tip_api.contracts.china_ashare.v1.foundation import (
    MARKET_ID,
    ChinaAshareBoard,
    ChinaAshareExchange,
    ChinaAshareSecurityForm,
    FrozenContract,
)
from tip_api.contracts.common import (
    QualityStatus,
    normalize_required_string,
    normalize_utc_datetime,
)


RESEARCH_IDENTITY_NAMESPACE = UUID("7b476390-b188-4c88-952a-b98643b67f17")
IDENTITY_LIFECYCLE_REPORT_VERSION = "china-ashare-identity-lifecycle-report/1.0"
_SOURCE_SECURITY_ID = re.compile(r"^(?:sh|sz|bj)\.[0-9]{6}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_REASON = re.compile(r"^[a-z][a-z0-9_]*$")


class ChinaAshareResearchInstrumentIdentityV1(FrozenContract):
    """One listed-security occurrence keyed independently from ticker alone."""

    schema_version: Literal["1.0"] = "1.0"
    market_id: Literal["china_a_share"] = MARKET_ID
    instrument_id: UUID
    identity_key: str
    source_security_id: str
    display_ticker: str
    current_name: str
    exchange: ChinaAshareExchange
    board: ChinaAshareBoard
    security_form: ChinaAshareSecurityForm
    listing_date: date
    alias_valid_from: date
    official_observation_fingerprint: str
    baostock_observation_fingerprint: str
    pilot_decision_fingerprint: str
    append_only: Literal[True] = True
    ticker_is_permanent_key: Literal[False] = False
    quality_status: Literal[QualityStatus.VALID] = QualityStatus.VALID
    reason_codes: tuple[str, ...] = Field(min_length=1)
    canonical_apply_authorized: Literal[False] = False
    logical_fingerprint: str

    @field_validator("source_security_id", mode="before")
    @classmethod
    def source_id_is_canonical(cls, value: str) -> str:
        normalized = normalize_required_string(
            value, field_name="source_security_id"
        ).lower()
        if not _SOURCE_SECURITY_ID.fullmatch(normalized):
            raise ValueError("source_security_id is invalid")
        return normalized

    @field_validator("identity_key", "display_ticker", "current_name", mode="before")
    @classmethod
    def required_text(cls, value: str, info: Any) -> str:
        return normalize_required_string(value, field_name=info.field_name)

    @field_validator("listing_date", "alias_valid_from", mode="before")
    @classmethod
    def dates_are_dates(cls, value: Any) -> Any:
        if isinstance(value, datetime):
            raise ValueError("identity dates must not receive datetimes")
        return value

    @field_validator(
        "official_observation_fingerprint",
        "baostock_observation_fingerprint",
        "pilot_decision_fingerprint",
        "logical_fingerprint",
    )
    @classmethod
    def hashes_are_sha256(cls, value: str, info: Any) -> str:
        return _sha(value, info.field_name)

    @field_validator("reason_codes", mode="before")
    @classmethod
    def reasons_are_canonical(cls, value: Any) -> tuple[str, ...]:
        return _reasons(value)

    @model_validator(mode="after")
    def identity_reconciles(self) -> "ChinaAshareResearchInstrumentIdentityV1":
        expected_key = research_identity_key(
            source_security_id=self.source_security_id,
            exchange=self.exchange,
            board=self.board,
            listing_date=self.listing_date,
        )
        if self.identity_key != expected_key:
            raise ValueError("research identity key differs from listed occurrence")
        if self.instrument_id != uuid5(RESEARCH_IDENTITY_NAMESPACE, expected_key):
            raise ValueError("instrument ID differs from research identity key")
        if self.alias_valid_from != self.listing_date:
            raise ValueError("first alias validity must start on listing date")
        prefix, suffix = {
            ChinaAshareExchange.SSE: ("sh", "SH"),
            ChinaAshareExchange.SZSE: ("sz", "SZ"),
            ChinaAshareExchange.BSE: ("bj", "BJ"),
        }[self.exchange]
        code = self.source_security_id.split(".", 1)[1]
        if self.source_security_id != f"{prefix}.{code}":
            raise ValueError("source security exchange differs")
        if self.display_ticker != f"{code}.{suffix}":
            raise ValueError("display ticker differs")
        if self.board is ChinaAshareBoard.UNKNOWN:
            raise ValueError("stable research identity requires a proven board")
        if self.security_form is ChinaAshareSecurityForm.UNKNOWN:
            raise ValueError("stable research identity requires a proven form")
        if "listed_occurrence_keyed" not in self.reason_codes:
            raise ValueError("stable identity requires occurrence-key reason")
        if research_instrument_identity_fingerprint(self) != self.logical_fingerprint:
            raise ValueError("research identity fingerprint differs")
        return self


class ChinaAshareListedLifecycleDecisionV1(FrozenContract):
    schema_version: Literal["1.0"] = "1.0"
    market_id: Literal["china_a_share"] = MARKET_ID
    instrument_id: UUID
    source_security_id: str
    interval_start: date
    interval_end: date
    listing_date: date
    current_list_observed_as_of: date
    expected_session_count: int = Field(ge=1)
    observed_state_count: int = Field(ge=0)
    trading_or_suspended_state_count: int = Field(ge=0)
    not_listed_state_count: int = Field(ge=0)
    unknown_state_count: int = Field(ge=0)
    security_termination_event_count: int = Field(ge=0)
    issuer_only_event_count: int = Field(ge=0)
    state_dates_complete: bool
    listed_interval_complete: bool
    quality_status: QualityStatus
    evidence_fingerprints: tuple[str, ...] = Field(min_length=1)
    reason_codes: tuple[str, ...] = Field(min_length=1)

    @field_validator("source_security_id", mode="before")
    @classmethod
    def source_id_is_canonical(cls, value: str) -> str:
        normalized = normalize_required_string(
            value, field_name="source_security_id"
        ).lower()
        if not _SOURCE_SECURITY_ID.fullmatch(normalized):
            raise ValueError("source_security_id is invalid")
        return normalized

    @field_validator(
        "interval_start",
        "interval_end",
        "listing_date",
        "current_list_observed_as_of",
        mode="before",
    )
    @classmethod
    def dates_are_dates(cls, value: Any) -> Any:
        if isinstance(value, datetime):
            raise ValueError("lifecycle dates must not receive datetimes")
        return value

    @field_validator("evidence_fingerprints", mode="before")
    @classmethod
    def fingerprints_are_canonical(cls, value: Any) -> tuple[str, ...]:
        if not isinstance(value, (tuple, list, set, frozenset)):
            raise ValueError("evidence fingerprints must be an ordered collection")
        normalized = tuple(sorted({str(item).strip().lower() for item in value}))
        if not normalized or any(not _SHA256.fullmatch(item) for item in normalized):
            raise ValueError("evidence fingerprints must contain SHA-256 values")
        return normalized

    @field_validator("reason_codes", mode="before")
    @classmethod
    def reasons_are_canonical(cls, value: Any) -> tuple[str, ...]:
        return _reasons(value)

    @model_validator(mode="after")
    def lifecycle_reconciles(self) -> "ChinaAshareListedLifecycleDecisionV1":
        if self.interval_end < self.interval_start:
            raise ValueError("lifecycle interval is reversed")
        if self.listing_date > self.interval_start:
            raise ValueError("listed lifecycle cannot start before listing")
        if self.current_list_observed_as_of < self.interval_end:
            raise ValueError("current-list evidence must follow interval end")
        if self.trading_or_suspended_state_count > self.observed_state_count:
            raise ValueError("classified lifecycle states exceed observed states")
        expected_complete = (
            self.observed_state_count == self.expected_session_count
            and self.trading_or_suspended_state_count == self.expected_session_count
            and self.not_listed_state_count == 0
            and self.unknown_state_count == 0
        )
        if self.state_dates_complete is not expected_complete:
            raise ValueError("state-date completeness differs from counts")
        expected_listed = (
            self.state_dates_complete
            and self.security_termination_event_count == 0
            and self.issuer_only_event_count == 0
        )
        if self.listed_interval_complete is not expected_listed:
            raise ValueError("listed interval status differs from evidence")
        if self.listed_interval_complete and self.quality_status is not QualityStatus.VALID:
            raise ValueError("complete lifecycle must be valid")
        if not self.listed_interval_complete and self.quality_status is QualityStatus.VALID:
            raise ValueError("incomplete lifecycle cannot be valid")
        return self


class ChinaAshareIdentityLifecycleReportV1(FrozenContract):
    schema_version: Literal["1.0"] = "1.0"
    report_version: Literal[
        "china-ashare-identity-lifecycle-report/1.0"
    ] = IDENTITY_LIFECYCLE_REPORT_VERSION
    market_id: Literal["china_a_share"] = MARKET_ID
    reference_package_fingerprint: str
    daily_package_fingerprint: str
    evaluated_at: datetime
    interval_start: date
    interval_end: date
    planned_instrument_count: int = Field(ge=1)
    resolved_identity_count: int = Field(ge=0)
    quarantined_identity_count: int = Field(ge=0)
    complete_lifecycle_count: int = Field(ge=0)
    incomplete_lifecycle_count: int = Field(ge=0)
    exact_official_source_bytes_retained: bool
    stable_identity_family_complete: bool
    lifecycle_family_complete: bool
    identities: tuple[ChinaAshareResearchInstrumentIdentityV1, ...]
    lifecycle_decisions: tuple[ChinaAshareListedLifecycleDecisionV1, ...]
    reason_codes: tuple[str, ...] = Field(min_length=1)
    canonical_apply_authorized: Literal[False] = False
    research_backtest_authorized: Literal[False] = False
    product_publication_authorized: Literal[False] = False
    deployment_authorized: Literal[False] = False
    logical_fingerprint: str

    @field_validator(
        "reference_package_fingerprint",
        "daily_package_fingerprint",
        "logical_fingerprint",
    )
    @classmethod
    def hashes_are_sha256(cls, value: str, info: Any) -> str:
        return _sha(value, info.field_name)

    @field_validator("evaluated_at")
    @classmethod
    def evaluated_time_is_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @field_validator("interval_start", "interval_end", mode="before")
    @classmethod
    def dates_are_dates(cls, value: Any) -> Any:
        if isinstance(value, datetime):
            raise ValueError("report interval must contain dates")
        return value

    @field_validator("reason_codes", mode="before")
    @classmethod
    def reasons_are_canonical(cls, value: Any) -> tuple[str, ...]:
        return _reasons(value)

    @model_validator(mode="after")
    def report_reconciles(self) -> "ChinaAshareIdentityLifecycleReportV1":
        if self.interval_end < self.interval_start:
            raise ValueError("identity lifecycle report interval is reversed")
        identity_ids = tuple(item.instrument_id for item in self.identities)
        lifecycle_ids = tuple(item.instrument_id for item in self.lifecycle_decisions)
        if identity_ids != tuple(sorted(set(identity_ids), key=str)):
            raise ValueError("identities must be unique and ordered")
        if lifecycle_ids != tuple(sorted(set(lifecycle_ids), key=str)):
            raise ValueError("lifecycle decisions must be unique and ordered")
        if identity_ids != lifecycle_ids:
            raise ValueError("identity and lifecycle populations differ")
        if self.resolved_identity_count != len(self.identities):
            raise ValueError("resolved identity count differs")
        if self.planned_instrument_count != (
            self.resolved_identity_count + self.quarantined_identity_count
        ):
            raise ValueError("identity dispositions do not partition the plan")
        complete = sum(item.listed_interval_complete for item in self.lifecycle_decisions)
        if self.complete_lifecycle_count != complete:
            raise ValueError("complete lifecycle count differs")
        if self.incomplete_lifecycle_count != len(self.lifecycle_decisions) - complete:
            raise ValueError("incomplete lifecycle count differs")
        expected_identity = (
            self.exact_official_source_bytes_retained
            and self.resolved_identity_count > 0
            and self.quarantined_identity_count == 0
        )
        if self.stable_identity_family_complete is not expected_identity:
            raise ValueError("stable identity family status differs")
        expected_lifecycle = (
            self.stable_identity_family_complete
            and self.complete_lifecycle_count == self.resolved_identity_count
            and self.incomplete_lifecycle_count == 0
        )
        if self.lifecycle_family_complete is not expected_lifecycle:
            raise ValueError("lifecycle family status differs")
        if identity_lifecycle_report_fingerprint(self) != self.logical_fingerprint:
            raise ValueError("identity lifecycle report fingerprint differs")
        return self


class ChinaAshareIdentityLifecycleRawArtifactV1(FrozenContract):
    artifact_kind: Literal[
        "sse_main_current",
        "sse_star_current",
        "szse_a_current",
        "sse_delist",
        "szse_delist",
    ]
    exchange: ChinaAshareExchange
    retrieved_at: datetime
    final_url: str
    content_type: str
    relative_path: str
    byte_size: int = Field(ge=1)
    physical_sha256: str

    @field_validator("retrieved_at")
    @classmethod
    def retrieved_time_is_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @field_validator("final_url", mode="before")
    @classmethod
    def final_url_is_official_https(cls, value: str) -> str:
        normalized = normalize_required_string(value, field_name="final_url")
        parsed = urlparse(normalized)
        if parsed.scheme != "https" or parsed.hostname not in {
            "query.sse.com.cn",
            "www.szse.cn",
        }:
            raise ValueError("identity artifact final URL must be official HTTPS")
        return normalized

    @field_validator("content_type", mode="before")
    @classmethod
    def content_type_is_present(cls, value: str) -> str:
        return normalize_required_string(value, field_name="content_type")

    @field_validator("relative_path", mode="before")
    @classmethod
    def relative_path_is_safe(cls, value: str) -> str:
        normalized = normalize_required_string(value, field_name="relative_path")
        path = PurePosixPath(normalized)
        if path.is_absolute() or ".." in path.parts or path.as_posix() != normalized:
            raise ValueError("identity artifact relative path is unsafe")
        if not normalized.startswith("raw/"):
            raise ValueError("identity artifact must use raw path")
        return normalized

    @field_validator("physical_sha256")
    @classmethod
    def physical_hash_is_sha256(cls, value: str) -> str:
        return _sha(value, "physical_sha256")


class ChinaAshareIdentityLifecyclePackageManifestV1(FrozenContract):
    schema_version: Literal["1.0"] = "1.0"
    package_version: Literal[
        "china-ashare-identity-lifecycle-package/1.0"
    ] = "china-ashare-identity-lifecycle-package/1.0"
    market_id: Literal["china_a_share"] = MARKET_ID
    reference_package_fingerprint: str
    daily_package_fingerprint: str
    created_at: datetime
    identities_document_sha256: str
    lifecycle_document_sha256: str
    report_document_sha256: str
    report_fingerprint: str
    raw_artifacts: tuple[ChinaAshareIdentityLifecycleRawArtifactV1, ...]
    canonical_apply_authorized: Literal[False] = False
    research_backtest_authorized: Literal[False] = False
    product_publication_authorized: Literal[False] = False
    deployment_authorized: Literal[False] = False
    logical_fingerprint: str

    @field_validator(
        "reference_package_fingerprint",
        "daily_package_fingerprint",
        "identities_document_sha256",
        "lifecycle_document_sha256",
        "report_document_sha256",
        "report_fingerprint",
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
    def manifest_reconciles(self) -> "ChinaAshareIdentityLifecyclePackageManifestV1":
        keys = tuple((item.artifact_kind, item.relative_path) for item in self.raw_artifacts)
        if keys != tuple(sorted(set(keys))):
            raise ValueError("identity lifecycle raw artifacts must be unique and ordered")
        if len(self.raw_artifacts) != 5:
            raise ValueError("identity lifecycle package requires five official artifacts")
        if identity_lifecycle_package_manifest_fingerprint(self) != self.logical_fingerprint:
            raise ValueError("identity lifecycle package fingerprint differs")
        return self


def research_identity_key(
    *,
    source_security_id: str,
    exchange: ChinaAshareExchange,
    board: ChinaAshareBoard,
    listing_date: date,
) -> str:
    return "|".join(
        (source_security_id.lower(), exchange.value, board.value, listing_date.isoformat())
    )


def build_research_instrument_identity(
    **values: Any,
) -> ChinaAshareResearchInstrumentIdentityV1:
    source_security_id = str(values["source_security_id"]).strip().lower()
    exchange = ChinaAshareExchange(values["exchange"])
    board = ChinaAshareBoard(values["board"])
    listing_date = values["listing_date"]
    key = research_identity_key(
        source_security_id=source_security_id,
        exchange=exchange,
        board=board,
        listing_date=listing_date,
    )
    values = {
        **values,
        "source_security_id": source_security_id,
        "exchange": exchange,
        "board": board,
        "identity_key": key,
        "instrument_id": uuid5(RESEARCH_IDENTITY_NAMESPACE, key),
    }
    candidate = ChinaAshareResearchInstrumentIdentityV1.model_construct(
        **values, logical_fingerprint="0" * 64
    )
    return ChinaAshareResearchInstrumentIdentityV1.model_validate(
        {
            **candidate.model_dump(mode="python"),
            "logical_fingerprint": research_instrument_identity_fingerprint(candidate),
        }
    )


def build_identity_lifecycle_report(**values: Any) -> ChinaAshareIdentityLifecycleReportV1:
    candidate = ChinaAshareIdentityLifecycleReportV1.model_construct(
        **values, logical_fingerprint="0" * 64
    )
    return ChinaAshareIdentityLifecycleReportV1.model_validate(
        {
            **candidate.model_dump(mode="python"),
            "logical_fingerprint": identity_lifecycle_report_fingerprint(candidate),
        }
    )


def build_identity_lifecycle_package_manifest(
    **values: Any,
) -> ChinaAshareIdentityLifecyclePackageManifestV1:
    candidate = ChinaAshareIdentityLifecyclePackageManifestV1.model_construct(
        **values, logical_fingerprint="0" * 64
    )
    return ChinaAshareIdentityLifecyclePackageManifestV1.model_validate(
        {
            **candidate.model_dump(mode="python"),
            "logical_fingerprint": identity_lifecycle_package_manifest_fingerprint(
                candidate
            ),
        }
    )


def research_instrument_identity_fingerprint(
    value: ChinaAshareResearchInstrumentIdentityV1,
) -> str:
    return _fingerprint(value.model_dump(mode="json", exclude={"logical_fingerprint"}))


def identity_lifecycle_report_fingerprint(
    value: ChinaAshareIdentityLifecycleReportV1,
) -> str:
    return _fingerprint(value.model_dump(mode="json", exclude={"logical_fingerprint"}))


def identity_lifecycle_package_manifest_fingerprint(
    value: ChinaAshareIdentityLifecyclePackageManifestV1,
) -> str:
    return _fingerprint(value.model_dump(mode="json", exclude={"logical_fingerprint"}))


def _sha(value: str, field_name: str) -> str:
    normalized = normalize_required_string(value, field_name=field_name).lower()
    if not _SHA256.fullmatch(normalized):
        raise ValueError(f"{field_name} must be a lowercase SHA-256")
    return normalized


def _reasons(value: Any) -> tuple[str, ...]:
    if not isinstance(value, (tuple, list, set, frozenset)):
        raise ValueError("reason codes must be an ordered collection")
    normalized = tuple(sorted({str(item).strip().lower() for item in value}))
    if not normalized or any(not _REASON.fullmatch(item) for item in normalized):
        raise ValueError("reason codes must be canonical snake_case")
    return normalized


def _fingerprint(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode()
    ).hexdigest()
