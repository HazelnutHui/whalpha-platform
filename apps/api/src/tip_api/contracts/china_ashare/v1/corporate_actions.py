"""Point-in-time A-share distribution and adjustment reconciliation contracts."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from pathlib import PurePosixPath
from typing import Any, Literal
from urllib.parse import urlparse
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from tip_api.contracts.china_ashare.v1.foundation import MARKET_ID, FrozenContract
from tip_api.contracts.common import (
    QualityStatus,
    ensure_finite_decimal,
    normalize_optional_string,
    normalize_required_string,
    normalize_utc_datetime,
    reject_float_decimal_input,
)


CORPORATE_ACTION_RECONCILIATION_VERSION = (
    "china-ashare-corporate-action-adjustment-reconciliation/1.0"
)
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_SOURCE_SECURITY_ID = re.compile(r"^(?:sh|sz|bj)\.[0-9]{6}$")
_REASON_CODE = re.compile(r"^[a-z][a-z0-9_]*$")


class ChinaAshareDistributionActionType(StrEnum):
    CASH_DIVIDEND = "cash_dividend"
    STOCK_DIVIDEND = "stock_dividend"
    CAPITALIZATION = "capitalization"
    RIGHTS_ISSUE = "rights_issue"
    COMPOSITE_DISTRIBUTION = "composite_distribution"


class ChinaAshareAdjustmentReconciliationStatus(StrEnum):
    MATCHED_ACTION = "matched_action"
    LEFT_BOUNDARY_ACTION = "left_boundary_action"
    PROVIDER_NOOP_CORRECTION = "provider_noop_correction"
    ACTION_WITHOUT_ADJUSTMENT = "action_without_adjustment"
    ADJUSTMENT_WITHOUT_ACTION = "adjustment_without_action"
    FACTOR_CONFLICT = "factor_conflict"


class ChinaAshareCorporateActionObservationV1(FrozenContract):
    """One implemented distribution observed from a declared source row."""

    schema_version: Literal["1.0"] = "1.0"
    market_id: Literal["china_a_share"] = MARKET_ID
    instrument_id: UUID
    source_security_id: str
    action_type: ChinaAshareDistributionActionType
    implementation_announcement_date: date
    record_date: date
    ex_date: date
    payment_date: date | None = None
    shares_arrival_date: date | None = None
    cash_dividend_per_share_cny: Decimal = Decimal("0")
    bonus_share_ratio: Decimal = Decimal("0")
    capitalization_ratio: Decimal = Decimal("0")
    rights_issue_ratio: Decimal = Decimal("0")
    rights_issue_price_per_share_cny: Decimal | None = None
    action_description: str
    report_period: str | None = None
    source: str
    source_retrieved_at: datetime
    raw_payload_sha256: str
    quality_status: QualityStatus
    reason_codes: tuple[str, ...] = ()
    normalized_return_authorized: Literal[False] = False
    logical_fingerprint: str

    @field_validator("source_security_id", mode="before")
    @classmethod
    def source_id_is_canonical(cls, value: str) -> str:
        normalized = normalize_required_string(
            value, field_name="source_security_id"
        ).lower()
        if not _SOURCE_SECURITY_ID.fullmatch(normalized):
            raise ValueError("source_security_id must use sh|sz|bj plus six digits")
        return normalized

    @field_validator(
        "implementation_announcement_date",
        "record_date",
        "ex_date",
        "payment_date",
        "shares_arrival_date",
        mode="before",
    )
    @classmethod
    def dates_are_dates(cls, value: Any) -> Any:
        if isinstance(value, datetime):
            raise ValueError("corporate-action dates must not receive datetimes")
        return value

    @field_validator(
        "cash_dividend_per_share_cny",
        "bonus_share_ratio",
        "capitalization_ratio",
        "rights_issue_ratio",
        "rights_issue_price_per_share_cny",
        mode="before",
    )
    @classmethod
    def decimals_are_exact(cls, value: Any, info: Any) -> Any:
        if value is None:
            return None
        return reject_float_decimal_input(value, field_name=info.field_name)

    @field_validator(
        "cash_dividend_per_share_cny",
        "bonus_share_ratio",
        "capitalization_ratio",
        "rights_issue_ratio",
        "rights_issue_price_per_share_cny",
    )
    @classmethod
    def decimals_are_non_negative(
        cls, value: Decimal | None, info: Any
    ) -> Decimal | None:
        if value is None:
            return None
        normalized = ensure_finite_decimal(value, field_name=info.field_name)
        if normalized < 0:
            raise ValueError(f"{info.field_name} must be non-negative")
        return normalized

    @field_validator("action_description", "source", mode="before")
    @classmethod
    def required_text(cls, value: str, info: Any) -> str:
        return normalize_required_string(value, field_name=info.field_name)

    @field_validator("report_period", mode="before")
    @classmethod
    def optional_text(cls, value: str | None) -> str | None:
        return normalize_optional_string(value, field_name="report_period")

    @field_validator("source_retrieved_at")
    @classmethod
    def retrieved_time_is_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @field_validator("raw_payload_sha256", "logical_fingerprint")
    @classmethod
    def hashes_are_sha256(cls, value: str, info: Any) -> str:
        return _sha(value, info.field_name)

    @field_validator("reason_codes", mode="before")
    @classmethod
    def reasons_are_canonical(cls, value: Any) -> tuple[str, ...]:
        return _reason_codes(value)

    @model_validator(mode="after")
    def action_reconciles(self) -> "ChinaAshareCorporateActionObservationV1":
        if self.implementation_announcement_date > self.record_date:
            raise ValueError("implementation announcement cannot follow record date")
        if self.record_date >= self.ex_date:
            raise ValueError("record date must precede ex-date")
        if self.payment_date is not None and self.payment_date < self.ex_date:
            raise ValueError("payment date cannot precede ex-date")
        if self.shares_arrival_date is not None and self.shares_arrival_date < self.ex_date:
            raise ValueError("shares arrival date cannot precede ex-date")
        cash = self.cash_dividend_per_share_cny > 0
        bonus = self.bonus_share_ratio > 0
        capitalization = self.capitalization_ratio > 0
        rights = self.rights_issue_ratio > 0
        if not any((cash, bonus, capitalization, rights)):
            raise ValueError("corporate action must contain an economic distribution")
        if rights != (self.rights_issue_price_per_share_cny is not None):
            raise ValueError("rights issue ratio and price must be present together")
        expected_type = _distribution_type(
            cash=cash,
            bonus=bonus,
            capitalization=capitalization,
            rights=rights,
        )
        if self.action_type is not expected_type:
            raise ValueError("action type differs from economic components")
        if corporate_action_observation_fingerprint(self) != self.logical_fingerprint:
            raise ValueError("corporate-action observation fingerprint differs")
        return self


class ChinaAshareAdjustmentActionReconciliationV1(FrozenContract):
    """One action/factor decision without silently accepting provider semantics."""

    instrument_id: UUID
    source_security_id: str
    session_date: date
    action_fingerprint: str | None = None
    previous_close_cny: Decimal | None = None
    exchange_reference_pre_close_cny: Decimal | None = None
    theoretical_unrounded_reference_cny: Decimal | None = None
    expected_adjustment_step: Decimal | None = None
    observed_fore_step: Decimal | None = None
    observed_back_step: Decimal | None = None
    fore_relative_error: Decimal | None = None
    back_relative_error: Decimal | None = None
    provider_factor: Decimal | None = None
    status: ChinaAshareAdjustmentReconciliationStatus
    quality_status: QualityStatus
    reason_codes: tuple[str, ...] = Field(min_length=1)

    @field_validator("source_security_id", mode="before")
    @classmethod
    def source_id_is_canonical(cls, value: str) -> str:
        normalized = normalize_required_string(
            value, field_name="source_security_id"
        ).lower()
        if not _SOURCE_SECURITY_ID.fullmatch(normalized):
            raise ValueError("source_security_id must use sh|sz|bj plus six digits")
        return normalized

    @field_validator("session_date", mode="before")
    @classmethod
    def session_is_date(cls, value: Any) -> Any:
        if isinstance(value, datetime):
            raise ValueError("session_date must not receive a datetime")
        return value

    @field_validator("action_fingerprint")
    @classmethod
    def optional_hash_is_sha256(cls, value: str | None) -> str | None:
        return None if value is None else _sha(value, "action_fingerprint")

    @field_validator(
        "previous_close_cny",
        "exchange_reference_pre_close_cny",
        "theoretical_unrounded_reference_cny",
        "expected_adjustment_step",
        "observed_fore_step",
        "observed_back_step",
        "fore_relative_error",
        "back_relative_error",
        "provider_factor",
        mode="before",
    )
    @classmethod
    def optional_decimals_are_exact(cls, value: Any, info: Any) -> Any:
        if value is None:
            return None
        return reject_float_decimal_input(value, field_name=info.field_name)

    @field_validator(
        "previous_close_cny",
        "exchange_reference_pre_close_cny",
        "theoretical_unrounded_reference_cny",
        "expected_adjustment_step",
        "observed_fore_step",
        "observed_back_step",
        "provider_factor",
    )
    @classmethod
    def optional_values_are_positive(
        cls, value: Decimal | None, info: Any
    ) -> Decimal | None:
        if value is None:
            return None
        normalized = ensure_finite_decimal(value, field_name=info.field_name)
        if normalized <= 0:
            raise ValueError(f"{info.field_name} must be positive")
        return normalized

    @field_validator("fore_relative_error", "back_relative_error")
    @classmethod
    def errors_are_non_negative(
        cls, value: Decimal | None, info: Any
    ) -> Decimal | None:
        if value is None:
            return None
        normalized = ensure_finite_decimal(value, field_name=info.field_name)
        if normalized < 0:
            raise ValueError(f"{info.field_name} must be non-negative")
        return normalized

    @field_validator("reason_codes", mode="before")
    @classmethod
    def reasons_are_canonical(cls, value: Any) -> tuple[str, ...]:
        return _reason_codes(value)

    @model_validator(mode="after")
    def decision_reconciles(self) -> "ChinaAshareAdjustmentActionReconciliationV1":
        action_statuses = {
            ChinaAshareAdjustmentReconciliationStatus.MATCHED_ACTION,
            ChinaAshareAdjustmentReconciliationStatus.LEFT_BOUNDARY_ACTION,
            ChinaAshareAdjustmentReconciliationStatus.ACTION_WITHOUT_ADJUSTMENT,
            ChinaAshareAdjustmentReconciliationStatus.FACTOR_CONFLICT,
        }
        if (self.action_fingerprint is not None) != (self.status in action_statuses):
            raise ValueError("action binding differs from reconciliation status")
        if self.status is ChinaAshareAdjustmentReconciliationStatus.MATCHED_ACTION:
            required = (
                self.previous_close_cny,
                self.exchange_reference_pre_close_cny,
                self.theoretical_unrounded_reference_cny,
                self.expected_adjustment_step,
                self.observed_fore_step,
                self.observed_back_step,
                self.fore_relative_error,
                self.back_relative_error,
                self.provider_factor,
            )
            if any(item is None for item in required):
                raise ValueError("matched action requires complete factor evidence")
        if self.status is ChinaAshareAdjustmentReconciliationStatus.PROVIDER_NOOP_CORRECTION:
            if self.action_fingerprint is not None:
                raise ValueError("provider no-op correction cannot bind an action")
            if self.observed_fore_step != Decimal("1") or self.observed_back_step != Decimal("1"):
                raise ValueError("provider no-op correction requires unchanged cumulative factors")
        return self


class ChinaAshareCorporateActionReconciliationReportV1(FrozenContract):
    schema_version: Literal["1.0"] = "1.0"
    report_version: Literal[
        "china-ashare-corporate-action-adjustment-reconciliation/1.0"
    ] = CORPORATE_ACTION_RECONCILIATION_VERSION
    market_id: Literal["china_a_share"] = MARKET_ID
    daily_package_fingerprint: str
    evaluated_at: datetime
    start_date: date
    end_date: date
    instrument_count: int = Field(ge=1)
    corporate_action_count: int = Field(ge=0)
    adjustment_observation_count: int = Field(ge=0)
    matched_action_count: int = Field(ge=0)
    left_boundary_action_count: int = Field(ge=0)
    provider_noop_correction_count: int = Field(ge=0)
    action_without_adjustment_count: int = Field(ge=0)
    adjustment_without_action_count: int = Field(ge=0)
    factor_conflict_count: int = Field(ge=0)
    raw_upstream_payload_retained: bool
    cross_source_action_reconciled: bool
    adjustment_semantics_reconciled: bool
    corporate_action_family_complete: bool
    gross_total_return_authorized: bool
    decisions: tuple[ChinaAshareAdjustmentActionReconciliationV1, ...]
    reason_codes: tuple[str, ...] = Field(min_length=1)
    canonical_apply_authorized: Literal[False] = False
    research_backtest_authorized: Literal[False] = False
    product_publication_authorized: Literal[False] = False
    deployment_authorized: Literal[False] = False
    logical_fingerprint: str

    @field_validator("daily_package_fingerprint", "logical_fingerprint")
    @classmethod
    def hashes_are_sha256(cls, value: str, info: Any) -> str:
        return _sha(value, info.field_name)

    @field_validator("evaluated_at")
    @classmethod
    def evaluated_time_is_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @field_validator("start_date", "end_date", mode="before")
    @classmethod
    def dates_are_dates(cls, value: Any) -> Any:
        if isinstance(value, datetime):
            raise ValueError("report range must contain dates")
        return value

    @field_validator("reason_codes", mode="before")
    @classmethod
    def reasons_are_canonical(cls, value: Any) -> tuple[str, ...]:
        return _reason_codes(value)

    @model_validator(mode="after")
    def report_reconciles(self) -> "ChinaAshareCorporateActionReconciliationReportV1":
        if self.end_date < self.start_date:
            raise ValueError("report range is reversed")
        ordered = tuple(
            sorted(
                self.decisions,
                key=lambda item: (str(item.instrument_id), item.session_date, item.status.value),
            )
        )
        if ordered != self.decisions:
            raise ValueError("reconciliation decisions must be ordered")
        counts = {status: 0 for status in ChinaAshareAdjustmentReconciliationStatus}
        for item in self.decisions:
            counts[item.status] += 1
        expected = {
            ChinaAshareAdjustmentReconciliationStatus.MATCHED_ACTION: self.matched_action_count,
            ChinaAshareAdjustmentReconciliationStatus.LEFT_BOUNDARY_ACTION: self.left_boundary_action_count,
            ChinaAshareAdjustmentReconciliationStatus.PROVIDER_NOOP_CORRECTION: self.provider_noop_correction_count,
            ChinaAshareAdjustmentReconciliationStatus.ACTION_WITHOUT_ADJUSTMENT: self.action_without_adjustment_count,
            ChinaAshareAdjustmentReconciliationStatus.ADJUSTMENT_WITHOUT_ACTION: self.adjustment_without_action_count,
            ChinaAshareAdjustmentReconciliationStatus.FACTOR_CONFLICT: self.factor_conflict_count,
        }
        if counts != expected:
            raise ValueError("reconciliation decision counts differ")
        action_bound = sum(item.action_fingerprint is not None for item in self.decisions)
        if action_bound != self.corporate_action_count:
            raise ValueError("corporate-action count differs from bound decisions")
        adjustment_bound = len(self.decisions) - self.action_without_adjustment_count
        if adjustment_bound != self.adjustment_observation_count:
            raise ValueError("adjustment observation count differs from decisions")
        blockers = any(
            (
                self.left_boundary_action_count,
                self.action_without_adjustment_count,
                self.adjustment_without_action_count,
                self.factor_conflict_count,
            )
        )
        if self.adjustment_semantics_reconciled and (
            blockers or not self.raw_upstream_payload_retained
        ):
            raise ValueError("adjustment semantics cannot pass with unresolved evidence")
        if self.corporate_action_family_complete and (
            not self.adjustment_semantics_reconciled
            or not self.cross_source_action_reconciled
        ):
            raise ValueError("corporate-action family cannot pass before all evidence gates")
        if self.gross_total_return_authorized != self.corporate_action_family_complete:
            raise ValueError("gross total-return authority must follow family completion")
        if corporate_action_reconciliation_report_fingerprint(self) != self.logical_fingerprint:
            raise ValueError("corporate-action reconciliation report fingerprint differs")
        return self


class ChinaAshareCorporateActionRawArtifactV1(FrozenContract):
    source_kind: Literal["distribution", "rights_issue"]
    source_security_id: str
    retrieved_at: datetime
    final_url: str
    content_type: str
    relative_path: str
    byte_size: int = Field(ge=1)
    physical_sha256: str

    @field_validator("source_security_id", mode="before")
    @classmethod
    def source_id_is_canonical(cls, value: str) -> str:
        normalized = normalize_required_string(
            value, field_name="source_security_id"
        ).lower()
        if not _SOURCE_SECURITY_ID.fullmatch(normalized):
            raise ValueError("source_security_id must use sh|sz|bj plus six digits")
        return normalized

    @field_validator("retrieved_at")
    @classmethod
    def retrieved_time_is_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @field_validator("final_url", mode="before")
    @classmethod
    def final_url_is_cninfo_https(cls, value: str) -> str:
        normalized = normalize_required_string(value, field_name="final_url")
        parsed = urlparse(normalized)
        if parsed.scheme != "https" or parsed.hostname != "webapi.cninfo.com.cn":
            raise ValueError("raw artifact final URL must be CNINFO HTTPS")
        return normalized

    @field_validator("content_type", mode="before")
    @classmethod
    def content_type_is_json(cls, value: str) -> str:
        normalized = normalize_required_string(value, field_name="content_type")
        if "json" not in normalized.lower():
            raise ValueError("raw artifact content type must be JSON")
        return normalized

    @field_validator("relative_path", mode="before")
    @classmethod
    def relative_path_is_safe(cls, value: str) -> str:
        normalized = normalize_required_string(value, field_name="relative_path")
        path = PurePosixPath(normalized)
        if path.is_absolute() or ".." in path.parts or path.as_posix() != normalized:
            raise ValueError("raw artifact relative path is unsafe")
        if not normalized.startswith("raw/") or not normalized.endswith(".json"):
            raise ValueError("raw artifact must use a raw JSON path")
        return normalized

    @field_validator("physical_sha256")
    @classmethod
    def physical_hash_is_sha256(cls, value: str) -> str:
        return _sha(value, "physical_sha256")


class ChinaAshareCorporateActionPackageManifestV1(FrozenContract):
    schema_version: Literal["1.0"] = "1.0"
    package_version: Literal[
        "china-ashare-corporate-action-evidence-package/1.0"
    ] = "china-ashare-corporate-action-evidence-package/1.0"
    market_id: Literal["china_a_share"] = MARKET_ID
    daily_package_fingerprint: str
    created_at: datetime
    actions_document_sha256: str
    adjustments_document_sha256: str
    crosschecks_document_sha256: str
    report_document_sha256: str
    report_fingerprint: str
    raw_artifacts: tuple[ChinaAshareCorporateActionRawArtifactV1, ...]
    raw_upstream_payload_retained: bool
    canonical_apply_authorized: Literal[False] = False
    research_backtest_authorized: Literal[False] = False
    product_publication_authorized: Literal[False] = False
    deployment_authorized: Literal[False] = False
    logical_fingerprint: str

    @field_validator(
        "daily_package_fingerprint",
        "actions_document_sha256",
        "adjustments_document_sha256",
        "crosschecks_document_sha256",
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
    def manifest_reconciles(self) -> "ChinaAshareCorporateActionPackageManifestV1":
        keys = tuple(
            (item.source_security_id, item.source_kind, item.relative_path)
            for item in self.raw_artifacts
        )
        if keys != tuple(sorted(set(keys))):
            raise ValueError("raw corporate-action artifacts must be unique and ordered")
        if self.raw_upstream_payload_retained != bool(self.raw_artifacts):
            raise ValueError("raw retention status differs from artifacts")
        if corporate_action_package_manifest_fingerprint(self) != self.logical_fingerprint:
            raise ValueError("corporate-action package manifest fingerprint differs")
        return self


def build_corporate_action_observation(**values: Any) -> ChinaAshareCorporateActionObservationV1:
    if "action_type" in values:
        values["action_type"] = ChinaAshareDistributionActionType(values["action_type"])
    candidate = ChinaAshareCorporateActionObservationV1.model_construct(
        **values,
        logical_fingerprint="0" * 64,
    )
    return ChinaAshareCorporateActionObservationV1.model_validate(
        {
            **candidate.model_dump(mode="python"),
            "logical_fingerprint": corporate_action_observation_fingerprint(candidate),
        }
    )


def build_corporate_action_reconciliation_report(
    **values: Any,
) -> ChinaAshareCorporateActionReconciliationReportV1:
    candidate = ChinaAshareCorporateActionReconciliationReportV1.model_construct(
        **values,
        logical_fingerprint="0" * 64,
    )
    return ChinaAshareCorporateActionReconciliationReportV1.model_validate(
        {
            **candidate.model_dump(mode="python"),
            "logical_fingerprint": corporate_action_reconciliation_report_fingerprint(
                candidate
            ),
        }
    )


def build_corporate_action_package_manifest(
    **values: Any,
) -> ChinaAshareCorporateActionPackageManifestV1:
    candidate = ChinaAshareCorporateActionPackageManifestV1.model_construct(
        **values,
        logical_fingerprint="0" * 64,
    )
    return ChinaAshareCorporateActionPackageManifestV1.model_validate(
        {
            **candidate.model_dump(mode="python"),
            "logical_fingerprint": corporate_action_package_manifest_fingerprint(
                candidate
            ),
        }
    )


def corporate_action_observation_fingerprint(
    value: ChinaAshareCorporateActionObservationV1,
) -> str:
    return _fingerprint(value.model_dump(mode="json", exclude={"logical_fingerprint"}))


def corporate_action_reconciliation_report_fingerprint(
    value: ChinaAshareCorporateActionReconciliationReportV1,
) -> str:
    return _fingerprint(value.model_dump(mode="json", exclude={"logical_fingerprint"}))


def corporate_action_package_manifest_fingerprint(
    value: ChinaAshareCorporateActionPackageManifestV1,
) -> str:
    return _fingerprint(value.model_dump(mode="json", exclude={"logical_fingerprint"}))


def _distribution_type(
    *, cash: bool, bonus: bool, capitalization: bool, rights: bool
) -> ChinaAshareDistributionActionType:
    if sum((cash, bonus, capitalization, rights)) > 1:
        return ChinaAshareDistributionActionType.COMPOSITE_DISTRIBUTION
    if cash:
        return ChinaAshareDistributionActionType.CASH_DIVIDEND
    if bonus:
        return ChinaAshareDistributionActionType.STOCK_DIVIDEND
    if capitalization:
        return ChinaAshareDistributionActionType.CAPITALIZATION
    return ChinaAshareDistributionActionType.RIGHTS_ISSUE


def _reason_codes(value: Any) -> tuple[str, ...]:
    if not isinstance(value, (tuple, list, set, frozenset)):
        raise ValueError("reason_codes must be an ordered collection")
    normalized = tuple(sorted({str(item).strip().lower() for item in value}))
    if any(not _REASON_CODE.fullmatch(item) for item in normalized):
        raise ValueError("reason_codes must be canonical snake_case")
    return normalized


def _sha(value: str, field_name: str) -> str:
    normalized = normalize_required_string(value, field_name=field_name).lower()
    if not _SHA256.fullmatch(normalized):
        raise ValueError(f"{field_name} must be a lowercase SHA-256")
    return normalized


def _fingerprint(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
    ).hexdigest()
