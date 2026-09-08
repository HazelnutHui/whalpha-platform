"""Build an owner-only split-adjustment candidate from resolved observations."""

from __future__ import annotations

import hashlib
import json
import os
import socket
import stat
from collections import defaultdict
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Iterator, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic_core import to_jsonable_python

from tip_api.contracts.common import (
    ensure_finite_decimal,
    normalize_utc_datetime,
    reject_float_decimal_input,
)
from tip_api.contracts.market_data.v1 import (
    CorporateActionRecordStatus,
    CorporateActionSourceObservationV1,
    CorporateActionType,
    ResolutionStatus,
)
from tip_api.services.historical_adjustment_invariants import (
    calculate_composed_split_adjustment_multipliers,
)
from tip_api.services.historical_corporate_action_resolution_shadow import (
    HistoricalCorporateActionResolutionShadowError,
    read_historical_corporate_action_resolution_shadow,
    read_historical_ticker_candidates_bound_to_resolution_shadow,
)


CONTRACT_VERSION = "historical-split-adjustment-candidate/1.0"
METHODOLOGY_VERSION = "resolved-event-ratio-split-adjustment-v1"
APPROVED_DATA_ROOT = Path("/data/trading-intelligence-platform")
FILE_NAME = "candidate.json"
MAXIMUM_JSON_BYTES = 16 * 1024 * 1024
_SHA256_PATTERN = r"^[0-9a-f]{64}$"
_SPLIT_TYPES = frozenset(
    {
        CorporateActionType.STOCK_SPLIT,
        CorporateActionType.REVERSE_SPLIT,
        CorporateActionType.STOCK_DIVIDEND,
    }
)


class HistoricalSplitAdjustmentCandidateError(RuntimeError):
    """Raised when a split-adjustment candidate cannot be trusted."""


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class SplitAdjustmentSourceActionV1(FrozenModel):
    source_action_id: str
    source_revision: int = Field(ge=1)
    action_type: CorporateActionType
    split_ratio_from: Decimal
    split_ratio_to: Decimal

    @field_validator("split_ratio_from", "split_ratio_to", mode="before")
    @classmethod
    def reject_float_ratios(cls, value: object, info: object) -> object:
        field_name = getattr(info, "field_name", "split_ratio")
        return reject_float_decimal_input(value, field_name=field_name)

    @field_validator("split_ratio_from", "split_ratio_to")
    @classmethod
    def positive_ratios(cls, value: Decimal, info: object) -> Decimal:
        field_name = getattr(info, "field_name", "split_ratio")
        normalized = ensure_finite_decimal(value, field_name=field_name)
        if normalized <= 0:
            raise ValueError(f"{field_name} must be positive")
        return normalized

    @model_validator(mode="after")
    def split_only(self) -> "SplitAdjustmentSourceActionV1":
        if self.action_type not in _SPLIT_TYPES:
            raise ValueError("adjustment source action must be split-like")
        return self


