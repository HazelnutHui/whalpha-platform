"""Provider-neutral boundary for isolated China A-share source observations."""

from __future__ import annotations

import re
from datetime import date, datetime
from enum import StrEnum
from typing import Any, Protocol, runtime_checkable
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from tip_api.contracts.china_ashare.v1 import (
    ChinaAshareAdjustmentFactorObservationV1,
    ChinaAshareBoard,
    ChinaAshareDailyBarV1,
    ChinaAshareDailyTradingStateV1,
    ChinaAshareInstrumentSourceObservationV1,
    ChinaAshareSecurityForm,
    ChinaAshareSourceSecuritySnapshotStateV1,
)


_SOURCE_SECURITY_ID = re.compile(r"^(?:sh|sz|bj)\.[0-9]{6}$")


class ChinaAshareSourceCapability(StrEnum):
    INSTRUMENT_SNAPSHOT = "instrument_snapshot"
    RAW_DAILY_BAR = "raw_daily_bar"
    DAILY_TRADING_STATE = "daily_trading_state"
    ADJUSTMENT_FACTOR_OBSERVATION = "adjustment_factor_observation"


class FrozenContract(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class ChinaAshareSourceInstrumentQuery(FrozenContract):
    as_of_date: date

    @field_validator("as_of_date", mode="before")
    @classmethod
    def date_is_not_datetime(cls, value: Any) -> Any:
        if isinstance(value, datetime):
            raise ValueError("as_of_date must not receive a datetime")
        return value


class ChinaAshareSourceDailyQuery(FrozenContract):
    source_security_ids: tuple[str, ...] = Field(min_length=1)
    start_date: date
    end_date: date

    @field_validator("source_security_ids", mode="before")
    @classmethod
    def source_ids_are_canonical(cls, value: Any) -> tuple[str, ...]:
        if not isinstance(value, (tuple, list)):
            raise ValueError("source_security_ids must be an ordered collection")
        normalized = tuple(sorted({str(item).strip().lower() for item in value}))
        if not normalized or any(not _SOURCE_SECURITY_ID.fullmatch(item) for item in normalized):
            raise ValueError("source_security_ids must use sh|sz|bj plus a six-digit code")
        return normalized

    @field_validator("start_date", "end_date", mode="before")
    @classmethod
    def dates_are_not_datetimes(cls, value: Any) -> Any:
        if isinstance(value, datetime):
            raise ValueError("source history dates must not receive datetime values")
        return value

    @model_validator(mode="after")
    def interval_is_ordered(self) -> "ChinaAshareSourceDailyQuery":
        if self.end_date < self.start_date:
            raise ValueError("end_date must not precede start_date")
        return self


class ChinaAshareIdentityBindingV1(FrozenContract):
    """A separately established stable-ID, board, and form binding.

    Source adapters may consume this evidence but may not create it from code
    prefixes or security names.
    """

    source_security_id: str
    instrument_id: UUID
    board: ChinaAshareBoard
    security_form: ChinaAshareSecurityForm
    evidence_fingerprints: tuple[str, ...] = Field(min_length=1)

    @field_validator("source_security_id", mode="before")
    @classmethod
    def source_id_is_canonical(cls, value: str) -> str:
        normalized = str(value).strip().lower()
        if not _SOURCE_SECURITY_ID.fullmatch(normalized):
            raise ValueError("source_security_id is invalid")
        return normalized

    @field_validator("evidence_fingerprints", mode="before")
    @classmethod
    def fingerprints_are_canonical(cls, value: Any) -> tuple[str, ...]:
        if not isinstance(value, (tuple, list)):
            raise ValueError("evidence_fingerprints must be an ordered collection")
        normalized = tuple(sorted({str(item).strip().lower() for item in value}))
        if not normalized or any(not re.fullmatch(r"[0-9a-f]{64}", item) for item in normalized):
            raise ValueError("evidence_fingerprints must contain SHA-256 values")
        return normalized

    @model_validator(mode="after")
    def binding_is_source_proven(self) -> "ChinaAshareIdentityBindingV1":
        if self.board is ChinaAshareBoard.UNKNOWN:
            raise ValueError("identity binding cannot use an unknown board")
        if self.security_form is ChinaAshareSecurityForm.UNKNOWN:
            raise ValueError("identity binding cannot use an unknown security form")
        return self


class ChinaAshareDailySourceBatchV1(FrozenContract):
    provider_id: str
    query: ChinaAshareSourceDailyQuery
    bars: tuple[ChinaAshareDailyBarV1, ...]
    trading_states: tuple[ChinaAshareDailyTradingStateV1, ...]
    source_request_count: int = Field(ge=1)

    @field_validator("provider_id", mode="before")
    @classmethod
    def provider_is_present(cls, value: str) -> str:
        normalized = str(value).strip()
        if not normalized:
            raise ValueError("provider_id must not be empty")
        return normalized

    @model_validator(mode="after")
    def batch_reconciles(self) -> "ChinaAshareDailySourceBatchV1":
        if self.source_request_count != len(self.query.source_security_ids):
            raise ValueError("source_request_count must equal requested security count")
        bar_keys = [(item.instrument_id, item.session_date) for item in self.bars]
        state_keys = [
            (item.instrument_id, item.session_date) for item in self.trading_states
        ]
        if len(bar_keys) != len(set(bar_keys)):
            raise ValueError("daily source batch contains duplicate bar keys")
        if len(state_keys) != len(set(state_keys)):
            raise ValueError("daily source batch contains duplicate trading-state keys")
        if not set(bar_keys).issubset(state_keys):
            raise ValueError("every daily bar requires a matching trading state")
        for item in (*self.bars, *self.trading_states):
            if item.source != self.provider_id:
                raise ValueError("batch item source differs from provider_id")
            if not self.query.start_date <= item.session_date <= self.query.end_date:
                raise ValueError("batch item falls outside the requested interval")
        bar_key_set = set(bar_keys)
        for item in self.trading_states:
            key = (item.instrument_id, item.session_date)
            if item.trading_status.value in {"trading", "resumed"} and key not in bar_key_set:
                raise ValueError("trading session requires a daily bar")
            if item.trading_status.value in {"suspended", "not_listed"} and key in bar_key_set:
                raise ValueError("non-trading session must not carry a daily bar")
        return self


class ChinaAshareInstrumentSourceBatchV1(FrozenContract):
    provider_id: str
    query: ChinaAshareSourceInstrumentQuery
    instruments: tuple[ChinaAshareInstrumentSourceObservationV1, ...]
    source_states: tuple[ChinaAshareSourceSecuritySnapshotStateV1, ...]
    source_request_count: int = Field(ge=1)

    @field_validator("provider_id", mode="before")
    @classmethod
    def provider_is_present(cls, value: str) -> str:
        normalized = str(value).strip()
        if not normalized:
            raise ValueError("provider_id must not be empty")
        return normalized

    @model_validator(mode="after")
    def batch_reconciles(self) -> "ChinaAshareInstrumentSourceBatchV1":
        if self.source_request_count != 1:
            raise ValueError("instrument snapshot requires exactly one source request")
        instrument_ids = tuple(item.source_security_id for item in self.instruments)
        state_ids = tuple(item.source_security_id for item in self.source_states)
        if instrument_ids != tuple(sorted(set(instrument_ids))):
            raise ValueError("instrument observations must be unique and sorted")
        if state_ids != tuple(sorted(set(state_ids))):
            raise ValueError("source states must be unique and sorted")
        if instrument_ids != state_ids:
            raise ValueError("instrument observations and source states must align")
        for item in self.instruments:
            if item.source != self.provider_id or item.as_of_date != self.query.as_of_date:
                raise ValueError("instrument observation differs from batch scope")
        for item in self.source_states:
            if item.source != self.provider_id or item.session_date != self.query.as_of_date:
                raise ValueError("source state differs from batch scope")
        return self


@runtime_checkable
class ChinaAshareSourceProvider(Protocol):
    @property
    def provider_id(self) -> str:
        ...

    @property
    def capabilities(self) -> frozenset[ChinaAshareSourceCapability]:
        ...

    def get_instrument_observations(
        self,
        query: ChinaAshareSourceInstrumentQuery,
        *,
        identity_bindings: tuple[ChinaAshareIdentityBindingV1, ...] = (),
    ) -> tuple[ChinaAshareInstrumentSourceObservationV1, ...]:
        ...

    def get_instrument_snapshot(
        self,
        query: ChinaAshareSourceInstrumentQuery,
        *,
        identity_bindings: tuple[ChinaAshareIdentityBindingV1, ...] = (),
    ) -> ChinaAshareInstrumentSourceBatchV1:
        ...

    def get_daily_observations(
        self,
        query: ChinaAshareSourceDailyQuery,
        *,
        identity_bindings: tuple[ChinaAshareIdentityBindingV1, ...],
    ) -> ChinaAshareDailySourceBatchV1:
        ...

    def get_adjustment_factor_observations(
        self,
        query: ChinaAshareSourceDailyQuery,
        *,
        identity_bindings: tuple[ChinaAshareIdentityBindingV1, ...],
    ) -> tuple[ChinaAshareAdjustmentFactorObservationV1, ...]:
        ...
