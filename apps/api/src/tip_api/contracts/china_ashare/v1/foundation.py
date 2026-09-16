"""Isolated China A-share contracts for multi-session daily research.

These contracts model source observations and research admission.  They do not
write canonical data, grant performance authority, or make A-share records
visible to the U.S.-equity product surface.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
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


MARKET_ID = "china_a_share"
CHINA_ASHARE_INITIAL_UNIVERSE_ID = "china-a-share-common-stock-research-v1"
ADMISSION_CONTRACT_VERSION = "china-ashare-daily-research-admission/1.0"
_SHA256 = r"^[0-9a-f]{64}$"
_SOURCE_CODE = re.compile(r"^[0-9]{6}$")
_SOURCE_SECURITY_ID = re.compile(r"^(?:sh|sz|bj)\.[0-9]{6}$")
_REASON_CODE = re.compile(r"^[a-z][a-z0-9_]*$")


class ChinaAshareExchange(StrEnum):
    SSE = "SSE"
    SZSE = "SZSE"
    BSE = "BSE"


class ChinaAshareBoard(StrEnum):
    SSE_MAIN = "sse_main"
    STAR = "star"
    SZSE_MAIN = "szse_main"
    CHINEXT = "chinext"
    BSE = "bse"
    CDR = "cdr"
    UNKNOWN = "unknown"


class ChinaAshareSecurityForm(StrEnum):
    COMMON_STOCK = "common_stock"
    CDR = "cdr"
    UNKNOWN = "unknown"


class ChinaAshareListingStatus(StrEnum):
    LISTED = "listed"
    DELISTED = "delisted"
    PAUSED_LISTING = "paused_listing"
    APPROVED_NOT_TRADING = "approved_not_trading"
    UNLISTED = "unlisted"
    UNKNOWN = "unknown"


class ChinaAshareIdentityResolutionStatus(StrEnum):
    RESOLVED = "resolved"
    UNRESOLVED = "unresolved"
    QUARANTINED = "quarantined"


class ChinaAshareLifecycleEventType(StrEnum):
    TERMINATED_LISTING = "terminated_listing"
    PAUSED_OR_TERMINATED_LISTING = "paused_or_terminated_listing"


class ChinaAshareLifecycleSubjectKind(StrEnum):
    ISSUER_CODE = "issuer_code"
    SECURITY_CODE = "security_code"


class ChinaAshareTradingStatus(StrEnum):
    TRADING = "trading"
    SUSPENDED = "suspended"
    RESUMED = "resumed"
    NOT_LISTED = "not_listed"
    UNKNOWN = "unknown"


class ChinaAshareRiskWarningStatus(StrEnum):
    NONE = "none"
    PRESENT_UNSPECIFIED = "present_unspecified"
    OTHER_RISK_WARNING = "other_risk_warning"
    DELISTING_RISK_WARNING = "delisting_risk_warning"
    COMBINED_RISK_WARNING = "combined_risk_warning"
    DELISTING_PERIOD = "delisting_period"
    UNKNOWN = "unknown"


class ChinaAsharePriceLimitRegime(StrEnum):
    NO_DAILY_LIMIT = "no_daily_limit"
    PERCENT_10 = "percent_10"
    PERCENT_20 = "percent_20"
    PERCENT_30 = "percent_30"
    SOURCE_OBSERVED_OTHER = "source_observed_other"
    UNKNOWN = "unknown"


class ChinaAshareUniverseDisposition(StrEnum):
    INCLUDED = "included"
    EXCLUDED = "excluded"
    QUARANTINED = "quarantined"


class ChinaAshareFoundationFamily(StrEnum):
    INSTRUMENT_IDENTITY = "instrument_identity"
    TRADING_CALENDAR = "trading_calendar"
    RAW_EOD_PRICE = "raw_eod_price"
    DAILY_PRICE_LIMIT = "daily_price_limit"
    SUSPENSION_STATE = "suspension_state"
    RISK_WARNING_STATE = "risk_warning_state"
    ADJUSTMENT_FACTOR = "adjustment_factor"
    CORPORATE_ACTION = "corporate_action"
    INSTRUMENT_LIFECYCLE = "instrument_lifecycle"
    DAILY_UNIVERSE_MEMBERSHIP = "daily_universe_membership"
    TRADING_RULE_SCHEDULE = "trading_rule_schedule"
    FEE_SCHEDULE = "fee_schedule"
    HISTORICAL_COVERAGE = "historical_coverage"


CHINA_ASHARE_FOUNDATION_FAMILY_ORDER = tuple(ChinaAshareFoundationFamily)
CHINA_ASHARE_DAILY_REQUIRED_FAMILIES = frozenset(
    CHINA_ASHARE_FOUNDATION_FAMILY_ORDER
)


class ChinaAshareFoundationCoverageStatus(StrEnum):
    ABSENT = "absent"
    PILOT_ONLY = "pilot_only"
    PARTIAL = "partial"
    COMPLETE = "complete"


class ChinaAshareFoundationEvidenceTier(StrEnum):
    MISSING = "missing"
    SOURCE_OBSERVATION = "source_observation"
    RECONSTRUCTED_POINT_IN_TIME = "reconstructed_point_in_time"
    AS_OPERATED = "as_operated"
    RECONCILED = "reconciled"
    MIXED = "mixed"


class ChinaAshareResearchAdmissionStatus(StrEnum):
    SOURCE_INCOMPLETE = "source_incomplete"
    QUARANTINED = "quarantined"
    RESEARCH_BACKTEST_READY = "research_backtest_ready"


class FrozenContract(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class ChinaAshareInstrumentSourceObservationV1(FrozenContract):
    """One normalized source observation before canonical identity publication."""

    schema_version: Literal["1.0"] = "1.0"
    market_id: Literal["china_a_share"] = MARKET_ID
    source_security_id: str
    source_code: str
    display_ticker: str
    name: str
    exchange: ChinaAshareExchange
    board: ChinaAshareBoard
    security_form: ChinaAshareSecurityForm
    listing_status: ChinaAshareListingStatus
    list_date: date | None = None
    delist_date: date | None = None
    as_of_date: date
    instrument_id: UUID | None = None
    resolution_status: ChinaAshareIdentityResolutionStatus
    source: str
    source_available_at: datetime | None = None
    ingested_at: datetime
    quality_status: QualityStatus
    reason_codes: tuple[str, ...] = ()

    @field_validator("list_date", "delist_date", "as_of_date", mode="before")
    @classmethod
    def dates_are_dates(cls, value: Any) -> Any:
        if isinstance(value, datetime):
            raise ValueError("A-share identity date fields must not receive datetime values")
        return value

    @field_validator("source_code", mode="before")
    @classmethod
    def code_is_six_digits(cls, value: str) -> str:
        normalized = normalize_required_string(value, field_name="source_code")
        if not _SOURCE_CODE.fullmatch(normalized):
            raise ValueError("source_code must contain exactly six digits")
        return normalized

    @field_validator("source_security_id", "name", "source", mode="before")
    @classmethod
    def required_text(cls, value: str, info: Any) -> str:
        return normalize_required_string(value, field_name=info.field_name)

    @field_validator("display_ticker", mode="before")
    @classmethod
    def ticker_is_upper(cls, value: str) -> str:
        return normalize_required_string(
            value,
            field_name="display_ticker",
            uppercase=True,
        )

    @field_validator("source_available_at", "ingested_at")
    @classmethod
    def times_are_utc(cls, value: datetime | None) -> datetime | None:
        return None if value is None else normalize_utc_datetime(value)

    @field_validator("reason_codes", mode="before")
    @classmethod
    def reasons_are_canonical(cls, value: Any) -> tuple[str, ...]:
        return _normalize_reason_codes(value)

    @model_validator(mode="after")
    def identity_reconciles(self) -> "ChinaAshareInstrumentSourceObservationV1":
        permitted_boards = {
            ChinaAshareExchange.SSE: {
                ChinaAshareBoard.SSE_MAIN,
                ChinaAshareBoard.STAR,
                ChinaAshareBoard.CDR,
                ChinaAshareBoard.UNKNOWN,
            },
            ChinaAshareExchange.SZSE: {
                ChinaAshareBoard.SZSE_MAIN,
                ChinaAshareBoard.CHINEXT,
                ChinaAshareBoard.CDR,
                ChinaAshareBoard.UNKNOWN,
            },
            ChinaAshareExchange.BSE: {
                ChinaAshareBoard.BSE,
                ChinaAshareBoard.UNKNOWN,
            },
        }
        if self.board not in permitted_boards[self.exchange]:
            raise ValueError("board is incompatible with exchange")
        suffix = {
            ChinaAshareExchange.SSE: "SH",
            ChinaAshareExchange.SZSE: "SZ",
            ChinaAshareExchange.BSE: "BJ",
        }[self.exchange]
        if self.display_ticker != f"{self.source_code}.{suffix}":
            raise ValueError("display_ticker differs from source code and exchange")
        if self.security_form is ChinaAshareSecurityForm.CDR and self.board is not ChinaAshareBoard.CDR:
            raise ValueError("CDR security form requires the CDR board state")
        if self.board is ChinaAshareBoard.CDR and self.security_form is not ChinaAshareSecurityForm.CDR:
            raise ValueError("CDR board state requires CDR security form")
        if self.list_date is not None and self.delist_date is not None and self.delist_date < self.list_date:
            raise ValueError("delist_date must not precede list_date")
        if self.listing_status is ChinaAshareListingStatus.DELISTED and self.delist_date is None:
            raise ValueError("delisted observations require delist_date")
        if self.resolution_status is ChinaAshareIdentityResolutionStatus.RESOLVED:
            if self.instrument_id is None:
                raise ValueError("resolved identity requires instrument_id")
            if self.board is ChinaAshareBoard.UNKNOWN:
                raise ValueError("resolved identity requires source-proven board")
            if self.security_form is ChinaAshareSecurityForm.UNKNOWN:
                raise ValueError("resolved identity requires source-proven security form")
            if self.quality_status in {QualityStatus.REJECTED, QualityStatus.PENDING_REVIEW}:
                raise ValueError("resolved identity cannot have unresolved quality")
        else:
            if self.instrument_id is not None:
                raise ValueError("unresolved identity must not carry instrument_id")
            if not self.reason_codes:
                raise ValueError("unresolved identity requires reason codes")
        if self.source_available_at is not None and self.source_available_at > self.ingested_at:
            raise ValueError("source availability cannot follow ingestion")
        return self


class ChinaAshareSourceSecuritySnapshotStateV1(FrozenContract):
    """Provider-keyed trading state before a stable identity is established."""

    schema_version: Literal["1.0"] = "1.0"
    market_id: Literal["china_a_share"] = MARKET_ID
    source_security_id: str
    session_date: date
    trading_status: ChinaAshareTradingStatus
    source: str
    source_available_at: datetime | None = None
    ingested_at: datetime
    quality_status: QualityStatus
    reason_codes: tuple[str, ...] = ()

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

    @field_validator("session_date", mode="before")
    @classmethod
    def session_is_date(cls, value: Any) -> Any:
        if isinstance(value, datetime):
            raise ValueError("session_date must not receive a datetime")
        return value

    @field_validator("source", mode="before")
    @classmethod
    def source_is_present(cls, value: str) -> str:
        return normalize_required_string(value, field_name="source")

    @field_validator("source_available_at", "ingested_at")
    @classmethod
    def times_are_utc(cls, value: datetime | None) -> datetime | None:
        return None if value is None else normalize_utc_datetime(value)

    @field_validator("reason_codes", mode="before")
    @classmethod
    def reasons_are_canonical(cls, value: Any) -> tuple[str, ...]:
        return _normalize_reason_codes(value)

    @model_validator(mode="after")
    def source_state_reconciles(self) -> "ChinaAshareSourceSecuritySnapshotStateV1":
        if self.trading_status is ChinaAshareTradingStatus.UNKNOWN and not self.reason_codes:
            raise ValueError("unknown source trading state requires reason codes")
        if self.source_available_at is not None and self.source_available_at > self.ingested_at:
            raise ValueError("source availability cannot follow ingestion")
        return self


class ChinaAshareLifecycleSourceObservationV1(FrozenContract):
    """Source-keyed lifecycle evidence before stable-identity adjudication."""

    schema_version: Literal["1.0"] = "1.0"
    market_id: Literal["china_a_share"] = MARKET_ID
    source_subject_key: str
    source_subject_code: str
    subject_kind: ChinaAshareLifecycleSubjectKind
    source_security_id: str | None = None
    display_ticker: str | None = None
    source_row_sequence: int = Field(ge=1)
    name: str
    exchange: ChinaAshareExchange
    event_type: ChinaAshareLifecycleEventType
    list_date: date | None = None
    event_date: date
    as_of_date: date
    source: str
    source_available_at: datetime | None = None
    ingested_at: datetime
    quality_status: QualityStatus
    reason_codes: tuple[str, ...] = ()

    @field_validator("source_subject_key", mode="before")
    @classmethod
    def subject_key_is_canonical(cls, value: str) -> str:
        normalized = normalize_required_string(
            value,
            field_name="source_subject_key",
        ).lower()
        if not re.fullmatch(
            r"(?:sse_issuer|sse_security|szse_security|bse_security)\.[0-9]{6}",
            normalized,
        ):
            raise ValueError("source_subject_key is invalid")
        return normalized

    @field_validator("source_subject_code", mode="before")
    @classmethod
    def code_is_six_digits(cls, value: str) -> str:
        normalized = normalize_required_string(value, field_name="source_subject_code")
        if not _SOURCE_CODE.fullmatch(normalized):
            raise ValueError("source_subject_code must contain exactly six digits")
        return normalized

    @field_validator("source_security_id", mode="before")
    @classmethod
    def optional_source_id_is_canonical(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = normalize_required_string(
            value,
            field_name="source_security_id",
        ).lower()
        if not _SOURCE_SECURITY_ID.fullmatch(normalized):
            raise ValueError("source_security_id must use sh|sz|bj plus six digits")
        return normalized

    @field_validator("display_ticker", mode="before")
    @classmethod
    def optional_ticker_is_upper(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return normalize_required_string(value, field_name="display_ticker", uppercase=True)

    @field_validator("name", "source", mode="before")
    @classmethod
    def required_text(cls, value: str, info: Any) -> str:
        return normalize_required_string(value, field_name=info.field_name)

    @field_validator("list_date", "event_date", "as_of_date", mode="before")
    @classmethod
    def dates_are_dates(cls, value: Any) -> Any:
        if isinstance(value, datetime):
            raise ValueError("lifecycle date fields must not receive datetime values")
        return value

    @field_validator("source_available_at", "ingested_at")
    @classmethod
    def times_are_utc(cls, value: datetime | None) -> datetime | None:
        return None if value is None else normalize_utc_datetime(value)

    @field_validator("reason_codes", mode="before")
    @classmethod
    def reasons_are_canonical(cls, value: Any) -> tuple[str, ...]:
        return _normalize_reason_codes(value)

    @model_validator(mode="after")
    def lifecycle_reconciles(self) -> "ChinaAshareLifecycleSourceObservationV1":
        subject_prefix = {
            (ChinaAshareExchange.SSE, ChinaAshareLifecycleSubjectKind.ISSUER_CODE): (
                "sse_issuer"
            ),
            (ChinaAshareExchange.SSE, ChinaAshareLifecycleSubjectKind.SECURITY_CODE): (
                "sse_security"
            ),
            (ChinaAshareExchange.SZSE, ChinaAshareLifecycleSubjectKind.SECURITY_CODE): (
                "szse_security"
            ),
            (ChinaAshareExchange.BSE, ChinaAshareLifecycleSubjectKind.SECURITY_CODE): (
                "bse_security"
            ),
        }.get((self.exchange, self.subject_kind))
        if subject_prefix is None:
            raise ValueError("lifecycle subject kind is incompatible with exchange")
        if self.source_subject_key != f"{subject_prefix}.{self.source_subject_code}":
            raise ValueError("source subject key differs from exchange, kind, and code")
        if self.subject_kind is ChinaAshareLifecycleSubjectKind.ISSUER_CODE:
            if self.source_security_id is not None or self.display_ticker is not None:
                raise ValueError("issuer lifecycle evidence cannot claim security identity")
            if "issuer_security_identity_unproven" not in self.reason_codes:
                raise ValueError("issuer lifecycle evidence requires identity warning")
        else:
            prefix, suffix = {
                ChinaAshareExchange.SSE: ("sh", "SH"),
                ChinaAshareExchange.SZSE: ("sz", "SZ"),
                ChinaAshareExchange.BSE: ("bj", "BJ"),
            }[self.exchange]
            if self.source_security_id != f"{prefix}.{self.source_subject_code}":
                raise ValueError("source security identifier differs from exchange and code")
            if self.display_ticker != f"{self.source_subject_code}.{suffix}":
                raise ValueError("display ticker differs from exchange and code")
        if self.list_date is not None and self.event_date < self.list_date:
            raise ValueError("lifecycle event cannot precede listing")
        if self.event_type is ChinaAshareLifecycleEventType.PAUSED_OR_TERMINATED_LISTING:
            if "source_status_conflates_pause_and_termination" not in self.reason_codes:
                raise ValueError("ambiguous lifecycle event requires ambiguity reason")
        if self.source_available_at is not None and self.source_available_at > self.ingested_at:
            raise ValueError("source availability cannot follow ingestion")
        return self


class ChinaAshareDailyBarV1(FrozenContract):
    """Normalized unadjusted A-share daily OHLCV observation."""

    schema_version: Literal["1.0"] = "1.0"
    market_id: Literal["china_a_share"] = MARKET_ID
    instrument_id: UUID
    session_date: date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    pre_close: Decimal
    volume_shares: Decimal
    turnover_amount_cny: Decimal
    adjustment_basis: Literal["unadjusted"] = "unadjusted"
    source: str
    source_record_id: str | None = None
    source_available_at: datetime | None = None
    ingested_at: datetime
    revision: int = Field(ge=1)
    quality_status: QualityStatus
    reason_codes: tuple[str, ...] = ()

    @field_validator("session_date", mode="before")
    @classmethod
    def session_is_date(cls, value: Any) -> Any:
        if isinstance(value, datetime):
            raise ValueError("session_date must not receive a datetime")
        return value

    @field_validator(
        "open",
        "high",
        "low",
        "close",
        "pre_close",
        "volume_shares",
        "turnover_amount_cny",
        mode="before",
    )
    @classmethod
    def decimals_are_exact(cls, value: Any, info: Any) -> Any:
        return reject_float_decimal_input(value, field_name=info.field_name)

    @field_validator(
        "open",
        "high",
        "low",
        "close",
        "pre_close",
        "volume_shares",
        "turnover_amount_cny",
    )
    @classmethod
    def decimals_are_finite(cls, value: Decimal, info: Any) -> Decimal:
        return ensure_finite_decimal(value, field_name=info.field_name)

    @field_validator("open", "high", "low", "close", "pre_close")
    @classmethod
    def prices_are_positive(cls, value: Decimal, info: Any) -> Decimal:
        if value <= 0:
            raise ValueError(f"{info.field_name} must be positive")
        return value

    @field_validator("volume_shares", "turnover_amount_cny")
    @classmethod
    def activity_is_non_negative(cls, value: Decimal, info: Any) -> Decimal:
        if value < 0:
            raise ValueError(f"{info.field_name} must be non-negative")
        return value

    @field_validator("source", mode="before")
    @classmethod
    def source_is_present(cls, value: str) -> str:
        return normalize_required_string(value, field_name="source")

    @field_validator("source_record_id", mode="before")
    @classmethod
    def source_record_is_optional(cls, value: str | None) -> str | None:
        return normalize_optional_string(value, field_name="source_record_id")

    @field_validator("source_available_at", "ingested_at")
    @classmethod
    def times_are_utc(cls, value: datetime | None) -> datetime | None:
        return None if value is None else normalize_utc_datetime(value)

    @field_validator("reason_codes", mode="before")
    @classmethod
    def reasons_are_canonical(cls, value: Any) -> tuple[str, ...]:
        return _normalize_reason_codes(value)

    @model_validator(mode="after")
    def bar_reconciles(self) -> "ChinaAshareDailyBarV1":
        if self.high < max(self.open, self.close, self.low):
            raise ValueError("high is inconsistent with OHLC")
        if self.low > min(self.open, self.close, self.high):
            raise ValueError("low is inconsistent with OHLC")
        if self.source_available_at is not None and self.source_available_at > self.ingested_at:
            raise ValueError("source availability cannot follow ingestion")
        return self


class ChinaAshareAdjustmentFactorObservationV1(FrozenContract):
    """Provider adjustment observation without assuming return semantics."""

    schema_version: Literal["1.0"] = "1.0"
    market_id: Literal["china_a_share"] = MARKET_ID
    instrument_id: UUID
    session_date: date
    provider_factor: Decimal
    provider_semantics: str
    source: str
    source_available_at: datetime | None = None
    ingested_at: datetime
    normalized_return_authorized: Literal[False] = False
    quality_status: QualityStatus
    reason_codes: tuple[str, ...] = ()

    @field_validator("session_date", mode="before")
    @classmethod
    def session_is_date(cls, value: Any) -> Any:
        if isinstance(value, datetime):
            raise ValueError("session_date must not receive a datetime")
        return value

    @field_validator("provider_factor", mode="before")
    @classmethod
    def factor_is_exact(cls, value: Any) -> Any:
        return reject_float_decimal_input(value, field_name="provider_factor")

    @field_validator("provider_factor")
    @classmethod
    def factor_is_positive(cls, value: Decimal) -> Decimal:
        value = ensure_finite_decimal(value, field_name="provider_factor")
        if value <= 0:
            raise ValueError("provider_factor must be positive")
        return value

    @field_validator("provider_semantics", "source", mode="before")
    @classmethod
    def required_text(cls, value: str, info: Any) -> str:
        return normalize_required_string(value, field_name=info.field_name)

    @field_validator("source_available_at", "ingested_at")
    @classmethod
    def times_are_utc(cls, value: datetime | None) -> datetime | None:
        return None if value is None else normalize_utc_datetime(value)

    @field_validator("reason_codes", mode="before")
    @classmethod
    def reasons_are_canonical(cls, value: Any) -> tuple[str, ...]:
        return _normalize_reason_codes(value)

    @model_validator(mode="after")
    def availability_reconciles(self) -> "ChinaAshareAdjustmentFactorObservationV1":
        if self.source_available_at is not None and self.source_available_at > self.ingested_at:
            raise ValueError("source availability cannot follow ingestion")
        return self


class ChinaAshareDailyTradingStateV1(FrozenContract):
    """Daily tradability state kept separate from prices and ticker names."""

    schema_version: Literal["1.0"] = "1.0"
    market_id: Literal["china_a_share"] = MARKET_ID
    instrument_id: UUID
    session_date: date
    exchange: ChinaAshareExchange
    board: ChinaAshareBoard
    trading_status: ChinaAshareTradingStatus
    risk_warning_status: ChinaAshareRiskWarningStatus
    price_limit_regime: ChinaAsharePriceLimitRegime
    pre_close: Decimal | None = None
    up_limit: Decimal | None = None
    down_limit: Decimal | None = None
    exact_limit_prices_source_observed: bool
    source: str
    source_available_at: datetime | None = None
    ingested_at: datetime
    quality_status: QualityStatus
    reason_codes: tuple[str, ...] = ()

    @field_validator("session_date", mode="before")
    @classmethod
    def session_is_date(cls, value: Any) -> Any:
        if isinstance(value, datetime):
            raise ValueError("session_date must not receive a datetime")
        return value

    @field_validator("pre_close", "up_limit", "down_limit", mode="before")
    @classmethod
    def decimals_are_exact(cls, value: Any, info: Any) -> Any:
        if value is None:
            return None
        return reject_float_decimal_input(value, field_name=info.field_name)

    @field_validator("pre_close", "up_limit", "down_limit")
    @classmethod
    def prices_are_positive(cls, value: Decimal | None, info: Any) -> Decimal | None:
        if value is None:
            return None
        value = ensure_finite_decimal(value, field_name=info.field_name)
        if value <= 0:
            raise ValueError(f"{info.field_name} must be positive")
        return value

    @field_validator("source", mode="before")
    @classmethod
    def source_is_present(cls, value: str) -> str:
        return normalize_required_string(value, field_name="source")

    @field_validator("source_available_at", "ingested_at")
    @classmethod
    def times_are_utc(cls, value: datetime | None) -> datetime | None:
        return None if value is None else normalize_utc_datetime(value)

    @field_validator("reason_codes", mode="before")
    @classmethod
    def reasons_are_canonical(cls, value: Any) -> tuple[str, ...]:
        return _normalize_reason_codes(value)

    @model_validator(mode="after")
    def state_reconciles(self) -> "ChinaAshareDailyTradingStateV1":
        permitted_boards = {
            ChinaAshareExchange.SSE: {
                ChinaAshareBoard.SSE_MAIN,
                ChinaAshareBoard.STAR,
                ChinaAshareBoard.CDR,
                ChinaAshareBoard.UNKNOWN,
            },
            ChinaAshareExchange.SZSE: {
                ChinaAshareBoard.SZSE_MAIN,
                ChinaAshareBoard.CHINEXT,
                ChinaAshareBoard.CDR,
                ChinaAshareBoard.UNKNOWN,
            },
            ChinaAshareExchange.BSE: {
                ChinaAshareBoard.BSE,
                ChinaAshareBoard.UNKNOWN,
            },
        }
        if self.board not in permitted_boards[self.exchange]:
            raise ValueError("board is incompatible with exchange")
        limits = (self.pre_close, self.up_limit, self.down_limit)
        if self.exact_limit_prices_source_observed:
            if any(value is None for value in limits):
                raise ValueError("observed limit prices require pre_close and both limits")
            assert self.up_limit is not None and self.down_limit is not None
            if self.up_limit <= self.down_limit:
                raise ValueError("up_limit must exceed down_limit")
            if self.price_limit_regime in {
                ChinaAsharePriceLimitRegime.NO_DAILY_LIMIT,
                ChinaAsharePriceLimitRegime.UNKNOWN,
            }:
                raise ValueError("observed limit prices require a bounded limit regime")
        elif any(value is not None for value in (self.up_limit, self.down_limit)):
            raise ValueError("unobserved exact limits must remain null")
        if self.price_limit_regime is ChinaAsharePriceLimitRegime.NO_DAILY_LIMIT and any(
            value is not None for value in (self.up_limit, self.down_limit)
        ):
            raise ValueError("no-limit session must not carry daily limit prices")
        if (
            self.trading_status is ChinaAshareTradingStatus.UNKNOWN
            or self.risk_warning_status is ChinaAshareRiskWarningStatus.UNKNOWN
            or self.price_limit_regime is ChinaAsharePriceLimitRegime.UNKNOWN
        ) and not self.reason_codes:
            raise ValueError("unknown trading state requires reason codes")
        if self.source_available_at is not None and self.source_available_at > self.ingested_at:
            raise ValueError("source availability cannot follow ingestion")
        return self


class ChinaAshareTradingRuleV1(FrozenContract):
    """Effective-dated trading-rule evidence; rules are data, not constants."""

    schema_version: Literal["1.0"] = "1.0"
    market_id: Literal["china_a_share"] = MARKET_ID
    rule_id: str
    exchange: ChinaAshareExchange
    board: ChinaAshareBoard
    risk_warning_status: ChinaAshareRiskWarningStatus
    effective_from: date
    effective_to: date | None = None
    settlement_rule: Literal["t_plus_one"] = "t_plus_one"
    daily_price_limit_ratio: Decimal | None = None
    ipo_no_limit_session_count: int = Field(ge=0)
    minimum_buy_order_shares: int = Field(ge=1)
    order_increment_shares: int = Field(ge=1)
    official_source_url: str
    source_available_at: datetime
    ingested_at: datetime
    quality_status: QualityStatus

    @field_validator("effective_from", "effective_to", mode="before")
    @classmethod
    def dates_are_dates(cls, value: Any) -> Any:
        if isinstance(value, datetime):
            raise ValueError("rule effective fields must contain dates")
        return value

    @field_validator("daily_price_limit_ratio", mode="before")
    @classmethod
    def ratio_is_exact(cls, value: Any) -> Any:
        if value is None:
            return None
        return reject_float_decimal_input(value, field_name="daily_price_limit_ratio")

    @field_validator("daily_price_limit_ratio")
    @classmethod
    def ratio_is_bounded(cls, value: Decimal | None) -> Decimal | None:
        if value is None:
            return None
        value = ensure_finite_decimal(value, field_name="daily_price_limit_ratio")
        if value <= 0 or value > 1:
            raise ValueError("daily_price_limit_ratio must be in (0, 1]")
        return value

    @field_validator("rule_id", "official_source_url", mode="before")
    @classmethod
    def required_text(cls, value: str, info: Any) -> str:
        return normalize_required_string(value, field_name=info.field_name)

    @field_validator("source_available_at", "ingested_at")
    @classmethod
    def times_are_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @model_validator(mode="after")
    def rule_reconciles(self) -> "ChinaAshareTradingRuleV1":
        if self.effective_to is not None and self.effective_to < self.effective_from:
            raise ValueError("effective_to must not precede effective_from")
        if self.source_available_at > self.ingested_at:
            raise ValueError("source availability cannot follow ingestion")
        return self


class ChinaAshareUniverseDecisionV1(FrozenContract):
    """One explicit point-in-time research-Universe decision."""

    schema_version: Literal["1.0"] = "1.0"
    market_id: Literal["china_a_share"] = MARKET_ID
    universe_id: Literal["china-a-share-common-stock-research-v1"] = (
        CHINA_ASHARE_INITIAL_UNIVERSE_ID
    )
    instrument_id: UUID
    session_date: date
    methodology_version: str
    disposition: ChinaAshareUniverseDisposition
    reason_codes: tuple[str, ...] = Field(min_length=1)
    source_cutoff_at: datetime
    evaluated_at: datetime
    input_fingerprints: tuple[str, ...] = Field(min_length=1)
    performance_eligible: bool

    @field_validator("session_date", mode="before")
    @classmethod
    def session_is_date(cls, value: Any) -> Any:
        if isinstance(value, datetime):
            raise ValueError("session_date must not receive a datetime")
        return value

    @field_validator("methodology_version", mode="before")
    @classmethod
    def methodology_is_present(cls, value: str) -> str:
        return normalize_required_string(value, field_name="methodology_version")

    @field_validator("reason_codes", mode="before")
    @classmethod
    def reasons_are_canonical(cls, value: Any) -> tuple[str, ...]:
        return _normalize_reason_codes(value)

    @field_validator("input_fingerprints", mode="before")
    @classmethod
    def fingerprints_are_canonical(cls, value: Any) -> tuple[str, ...]:
        if not isinstance(value, (tuple, list)):
            raise ValueError("input_fingerprints must be an ordered collection")
        normalized = tuple(sorted(set(value)))
        if not normalized or any(not re.fullmatch(_SHA256, item) for item in normalized):
            raise ValueError("input_fingerprints must contain unique SHA-256 values")
        return normalized

    @field_validator("source_cutoff_at", "evaluated_at")
    @classmethod
    def times_are_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @model_validator(mode="after")
    def decision_reconciles(self) -> "ChinaAshareUniverseDecisionV1":
        if self.evaluated_at < self.source_cutoff_at:
            raise ValueError("Universe evaluation cannot precede its source cutoff")
        if self.performance_eligible and self.disposition is not ChinaAshareUniverseDisposition.INCLUDED:
            raise ValueError("only included decisions may be performance eligible")
        return self


class ChinaAshareFoundationFamilyCensusV1(FrozenContract):
    family: ChinaAshareFoundationFamily
    required_for_daily_research: bool
    coverage_status: ChinaAshareFoundationCoverageStatus
    evidence_tier: ChinaAshareFoundationEvidenceTier
    target_session_count: int | None = Field(default=None, ge=1)
    covered_session_count: int | None = Field(default=None, ge=0)
    missing_session_count: int | None = Field(default=None, ge=0)
    record_count: int | None = Field(default=None, ge=0)
    quarantined_record_count: int | None = Field(default=None, ge=0)
    source_ids: tuple[str, ...] = ()
    reason_codes: tuple[str, ...] = Field(min_length=1)

    @field_validator("source_ids", mode="before")
    @classmethod
    def sources_are_canonical(cls, value: Any) -> tuple[str, ...]:
        return _normalize_required_collection(value, field_name="source_ids")

    @field_validator("reason_codes", mode="before")
    @classmethod
    def reasons_are_canonical(cls, value: Any) -> tuple[str, ...]:
        return _normalize_reason_codes(value)

    @model_validator(mode="after")
    def coverage_reconciles(self) -> "ChinaAshareFoundationFamilyCensusV1":
        counts = (
            self.target_session_count,
            self.covered_session_count,
            self.missing_session_count,
        )
        if any(value is not None for value in counts):
            if any(value is None for value in counts):
                raise ValueError("session coverage requires all three counts")
            assert self.target_session_count is not None
            assert self.covered_session_count is not None
            assert self.missing_session_count is not None
            if self.covered_session_count + self.missing_session_count != self.target_session_count:
                raise ValueError("family session counts do not reconcile")
        if self.quarantined_record_count is not None and self.record_count is not None:
            if self.quarantined_record_count > self.record_count:
                raise ValueError("quarantined count cannot exceed record count")
        if self.coverage_status is ChinaAshareFoundationCoverageStatus.ABSENT:
            if self.evidence_tier is not ChinaAshareFoundationEvidenceTier.MISSING:
                raise ValueError("absent family requires missing evidence tier")
            if self.record_count not in (None, 0):
                raise ValueError("absent family cannot have records")
        if self.coverage_status is ChinaAshareFoundationCoverageStatus.COMPLETE:
            if self.evidence_tier is ChinaAshareFoundationEvidenceTier.MISSING:
                raise ValueError("complete family cannot use missing evidence")
            if self.missing_session_count not in (None, 0):
                raise ValueError("complete family cannot have missing sessions")
        return self


class ChinaAshareDailyResearchAdmissionV1(FrozenContract):
    schema_version: Literal["1.0"] = "1.0"
    contract_version: Literal["china-ashare-daily-research-admission/1.0"] = (
        ADMISSION_CONTRACT_VERSION
    )
    market_id: Literal["china_a_share"] = MARKET_ID
    universe_id: Literal["china-a-share-common-stock-research-v1"] = (
        CHINA_ASHARE_INITIAL_UNIVERSE_ID
    )
    intended_use: Literal["multi_session_daily_factor_and_strategy_research"] = (
        "multi_session_daily_factor_and_strategy_research"
    )
    first_target_session: date
    last_target_session: date
    target_session_count: int = Field(ge=1)
    families: tuple[ChinaAshareFoundationFamilyCensusV1, ...] = Field(min_length=13)
    status: ChinaAshareResearchAdmissionStatus
    blocking_families: tuple[ChinaAshareFoundationFamily, ...]
    daily_research_backtest_authorized: bool
    intraday_execution_backtest_authorized: Literal[False] = False
    live_model_authorized: Literal[False] = False
    product_publication_authorized: Literal[False] = False
    production_write_count: Literal[0] = 0
    logical_fingerprint: str = Field(pattern=_SHA256)

    @field_validator("first_target_session", "last_target_session", mode="before")
    @classmethod
    def dates_are_dates(cls, value: Any) -> Any:
        if isinstance(value, datetime):
            raise ValueError("target session fields must contain dates")
        return value

    @model_validator(mode="after")
    def admission_reconciles(self) -> "ChinaAshareDailyResearchAdmissionV1":
        if self.last_target_session < self.first_target_session:
            raise ValueError("target interval is reversed")
        if tuple(item.family for item in self.families) != CHINA_ASHARE_FOUNDATION_FAMILY_ORDER:
            raise ValueError("A-share foundation family set is incomplete or unordered")
        for item in self.families:
            if item.required_for_daily_research != (item.family in CHINA_ASHARE_DAILY_REQUIRED_FAMILIES):
                raise ValueError("daily-research family policy differs")
        expected_blockers = tuple(
            item.family
            for item in self.families
            if item.required_for_daily_research
            and item.coverage_status is not ChinaAshareFoundationCoverageStatus.COMPLETE
        )
        if self.blocking_families != expected_blockers:
            raise ValueError("blocking families differ from coverage evidence")
        if self.daily_research_backtest_authorized != (not expected_blockers):
            raise ValueError("daily research authority differs from blockers")
        expected_status = (
            ChinaAshareResearchAdmissionStatus.RESEARCH_BACKTEST_READY
            if not expected_blockers
            else ChinaAshareResearchAdmissionStatus.QUARANTINED
            if any(
                item.quarantined_record_count
                for item in self.families
                if item.required_for_daily_research
            )
            else ChinaAshareResearchAdmissionStatus.SOURCE_INCOMPLETE
        )
        if self.status is not expected_status:
            raise ValueError("admission status differs from family evidence")
        if china_ashare_daily_research_admission_fingerprint(self) != self.logical_fingerprint:
            raise ValueError("A-share admission fingerprint differs")
        return self


def build_china_ashare_daily_research_admission(
    *,
    target_sessions: tuple[date, ...],
    families: tuple[ChinaAshareFoundationFamilyCensusV1, ...],
) -> ChinaAshareDailyResearchAdmissionV1:
    if not target_sessions or target_sessions != tuple(sorted(set(target_sessions))):
        raise ValueError("target_sessions must be non-empty, unique, and ordered")
    blockers = tuple(
        item.family
        for item in families
        if item.required_for_daily_research
        and item.coverage_status is not ChinaAshareFoundationCoverageStatus.COMPLETE
    )
    status = (
        ChinaAshareResearchAdmissionStatus.RESEARCH_BACKTEST_READY
        if not blockers
        else ChinaAshareResearchAdmissionStatus.QUARANTINED
        if any(
            item.quarantined_record_count
            for item in families
            if item.required_for_daily_research
        )
        else ChinaAshareResearchAdmissionStatus.SOURCE_INCOMPLETE
    )
    payload: dict[str, Any] = {
        "schema_version": "1.0",
        "contract_version": ADMISSION_CONTRACT_VERSION,
        "market_id": MARKET_ID,
        "universe_id": CHINA_ASHARE_INITIAL_UNIVERSE_ID,
        "intended_use": "multi_session_daily_factor_and_strategy_research",
        "first_target_session": target_sessions[0],
        "last_target_session": target_sessions[-1],
        "target_session_count": len(target_sessions),
        "families": families,
        "status": status,
        "blocking_families": blockers,
        "daily_research_backtest_authorized": not blockers,
        "intraday_execution_backtest_authorized": False,
        "live_model_authorized": False,
        "product_publication_authorized": False,
        "production_write_count": 0,
    }
    return ChinaAshareDailyResearchAdmissionV1(
        **payload,
        logical_fingerprint=china_ashare_daily_research_admission_fingerprint(payload),
    )


def china_ashare_daily_research_admission_fingerprint(
    value: ChinaAshareDailyResearchAdmissionV1 | dict[str, Any],
) -> str:
    payload = (
        value.model_dump(mode="json", exclude={"logical_fingerprint"})
        if isinstance(value, ChinaAshareDailyResearchAdmissionV1)
        else value
    )
    return hashlib.sha256(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            default=_json_default,
        ).encode("utf-8")
    ).hexdigest()


def _normalize_reason_codes(value: Any) -> tuple[str, ...]:
    normalized = _normalize_required_collection(value, field_name="reason_codes")
    if any(not _REASON_CODE.fullmatch(item) for item in normalized):
        raise ValueError("reason_codes must contain lower snake_case values")
    return normalized


def _normalize_required_collection(value: Any, *, field_name: str) -> tuple[str, ...]:
    if not isinstance(value, (tuple, list)):
        raise ValueError(f"{field_name} must be an ordered collection")
    normalized = tuple(
        sorted(
            {
                normalize_required_string(item, field_name=field_name)
                for item in value
            }
        )
    )
    return normalized


def _json_default(value: Any) -> Any:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, Decimal):
        return str(value)
    raise TypeError(f"unsupported fingerprint value: {type(value).__name__}")