class SplitAdjustmentEventCandidateV1(FrozenModel):
    schema_version: Literal["1.0"] = "1.0"
    instrument_id: UUID
    effective_date: date
    source_actions: tuple[SplitAdjustmentSourceActionV1, ...] = Field(
        min_length=1
    )
    source_action_set_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    price_multiplier_to_post_event_basis: Decimal
    volume_multiplier_to_post_event_basis: Decimal
    quality_flags: tuple[str, ...] = ()

    @field_validator(
        "price_multiplier_to_post_event_basis",
        "volume_multiplier_to_post_event_basis",
        mode="before",
    )
    @classmethod
    def reject_float_factors(cls, value: object, info: object) -> object:
        field_name = getattr(info, "field_name", "factor")
        return reject_float_decimal_input(value, field_name=field_name)

    @field_validator(
        "price_multiplier_to_post_event_basis",
        "volume_multiplier_to_post_event_basis",
    )
    @classmethod
    def positive_factors(cls, value: Decimal, info: object) -> Decimal:
        field_name = getattr(info, "field_name", "factor")
        normalized = ensure_finite_decimal(value, field_name=field_name)
        if normalized <= 0:
            raise ValueError(f"{field_name} must be positive")
        return normalized

    @model_validator(mode="after")
    def event_reconciles(self) -> "SplitAdjustmentEventCandidateV1":
        ordered = tuple(
            sorted(
                self.source_actions,
                key=lambda item: (item.source_action_id, item.source_revision),
            )
        )
        if self.source_actions != ordered or len(
            {(item.source_action_id, item.source_revision) for item in ordered}
        ) != len(ordered):
            raise ValueError("split event source actions must be unique and ordered")
        if _fingerprint(tuple(item.model_dump(mode="json") for item in ordered)) != (
            self.source_action_set_fingerprint
        ):
            raise ValueError("split event source-action fingerprint differs")
        factors = calculate_composed_split_adjustment_multipliers(
            (item.split_ratio_from, item.split_ratio_to) for item in ordered
        )
        if (
            self.price_multiplier_to_post_event_basis
            != factors.price_multiplier_to_post_event_basis
            or self.volume_multiplier_to_post_event_basis
            != factors.volume_multiplier_to_post_event_basis
        ):
            raise ValueError("split event composed factors differ")
        expected_flags = (
            ("multiple_same_date_split_actions",) if len(ordered) > 1 else ()
        )
        if self.quality_flags != expected_flags:
            raise ValueError("split event quality flags differ")
        return self


class UnresolvedSplitImpactCandidateV1(FrozenModel):
    schema_version: Literal["1.0"] = "1.0"
    instrument_id: UUID
    provider_tickers: tuple[str, ...] = Field(min_length=1)
    effective_dates: tuple[date, ...] = Field(min_length=1)
    source_action_ids: tuple[str, ...] = Field(min_length=1)
    source_action_set_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    impact_status: Literal["quarantined"] = "quarantined"
    candidate_method: Literal["historical_exact_resolver_presence_only"] = (
        "historical_exact_resolver_presence_only"
    )
    quality_flags: tuple[str, ...] = (
        "unresolved_split_possible_historical_identity",
        "ticker_presence_does_not_assign_action",
    )

    @model_validator(mode="after")
    def impact_reconciles(self) -> "UnresolvedSplitImpactCandidateV1":
        if (
            self.provider_tickers != tuple(sorted(set(self.provider_tickers)))
            or self.effective_dates != tuple(sorted(set(self.effective_dates)))
            or self.source_action_ids != tuple(sorted(set(self.source_action_ids)))
        ):
            raise ValueError("unresolved impact evidence must be unique and ordered")
        if self.quality_flags != (
            "unresolved_split_possible_historical_identity",
            "ticker_presence_does_not_assign_action",
        ):
            raise ValueError("unresolved impact quality flags differ")
        payload = {
            "instrument_id": str(self.instrument_id),
            "provider_tickers": self.provider_tickers,
            "effective_dates": tuple(item.isoformat() for item in self.effective_dates),
            "source_action_ids": self.source_action_ids,
        }
        if _fingerprint(payload) != self.source_action_set_fingerprint:
            raise ValueError("unresolved impact fingerprint differs")
        return self


