"""Select one registered issuer-level SEC fact at an explicit historical cutoff."""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic_core import to_jsonable_python

from tip_api.contracts.common import normalize_utc_datetime
from tip_api.providers.sec.fundamental_query_readiness_census import (
    _SelectedRow,
    _classify_row,
)
from tip_api.providers.sec.fundamental_query_registry import (
    SecFundamentalQueryV1,
    build_first_sec_fundamental_query_registry,
)


CONTRACT_VERSION = "sec-point-in-time-fundamental-selection/1.0"
_CIK = r"^[0-9]{10}$"
_SHA256 = r"^[0-9a-f]{64}$"


class SecPointInTimeFundamentalSelectionError(RuntimeError):
    """Raised when registered issuer-fact selection cannot be proven."""


class _FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class SecIssuerFundamentalSelectionV1(_FrozenModel):
    contract_version: Literal[
        "sec-point-in-time-fundamental-selection/1.0"
    ] = CONTRACT_VERSION
    query_id: str = Field(pattern=r"^[a-z0-9_]+_v1$")
    registry_logical_fingerprint: str = Field(pattern=_SHA256)
    economic_grain: Literal["issuer"] = "issuer"
    companyfacts_cik: str = Field(pattern=_CIK)
    evaluated_session: date
    cutoff_at: datetime
    selection_status: Literal["selected", "not_available", "quarantined"]
    reason_codes: tuple[str, ...]
    value_kind: Literal["decimal", "integer"] | None = None
    value_text: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    source_available_at: datetime | None = None
    signal_eligible_session: date | None = None
    accession_numbers: tuple[str, ...] = ()
    forms: tuple[str, ...] = ()
    filed_dates: tuple[date, ...] = ()
    source_occurrence_ids: tuple[str, ...] = ()
    visible_revision_state_count: int = Field(ge=0)
    selected_occurrence_count: int = Field(ge=0)
    exact_duplicate_redundant_occurrence_count: int = Field(ge=0)
    security_projection_authorized: Literal[False] = False
    feature_materialization_authorized: Literal[False] = False
    strategy_outcome_access_count: Literal[0] = 0
    research_performance_authorized: Literal[False] = False
    logical_fingerprint: str = Field(pattern=_SHA256)

    @field_validator("cutoff_at", "source_available_at")
    @classmethod
    def datetimes_are_utc(cls, value: datetime | None) -> datetime | None:
        return None if value is None else normalize_utc_datetime(value)

    @model_validator(mode="after")
    def selection_reconciles(self) -> "SecIssuerFundamentalSelectionV1":
        registry = build_first_sec_fundamental_query_registry()
        if (
            self.query_id not in registry.query_order
            or self.registry_logical_fingerprint != registry.logical_fingerprint
        ):
            raise ValueError("fundamental selection registry binding differs")
        if self.reason_codes != tuple(sorted(set(self.reason_codes))):
            raise ValueError("fundamental selection reasons differ")
        for values in (
            self.accession_numbers,
            self.forms,
            self.filed_dates,
            self.source_occurrence_ids,
        ):
            if values != tuple(sorted(set(values))):
                raise ValueError("fundamental selection evidence set differs")
        selected_values = (
            self.value_kind,
            self.value_text,
            self.end_date,
            self.source_available_at,
            self.signal_eligible_session,
        )
        if self.selection_status == "selected":
            if (
                self.reason_codes
                or not all(value is not None for value in selected_values)
                or not self.accession_numbers
                or not self.forms
                or not self.filed_dates
                or not self.source_occurrence_ids
                or self.visible_revision_state_count < 1
                or self.selected_occurrence_count != len(self.source_occurrence_ids)
                or self.selected_occurrence_count < len(self.accession_numbers)
                or self.exact_duplicate_redundant_occurrence_count
                != self.selected_occurrence_count - len(self.accession_numbers)
                or self.source_available_at > self.cutoff_at
                or self.signal_eligible_session > self.evaluated_session
                or self.end_date > self.cutoff_at.date()
            ):
                raise ValueError("selected fundamental evidence differs")
        elif (
            not self.reason_codes
            or any(value is not None for value in selected_values)
            or self.start_date is not None
            or self.accession_numbers
            or self.forms
            or self.filed_dates
            or self.source_occurrence_ids
            or self.visible_revision_state_count != 0
            or self.selected_occurrence_count != 0
            or self.exact_duplicate_redundant_occurrence_count != 0
        ):
            raise ValueError("unselected fundamental evidence differs")
        expected = _fingerprint(
            self.model_dump(mode="json", exclude={"logical_fingerprint"})
        )
        if self.logical_fingerprint != expected:
            raise ValueError("fundamental selection fingerprint differs")
        return self


