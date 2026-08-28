"""Provider-neutral point-in-time historical research contracts."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from pathlib import PurePosixPath
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from tip_api.contracts.common import (
    QualityStatus,
    ensure_finite_decimal,
    normalize_optional_string,
    normalize_required_string,
    normalize_utc_datetime,
    reject_float_decimal_input,
)
from tip_api.contracts.market_data.v1.provider_instrument_identity import ResolutionStatus


class KnowledgeTimeStatus(StrEnum):
    SOURCE_TIMESTAMP = "source_timestamp"
    FIRST_OBSERVED_ONLY = "first_observed_only"
    UNAVAILABLE = "unavailable"


class CorporateActionType(StrEnum):
    STOCK_SPLIT = "stock_split"
    REVERSE_SPLIT = "reverse_split"
    CASH_DIVIDEND = "cash_dividend"
    STOCK_DIVIDEND = "stock_dividend"
    SYMBOL_CHANGE = "symbol_change"
    MERGER = "merger"
    SPINOFF = "spinoff"
    DELISTING = "delisting"


class CorporateActionRecordStatus(StrEnum):
    ACTIVE = "active"
    CORRECTED = "corrected"
    CANCELLED = "cancelled"
    QUARANTINED = "quarantined"


class InstrumentLifecycleStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    DELISTED = "delisted"
    ACQUIRED = "acquired"
    MERGED = "merged"
    REORGANIZED = "reorganized"
    UNKNOWN = "unknown"


class LineageEvidenceStatus(StrEnum):
    AUTHORITATIVE = "authoritative"
    PROVIDER_EXPLICIT = "provider_explicit"
    REVIEWED = "reviewed"
    UNRESOLVED = "unresolved"


class UniverseMembershipDisposition(StrEnum):
    INCLUDED = "included"
    EXCLUDED = "excluded"
    QUARANTINED = "quarantined"


class UniverseMembershipOrigin(StrEnum):
    AS_OPERATED = "as_operated"
    RECONSTRUCTED_POINT_IN_TIME = "reconstructed_point_in_time"


class AdjustmentAvailabilityStatus(StrEnum):
    CLEAR = "clear"
    QUARANTINED = "quarantined"
    UNAVAILABLE = "unavailable"


class HistoricalDatasetFamily(StrEnum):
    EOD_PRICE_BAR = "eod_price_bar"
    POINT_IN_TIME_IDENTITY = "point_in_time_identity"
    UNIVERSE_MEMBERSHIP = "universe_membership"
    CORPORATE_ACTION = "corporate_action"
    INSTRUMENT_LIFECYCLE = "instrument_lifecycle"
    ADJUSTMENT_LEDGER = "adjustment_ledger"


class HistoricalReadinessStatus(StrEnum):
    MECHANICS_ONLY = "mechanics_only"
    SOURCE_INCOMPLETE = "source_incomplete"
    QUARANTINED = "quarantined"
    RESEARCH_READY = "research_ready"


class FrozenContract(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class CorporateActionSourceObservationV1(FrozenContract):
    """One source revision of a corporate-action event before canonical resolution."""

    schema_version: Literal["1.0"] = "1.0"
    provider: str
    source_action_id: str
    source_revision: int = Field(ge=1)
    supersedes_source_action_id: str | None = None
    record_status: CorporateActionRecordStatus
    action_type: CorporateActionType
    provider_ticker: str
    instrument_resolution_status: ResolutionStatus
    instrument_id: UUID | None = None
    announcement_date: date | None = None
    ex_date: date | None = None
    record_date: date | None = None
    pay_date: date | None = None
    effective_date: date
    split_ratio_from: Decimal | None = None
    split_ratio_to: Decimal | None = None
    cash_amount: Decimal | None = None
    currency: str | None = None
    new_ticker: str | None = None
    successor_instrument_id: UUID | None = None
    related_instrument_id: UUID | None = None
    termination_reason: str | None = None
    knowledge_time_status: KnowledgeTimeStatus
    source_available_at: datetime | None = None
    first_observed_at: datetime
    ingested_at: datetime
    quality_status: QualityStatus
    quality_flags: tuple[str, ...] = ()

    @field_validator(
        "announcement_date",
        "ex_date",
        "record_date",
        "pay_date",
        "effective_date",
        mode="before",
    )
    @classmethod
    def reject_datetime_dates(cls, value: Any) -> Any:
        if isinstance(value, datetime):
            raise ValueError("date fields must not receive datetime values")
        return value

    @field_validator("provider", "source_action_id", mode="before")
    @classmethod
    def required_text(cls, value: str, info: Any) -> str:
        return normalize_required_string(value, field_name=info.field_name)

    @field_validator("supersedes_source_action_id", "termination_reason", mode="before")
    @classmethod
    def optional_text(cls, value: str | None, info: Any) -> str | None:
        return normalize_optional_string(value, field_name=info.field_name)

    @field_validator("provider_ticker", "new_ticker", mode="before")
    @classmethod
    def ticker(cls, value: str | None, info: Any) -> str | None:
        if value is None:
            if info.field_name == "provider_ticker":
                raise ValueError("provider_ticker must not be null")
            return None
        return _ticker(value, info.field_name)

    @field_validator("currency", mode="before")
    @classmethod
    def currency_code(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = normalize_required_string(value, field_name="currency", uppercase=True)
        if len(normalized) != 3 or not normalized.isalpha():
            raise ValueError("currency must be an ISO alpha-3 code")
        return normalized

    @field_validator("split_ratio_from", "split_ratio_to", "cash_amount", mode="before")
    @classmethod
    def reject_float_decimals(cls, value: Any, info: Any) -> Any:
        return reject_float_decimal_input(value, field_name=info.field_name)

    @field_validator("split_ratio_from", "split_ratio_to", "cash_amount")
    @classmethod
    def positive_decimals(cls, value: Decimal | None, info: Any) -> Decimal | None:
        if value is None:
            return None
        value = ensure_finite_decimal(value, field_name=info.field_name)
        if value <= 0:
            raise ValueError(f"{info.field_name} must be positive")
        return value

    @field_validator("source_available_at", "first_observed_at", "ingested_at")
    @classmethod
    def utc(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        return normalize_utc_datetime(value)

    @field_validator("quality_flags", mode="before")
    @classmethod
    def flags(cls, value: Any) -> tuple[str, ...]:
        return _normalized_codes(value, "quality_flags")

    @model_validator(mode="after")
    def reconcile(self) -> "CorporateActionSourceObservationV1":
        if self.ingested_at < self.first_observed_at:
            raise ValueError("ingested_at must not precede first_observed_at")
        if self.knowledge_time_status is KnowledgeTimeStatus.SOURCE_TIMESTAMP:
            if self.source_available_at is None:
                raise ValueError("source timestamp knowledge requires source_available_at")
            if self.source_available_at > self.first_observed_at:
                raise ValueError("source_available_at must not follow first_observed_at")
        elif self.source_available_at is not None:
            raise ValueError("source_available_at requires source_timestamp knowledge")
        if self.instrument_resolution_status is ResolutionStatus.RESOLVED:
            if self.instrument_id is None:
                raise ValueError("resolved action observation requires instrument_id")
        elif self.instrument_id is not None:
            raise ValueError("unresolved action observation must not carry instrument_id")
        elif not self.quality_flags:
            raise ValueError("unresolved action observation requires quality_flags")
        split_types = {
            CorporateActionType.STOCK_SPLIT,
            CorporateActionType.REVERSE_SPLIT,
            CorporateActionType.STOCK_DIVIDEND,
        }
        has_split = self.split_ratio_from is not None or self.split_ratio_to is not None
        strict_action_fields = self.record_status is not CorporateActionRecordStatus.QUARANTINED
        if self.action_type in split_types:
            if strict_action_fields and (self.split_ratio_from is None or self.split_ratio_to is None):
                raise ValueError("split-like action requires both split ratios")
        elif has_split:
            raise ValueError("non-split action cannot carry split ratios")
        if self.action_type is CorporateActionType.CASH_DIVIDEND:
            if strict_action_fields and (
                self.cash_amount is None or self.currency is None or self.ex_date is None
            ):
                raise ValueError("cash dividend requires cash amount, currency, and ex_date")
        elif self.cash_amount is not None or self.currency is not None:
            raise ValueError("non-cash-dividend action cannot carry cash distribution fields")
        if (
            strict_action_fields
            and self.action_type is CorporateActionType.SYMBOL_CHANGE
            and self.new_ticker is None
        ):
            raise ValueError("symbol change requires new_ticker")
        if (
            strict_action_fields
            and self.action_type in {CorporateActionType.MERGER, CorporateActionType.SPINOFF}
            and not (self.successor_instrument_id or self.related_instrument_id)
        ):
            raise ValueError("merger or spinoff requires a supported related instrument")
        if (
            strict_action_fields
            and self.action_type is CorporateActionType.DELISTING
            and self.termination_reason is None
        ):
            raise ValueError("delisting requires termination_reason")
        if self.record_status in {
            CorporateActionRecordStatus.CORRECTED,
            CorporateActionRecordStatus.CANCELLED,
        } and self.supersedes_source_action_id is None:
            raise ValueError("corrected or cancelled action requires superseded source ID")
        if self.record_status is CorporateActionRecordStatus.QUARANTINED and not self.quality_flags:
            raise ValueError("quarantined action requires quality_flags")
        return self


class InstrumentLifecycleObservationV1(FrozenContract):
    """One effective-dated lifecycle or lineage observation for a stable instrument."""

    schema_version: Literal["1.0"] = "1.0"
    instrument_id: UUID
    as_of_date: date
    valid_from: date
    valid_to: date | None = None
    lifecycle_status: InstrumentLifecycleStatus
    ticker: str
    primary_exchange: str | None = None
    first_tradable_date: date | None = None
    last_tradable_date: date | None = None
    predecessor_instrument_id: UUID | None = None
    successor_instrument_id: UUID | None = None
    lineage_evidence_status: LineageEvidenceStatus
    terminal_cash_amount: Decimal | None = None
    terminal_currency: str | None = None
    source: str
    source_record_id: str
    source_revision: int = Field(ge=1)
    knowledge_time_status: KnowledgeTimeStatus
    source_available_at: datetime | None = None
    first_observed_at: datetime
    ingested_at: datetime
    quality_status: QualityStatus
    quality_flags: tuple[str, ...] = ()

    @field_validator("as_of_date", "valid_from", "valid_to", "first_tradable_date", "last_tradable_date", mode="before")
    @classmethod
    def reject_datetime_dates(cls, value: Any) -> Any:
        if isinstance(value, datetime):
            raise ValueError("date fields must not receive datetime values")
        return value

    @field_validator("ticker", mode="before")
    @classmethod
    def ticker_code(cls, value: str) -> str:
        return _ticker(value, "ticker")

    @field_validator("primary_exchange", "terminal_currency", mode="before")
    @classmethod
    def optional_code(cls, value: str | None, info: Any) -> str | None:
        if value is None:
            return None
        normalized = normalize_required_string(value, field_name=info.field_name, uppercase=True)
        if info.field_name == "terminal_currency" and (len(normalized) != 3 or not normalized.isalpha()):
            raise ValueError("terminal_currency must be an ISO alpha-3 code")
        return normalized

    @field_validator("source", "source_record_id", mode="before")
    @classmethod
    def required_text(cls, value: str, info: Any) -> str:
        return normalize_required_string(value, field_name=info.field_name)

    @field_validator("terminal_cash_amount", mode="before")
    @classmethod
    def reject_float_cash(cls, value: Any) -> Any:
        return reject_float_decimal_input(value, field_name="terminal_cash_amount")

    @field_validator("terminal_cash_amount")
    @classmethod
    def cash(cls, value: Decimal | None) -> Decimal | None:
        if value is None:
            return None
        value = ensure_finite_decimal(value, field_name="terminal_cash_amount")
        if value < 0:
            raise ValueError("terminal_cash_amount must be non-negative")
        return value

    @field_validator("source_available_at", "first_observed_at", "ingested_at")
    @classmethod
    def utc(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        return normalize_utc_datetime(value)

    @field_validator("quality_flags", mode="before")
    @classmethod
    def flags(cls, value: Any) -> tuple[str, ...]:
        return _normalized_codes(value, "quality_flags")

    @model_validator(mode="after")
    def reconcile(self) -> "InstrumentLifecycleObservationV1":
        if self.ingested_at < self.first_observed_at:
            raise ValueError("ingested_at must not precede first_observed_at")
        if self.valid_to is not None and self.valid_to <= self.valid_from:
            raise ValueError("valid_to must be later than valid_from")
        if not (self.valid_from <= self.as_of_date and (self.valid_to is None or self.as_of_date < self.valid_to)):
            raise ValueError("as_of_date must fall within lifecycle interval")
        if self.first_tradable_date and self.last_tradable_date and self.last_tradable_date < self.first_tradable_date:
            raise ValueError("last_tradable_date must not precede first_tradable_date")
        if self.instrument_id in {self.predecessor_instrument_id, self.successor_instrument_id}:
            raise ValueError("instrument cannot be its own predecessor or successor")
        if self.predecessor_instrument_id and self.predecessor_instrument_id == self.successor_instrument_id:
            raise ValueError("predecessor and successor must differ")
        if (self.terminal_cash_amount is None) != (self.terminal_currency is None):
            raise ValueError("terminal cash amount and currency must appear together")
        if self.knowledge_time_status is KnowledgeTimeStatus.SOURCE_TIMESTAMP:
            if self.source_available_at is None:
                raise ValueError("source timestamp knowledge requires source_available_at")
            if self.source_available_at > self.first_observed_at:
                raise ValueError("source_available_at must not follow first_observed_at")
        elif self.source_available_at is not None:
            raise ValueError("source_available_at requires source_timestamp knowledge")
        if self.lifecycle_status is InstrumentLifecycleStatus.UNKNOWN:
            if self.quality_status not in {QualityStatus.WARNING, QualityStatus.PENDING_REVIEW, QualityStatus.REJECTED}:
                raise ValueError("unknown lifecycle cannot be quality-valid")
            if not self.quality_flags:
                raise ValueError("unknown lifecycle requires quality_flags")
        if self.lineage_evidence_status is LineageEvidenceStatus.UNRESOLVED and not self.quality_flags:
            raise ValueError("unresolved lineage requires quality_flags")
        return self


class UniverseMembershipDecisionV1(FrozenContract):
    """One explicit included, excluded, or quarantined daily Universe decision."""

    schema_version: Literal["1.0"] = "1.0"
    universe_id: str
    instrument_id: UUID
    session_date: date
    methodology_version: str
    origin: UniverseMembershipOrigin
    disposition: UniverseMembershipDisposition
    is_member: bool | None
    reason_codes: tuple[str, ...]
    evaluated_base_fingerprint: str
    source_fingerprints: tuple[str, ...] = Field(min_length=1)
    source_data_cutoff: datetime
    evaluated_at: datetime
    quality_status: QualityStatus

    @field_validator("session_date", mode="before")
    @classmethod
    def reject_datetime_session(cls, value: Any) -> Any:
        if isinstance(value, datetime):
            raise ValueError("session_date must not receive a datetime")
        return value

    @field_validator("universe_id", "methodology_version", mode="before")
    @classmethod
    def required_text(cls, value: str, info: Any) -> str:
        return normalize_required_string(value, field_name=info.field_name)

    @field_validator("reason_codes", mode="before")
    @classmethod
    def reasons(cls, value: Any) -> tuple[str, ...]:
        return _normalized_codes(value, "reason_codes")

    @field_validator("evaluated_base_fingerprint")
    @classmethod
    def base_sha(cls, value: str) -> str:
        return _sha(value, "evaluated_base_fingerprint")

    @field_validator("source_fingerprints", mode="before")
    @classmethod
    def source_hashes(cls, value: Any) -> tuple[str, ...]:
        if not isinstance(value, (tuple, list)):
            raise ValueError("source_fingerprints must be an ordered collection")
        hashes = tuple(_sha(item, "source_fingerprints") for item in value)
        if len(hashes) != len(set(hashes)):
            raise ValueError("source_fingerprints must be unique")
        return hashes

    @field_validator("source_data_cutoff", "evaluated_at")
    @classmethod
    def utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @model_validator(mode="after")
    def reconcile(self) -> "UniverseMembershipDecisionV1":
        expected = {
            UniverseMembershipDisposition.INCLUDED: True,
            UniverseMembershipDisposition.EXCLUDED: False,
            UniverseMembershipDisposition.QUARANTINED: None,
        }[self.disposition]
        if self.is_member is not expected:
            raise ValueError("is_member must match three-state disposition")
        if not self.reason_codes:
            raise ValueError("membership decision requires reason_codes")
        if self.source_data_cutoff > self.evaluated_at:
            raise ValueError("source_data_cutoff must not follow evaluated_at")
        if self.disposition is UniverseMembershipDisposition.QUARANTINED and self.quality_status not in {
            QualityStatus.WARNING,
            QualityStatus.PENDING_REVIEW,
            QualityStatus.REJECTED,
        }:
            raise ValueError("quarantined membership cannot be quality-valid")
        return self


class AdjustmentLedgerEntryV1(FrozenContract):
    """One explicit adjustment projection from a raw session to a basis session."""

    schema_version: Literal["1.0"] = "1.0"
    instrument_id: UUID
    source_session: date
    basis_session: date
    factor_direction: Literal["multiply_raw_value_to_basis"] = "multiply_raw_value_to_basis"
    split_price_multiplier_to_basis: Decimal | None = None
    split_volume_multiplier_to_basis: Decimal | None = None
    split_adjustment_status: AdjustmentAvailabilityStatus
    total_return_multiplier_to_basis: Decimal | None = None
    total_return_adjustment_status: AdjustmentAvailabilityStatus
    source_action_set_fingerprint: str
    calculation_methodology_version: str
    source_data_cutoff: datetime
    calculated_at: datetime
    revision: int = Field(ge=1)
    quality_status: QualityStatus
    quality_flags: tuple[str, ...] = ()

    @field_validator("source_session", "basis_session", mode="before")
    @classmethod
    def reject_datetime_dates(cls, value: Any) -> Any:
        if isinstance(value, datetime):
            raise ValueError("session fields must not receive datetime values")
        return value

    @field_validator(
        "split_price_multiplier_to_basis",
        "split_volume_multiplier_to_basis",
        "total_return_multiplier_to_basis",
        mode="before",
    )
    @classmethod
    def reject_float_factors(cls, value: Any, info: Any) -> Any:
        return reject_float_decimal_input(value, field_name=info.field_name)

    @field_validator(
        "split_price_multiplier_to_basis",
        "split_volume_multiplier_to_basis",
        "total_return_multiplier_to_basis",
    )
    @classmethod
    def positive_factors(cls, value: Decimal | None, info: Any) -> Decimal | None:
        if value is None:
            return None
        value = ensure_finite_decimal(value, field_name=info.field_name)
        if value <= 0:
            raise ValueError(f"{info.field_name} must be positive")
        return value

    @field_validator("source_action_set_fingerprint")
    @classmethod
    def action_sha(cls, value: str) -> str:
        return _sha(value, "source_action_set_fingerprint")

    @field_validator("calculation_methodology_version", mode="before")
    @classmethod
    def methodology(cls, value: str) -> str:
        return normalize_required_string(value, field_name="calculation_methodology_version")

    @field_validator("source_data_cutoff", "calculated_at")
    @classmethod
    def utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @field_validator("quality_flags", mode="before")
    @classmethod
    def flags(cls, value: Any) -> tuple[str, ...]:
        return _normalized_codes(value, "quality_flags")

    @model_validator(mode="after")
    def reconcile(self) -> "AdjustmentLedgerEntryV1":
        if self.basis_session < self.source_session:
            raise ValueError("basis_session must not precede source_session")
        if self.source_data_cutoff > self.calculated_at:
            raise ValueError("source_data_cutoff must not follow calculated_at")
        split_factors = (
            self.split_price_multiplier_to_basis,
            self.split_volume_multiplier_to_basis,
        )
        if self.split_adjustment_status is AdjustmentAvailabilityStatus.CLEAR:
            if any(value is None for value in split_factors):
                raise ValueError("clear split adjustment requires price and volume multipliers")
        elif any(value is not None for value in split_factors):
            raise ValueError("non-clear split adjustment cannot carry multipliers")
        if self.total_return_adjustment_status is AdjustmentAvailabilityStatus.CLEAR:
            if self.total_return_multiplier_to_basis is None:
                raise ValueError("clear total-return adjustment requires a multiplier")
        elif self.total_return_multiplier_to_basis is not None:
            raise ValueError("non-clear total-return adjustment cannot carry a multiplier")
        non_clear = {
            self.split_adjustment_status,
            self.total_return_adjustment_status,
        } - {AdjustmentAvailabilityStatus.CLEAR}
        if non_clear and not self.quality_flags:
            raise ValueError("non-clear adjustment status requires quality_flags")
        if self.quality_status is QualityStatus.VALID and non_clear:
            raise ValueError("quality-valid adjustment cannot have non-clear status")
        return self


class HistoricalDatasetCoverageReferenceV1(FrozenContract):
    schema_version: Literal["1.0"] = "1.0"
    family: HistoricalDatasetFamily
    dataset_path: str
    record_count: int = Field(ge=0)
    first_session: date
    last_session: date
    logical_fingerprint: str
    physical_sha256: str
    completed: bool
    quarantined_record_count: int = Field(ge=0)

    @field_validator("dataset_path", mode="before")
    @classmethod
    def path(cls, value: str) -> str:
        normalized = normalize_required_string(value, field_name="dataset_path")
        path = PurePosixPath(normalized)
        if path.is_absolute() or ".." in path.parts or path.as_posix() != normalized:
            raise ValueError("dataset_path must be normalized and relative")
        return normalized

    @field_validator("first_session", "last_session", mode="before")
    @classmethod
    def reject_datetime_dates(cls, value: Any) -> Any:
        if isinstance(value, datetime):
            raise ValueError("session fields must not receive datetime values")
        return value

    @field_validator("logical_fingerprint", "physical_sha256")
    @classmethod
    def hashes(cls, value: str, info: Any) -> str:
        return _sha(value, info.field_name)

    @model_validator(mode="after")
    def reconcile(self) -> "HistoricalDatasetCoverageReferenceV1":
        if self.last_session < self.first_session:
            raise ValueError("last_session must not precede first_session")
        if self.quarantined_record_count > self.record_count:
            raise ValueError("quarantined count cannot exceed record count")
        return self


class HistoricalCoverageManifestV1(FrozenContract):
    """Bounded readiness statement over exact historical family fingerprints."""

    manifest_version: Literal["1.0"] = "1.0"
    coverage_id: str
    calendar_name: Literal["XNYS"] = "XNYS"
    sessions: tuple[date, ...] = Field(min_length=1)
    feature_warmup_sessions: int = Field(ge=0)
    maximum_outcome_horizon_sessions: int = Field(ge=1)
    matured_signal_session_count: int = Field(ge=0)
    datasets: tuple[HistoricalDatasetCoverageReferenceV1, ...]
    readiness_status: HistoricalReadinessStatus
    reason_codes: tuple[str, ...]
    created_at: datetime
    logical_fingerprint: str

    @field_validator("coverage_id", "logical_fingerprint")
    @classmethod
    def hashes(cls, value: str, info: Any) -> str:
        return _sha(value, info.field_name)

    @field_validator("sessions", mode="before")
    @classmethod
    def ordered_sessions(cls, value: Any) -> tuple[date, ...]:
        if not isinstance(value, (tuple, list)):
            raise ValueError("sessions must be an ordered collection")
        sessions = tuple(value)
        if any(isinstance(item, datetime) for item in sessions):
            raise ValueError("sessions must contain dates, not datetimes")
        if sessions != tuple(sorted(set(sessions))):
            raise ValueError("sessions must be unique and ordered")
        return sessions

    @field_validator("reason_codes", mode="before")
    @classmethod
    def reasons(cls, value: Any) -> tuple[str, ...]:
        return _normalized_codes(value, "reason_codes")

    @field_validator("created_at")
    @classmethod
    def utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @model_validator(mode="after")
    def reconcile(self) -> "HistoricalCoverageManifestV1":
        families = tuple(item.family for item in self.datasets)
        if len(families) != len(set(families)):
            raise ValueError("coverage dataset families must be unique")
        if self.matured_signal_session_count > len(self.sessions):
            raise ValueError("matured signal count cannot exceed session count")
        maximum_matured_count = max(
            0,
            len(self.sessions)
            - self.feature_warmup_sessions
            - self.maximum_outcome_horizon_sessions,
        )
        if self.matured_signal_session_count > maximum_matured_count:
            raise ValueError("matured signal count exceeds the bounded session window")
        required = set(HistoricalDatasetFamily)
        present = set(families)
        complete = {item.family for item in self.datasets if item.completed}
        if self.readiness_status is HistoricalReadinessStatus.RESEARCH_READY:
            if len(self.sessions) < 252:
                raise ValueError("research-ready manifest requires at least 252 sessions")
            if present != required or complete != required:
                raise ValueError("research-ready manifest requires every completed family")
            if any(
                item.first_session > self.sessions[0]
                or item.last_session < self.sessions[-1]
                for item in self.datasets
            ):
                raise ValueError("research-ready datasets must cover the manifest interval")
            if self.matured_signal_session_count == 0:
                raise ValueError("research-ready manifest requires mature signals")
            if self.reason_codes:
                raise ValueError("research-ready manifest cannot carry blocker reasons")
        elif not self.reason_codes:
            raise ValueError("non-ready manifest requires reason_codes")
        return self


def _ticker(value: str, field_name: str) -> str:
    normalized = normalize_required_string(value, field_name=field_name, uppercase=True)
    allowed = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-")
    if any(char not in allowed for char in normalized):
        raise ValueError(f"{field_name} contains unsupported characters")
    return normalized


def _normalized_codes(value: Any, field_name: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, (tuple, list, set, frozenset)):
        raise ValueError(f"{field_name} must be a collection")
    normalized = {
        normalize_required_string(item, field_name=field_name)
        .strip()
        .lower()
        .replace("-", "_")
        .replace(" ", "_")
        for item in value
    }
    return tuple(sorted(normalized))


def _sha(value: str, field_name: str) -> str:
    normalized = normalize_required_string(value, field_name=field_name).lower()
    if len(normalized) != 64 or any(char not in "0123456789abcdef" for char in normalized):
        raise ValueError(f"{field_name} must be a lowercase SHA-256 hex digest")
    return normalized