class HistoricalSplitAdjustmentCandidateV1(FrozenModel):
    contract_version: Literal[
        "historical-split-adjustment-candidate/1.0"
    ] = CONTRACT_VERSION
    completion_status: Literal["completed"] = "completed"
    methodology_version: Literal[
        "resolved-event-ratio-split-adjustment-v1"
    ] = METHODOLOGY_VERSION
    start_date: date
    basis_session: date
    calculated_at: datetime
    resolution_shadow_manifest_sha256: str = Field(pattern=_SHA256_PATTERN)
    resolution_shadow_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    identity_evidence_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    split_source_record_count: int = Field(ge=1)
    resolved_split_source_record_count: int = Field(ge=0)
    unresolved_split_source_record_count: int = Field(ge=0)
    resolved_event_group_count: int = Field(ge=0)
    multiple_same_date_event_group_count: int = Field(ge=0)
    unresolved_with_historical_identity_count: int = Field(ge=0)
    unresolved_without_historical_identity_count: int = Field(ge=0)
    unresolved_with_ambiguous_historical_identity_count: int = Field(ge=0)
    possible_impact_instrument_count: int = Field(ge=0)
    resolved_events: tuple[SplitAdjustmentEventCandidateV1, ...]
    possible_unresolved_impacts: tuple[UnresolvedSplitImpactCandidateV1, ...]
    unresolved_source_action_set_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    factor_direction: Literal["multiply_raw_value_to_basis"] = (
        "multiply_raw_value_to_basis"
    )
    event_inclusion_rule: Literal["source_session_lt_event_lte_basis"] = (
        "source_session_lt_event_lte_basis"
    )
    provider_cumulative_factor_usage: Literal["audit_only"] = "audit_only"
    total_return_adjustment_status: Literal["unavailable"] = "unavailable"
    ledger_projection_status: Literal["not_built"] = "not_built"
    point_in_time_eligibility: Literal["outcome_reconciliation_only"] = (
        "outcome_reconciliation_only"
    )
    latest_ticker_fallback_count: Literal[0] = 0
    nearest_session_fallback_count: Literal[0] = 0
    unresolved_action_assignment_count: Literal[0] = 0
    external_request_count: Literal[0] = 0
    canonical_data_write_count: Literal[0] = 0
    adjustment_ledger_write_count: Literal[0] = 0
    analytics_execution_count: Literal[0] = 0
    publication_count: Literal[0] = 0
    deployment_count: Literal[0] = 0
    logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)

    @field_validator("calculated_at")
    @classmethod
    def calculated_at_is_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @model_validator(mode="after")
    def candidate_reconciles(self) -> "HistoricalSplitAdjustmentCandidateV1":
        if self.basis_session < self.start_date:
            raise ValueError("split candidate basis precedes start")
        if self.split_source_record_count != (
            self.resolved_split_source_record_count
            + self.unresolved_split_source_record_count
        ):
            raise ValueError("split candidate source counts differ")
        expected_events = tuple(
            sorted(
                self.resolved_events,
                key=lambda item: (str(item.instrument_id), item.effective_date),
            )
        )
        expected_impacts = tuple(
            sorted(
                self.possible_unresolved_impacts,
                key=lambda item: str(item.instrument_id),
            )
        )
        event_keys = tuple(
            (item.instrument_id, item.effective_date) for item in self.resolved_events
        )
        action_keys = tuple(
            (action.source_action_id, action.source_revision)
            for event in self.resolved_events
            for action in event.source_actions
        )
        if (
            self.resolved_events != expected_events
            or self.possible_unresolved_impacts != expected_impacts
            or len(event_keys) != len(set(event_keys))
            or len(action_keys) != len(set(action_keys))
            or any(
                not (self.start_date <= item.effective_date <= self.basis_session)
                for item in self.resolved_events
            )
            or any(
                not all(
                    self.start_date <= effective_date <= self.basis_session
                    for effective_date in item.effective_dates
                )
                for item in self.possible_unresolved_impacts
            )
        ):
            raise ValueError("split candidate records are not ordered")
        if (
            self.resolved_event_group_count != len(self.resolved_events)
            or self.resolved_split_source_record_count
            != sum(len(item.source_actions) for item in self.resolved_events)
            or self.multiple_same_date_event_group_count
            != sum(len(item.source_actions) > 1 for item in self.resolved_events)
            or self.possible_impact_instrument_count
            != len(self.possible_unresolved_impacts)
            or self.unresolved_with_historical_identity_count
            + self.unresolved_without_historical_identity_count
            != self.unresolved_split_source_record_count
            or self.unresolved_with_ambiguous_historical_identity_count
            > self.unresolved_with_historical_identity_count
        ):
            raise ValueError("split candidate aggregate counts differ")
        expected = _fingerprint(
            self.model_dump(mode="json", exclude={"logical_fingerprint"})
        )
        if self.logical_fingerprint != expected:
            raise ValueError("split candidate logical fingerprint differs")
        return self