def select_sec_issuer_fundamental(
    *,
    rows: tuple[_SelectedRow, ...],
    query: SecFundamentalQueryV1,
    companyfacts_cik: str,
    evaluated_session: date,
    cutoff_at: datetime,
) -> SecIssuerFundamentalSelectionV1:
    """Select the latest unambiguous registered issuer fact at one cutoff."""

    cutoff = normalize_utc_datetime(cutoff_at)
    if any(
        row.companyfacts_cik != companyfacts_cik
        or row.namespace != query.namespace
        or row.concept_name != query.concept_name
        for row in rows
    ):
        raise SecPointInTimeFundamentalSelectionError(
            "fundamental selection row scope differs"
        )
    eligible = tuple(
        row
        for row in rows
        if _classify_row(row, query) == "query_eligible"
        and row.signal_eligible_session is not None
        and row.signal_eligible_session <= evaluated_session
        and row.source_available_at is not None
        and row.source_available_at <= cutoff
        and row.end_date is not None
        and row.end_date <= cutoff.date()
    )
    if not eligible:
        return _empty_selection(
            query=query,
            companyfacts_cik=companyfacts_cik,
            evaluated_session=evaluated_session,
            cutoff_at=cutoff,
            status="not_available",
            reasons=("no_query_eligible_occurrence_at_cutoff",),
        )
    latest_end = max(row.end_date for row in eligible if row.end_date is not None)
    latest = tuple(row for row in eligible if row.end_date == latest_end)
    period_starts = {row.start_date for row in latest}
    if len(period_starts) != 1:
        return _empty_selection(
            query=query,
            companyfacts_cik=companyfacts_cik,
            evaluated_session=evaluated_session,
            cutoff_at=cutoff,
            status="quarantined",
            reasons=("same_period_end_multiple_starts",),
        )
    by_accession: dict[str, list[_SelectedRow]] = defaultdict(list)
    for row in latest:
        by_accession[row.accession_number].append(row)
    clean: list[tuple[datetime, tuple[str, str], str, tuple[_SelectedRow, ...]]] = []
    for accession, accession_rows in by_accession.items():
        values = {(row.value_kind, row.value_text) for row in accession_rows}
        times = {row.source_available_at for row in accession_rows}
        metadata = {(row.form, row.filed_date) for row in accession_rows}
        if len(values) != 1 or len(times) != 1 or len(metadata) != 1 or None in times:
            return _empty_selection(
                query=query,
                companyfacts_cik=companyfacts_cik,
                evaluated_session=evaluated_session,
                cutoff_at=cutoff,
                status="quarantined",
                reasons=("within_accession_conflict",),
            )
        value_kind, value_text = next(iter(values))
        available_at = next(iter(times))
        if value_text is None or available_at is None:
            raise SecPointInTimeFundamentalSelectionError(
                "eligible fundamental accession is incomplete"
            )
        clean.append(
            (
                available_at,
                (value_kind, value_text),
                accession,
                tuple(accession_rows),
            )
        )
    by_time: dict[
        datetime,
        list[tuple[tuple[str, str], str, tuple[_SelectedRow, ...]]],
    ] = defaultdict(list)
    for available_at, value, accession, accession_rows in clean:
        by_time[available_at].append((value, accession, accession_rows))
    if any(len({item[0] for item in states}) > 1 for states in by_time.values()):
        return _empty_selection(
            query=query,
            companyfacts_cik=companyfacts_cik,
            evaluated_session=evaluated_session,
            cutoff_at=cutoff,
            status="quarantined",
            reasons=("same_availability_value_conflict",),
        )
    selected_time = max(by_time)
    selected_states = by_time[selected_time]
    selected_values = {item[0] for item in selected_states}
    if len(selected_values) != 1:
        raise SecPointInTimeFundamentalSelectionError(
            "fundamental latest state value differs"
        )
    value_kind, value_text = next(iter(selected_values))
    selected_rows = tuple(row for _, _, values in selected_states for row in values)
    accessions = tuple(sorted({item[1] for item in selected_states}))
    source_ids = tuple(sorted({row.source_occurrence_id for row in selected_rows}))
    if len(source_ids) != len(selected_rows):
        raise SecPointInTimeFundamentalSelectionError(
            "fundamental source occurrence ID is duplicated"
        )
    values = {
        "contract_version": CONTRACT_VERSION,
        "query_id": query.query_id,
        "registry_logical_fingerprint": (
            build_first_sec_fundamental_query_registry().logical_fingerprint
        ),
        "economic_grain": "issuer",
        "companyfacts_cik": companyfacts_cik,
        "evaluated_session": evaluated_session,
        "cutoff_at": cutoff,
        "selection_status": "selected",
        "reason_codes": (),
        "value_kind": value_kind,
        "value_text": value_text,
        "start_date": next(iter(period_starts)),
        "end_date": latest_end,
        "source_available_at": selected_time,
        "signal_eligible_session": max(
            row.signal_eligible_session
            for row in selected_rows
            if row.signal_eligible_session is not None
        ),
        "accession_numbers": accessions,
        "forms": tuple(sorted({row.form for row in selected_rows})),
        "filed_dates": tuple(sorted({row.filed_date for row in selected_rows})),
        "source_occurrence_ids": source_ids,
        "visible_revision_state_count": len(by_time),
        "selected_occurrence_count": len(selected_rows),
        "exact_duplicate_redundant_occurrence_count": (
            len(selected_rows) - len(accessions)
        ),
        "security_projection_authorized": False,
        "feature_materialization_authorized": False,
        "strategy_outcome_access_count": 0,
        "research_performance_authorized": False,
    }
    return SecIssuerFundamentalSelectionV1.model_validate(
        {**values, "logical_fingerprint": _fingerprint(values)}
    )


