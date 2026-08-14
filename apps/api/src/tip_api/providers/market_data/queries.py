"""Provider-neutral market-data query objects."""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, StrictBool, field_validator, model_validator


class RevisionSelection(StrEnum):
    """Revision selection behavior for EOD bar queries."""

    LATEST = "latest"
    ALL = "all"


def _deduplicate_uuids(values: tuple[UUID, ...]) -> tuple[UUID, ...]:
    seen: set[UUID] = set()
    deduped: list[UUID] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            deduped.append(value)
    return tuple(deduped)


def _reject_datetime_for_date(value: Any, *, field_name: str) -> Any:
    if isinstance(value, datetime):
        raise ValueError(f"{field_name} must not receive a datetime value")
    return value


class InstrumentQuery(BaseModel):
    """Canonical query for Instrument Master records."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    as_of_date: date
    instrument_ids: tuple[UUID, ...] | None = None
    active_only: StrictBool = False

    @field_validator("as_of_date", mode="before")
    @classmethod
    def reject_datetime_as_of_date(cls, value: Any) -> Any:
        return _reject_datetime_for_date(value, field_name="as_of_date")

    @field_validator("instrument_ids")
    @classmethod
    def normalize_instrument_ids(cls, value: tuple[UUID, ...] | None) -> tuple[UUID, ...] | None:
        if value is None:
            return None
        if len(value) == 0:
            raise ValueError("instrument_ids must contain at least one UUID when provided")
        return _deduplicate_uuids(value)


class EodBarQuery(BaseModel):
    """Canonical query for EOD Price Bar records."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    instrument_ids: tuple[UUID, ...]
    start_date: date
    end_date: date
    revision_selection: RevisionSelection = RevisionSelection.LATEST

    @field_validator("start_date", "end_date", mode="before")
    @classmethod
    def reject_datetime_dates(cls, value: Any, info: Any) -> Any:
        return _reject_datetime_for_date(value, field_name=info.field_name)

    @field_validator("instrument_ids")
    @classmethod
    def normalize_instrument_ids(cls, value: tuple[UUID, ...]) -> tuple[UUID, ...]:
        if len(value) == 0:
            raise ValueError("instrument_ids must contain at least one UUID")
        return _deduplicate_uuids(value)

    @model_validator(mode="after")
    def validate_date_range(self) -> EodBarQuery:
        if self.end_date < self.start_date:
            raise ValueError("end_date must not be earlier than start_date")
        return self