@dataclass(frozen=True, slots=True)
class HistoricalSplitAdjustmentCandidateResult:
    output_root: Path
    candidate: HistoricalSplitAdjustmentCandidateV1
    file_sha256: str
    status: Literal["published", "already_present"]


def build_historical_split_adjustment_candidate(
    *,
    data_root: Path,
    resolution_shadow_output_root: Path,
    output_root: Path,
    basis_session: date,
    calculated_at: datetime,
) -> HistoricalSplitAdjustmentCandidateResult:
    """Build a disconnected split-only candidate; never write canonical data."""

    with _network_prohibited():
        root = _validated_data_root(data_root)
        target = _validated_output_target(output_root)
        calculated_at = normalize_utc_datetime(calculated_at)
        shadow = read_historical_corporate_action_resolution_shadow(
            output_root=resolution_shadow_output_root
        )
        if basis_session != shadow.manifest.end_date:
            raise HistoricalSplitAdjustmentCandidateError(
                "split candidate basis must equal the resolution range end"
            )
        if calculated_at < shadow.manifest.materialized_at:
            raise HistoricalSplitAdjustmentCandidateError(
                "split candidate calculation precedes resolution"
            )
        split_records = tuple(
            item for item in shadow.records if item.action_type in _SPLIT_TYPES
        )
        if len(split_records) != shadow.manifest.split_source_record_count:
            raise HistoricalSplitAdjustmentCandidateError(
                "resolution shadow split count differs"
            )
        resolved = tuple(
            item
            for item in split_records
            if item.instrument_resolution_status is ResolutionStatus.RESOLVED
        )
        unresolved = tuple(
            item
            for item in split_records
            if item.instrument_resolution_status is not ResolutionStatus.RESOLVED
        )
        events = build_split_event_candidates(resolved, basis_session)
        requested_tickers = frozenset(item.provider_ticker for item in unresolved)
        try:
            historical_candidates = (
                read_historical_ticker_candidates_bound_to_resolution_shadow(
                    data_root=root,
                    resolution_shadow_output_root=resolution_shadow_output_root,
                    provider_tickers=requested_tickers,
                )
                if requested_tickers
                else {}
            )
        except HistoricalCorporateActionResolutionShadowError as exc:
            raise HistoricalSplitAdjustmentCandidateError(
                "historical unresolved-impact scan failed"
            ) from exc
        impacts, with_history, without_history, ambiguous = build_unresolved_split_impacts(
            unresolved,
            historical_candidates,
        )
        unresolved_fingerprint = _fingerprint(
            tuple(
                _unresolved_action_fingerprint_row(item)
                for item in sorted(
                    unresolved,
                    key=lambda item: (item.source_action_id, item.source_revision),
                )
            )
        )
        values = {
            "contract_version": CONTRACT_VERSION,
            "completion_status": "completed",
            "methodology_version": METHODOLOGY_VERSION,
            "start_date": shadow.manifest.start_date,
            "basis_session": basis_session,
            "calculated_at": calculated_at,
            "resolution_shadow_manifest_sha256": shadow.manifest_sha256,
            "resolution_shadow_logical_fingerprint": shadow.manifest.logical_fingerprint,
            "identity_evidence_logical_fingerprint": (
                shadow.manifest.identity_evidence_logical_fingerprint
            ),
            "split_source_record_count": len(split_records),
            "resolved_split_source_record_count": len(resolved),
            "unresolved_split_source_record_count": len(unresolved),
            "resolved_event_group_count": len(events),
            "multiple_same_date_event_group_count": sum(
                len(item.source_actions) > 1 for item in events
            ),
            "unresolved_with_historical_identity_count": with_history,
            "unresolved_without_historical_identity_count": without_history,
            "unresolved_with_ambiguous_historical_identity_count": ambiguous,
            "possible_impact_instrument_count": len(impacts),
            "resolved_events": events,
            "possible_unresolved_impacts": impacts,
            "unresolved_source_action_set_fingerprint": unresolved_fingerprint,
            "factor_direction": "multiply_raw_value_to_basis",
            "event_inclusion_rule": "source_session_lt_event_lte_basis",
            "provider_cumulative_factor_usage": "audit_only",
            "total_return_adjustment_status": "unavailable",
            "ledger_projection_status": "not_built",
            "point_in_time_eligibility": "outcome_reconciliation_only",
            "latest_ticker_fallback_count": 0,
            "nearest_session_fallback_count": 0,
            "unresolved_action_assignment_count": 0,
            "external_request_count": 0,
            "canonical_data_write_count": 0,
            "adjustment_ledger_write_count": 0,
            "analytics_execution_count": 0,
            "publication_count": 0,
            "deployment_count": 0,
        }
        candidate = HistoricalSplitAdjustmentCandidateV1.model_validate(
            {**values, "logical_fingerprint": _fingerprint(values)}
        )
        existing = _read_if_present(target)
        if existing is not None:
            if existing.candidate != candidate:
                raise HistoricalSplitAdjustmentCandidateError(
                    "existing split-adjustment candidate differs"
                )
            return existing

        staging = target.parent / f".{target.name}.staging.{os.getpid()}"
        if staging.exists() or staging.is_symlink():
            raise HistoricalSplitAdjustmentCandidateError(
                "split-adjustment candidate staging target exists"
            )
        staging.mkdir(mode=0o700)
        try:
            output = staging / FILE_NAME
            output.write_bytes(_pretty_json(candidate.model_dump(mode="json")))
            output.chmod(0o400)
            _fsync_file(output)
            _fsync_directory(staging)
            staging.replace(target)
            _fsync_directory(target.parent)
        except Exception:
            if staging.exists() and not staging.is_symlink():
                for child in staging.iterdir():
                    child.unlink()
                staging.rmdir()
            raise
        reread = read_historical_split_adjustment_candidate(output_root=target)
        if reread.candidate != candidate:
            raise HistoricalSplitAdjustmentCandidateError(
                "split-adjustment candidate formal reread differs"
            )
        return HistoricalSplitAdjustmentCandidateResult(
            output_root=reread.output_root,
            candidate=reread.candidate,
            file_sha256=reread.file_sha256,
            status="published",
        )


