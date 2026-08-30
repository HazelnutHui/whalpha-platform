"""Transparent Sector ETF Rotation V1 product contract."""

from __future__ import annotations

from datetime import date
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class SectorRotationAvailability(StrEnum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"


class SectorRotationPosture(StrEnum):
    LEADING_IMPROVING = "leading_improving"
    LEADING_WEAKENING = "leading_weakening"
    LAGGING_IMPROVING = "lagging_improving"
    LAGGING_WEAKENING = "lagging_weakening"
    NEUTRAL = "neutral"
    UNAVAILABLE = "unavailable"


class SectorRotationWindowV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    window_sessions: Literal[5, 10, 20]
    start_session: date | None
    end_session: date
    etf_return: str | None
    spy_return: str | None
    relative_return: str | None
    relative_rank: int | None = Field(default=None, ge=1)
    available_peer_count: int = Field(ge=0)
    availability: SectorRotationAvailability
    missing_reason: str | None

    @model_validator(mode="after")
    def availability_reconciles(self) -> "SectorRotationWindowV1":
        values = (self.start_session, self.etf_return, self.spy_return, self.relative_return)
        if self.availability is SectorRotationAvailability.AVAILABLE:
            if any(value is None for value in values) or self.missing_reason is not None:
                raise ValueError("available rotation window requires complete returns")
        elif any(value is not None for value in values) or self.relative_rank is not None:
            raise ValueError("unavailable rotation window cannot expose partial metrics")
        return self


class SectorRotationRecordV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    ticker: str
    sector: str
    registry_order: int = Field(ge=0)
    as_of_session: date
    windows: tuple[SectorRotationWindowV1, ...]
    five_day_relative_acceleration: str | None
    posture: SectorRotationPosture
    five_day_leadership_run_sessions: int = Field(ge=0)
    run_reaches_history_start: bool
    availability: SectorRotationAvailability
    missing_reason: str | None
    supporting_fact_codes: tuple[str, ...]
    counterevidence_codes: tuple[str, ...]
    warnings: tuple[str, ...]
    logical_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def record_reconciles(self) -> "SectorRotationRecordV1":
        if tuple(item.window_sessions for item in self.windows) != (5, 10, 20):
            raise ValueError("sector rotation windows must use fixed 5/10/20 order")
        if self.availability is SectorRotationAvailability.AVAILABLE:
            if self.posture is SectorRotationPosture.UNAVAILABLE or self.missing_reason is not None:
                raise ValueError("available sector rotation record is inconsistent")
        elif self.posture is not SectorRotationPosture.UNAVAILABLE or self.missing_reason is None:
            raise ValueError("unavailable sector rotation record is inconsistent")
        return self


class SectorEtfRotationSnapshotV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["1.0"] = "1.0"
    contract_version: Literal["sector-etf-rotation/1.0"] = "sector-etf-rotation/1.0"
    calculation_version: Literal["sector-etf-rotation-v1.0.0"] = "sector-etf-rotation-v1.0.0"
    parameter_set_id: Literal["sector-etf-rotation-fixed-registry-1"] = "sector-etf-rotation-fixed-registry-1"
    parameter_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    as_of_session: date
    input_first_session: date
    input_last_session: date
    input_session_count: int = Field(ge=21)
    benchmark_ticker: Literal["SPY"] = "SPY"
    records: tuple[SectorRotationRecordV1, ...]
    theme_status: Literal["unavailable_no_governed_membership"] = "unavailable_no_governed_membership"
    source_history_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    warnings: tuple[str, ...]
    logical_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def product_reconciles(self) -> "SectorEtfRotationSnapshotV1":
        if self.as_of_session != self.input_last_session:
            raise ValueError("sector rotation as-of differs from input tail")
        if len(self.records) != 11 or tuple(item.registry_order for item in self.records) != tuple(range(11)):
            raise ValueError("sector rotation requires the fixed 11-sector registry")
        if len({item.ticker for item in self.records}) != 11:
            raise ValueError("sector rotation registry contains duplicate tickers")
        for window_index, window_sessions in enumerate((5, 10, 20)):
            available = tuple(
                item.windows[window_index]
                for item in self.records
                if item.windows[window_index].availability
                is SectorRotationAvailability.AVAILABLE
            )
            if any(item.window_sessions != window_sessions for item in available):
                raise ValueError("sector rotation window index differs")
            if any(item.relative_rank is None for item in available):
                raise ValueError("available sector rotation window requires a rank")
            if any(
                item.windows[window_index].available_peer_count != len(available)
                for item in self.records
            ):
                raise ValueError("sector rotation peer coverage differs")
            if any(
                item.relative_rank is not None
                and item.relative_rank > len(available)
                for item in available
            ):
                raise ValueError("sector rotation rank exceeds peer coverage")
        return self


class SectorRotationOracleComparisonV1(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    contract_version: Literal["sector-etf-rotation-oracle/1.0"] = "sector-etf-rotation-oracle/1.0"
    as_of_session: date
    record_count: Literal[11] = 11
    mismatch_count: int = Field(ge=0)
    mismatches: tuple[str, ...]
    source_product_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def mismatches_reconcile(self) -> "SectorRotationOracleComparisonV1":
        if self.mismatch_count != len(self.mismatches):
            raise ValueError("sector rotation Oracle mismatch count differs")
        return self
