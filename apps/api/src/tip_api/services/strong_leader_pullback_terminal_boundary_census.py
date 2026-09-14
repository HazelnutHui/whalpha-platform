"""Reconcile first-strategy lifecycle proxy dates with canonical EOD presence."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import stat
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Literal, Mapping
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic_core import to_jsonable_python

from tip_api.contracts.analytics.v1.candidate_strategy_development_coverage import (
    STRONG_LEADER_PULLBACK_CENSUS_FIRST_SESSION,
    STRONG_LEADER_PULLBACK_CENSUS_LAST_SESSION,
    STRONG_LEADER_PULLBACK_CENSUS_SESSION_COUNT,
)
from tip_api.contracts.common import normalize_utc_datetime
from tip_api.persistence.development_coverage_census import (
    REPORT_FILE as DEVELOPMENT_REPORT_FILE,
    read_development_coverage_census,
)
from tip_api.persistence.eod_read import EodInstrumentPresenceSessionRead
from tip_api.persistence.parquet.eod_read import CanonicalEodReadRepository
from tip_api.services import strong_leader_pullback_evidence_blocker_census as blocker_source
from tip_api.services.market_calendar import ExchangeCalendar


CONTRACT_VERSION = "strong-leader-pullback-terminal-boundary-census/1.0"
REPORT_FILE = "terminal-boundary-census.json"
MAXIMUM_REPORT_BYTES = 512 * 1024
APPROVED_DATA_ROOT = Path("/data/trading-intelligence-platform")

_HORIZONS = (1, 3, 5)
_REVISION_PATTERN = r"^[0-9a-f]{40}$"
_SHA256_PATTERN = r"^[0-9a-f]{64}$"
_OUTPUT_NAME_PATTERN = r"^census=[A-Za-z0-9._-]+$"

BoundaryRelation = Literal[
    "eod_precedes_identity_observation",
    "eod_matches_identity_observation",
    "eod_follows_identity_observation",
]


class StrongLeaderPullbackTerminalBoundaryCensusError(RuntimeError):
    """Raised when the terminal-boundary reconciliation cannot be proven."""


class _FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class TerminalBoundaryDecisionV1(_FrozenModel):
    instrument_id: UUID
    canonical_identity_first_observed_date: date
    canonical_identity_last_observed_date: date
    strategy_window_last_eod_observed_date: date
    provider_delist_date_candidate: date
    boundary_relation: BoundaryRelation
    included_path_count: int = Field(ge=1)
    legacy_horizon_1_crossing_path_count: int = Field(ge=0)
    legacy_horizon_3_crossing_path_count: int = Field(ge=0)
    legacy_horizon_5_crossing_path_count: int = Field(ge=0)
    corrected_horizon_1_crossing_path_count: int = Field(ge=0)
    corrected_horizon_3_crossing_path_count: int = Field(ge=0)
    corrected_horizon_5_crossing_path_count: int = Field(ge=0)
    path_counts_changed: bool
    newly_horizon_5_in_scope: bool
    identity_observation_is_terminal_fact: Literal[False] = False
    eod_observation_is_terminal_fact: Literal[False] = False
    terminal_outcome_authorized: Literal[False] = False
    logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)

    @model_validator(mode="after")
    def decision_reconciles(self) -> "TerminalBoundaryDecisionV1":
        legacy = (
            self.legacy_horizon_1_crossing_path_count,
            self.legacy_horizon_3_crossing_path_count,
            self.legacy_horizon_5_crossing_path_count,
        )
        corrected = (
            self.corrected_horizon_1_crossing_path_count,
            self.corrected_horizon_3_crossing_path_count,
            self.corrected_horizon_5_crossing_path_count,
        )
        expected_relation: BoundaryRelation
        if (
            self.strategy_window_last_eod_observed_date
            < self.canonical_identity_last_observed_date
        ):
            expected_relation = "eod_precedes_identity_observation"
        elif (
            self.strategy_window_last_eod_observed_date
            == self.canonical_identity_last_observed_date
        ):
            expected_relation = "eod_matches_identity_observation"
        else:
            expected_relation = "eod_follows_identity_observation"
        if (
            self.canonical_identity_first_observed_date
            > self.canonical_identity_last_observed_date
            or legacy != tuple(sorted(legacy))
            or corrected != tuple(sorted(corrected))
            or self.boundary_relation != expected_relation
            or self.path_counts_changed != (legacy != corrected)
            or self.newly_horizon_5_in_scope
            != (legacy[2] == 0 and corrected[2] > 0)
            or self.logical_fingerprint
            != _fingerprint(
                self.model_dump(mode="json", exclude={"logical_fingerprint"})
            )
        ):
            raise ValueError("terminal-boundary decision differs")
        return self


class StrongLeaderPullbackTerminalBoundaryCensusV1(_FrozenModel):
    contract_version: Literal[
        "strong-leader-pullback-terminal-boundary-census/1.0"
    ] = CONTRACT_VERSION
    completion_status: Literal["terminal_boundary_reconciled"] = (
        "terminal_boundary_reconciled"
    )
    implementation_revision: str = Field(pattern=_REVISION_PATTERN)
    evaluated_at: datetime
    ruleset_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    blocker_census_manifest_sha256: str = Field(pattern=_SHA256_PATTERN)
    blocker_census_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    development_census_report_sha256: str = Field(pattern=_SHA256_PATTERN)
    development_census_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    membership_binding_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    eod_session_binding_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    eod_first_session: date
    eod_last_session: date
    eod_session_count: int = Field(ge=1)
    lifecycle_instrument_count: int = Field(ge=1)
    boundary_relation_counts: tuple[tuple[str, int], ...]
    changed_instrument_count: int = Field(ge=0)
    newly_horizon_5_in_scope_instrument_count: int = Field(ge=0)
    legacy_horizon_1_crossing_instrument_count: int = Field(ge=0)
    legacy_horizon_3_crossing_instrument_count: int = Field(ge=0)
    legacy_horizon_5_crossing_instrument_count: int = Field(ge=0)
    corrected_horizon_1_crossing_instrument_count: int = Field(ge=0)
    corrected_horizon_3_crossing_instrument_count: int = Field(ge=0)
    corrected_horizon_5_crossing_instrument_count: int = Field(ge=0)
    legacy_horizon_1_crossing_path_count: int = Field(ge=0)
    legacy_horizon_3_crossing_path_count: int = Field(ge=0)
    legacy_horizon_5_crossing_path_count: int = Field(ge=0)
    corrected_horizon_1_crossing_path_count: int = Field(ge=0)
    corrected_horizon_3_crossing_path_count: int = Field(ge=0)
    corrected_horizon_5_crossing_path_count: int = Field(ge=0)
    decisions: tuple[TerminalBoundaryDecisionV1, ...]
    legacy_identity_boundary_not_terminal_eod: Literal[True] = True
    outcome_blind: Literal[True] = True
    terminal_outcome_count: Literal[0] = 0
    strategy_trigger_count: Literal[0] = 0
    forward_outcome_count: Literal[0] = 0
    performance_metric_count: Literal[0] = 0
    parameter_selection_count: Literal[0] = 0
    canonical_data_write_count: Literal[0] = 0
    historical_coverage_write_count: Literal[0] = 0
    research_admission_count: Literal[0] = 0
    candidate_write_count: Literal[0] = 0
    publication_count: Literal[0] = 0
    deployment_count: Literal[0] = 0
    scheduler_change_count: Literal[0] = 0
    network_request_count: Literal[0] = 0
    logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)

    @field_validator("evaluated_at")
    @classmethod
    def evaluated_at_is_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @model_validator(mode="after")
    def report_reconciles(self) -> "StrongLeaderPullbackTerminalBoundaryCensusV1":
        decisions = self.decisions
        ids = tuple(item.instrument_id for item in decisions)
        relations = Counter(item.boundary_relation for item in decisions)
        expected_relations = tuple(sorted(relations.items()))
        if (
            ids != tuple(sorted(set(ids), key=str))
            or len(decisions) != self.lifecycle_instrument_count
            or self.boundary_relation_counts != expected_relations
            or self.changed_instrument_count
            != sum(item.path_counts_changed for item in decisions)
            or self.newly_horizon_5_in_scope_instrument_count
            != sum(item.newly_horizon_5_in_scope for item in decisions)
            or self.eod_first_session > self.eod_last_session
            or self.ruleset_fingerprint != _ruleset_fingerprint()
            or any(
                getattr(self, f"legacy_horizon_{horizon}_crossing_instrument_count")
                != sum(
                    getattr(item, f"legacy_horizon_{horizon}_crossing_path_count")
                    > 0
                    for item in decisions
                )
                or getattr(
                    self, f"corrected_horizon_{horizon}_crossing_instrument_count"
                )
                != sum(
                    getattr(item, f"corrected_horizon_{horizon}_crossing_path_count")
                    > 0
                    for item in decisions
                )
                or getattr(self, f"legacy_horizon_{horizon}_crossing_path_count")
                != sum(
                    getattr(item, f"legacy_horizon_{horizon}_crossing_path_count")
                    for item in decisions
                )
                or getattr(self, f"corrected_horizon_{horizon}_crossing_path_count")
                != sum(
                    getattr(item, f"corrected_horizon_{horizon}_crossing_path_count")
                    for item in decisions
                )
                for horizon in _HORIZONS
            )
            or self.logical_fingerprint
            != _fingerprint(
                self.model_dump(mode="json", exclude={"logical_fingerprint"})
            )
        ):
            raise ValueError("terminal-boundary census differs")
        return self


@dataclass(frozen=True, slots=True)
class StrongLeaderPullbackTerminalBoundaryCensusResult:
    output_root: Path
    report: StrongLeaderPullbackTerminalBoundaryCensusV1
    report_sha256: str
    status: Literal["published", "already_present"]


def build_strong_leader_pullback_terminal_boundary_census(
    *,
    data_root: Path,
    development_census_root: Path,
    blocker_census_root: Path,
    blocker_census_custody_root: Path,
    output_root: Path,
    output_custody_root: Path,
    implementation_revision: str,
    evaluated_at: datetime,
) -> StrongLeaderPullbackTerminalBoundaryCensusResult:
    """Build one immutable correction without outcomes, network, or `/data` writes."""

    with blocker_source._network_prohibited():
        root = blocker_source._validated_data_root(data_root)
        if root != APPROVED_DATA_ROOT:
            raise StrongLeaderPullbackTerminalBoundaryCensusError(
                "terminal-boundary data root differs"
            )
        blocker = blocker_source.read_strong_leader_pullback_evidence_blocker_census(
            output_root=blocker_census_root,
            output_custody_root=blocker_census_custody_root,
        )
        development = read_development_coverage_census(
            output_root=development_census_root
        )
        development_sha256 = _file_sha256(
            development_census_root / DEVELOPMENT_REPORT_FILE
        )
        calendar = ExchangeCalendar()
        signal_sessions = calendar.sessions_in_range(
            STRONG_LEADER_PULLBACK_CENSUS_FIRST_SESSION,
            STRONG_LEADER_PULLBACK_CENSUS_LAST_SESSION,
        )
        if len(signal_sessions) != STRONG_LEADER_PULLBACK_CENSUS_SESSION_COUNT:
            raise StrongLeaderPullbackTerminalBoundaryCensusError(
                "terminal-boundary signal sessions differ"
            )
        extended = calendar.sessions_before(signal_sessions[0], 20) + signal_sessions
        for _ in range(5):
            extended += (calendar.next_session(extended[-1]),)
        signals, membership_binding, _ = blocker_source._read_included_paths(
            root=root,
            sessions=signal_sessions,
            report=development,
            session_index={value: index for index, value in enumerate(extended)},
        )
        lifecycle_ids = frozenset(
            item.instrument_id for item in blocker.lifecycle_records
        )
        eod_sessions = tuple(
            value
            for value in extended
            if signal_sessions[0] <= value <= extended[-1]
        )
        reads = CanonicalEodReadRepository(root).read_instrument_presence_sessions(
            eod_sessions, lifecycle_ids
        )
        report = _build_report(
            blocker=blocker,
            development=development,
            development_sha256=development_sha256,
            membership_binding=membership_binding,
            extended_sessions=extended,
            signal_sessions=signal_sessions,
            signals=signals,
            eod_reads=reads,
            implementation_revision=implementation_revision,
            evaluated_at=evaluated_at,
        )
        return _write_report(
            output_root=output_root,
            output_custody_root=output_custody_root,
            report=report,
        )


def read_strong_leader_pullback_terminal_boundary_census(
    *, output_root: Path, output_custody_root: Path
) -> StrongLeaderPullbackTerminalBoundaryCensusResult:
    root = _validated_completed_output(output_root, output_custody_root)
    if {item.name for item in root.iterdir()} != {REPORT_FILE}:
        raise StrongLeaderPullbackTerminalBoundaryCensusError(
            "terminal-boundary package members differ"
        )
    path = root / REPORT_FILE
    _require_regular_file(path, 0o400, MAXIMUM_REPORT_BYTES)
    raw = path.read_bytes()
    try:
        report = StrongLeaderPullbackTerminalBoundaryCensusV1.model_validate_json(raw)
    except Exception as exc:
        raise StrongLeaderPullbackTerminalBoundaryCensusError(
            "terminal-boundary report is invalid"
        ) from exc
    if raw != _json_bytes(report.model_dump(mode="json")):
        raise StrongLeaderPullbackTerminalBoundaryCensusError(
            "terminal-boundary report bytes are not canonical"
        )
    return StrongLeaderPullbackTerminalBoundaryCensusResult(
        output_root=root,
        report=report,
        report_sha256=_sha256_bytes(raw),
        status="already_present",
    )


def _build_report(
    *,
    blocker: object,
    development: object,
    development_sha256: str,
    membership_binding: str,
    extended_sessions: tuple[date, ...],
    signal_sessions: tuple[date, ...],
    signals: Mapping[UUID, tuple[int, ...]],
    eod_reads: tuple[EodInstrumentPresenceSessionRead, ...],
    implementation_revision: str,
    evaluated_at: datetime,
) -> StrongLeaderPullbackTerminalBoundaryCensusV1:
    if re.fullmatch(_REVISION_PATTERN, implementation_revision) is None:
        raise StrongLeaderPullbackTerminalBoundaryCensusError(
            "terminal-boundary revision is invalid"
        )
    if (
        blocker.manifest.development_census_sha256 != development_sha256
        or blocker.manifest.development_census_logical_fingerprint
        != development.logical_fingerprint
        or blocker.manifest.membership_binding_fingerprint != membership_binding
        or len(signal_sessions) != STRONG_LEADER_PULLBACK_CENSUS_SESSION_COUNT
        or tuple(item.integrity.session_date for item in eod_reads)
        != tuple(sorted(item.integrity.session_date for item in eod_reads))
    ):
        raise StrongLeaderPullbackTerminalBoundaryCensusError(
            "terminal-boundary upstream bindings differ"
        )
    read_by_date = {item.integrity.session_date: item for item in eod_reads}
    expected_eod_sessions = tuple(
        item
        for item in extended_sessions
        if signal_sessions[0] <= item <= extended_sessions[-1]
    )
    if tuple(read_by_date) != expected_eod_sessions:
        raise StrongLeaderPullbackTerminalBoundaryCensusError(
            "terminal-boundary EOD session scope differs"
        )
    population = {item.instrument_id for item in blocker.lifecycle_records}
    if set(signals) & population != population:
        raise StrongLeaderPullbackTerminalBoundaryCensusError(
            "terminal-boundary lifecycle paths are missing"
        )
    presence_dates = {
        instrument_id: tuple(
            session
            for session, read in read_by_date.items()
            if instrument_id in read.instrument_ids
        )
        for instrument_id in population
    }
    decisions = tuple(
        _decision(
            lifecycle=item,
            signal_indexes=signals[item.instrument_id],
            extended_sessions=extended_sessions,
            read_by_date=read_by_date,
            presence_dates=presence_dates[item.instrument_id],
        )
        for item in sorted(blocker.lifecycle_records, key=lambda value: str(value.instrument_id))
    )
    for horizon in _HORIZONS:
        if (
            sum(
                getattr(item, f"legacy_horizon_{horizon}_crossing_path_count")
                for item in decisions
            )
            != getattr(
                blocker.manifest,
                f"horizon_{horizon}_lifecycle_crossing_path_count",
            )
            or sum(
                getattr(item, f"legacy_horizon_{horizon}_crossing_path_count")
                > 0
                for item in decisions
            )
            != getattr(
                blocker.manifest,
                f"horizon_{horizon}_lifecycle_crossing_instrument_count",
            )
        ):
            raise StrongLeaderPullbackTerminalBoundaryCensusError(
                "terminal-boundary legacy aggregates differ"
            )
    relation_counts = Counter(item.boundary_relation for item in decisions)
    eod_binding = _fingerprint(
        tuple(
            {
                "session_date": item.integrity.session_date,
                "record_count": item.integrity.record_count,
                "content_fingerprint": item.integrity.content_fingerprint,
                "parquet_sha256": item.integrity.parquet_sha256,
                "identity_snapshot_date": item.integrity.identity_snapshot_date,
                "identity_snapshot_fingerprint": (
                    item.integrity.identity_snapshot_fingerprint
                ),
            }
            for item in eod_reads
        )
    )
    values: dict[str, object] = {
        "implementation_revision": implementation_revision,
        "evaluated_at": normalize_utc_datetime(evaluated_at),
        "ruleset_fingerprint": _ruleset_fingerprint(),
        "blocker_census_manifest_sha256": blocker.manifest_sha256,
        "blocker_census_logical_fingerprint": blocker.manifest.logical_fingerprint,
        "development_census_report_sha256": development_sha256,
        "development_census_logical_fingerprint": development.logical_fingerprint,
        "membership_binding_fingerprint": membership_binding,
        "eod_session_binding_fingerprint": eod_binding,
        "eod_first_session": expected_eod_sessions[0],
        "eod_last_session": expected_eod_sessions[-1],
        "eod_session_count": len(expected_eod_sessions),
        "lifecycle_instrument_count": len(decisions),
        "boundary_relation_counts": tuple(sorted(relation_counts.items())),
        "changed_instrument_count": sum(item.path_counts_changed for item in decisions),
        "newly_horizon_5_in_scope_instrument_count": sum(
            item.newly_horizon_5_in_scope for item in decisions
        ),
        "decisions": decisions,
    }
    for prefix in ("legacy", "corrected"):
        for horizon in _HORIZONS:
            field = f"{prefix}_horizon_{horizon}_crossing_path_count"
            values[field] = sum(getattr(item, field) for item in decisions)
            values[f"{prefix}_horizon_{horizon}_crossing_instrument_count"] = sum(
                getattr(item, field) > 0 for item in decisions
            )
    provisional = StrongLeaderPullbackTerminalBoundaryCensusV1.model_construct(
        **values, logical_fingerprint="0" * 64
    )
    return StrongLeaderPullbackTerminalBoundaryCensusV1.model_validate(
        {
            **values,
            "logical_fingerprint": _fingerprint(
                provisional.model_dump(mode="json", exclude={"logical_fingerprint"})
            ),
        }
    )


def _decision(
    *,
    lifecycle: object,
    signal_indexes: tuple[int, ...],
    extended_sessions: tuple[date, ...],
    read_by_date: Mapping[date, EodInstrumentPresenceSessionRead],
    presence_dates: tuple[date, ...],
) -> TerminalBoundaryDecisionV1:
    if not presence_dates or len(signal_indexes) != lifecycle.included_path_count:
        raise StrongLeaderPullbackTerminalBoundaryCensusError(
            "terminal-boundary EOD presence or path count differs"
        )
    for index in signal_indexes:
        session = extended_sessions[index]
        if (
            session not in read_by_date
            or lifecycle.instrument_id not in read_by_date[session].instrument_ids
        ):
            raise StrongLeaderPullbackTerminalBoundaryCensusError(
                "terminal-boundary included path lacks signal-session EOD"
            )
    eod_last = presence_dates[-1]
    legacy = {
        horizon: getattr(
            lifecycle, f"horizon_{horizon}_crosses_last_observed_path_count"
        )
        for horizon in _HORIZONS
    }
    recalculated_legacy = {
        horizon: sum(
            extended_sessions[index + horizon]
            > lifecycle.canonical_last_observed_date
            for index in signal_indexes
        )
        for horizon in _HORIZONS
    }
    if legacy != recalculated_legacy:
        raise StrongLeaderPullbackTerminalBoundaryCensusError(
            "terminal-boundary legacy path calculation differs"
        )
    corrected = {
        horizon: sum(
            extended_sessions[index + horizon] > eod_last for index in signal_indexes
        )
        for horizon in _HORIZONS
    }
    if eod_last < lifecycle.canonical_last_observed_date:
        relation: BoundaryRelation = "eod_precedes_identity_observation"
    elif eod_last == lifecycle.canonical_last_observed_date:
        relation = "eod_matches_identity_observation"
    else:
        relation = "eod_follows_identity_observation"
    values = {
        "instrument_id": lifecycle.instrument_id,
        "canonical_identity_first_observed_date": (
            lifecycle.canonical_first_observed_date
        ),
        "canonical_identity_last_observed_date": (
            lifecycle.canonical_last_observed_date
        ),
        "strategy_window_last_eod_observed_date": eod_last,
        "provider_delist_date_candidate": lifecycle.provider_delist_date_candidate,
        "boundary_relation": relation,
        "included_path_count": lifecycle.included_path_count,
        **{
            f"legacy_horizon_{horizon}_crossing_path_count": legacy[horizon]
            for horizon in _HORIZONS
        },
        **{
            f"corrected_horizon_{horizon}_crossing_path_count": corrected[horizon]
            for horizon in _HORIZONS
        },
        "path_counts_changed": legacy != corrected,
        "newly_horizon_5_in_scope": legacy[5] == 0 and corrected[5] > 0,
    }
    provisional = TerminalBoundaryDecisionV1.model_construct(
        **values, logical_fingerprint="0" * 64
    )
    return TerminalBoundaryDecisionV1.model_validate(
        {
            **values,
            "logical_fingerprint": _fingerprint(
                provisional.model_dump(mode="json", exclude={"logical_fingerprint"})
            ),
        }
    )


def _ruleset_fingerprint() -> str:
    return _fingerprint(
        {
            "contract_version": CONTRACT_VERSION,
            "population": "all_blocker_lifecycle_instruments",
            "legacy_boundary": "canonical_instrument_identity_last_observation",
            "corrected_boundary": "last_canonical_eod_presence_in_strategy_window",
            "eod_scope": "first_signal_through_five_sessions_after_last_signal",
            "forward_horizons": _HORIZONS,
            "identity_observation_is_terminal_fact": False,
            "eod_observation_is_terminal_fact": False,
            "outcome_blind": True,
        }
    )


def _write_report(
    *,
    output_root: Path,
    output_custody_root: Path,
    report: StrongLeaderPullbackTerminalBoundaryCensusV1,
) -> StrongLeaderPullbackTerminalBoundaryCensusResult:
    target = _validated_output_target(output_root, output_custody_root)
    if target.exists() or target.is_symlink():
        existing = read_strong_leader_pullback_terminal_boundary_census(
            output_root=target,
            output_custody_root=output_custody_root,
        )
        if existing.report != report:
            raise StrongLeaderPullbackTerminalBoundaryCensusError(
                "existing terminal-boundary census differs"
            )
        return existing
    partial = target.parent / f".{target.name}.partial"
    if partial.exists() or partial.is_symlink():
        raise StrongLeaderPullbackTerminalBoundaryCensusError(
            "terminal-boundary staging target exists"
        )
    partial.mkdir(mode=0o700)
    try:
        _write_exclusive(
            partial / REPORT_FILE,
            _json_bytes(report.model_dump(mode="json")),
        )
        _fsync_directory(partial)
        partial.replace(target)
        _fsync_directory(target.parent)
    except Exception:
        if partial.exists() and not partial.is_symlink():
            shutil.rmtree(partial)
        raise
    reread = read_strong_leader_pullback_terminal_boundary_census(
        output_root=target,
        output_custody_root=output_custody_root,
    )
    return StrongLeaderPullbackTerminalBoundaryCensusResult(
        output_root=target,
        report=reread.report,
        report_sha256=reread.report_sha256,
        status="published",
    )


def _fingerprint(value: object) -> str:
    return _sha256_bytes(_json_bytes(value))


def _json_bytes(value: object) -> bytes:
    return (
        json.dumps(
            to_jsonable_python(value),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _validated_output_target(path: Path, custody_root: Path) -> Path:
    if not path.is_absolute() or not custody_root.is_absolute():
        raise StrongLeaderPullbackTerminalBoundaryCensusError(
            "terminal-boundary paths must be absolute"
        )
    custody = custody_root.resolve(strict=True)
    if (
        custody_root != custody
        or custody.is_symlink()
        or not custody.is_dir()
        or custody.stat().st_uid != os.getuid()
        or stat.S_IMODE(custody.stat().st_mode) != 0o700
        or path.parent != custody
        or re.fullmatch(_OUTPUT_NAME_PATTERN, path.name) is None
    ):
        raise StrongLeaderPullbackTerminalBoundaryCensusError(
            "terminal-boundary custody or target is unsafe"
        )
    return path


def _validated_completed_output(path: Path, custody_root: Path) -> Path:
    target = _validated_output_target(path, custody_root)
    if (
        target.is_symlink()
        or not target.is_dir()
        or target.stat().st_uid != os.getuid()
        or stat.S_IMODE(target.stat().st_mode) != 0o700
        or target.resolve(strict=True) != target
    ):
        raise StrongLeaderPullbackTerminalBoundaryCensusError(
            "terminal-boundary output is unavailable or unsafe"
        )
    return target


def _require_regular_file(path: Path, mode: int, maximum_bytes: int) -> None:
    if path.is_symlink() or not path.is_file():
        raise StrongLeaderPullbackTerminalBoundaryCensusError(
            "terminal-boundary file is unavailable or unsafe"
        )
    metadata = path.stat()
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_uid != os.getuid()
        or stat.S_IMODE(metadata.st_mode) != mode
        or metadata.st_size < 1
        or metadata.st_size > maximum_bytes
    ):
        raise StrongLeaderPullbackTerminalBoundaryCensusError(
            "terminal-boundary file metadata differs"
        )


def _write_exclusive(path: Path, payload: bytes) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o400)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    except Exception:
        if path.exists() and not path.is_symlink():
            path.unlink()
        raise


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