def read_historical_split_adjustment_candidate(
    *, output_root: Path
) -> HistoricalSplitAdjustmentCandidateResult:
    root = _validated_completed_output(output_root)
    entries = tuple(root.iterdir())
    if len(entries) != 1 or entries[0].name != FILE_NAME:
        raise HistoricalSplitAdjustmentCandidateError(
            "split-adjustment candidate file set differs"
        )
    path = root / FILE_NAME
    _require_regular_file(path, 0o400)
    size = path.stat().st_size
    if size < 1 or size > MAXIMUM_JSON_BYTES:
        raise HistoricalSplitAdjustmentCandidateError(
            "split-adjustment candidate size is invalid"
        )
    raw = path.read_bytes()
    try:
        candidate = HistoricalSplitAdjustmentCandidateV1.model_validate_json(raw)
    except Exception as exc:
        raise HistoricalSplitAdjustmentCandidateError(
            "split-adjustment candidate contract is invalid"
        ) from exc
    return HistoricalSplitAdjustmentCandidateResult(
        output_root=root,
        candidate=candidate,
        file_sha256=hashlib.sha256(raw).hexdigest(),
        status="already_present",
    )


def build_split_event_candidates(
    records: tuple[CorporateActionSourceObservationV1, ...],
    basis_session: date,
) -> tuple[SplitAdjustmentEventCandidateV1, ...]:
    grouped: dict[
        tuple[UUID, date], list[CorporateActionSourceObservationV1]
    ] = defaultdict(list)
    for record in records:
        if (
            record.instrument_id is None
            or record.record_status is not CorporateActionRecordStatus.ACTIVE
            or record.action_type not in _SPLIT_TYPES
            or record.split_ratio_from is None
            or record.split_ratio_to is None
            or record.effective_date > basis_session
        ):
            raise HistoricalSplitAdjustmentCandidateError(
                "resolved split observation is not eligible for candidate math"
            )
        grouped[(record.instrument_id, record.effective_date)].append(record)

    events: list[SplitAdjustmentEventCandidateV1] = []
    for (instrument_id, effective_date), rows in sorted(
        grouped.items(), key=lambda item: (str(item[0][0]), item[0][1])
    ):
        actions = tuple(
            sorted(
                (
                    SplitAdjustmentSourceActionV1(
                        source_action_id=row.source_action_id,
                        source_revision=row.source_revision,
                        action_type=row.action_type,
                        split_ratio_from=row.split_ratio_from,
                        split_ratio_to=row.split_ratio_to,
                    )
                    for row in rows
                ),
                key=lambda item: (item.source_action_id, item.source_revision),
            )
        )
        factors = calculate_composed_split_adjustment_multipliers(
            (item.split_ratio_from, item.split_ratio_to) for item in actions
        )
        action_fingerprint = _fingerprint(
            tuple(item.model_dump(mode="json") for item in actions)
        )
        events.append(
            SplitAdjustmentEventCandidateV1(
                instrument_id=instrument_id,
                effective_date=effective_date,
                source_actions=actions,
                source_action_set_fingerprint=action_fingerprint,
                price_multiplier_to_post_event_basis=(
                    factors.price_multiplier_to_post_event_basis
                ),
                volume_multiplier_to_post_event_basis=(
                    factors.volume_multiplier_to_post_event_basis
                ),
                quality_flags=(
                    ("multiple_same_date_split_actions",)
                    if len(actions) > 1
                    else ()
                ),
            )
        )
    return tuple(events)