def _empty_selection(
    *,
    query: SecFundamentalQueryV1,
    companyfacts_cik: str,
    evaluated_session: date,
    cutoff_at: datetime,
    status: Literal["not_available", "quarantined"],
    reasons: tuple[str, ...],
) -> SecIssuerFundamentalSelectionV1:
    values = {
        "contract_version": CONTRACT_VERSION,
        "query_id": query.query_id,
        "registry_logical_fingerprint": (
            build_first_sec_fundamental_query_registry().logical_fingerprint
        ),
        "economic_grain": "issuer",
        "companyfacts_cik": companyfacts_cik,
        "evaluated_session": evaluated_session,
        "cutoff_at": cutoff_at,
        "selection_status": status,
        "reason_codes": tuple(sorted(set(reasons))),
        "value_kind": None,
        "value_text": None,
        "start_date": None,
        "end_date": None,
        "source_available_at": None,
        "signal_eligible_session": None,
        "accession_numbers": (),
        "forms": (),
        "filed_dates": (),
        "source_occurrence_ids": (),
        "visible_revision_state_count": 0,
        "selected_occurrence_count": 0,
        "exact_duplicate_redundant_occurrence_count": 0,
        "security_projection_authorized": False,
        "feature_materialization_authorized": False,
        "strategy_outcome_access_count": 0,
        "research_performance_authorized": False,
    }
    return SecIssuerFundamentalSelectionV1.model_validate(
        {**values, "logical_fingerprint": _fingerprint(values)}
    )


def _fingerprint(value: object) -> str:
    raw = json.dumps(
        to_jsonable_python(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()