def build_unresolved_split_impacts(
    unresolved: tuple[CorporateActionSourceObservationV1, ...],
    historical_candidates: dict[str, frozenset[UUID]],
) -> tuple[tuple[UnresolvedSplitImpactCandidateV1, ...], int, int, int]:
    by_instrument: dict[
        UUID, list[CorporateActionSourceObservationV1]
    ] = defaultdict(list)
    with_history = 0
    without_history = 0
    ambiguous = 0
    for record in unresolved:
        candidates = historical_candidates.get(record.provider_ticker, frozenset())
        if not candidates:
            without_history += 1
            continue
        with_history += 1
        if len(candidates) > 1:
            ambiguous += 1
        for instrument_id in candidates:
            by_instrument[instrument_id].append(record)

    impacts: list[UnresolvedSplitImpactCandidateV1] = []
    for instrument_id, rows in sorted(
        by_instrument.items(), key=lambda item: str(item[0])
    ):
        provider_tickers = tuple(sorted({item.provider_ticker for item in rows}))
        effective_dates = tuple(sorted({item.effective_date for item in rows}))
        source_action_ids = tuple(sorted({item.source_action_id for item in rows}))
        payload = {
            "instrument_id": str(instrument_id),
            "provider_tickers": provider_tickers,
            "effective_dates": tuple(item.isoformat() for item in effective_dates),
            "source_action_ids": source_action_ids,
        }
        impacts.append(
            UnresolvedSplitImpactCandidateV1(
                instrument_id=instrument_id,
                provider_tickers=provider_tickers,
                effective_dates=effective_dates,
                source_action_ids=source_action_ids,
                source_action_set_fingerprint=_fingerprint(payload),
            )
        )
    return tuple(impacts), with_history, without_history, ambiguous


def _unresolved_action_fingerprint_row(
    item: CorporateActionSourceObservationV1,
) -> dict[str, object]:
    return {
        "source_action_id": item.source_action_id,
        "source_revision": item.source_revision,
        "provider_ticker": item.provider_ticker,
        "effective_date": item.effective_date.isoformat(),
        "action_type": item.action_type.value,
        "split_ratio_from": str(item.split_ratio_from),
        "split_ratio_to": str(item.split_ratio_to),
        "quality_flags": item.quality_flags,
    }


def _read_if_present(
    target: Path,
) -> HistoricalSplitAdjustmentCandidateResult | None:
    if not target.exists() and not target.is_symlink():
        return None
    return read_historical_split_adjustment_candidate(output_root=target)


def _validated_data_root(path: Path) -> Path:
    if not path.is_absolute() or path.is_symlink() or not path.is_dir():
        raise HistoricalSplitAdjustmentCandidateError(
            "canonical data root is unavailable"
        )
    resolved = path.resolve(strict=True)
    if resolved != APPROVED_DATA_ROOT or path != resolved:
        raise HistoricalSplitAdjustmentCandidateError(
            "canonical data root is not the approved Dell root"
        )
    return resolved


def _validated_output_target(path: Path) -> Path:
    target = path.absolute()
    tmp = Path("/tmp").resolve(strict=True)
    if target == tmp or tmp not in target.parents:
        raise HistoricalSplitAdjustmentCandidateError(
            "split-adjustment candidate must be below /tmp"
        )
    _reject_symlink_chain(target.parent, tmp)
    if not target.parent.is_dir() or target.parent.is_symlink():
        raise HistoricalSplitAdjustmentCandidateError(
            "split-adjustment candidate parent is unsafe"
        )
    if target.exists() or target.is_symlink():
        if target.is_symlink() or not target.is_dir():
            raise HistoricalSplitAdjustmentCandidateError(
                "split-adjustment candidate target is unsafe"
            )
    return target


def _validated_completed_output(path: Path) -> Path:
    root = _validated_output_target(path)
    if (
        root.is_symlink()
        or not root.is_dir()
        or stat.S_IMODE(root.stat().st_mode) != 0o700
    ):
        raise HistoricalSplitAdjustmentCandidateError(
            "completed split-adjustment candidate is unavailable or not owner-only"
        )
    return root


def _reject_symlink_chain(path: Path, stop: Path) -> None:
    current = path.absolute()
    while current != stop:
        if current.exists() and current.is_symlink():
            raise HistoricalSplitAdjustmentCandidateError("path contains a symlink")
        if stop not in current.parents:
            raise HistoricalSplitAdjustmentCandidateError(
                "path escapes its trusted root"
            )
        current = current.parent


def _require_regular_file(path: Path, mode: int | None = None) -> None:
    if path.is_symlink() or not path.is_file():
        raise HistoricalSplitAdjustmentCandidateError(
            "required split-adjustment candidate file is missing or unsafe"
        )
    metadata = path.stat()
    if not stat.S_ISREG(metadata.st_mode) or (
        mode is not None and stat.S_IMODE(metadata.st_mode) != mode
    ):
        raise HistoricalSplitAdjustmentCandidateError(
            "split-adjustment candidate file mode differs"
        )


def _pretty_json(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _fingerprint(value: object) -> str:
    payload = json.dumps(
        to_jsonable_python(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _fsync_file(path: Path) -> None:
    with path.open("rb") as handle:
        os.fsync(handle.fileno())


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


@contextmanager
def _network_prohibited() -> Iterator[None]:
    original_socket = socket.socket
    original_connection = socket.create_connection

    def blocked(*_args: object, **_kwargs: object) -> None:
        raise HistoricalSplitAdjustmentCandidateError(
            "network access is prohibited while building split adjustments"
        )

    socket.socket = blocked  # type: ignore[assignment]
    socket.create_connection = blocked  # type: ignore[assignment]
    try:
        yield
    finally:
        socket.socket = original_socket  # type: ignore[assignment]
        socket.create_connection = original_connection  # type: ignore[assignment]
