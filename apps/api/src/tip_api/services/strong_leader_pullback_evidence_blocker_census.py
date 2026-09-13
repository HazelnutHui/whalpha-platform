"""Outcome-blind action and lifecycle blocker census for the first strategy."""

from __future__ import annotations

import bisect
import hashlib
import json
import os
import re
import shutil
import socket
import stat
from collections import Counter, defaultdict
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Iterator, Literal
from uuid import UUID

import pyarrow as pa
import pyarrow.parquet as pq
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic_core import to_jsonable_python

from tip_api.contracts.analytics.v1.candidate_strategy_development_coverage import (
    STRONG_LEADER_PULLBACK_CENSUS_FIRST_SESSION,
    STRONG_LEADER_PULLBACK_CENSUS_LAST_SESSION,
    STRONG_LEADER_PULLBACK_CENSUS_MEMBERSHIP_METHODOLOGY,
    STRONG_LEADER_PULLBACK_CENSUS_PRIMARY_UNIVERSE,
    STRONG_LEADER_PULLBACK_CENSUS_SESSION_COUNT,
)
from tip_api.contracts.common import normalize_utc_datetime
from tip_api.contracts.market_data.v1 import (
    ResolutionStatus,
    UniverseMembershipDisposition,
)
from tip_api.contracts.market_data.v1.historical_inactive_lifecycle import (
    InactiveLifecycleDisposition,
)
from tip_api.persistence.development_admission_decision import (
    DECISION_FILE,
    read_development_admission_decision,
)
from tip_api.persistence.development_coverage_census import (
    REPORT_FILE,
    read_development_coverage_census,
)
from tip_api.services.historical_corporate_action_residual_evidence_census import (
    read_historical_corporate_action_residual_evidence_census,
)
from tip_api.services.historical_corporate_action_resolution_shadow import (
    read_historical_corporate_action_resolution_shadow,
)
from tip_api.services.historical_corporate_action_unresolved_census import (
    read_historical_corporate_action_unresolved_census_output,
)
from tip_api.services.historical_inactive_lifecycle_resolution_shadow import (
    read_historical_inactive_lifecycle_resolution_shadow,
)
from tip_api.services.market_calendar import ExchangeCalendar
from tip_api.services.research_universe_membership_canonical import (
    read_canonical_research_universe_membership,
)


CONTRACT_VERSION = "strong-leader-pullback-evidence-blocker-census/1.0"
ACTION_RECORD_VERSION = "strong-leader-pullback-action-exposure/1.0"
LIFECYCLE_RECORD_VERSION = "strong-leader-pullback-lifecycle-exposure/1.0"
APPROVED_DATA_ROOT = Path("/data/trading-intelligence-platform")
ACTION_FILE = "action-exposures.parquet"
LIFECYCLE_FILE = "lifecycle-exposures.parquet"
MANIFEST_FILE = "manifest.json"
MAXIMUM_ACTION_BYTES = 32 * 1024 * 1024
MAXIMUM_LIFECYCLE_BYTES = 4 * 1024 * 1024
MAXIMUM_MANIFEST_BYTES = 256 * 1024
_REVISION_PATTERN = r"^[0-9a-f]{40}$"
_SHA256_PATTERN = r"^[0-9a-f]{64}$"
_BUILD_NAME_PATTERN = r"^build=[A-Za-z0-9._-]+$"
_HORIZONS = (1, 3, 5)


ACTION_SCHEMA = pa.schema(
    [
        pa.field("contract_version", pa.string(), nullable=False),
        pa.field("source_action_id", pa.string(), nullable=False),
        pa.field("source_revision", pa.int32(), nullable=False),
        pa.field("provider_ticker", pa.string(), nullable=False),
        pa.field("effective_date", pa.date32(), nullable=False),
        pa.field("action_type", pa.string(), nullable=False),
        pa.field("semantic_requirement", pa.string(), nullable=False),
        pa.field("identity_evidence_kind", pa.string(), nullable=False),
        pa.field("candidate_instrument_id", pa.string(), nullable=False),
        pa.field("historical_candidate_classification", pa.string(), nullable=False),
        pa.field("exact_date_failure_reason", pa.string(), nullable=True),
        pa.field("feature_path_count", pa.int32(), nullable=False),
        pa.field("horizon_1_path_count", pa.int32(), nullable=False),
        pa.field("horizon_3_path_count", pa.int32(), nullable=False),
        pa.field("horizon_5_path_count", pa.int32(), nullable=False),
        pa.field("inactive_source_state", pa.string(), nullable=True),
        pa.field("inactive_source_type_codes", pa.list_(pa.string()), nullable=False),
        pa.field("finra_exact_date_symbol_occurrence_count", pa.int32(), nullable=False),
        pa.field("finra_exact_numeric_occurrence_count", pa.int32(), nullable=False),
        pa.field("finra_flag_codes", pa.list_(pa.string()), nullable=False),
        pa.field("stable_identity_assignment_authorized", pa.bool_(), nullable=False),
    ]
)

LIFECYCLE_SCHEMA = pa.schema(
    [
        pa.field("contract_version", pa.string(), nullable=False),
        pa.field("instrument_id", pa.string(), nullable=False),
        pa.field("source_anchor_dates", pa.list_(pa.date32()), nullable=False),
        pa.field("canonical_first_observed_date", pa.date32(), nullable=False),
        pa.field("canonical_last_observed_date", pa.date32(), nullable=False),
        pa.field("provider_delist_date_candidate", pa.date32(), nullable=False),
        pa.field("included_path_count", pa.int32(), nullable=False),
        pa.field("feature_window_outside_observed_span_path_count", pa.int32(), nullable=False),
        pa.field("horizon_1_crosses_last_observed_path_count", pa.int32(), nullable=False),
        pa.field("horizon_3_crosses_last_observed_path_count", pa.int32(), nullable=False),
        pa.field("horizon_5_crosses_last_observed_path_count", pa.int32(), nullable=False),
        pa.field("horizon_1_contains_delist_candidate_path_count", pa.int32(), nullable=False),
        pa.field("horizon_3_contains_delist_candidate_path_count", pa.int32(), nullable=False),
        pa.field("horizon_5_contains_delist_candidate_path_count", pa.int32(), nullable=False),
        pa.field("terminal_outcome_authorized", pa.bool_(), nullable=False),
    ]
)


class StrongLeaderPullbackEvidenceBlockerCensusError(RuntimeError):
    """Raised when the scoped diagnostic cannot be proven."""


class _FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class ActionExposureV1(_FrozenModel):
    contract_version: Literal[
        "strong-leader-pullback-action-exposure/1.0"
    ] = ACTION_RECORD_VERSION
    source_action_id: str
    source_revision: int = Field(ge=1)
    provider_ticker: str
    effective_date: date
    action_type: Literal[
        "cash_dividend", "reverse_split", "stock_dividend", "stock_split"
    ]
    semantic_requirement: Literal[
        "event_context_required", "price_share_adjustment_required"
    ]
    identity_evidence_kind: Literal[
        "exact_event_date_resolved", "history_candidate_unassigned"
    ]
    candidate_instrument_id: UUID
    historical_candidate_classification: Literal[
        "exact_event_date_resolved",
        "one_historical_candidate",
        "multiple_historical_candidates",
    ]
    exact_date_failure_reason: Literal[
        "event_date_identity_unavailable", "unresolved_ticker"
    ] | None = None
    feature_path_count: int = Field(ge=0)
    horizon_1_path_count: int = Field(ge=0)
    horizon_3_path_count: int = Field(ge=0)
    horizon_5_path_count: int = Field(ge=0)
    inactive_source_state: str | None = None
    inactive_source_type_codes: tuple[str, ...] = ()
    finra_exact_date_symbol_occurrence_count: int = Field(ge=0)
    finra_exact_numeric_occurrence_count: int = Field(ge=0)
    finra_flag_codes: tuple[str, ...] = ()
    stable_identity_assignment_authorized: Literal[False] = False

    @field_validator("source_action_id", "provider_ticker")
    @classmethod
    def text_is_trimmed(cls, value: str) -> str:
        if not value or value != value.strip():
            raise ValueError("action exposure text is invalid")
        return value

    @field_validator("inactive_source_type_codes", "finra_flag_codes", mode="before")
    @classmethod
    def codes_are_ordered(cls, value: object) -> tuple[str, ...]:
        values = tuple(value)  # type: ignore[arg-type]
        if values != tuple(sorted(set(values))):
            raise ValueError("action exposure codes are not ordered and unique")
        return values

    @model_validator(mode="after")
    def reconcile(self) -> "ActionExposureV1":
        if not self.feature_path_count and not self.horizon_5_path_count:
            raise ValueError("action exposure does not intersect a declared path")
        if not (
            self.horizon_1_path_count
            <= self.horizon_3_path_count
            <= self.horizon_5_path_count
        ):
            raise ValueError("action exposure horizon counts are not monotone")
        expected_semantic = (
            "event_context_required"
            if self.action_type == "cash_dividend"
            else "price_share_adjustment_required"
        )
        if self.semantic_requirement != expected_semantic:
            raise ValueError("action exposure semantic requirement differs")
        if self.identity_evidence_kind == "exact_event_date_resolved":
            if (
                self.historical_candidate_classification
                != "exact_event_date_resolved"
                or self.exact_date_failure_reason is not None
                or self.inactive_source_state is not None
                or self.inactive_source_type_codes
                or self.finra_exact_date_symbol_occurrence_count
                or self.finra_exact_numeric_occurrence_count
                or self.finra_flag_codes
            ):
                raise ValueError("resolved action carries residual-candidate evidence")
        elif (
            self.historical_candidate_classification
            == "exact_event_date_resolved"
            or self.exact_date_failure_reason is None
            or self.inactive_source_state is None
        ):
            raise ValueError("unassigned action candidate evidence is incomplete")
        if (
            self.finra_exact_numeric_occurrence_count
            > self.finra_exact_date_symbol_occurrence_count
        ):
            raise ValueError("FINRA numeric evidence exceeds symbol evidence")
        return self


class LifecycleExposureV1(_FrozenModel):
    contract_version: Literal[
        "strong-leader-pullback-lifecycle-exposure/1.0"
    ] = LIFECYCLE_RECORD_VERSION
    instrument_id: UUID
    source_anchor_dates: tuple[date, ...] = Field(min_length=1)
    canonical_first_observed_date: date
    canonical_last_observed_date: date
    provider_delist_date_candidate: date
    included_path_count: int = Field(ge=1)
    feature_window_outside_observed_span_path_count: int = Field(ge=0)
    horizon_1_crosses_last_observed_path_count: int = Field(ge=0)
    horizon_3_crosses_last_observed_path_count: int = Field(ge=0)
    horizon_5_crosses_last_observed_path_count: int = Field(ge=0)
    horizon_1_contains_delist_candidate_path_count: int = Field(ge=0)
    horizon_3_contains_delist_candidate_path_count: int = Field(ge=0)
    horizon_5_contains_delist_candidate_path_count: int = Field(ge=0)
    terminal_outcome_authorized: Literal[False] = False

    @field_validator("source_anchor_dates", mode="before")
    @classmethod
    def anchors_are_ordered(cls, value: object) -> tuple[date, ...]:
        values = tuple(value)  # type: ignore[arg-type]
        if values != tuple(sorted(set(values))):
            raise ValueError("lifecycle source anchors are not ordered and unique")
        return values

    @model_validator(mode="after")
    def reconcile(self) -> "LifecycleExposureV1":
        if not (
            self.canonical_first_observed_date
            <= self.canonical_last_observed_date
            < self.provider_delist_date_candidate
        ):
            raise ValueError("lifecycle candidate dates are invalid")
        if not (
            self.horizon_1_crosses_last_observed_path_count
            <= self.horizon_3_crosses_last_observed_path_count
            <= self.horizon_5_crosses_last_observed_path_count
        ):
            raise ValueError("lifecycle last-observed counts are not monotone")
        if not (
            self.horizon_1_contains_delist_candidate_path_count
            <= self.horizon_3_contains_delist_candidate_path_count
            <= self.horizon_5_contains_delist_candidate_path_count
        ):
            raise ValueError("lifecycle delist-candidate counts are not monotone")
        return self


class SourceBindingV1(_FrozenModel):
    name: str
    manifest_sha256: str = Field(pattern=_SHA256_PATTERN)
    logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    record_count: int = Field(ge=0)


class StrongLeaderPullbackEvidenceBlockerCensusManifestV1(_FrozenModel):
    contract_version: Literal[
        "strong-leader-pullback-evidence-blocker-census/1.0"
    ] = CONTRACT_VERSION
    completion_status: Literal["completed"] = "completed"
    dataset_name: Literal[
        "strong-leader-pullback-evidence-blocker-census"
    ] = "strong-leader-pullback-evidence-blocker-census"
    implementation_revision: str = Field(pattern=_REVISION_PATTERN)
    evaluated_at: datetime
    first_signal_session: date
    last_signal_session: date
    signal_session_count: int = Field(ge=1)
    feature_lookback_session_count: Literal[20] = 20
    feature_action_start_offset: Literal[-19] = -19
    forward_horizons: tuple[Literal[1, 3, 5], ...] = (1, 3, 5)
    entry_basis: Literal["next_session_open"] = "next_session_open"
    outcome_basis: Literal["underlying_stock_price_return"] = (
        "underlying_stock_price_return"
    )
    universe_id: str
    membership_methodology_version: str
    evidence_tier: Literal["reconstructed_point_in_time_latest_vintage"] = (
        "reconstructed_point_in_time_latest_vintage"
    )
    as_operated: Literal[False] = False
    outcome_blind: Literal[True] = True
    development_census_sha256: str = Field(pattern=_SHA256_PATTERN)
    development_census_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    rejected_admission_sha256: str = Field(pattern=_SHA256_PATTERN)
    rejected_admission_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    source_bindings: tuple[SourceBindingV1, ...] = Field(min_length=4)
    membership_binding_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    primary_decision_count: int = Field(ge=1)
    included_path_count: int = Field(ge=1)
    included_instrument_count: int = Field(ge=1)
    global_unresolved_source_record_count: int = Field(ge=1)
    global_zero_candidate_source_record_count: int = Field(ge=0)
    scoped_session_unresolved_source_record_count: int = Field(ge=0)
    scoped_session_zero_candidate_source_record_count: int = Field(ge=0)
    scoped_non_session_unresolved_source_record_count: int = Field(ge=0)
    scoped_candidate_relation_count: int = Field(ge=0)
    scoped_candidate_relation_to_included_instrument_count: int = Field(ge=0)
    action_exposure_record_count: int = Field(ge=0)
    resolved_action_exposure_record_count: int = Field(ge=0)
    unassigned_action_candidate_exposure_record_count: int = Field(ge=0)
    action_exposure_type_counts: tuple[tuple[str, str, int], ...]
    feature_action_path_relation_count: int = Field(ge=0)
    feature_action_unique_path_count: int = Field(ge=0)
    horizon_1_action_path_relation_count: int = Field(ge=0)
    horizon_1_action_unique_path_count: int = Field(ge=0)
    horizon_3_action_path_relation_count: int = Field(ge=0)
    horizon_3_action_unique_path_count: int = Field(ge=0)
    horizon_5_action_path_relation_count: int = Field(ge=0)
    horizon_5_action_unique_path_count: int = Field(ge=0)
    lifecycle_exposure_record_count: int = Field(ge=0)
    lifecycle_instrument_count: int = Field(ge=0)
    lifecycle_included_path_count: int = Field(ge=0)
    horizon_1_lifecycle_crossing_path_count: int = Field(ge=0)
    horizon_3_lifecycle_crossing_path_count: int = Field(ge=0)
    horizon_5_lifecycle_crossing_path_count: int = Field(ge=0)
    horizon_1_lifecycle_crossing_instrument_count: int = Field(ge=0)
    horizon_3_lifecycle_crossing_instrument_count: int = Field(ge=0)
    horizon_5_lifecycle_crossing_instrument_count: int = Field(ge=0)
    action_file: Literal["action-exposures.parquet"] = ACTION_FILE
    action_file_sha256: str = Field(pattern=_SHA256_PATTERN)
    action_file_bytes: int = Field(ge=1, le=MAXIMUM_ACTION_BYTES)
    action_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    lifecycle_file: Literal["lifecycle-exposures.parquet"] = LIFECYCLE_FILE
    lifecycle_file_sha256: str = Field(pattern=_SHA256_PATTERN)
    lifecycle_file_bytes: int = Field(ge=1, le=MAXIMUM_LIFECYCLE_BYTES)
    lifecycle_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    evidence_role: Literal["source_acquisition_priority_diagnostic_only"] = (
        "source_acquisition_priority_diagnostic_only"
    )
    unresolved_zero_candidate_rows_proven_irrelevant: Literal[False] = False
    strategy_trigger_count: Literal[0] = 0
    forward_outcome_count: Literal[0] = 0
    performance_metric_count: Literal[0] = 0
    parameter_selection_count: Literal[0] = 0
    cohort_selection_count: Literal[0] = 0
    stable_identity_assignment_count: Literal[0] = 0
    canonical_data_write_count: Literal[0] = 0
    historical_coverage_write_count: Literal[0] = 0
    research_admission_count: Literal[0] = 0
    candidate_write_count: Literal[0] = 0
    publication_count: Literal[0] = 0
    deployment_count: Literal[0] = 0
    scheduler_change_count: Literal[0] = 0
    external_request_count: Literal[0] = 0
    logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)

    @field_validator("evaluated_at")
    @classmethod
    def time_is_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @model_validator(mode="after")
    def reconcile(self) -> "StrongLeaderPullbackEvidenceBlockerCensusManifestV1":
        if (
            self.first_signal_session != STRONG_LEADER_PULLBACK_CENSUS_FIRST_SESSION
            or self.last_signal_session != STRONG_LEADER_PULLBACK_CENSUS_LAST_SESSION
            or self.signal_session_count != STRONG_LEADER_PULLBACK_CENSUS_SESSION_COUNT
            or self.universe_id != STRONG_LEADER_PULLBACK_CENSUS_PRIMARY_UNIVERSE
            or self.membership_methodology_version
            != STRONG_LEADER_PULLBACK_CENSUS_MEMBERSHIP_METHODOLOGY
        ):
            raise ValueError("strategy blocker census scope differs")
        if self.forward_horizons != _HORIZONS:
            raise ValueError("strategy blocker census horizons differ")
        if tuple(item.name for item in self.source_bindings) != tuple(
            sorted({item.name for item in self.source_bindings})
        ):
            raise ValueError("strategy blocker source bindings are not unique and ordered")
        if (
            self.resolved_action_exposure_record_count
            + self.unassigned_action_candidate_exposure_record_count
            != self.action_exposure_record_count
        ):
            raise ValueError("action exposure identity counts differ")
        if self.lifecycle_exposure_record_count != self.lifecycle_instrument_count:
            raise ValueError("lifecycle exposure count differs")
        values = self.model_dump(mode="json", exclude={"logical_fingerprint"})
        if self.logical_fingerprint != _fingerprint(values):
            raise ValueError("strategy blocker census fingerprint differs")
        return self


@dataclass(frozen=True, slots=True)
class StrongLeaderPullbackEvidenceBlockerCensusResult:
    output_root: Path
    manifest: StrongLeaderPullbackEvidenceBlockerCensusManifestV1
    action_records: tuple[ActionExposureV1, ...]
    lifecycle_records: tuple[LifecycleExposureV1, ...]
    manifest_sha256: str
    status: Literal["published", "already_present"]


def build_strong_leader_pullback_evidence_blocker_census(
    *,
    data_root: Path,
    development_census_root: Path,
    admission_decision_root: Path,
    resolution_shadow_output_root: Path,
    resolution_shadow_custody_root: Path,
    unresolved_census_output_root: Path,
    unresolved_census_custody_root: Path,
    residual_census_output_root: Path,
    residual_census_custody_root: Path,
    lifecycle_shadow_root: Path,
    lifecycle_shadow_custody_root: Path,
    lifecycle_anchor_dates: tuple[date, ...],
    output_root: Path,
    output_custody_root: Path,
    implementation_revision: str,
    evaluated_at: datetime,
) -> StrongLeaderPullbackEvidenceBlockerCensusResult:
    """Build one immutable, network-free, result-blind blocker census."""

    with _network_prohibited():
        return _build(
            data_root=data_root,
            development_census_root=development_census_root,
            admission_decision_root=admission_decision_root,
            resolution_shadow_output_root=resolution_shadow_output_root,
            resolution_shadow_custody_root=resolution_shadow_custody_root,
            unresolved_census_output_root=unresolved_census_output_root,
            unresolved_census_custody_root=unresolved_census_custody_root,
            residual_census_output_root=residual_census_output_root,
            residual_census_custody_root=residual_census_custody_root,
            lifecycle_shadow_root=lifecycle_shadow_root,
            lifecycle_shadow_custody_root=lifecycle_shadow_custody_root,
            lifecycle_anchor_dates=lifecycle_anchor_dates,
            output_root=output_root,
            output_custody_root=output_custody_root,
            implementation_revision=implementation_revision,
            evaluated_at=evaluated_at,
        )


def _build(
    *,
    data_root: Path,
    development_census_root: Path,
    admission_decision_root: Path,
    resolution_shadow_output_root: Path,
    resolution_shadow_custody_root: Path,
    unresolved_census_output_root: Path,
    unresolved_census_custody_root: Path,
    residual_census_output_root: Path,
    residual_census_custody_root: Path,
    lifecycle_shadow_root: Path,
    lifecycle_shadow_custody_root: Path,
    lifecycle_anchor_dates: tuple[date, ...],
    output_root: Path,
    output_custody_root: Path,
    implementation_revision: str,
    evaluated_at: datetime,
) -> StrongLeaderPullbackEvidenceBlockerCensusResult:
    if re.fullmatch(_REVISION_PATTERN, implementation_revision) is None:
        raise StrongLeaderPullbackEvidenceBlockerCensusError(
            "implementation revision is invalid"
        )
    if (
        not lifecycle_anchor_dates
        or lifecycle_anchor_dates != tuple(sorted(set(lifecycle_anchor_dates)))
    ):
        raise StrongLeaderPullbackEvidenceBlockerCensusError(
            "lifecycle anchors are empty, duplicated, or unordered"
        )
    root = _validated_data_root(data_root)
    target = _validated_output_target(output_root, output_custody_root)
    evaluated_at = normalize_utc_datetime(evaluated_at)
    development = read_development_coverage_census(
        output_root=development_census_root
    )
    admission = read_development_admission_decision(
        output_root=admission_decision_root
    )
    development_sha = _file_sha256(development_census_root / REPORT_FILE)
    admission_sha = _file_sha256(admission_decision_root / DECISION_FILE)
    if (
        admission.decision_status.value != "rejected_current_evidence"
        or admission.census_logical_fingerprint != development.logical_fingerprint
        or admission.census_physical_sha256 != development_sha
        or admission.admitted_cohort_selected
        or admission.development_authorized
        or development.contains_forward_outcomes
        or development.contains_performance_metrics
        or development.contains_strategy_triggers
        or development.admitted_cohort_selected
        or development.development_authorized
    ):
        raise StrongLeaderPullbackEvidenceBlockerCensusError(
            "development census or rejected admission binding differs"
        )
    calendar = ExchangeCalendar()
    sessions = calendar.sessions_in_range(
        STRONG_LEADER_PULLBACK_CENSUS_FIRST_SESSION,
        STRONG_LEADER_PULLBACK_CENSUS_LAST_SESSION,
    )
    if len(sessions) != STRONG_LEADER_PULLBACK_CENSUS_SESSION_COUNT:
        raise StrongLeaderPullbackEvidenceBlockerCensusError(
            "fixed strategy session range differs"
        )
    extended = calendar.sessions_before(sessions[0], 20) + sessions
    for _ in range(5):
        extended += (calendar.next_session(extended[-1]),)
    session_index = {item: index for index, item in enumerate(extended)}
    signals, membership_binding, primary_decisions = _read_included_paths(
        root=root,
        sessions=sessions,
        report=development,
        session_index=session_index,
    )
    if (
        sum(len(items) for items in signals.values())
        != development.raw_feature_path_complete_count
        or len(signals) != sum(
            item.raw_feature_path_complete_count > 0
            for item in development.instruments
        )
        or primary_decisions != development.primary_decision_count
    ):
        raise StrongLeaderPullbackEvidenceBlockerCensusError(
            "included strategy path population differs from development census"
        )

    shadow = read_historical_corporate_action_resolution_shadow(
        output_root=resolution_shadow_output_root,
        output_custody_root=resolution_shadow_custody_root,
    )
    unresolved = read_historical_corporate_action_unresolved_census_output(
        output_root=unresolved_census_output_root,
        output_custody_root=unresolved_census_custody_root,
    )
    residual = read_historical_corporate_action_residual_evidence_census(
        output_root=residual_census_output_root,
        output_custody_root=residual_census_custody_root,
    )
    if (
        unresolved.manifest.resolution_shadow_manifest_sha256
        != shadow.manifest_sha256
        or unresolved.manifest.resolution_shadow_logical_fingerprint
        != shadow.manifest.logical_fingerprint
        or residual.manifest.resolution_shadow_manifest_sha256
        != shadow.manifest_sha256
        or residual.manifest.resolution_shadow_logical_fingerprint
        != shadow.manifest.logical_fingerprint
        or residual.manifest.unresolved_census_manifest_sha256
        != unresolved.manifest_sha256
        or residual.manifest.unresolved_census_logical_fingerprint
        != unresolved.manifest.logical_fingerprint
    ):
        raise StrongLeaderPullbackEvidenceBlockerCensusError(
            "corporate-action evidence bindings differ"
        )
    lifecycle = tuple(
        read_historical_inactive_lifecycle_resolution_shadow(
            root=lifecycle_shadow_root,
            anchor_date=anchor,
            approved_custody_root=lifecycle_shadow_custody_root,
        )
        for anchor in lifecycle_anchor_dates
    )
    action_records, action_stats = _action_exposures(
        source_rows=shadow.records,
        unresolved_records=unresolved.records,
        residual_records=residual.records,
        signals=signals,
        session_index=session_index,
        scoped_sessions=frozenset(extended),
        scoped_first=extended[0],
        scoped_last=extended[-1],
    )
    lifecycle_records, lifecycle_stats = _lifecycle_exposures(
        lifecycle=lifecycle,
        signals=signals,
        sessions=extended,
    )
    action_table = pa.Table.from_pylist(
        [
            {
                **item.model_dump(mode="python"),
                "candidate_instrument_id": str(item.candidate_instrument_id),
            }
            for item in action_records
        ],
        schema=ACTION_SCHEMA,
    )
    lifecycle_table = pa.Table.from_pylist(
        [
            {
                **item.model_dump(mode="python"),
                "instrument_id": str(item.instrument_id),
            }
            for item in lifecycle_records
        ],
        schema=LIFECYCLE_SCHEMA,
    )

    if target.exists() or target.is_symlink():
        existing = read_strong_leader_pullback_evidence_blocker_census(
            output_root=target,
            output_custody_root=output_custody_root,
        )
        if (
            existing.action_records != action_records
            or existing.lifecycle_records != lifecycle_records
        ):
            raise StrongLeaderPullbackEvidenceBlockerCensusError(
                "existing strategy blocker census differs"
            )
        return existing

    partial = target.parent / f".{target.name}.partial.{os.getpid()}"
    if partial.exists() or partial.is_symlink():
        raise StrongLeaderPullbackEvidenceBlockerCensusError(
            "strategy blocker staging target exists"
        )
    partial.mkdir(mode=0o700)
    try:
        action_path = partial / ACTION_FILE
        lifecycle_path = partial / LIFECYCLE_FILE
        pq.write_table(action_table, action_path, compression="zstd", version="2.6")
        pq.write_table(lifecycle_table, lifecycle_path, compression="zstd", version="2.6")
        action_path.chmod(0o400)
        lifecycle_path.chmod(0o400)
        source_bindings = tuple(
            sorted(
                (
                    SourceBindingV1(
                        name="corporate_action_resolution_shadow",
                        manifest_sha256=shadow.manifest_sha256,
                        logical_fingerprint=shadow.manifest.logical_fingerprint,
                        record_count=shadow.manifest.mapped_record_count,
                    ),
                    SourceBindingV1(
                        name="corporate_action_unresolved_census",
                        manifest_sha256=unresolved.manifest_sha256,
                        logical_fingerprint=unresolved.manifest.logical_fingerprint,
                        record_count=unresolved.manifest.unresolved_typed_record_count,
                    ),
                    SourceBindingV1(
                        name="corporate_action_residual_evidence_census",
                        manifest_sha256=residual.manifest_sha256,
                        logical_fingerprint=residual.manifest.logical_fingerprint,
                        record_count=residual.manifest.residual_record_count,
                    ),
                    *(
                        SourceBindingV1(
                            name=f"inactive_lifecycle_{item.manifest.anchor_date.isoformat()}",
                            manifest_sha256=item.manifest_sha256,
                            logical_fingerprint=item.manifest.logical_fingerprint,
                            record_count=item.manifest.decision_artifact.record_count,
                        )
                        for item in lifecycle
                    ),
                ),
                key=lambda item: item.name,
            )
        )
        action_sha = _file_sha256(action_path)
        lifecycle_sha = _file_sha256(lifecycle_path)
        values = {
            "implementation_revision": implementation_revision,
            "evaluated_at": evaluated_at,
            "first_signal_session": sessions[0],
            "last_signal_session": sessions[-1],
            "signal_session_count": len(sessions),
            "universe_id": STRONG_LEADER_PULLBACK_CENSUS_PRIMARY_UNIVERSE,
            "membership_methodology_version": (
                STRONG_LEADER_PULLBACK_CENSUS_MEMBERSHIP_METHODOLOGY
            ),
            "development_census_sha256": development_sha,
            "development_census_logical_fingerprint": development.logical_fingerprint,
            "rejected_admission_sha256": admission_sha,
            "rejected_admission_logical_fingerprint": admission.logical_fingerprint,
            "source_bindings": source_bindings,
            "membership_binding_fingerprint": membership_binding,
            "primary_decision_count": primary_decisions,
            "included_path_count": sum(len(items) for items in signals.values()),
            "included_instrument_count": len(signals),
            **action_stats,
            **lifecycle_stats,
            "action_file_sha256": action_sha,
            "action_file_bytes": action_path.stat().st_size,
            "action_logical_fingerprint": _record_fingerprint(action_records),
            "lifecycle_file_sha256": lifecycle_sha,
            "lifecycle_file_bytes": lifecycle_path.stat().st_size,
            "lifecycle_logical_fingerprint": _record_fingerprint(lifecycle_records),
        }
        provisional = StrongLeaderPullbackEvidenceBlockerCensusManifestV1.model_construct(
            **values, logical_fingerprint="0" * 64
        )
        manifest = StrongLeaderPullbackEvidenceBlockerCensusManifestV1.model_validate(
            {
                **values,
                "logical_fingerprint": _fingerprint(
                    provisional.model_dump(
                        mode="json", exclude={"logical_fingerprint"}
                    )
                ),
            }
        )
        _write_exclusive(
            partial / MANIFEST_FILE,
            _json_bytes(manifest.model_dump(mode="json")),
        )
        _fsync_directory(partial)
        partial.replace(target)
        _fsync_directory(target.parent)
    except Exception:
        if partial.exists() and not partial.is_symlink() and partial.parent == target.parent:
            shutil.rmtree(partial)
            _fsync_directory(partial.parent)
        raise
    reread = read_strong_leader_pullback_evidence_blocker_census(
        output_root=target,
        output_custody_root=output_custody_root,
    )
    if reread.action_records != action_records or reread.lifecycle_records != lifecycle_records:
        raise StrongLeaderPullbackEvidenceBlockerCensusError(
            "strategy blocker census formal reread differs"
        )
    return StrongLeaderPullbackEvidenceBlockerCensusResult(
        output_root=target,
        manifest=reread.manifest,
        action_records=reread.action_records,
        lifecycle_records=reread.lifecycle_records,
        manifest_sha256=reread.manifest_sha256,
        status="published",
    )


def read_strong_leader_pullback_evidence_blocker_census(
    *, output_root: Path, output_custody_root: Path
) -> StrongLeaderPullbackEvidenceBlockerCensusResult:
    """Formally reread one completed output without reopening upstream sources."""

    root = _validated_completed_output(output_root, output_custody_root)
    if {item.name for item in root.iterdir()} != {
        ACTION_FILE,
        LIFECYCLE_FILE,
        MANIFEST_FILE,
    }:
        raise StrongLeaderPullbackEvidenceBlockerCensusError(
            "strategy blocker package members differ"
        )
    manifest_path = root / MANIFEST_FILE
    action_path = root / ACTION_FILE
    lifecycle_path = root / LIFECYCLE_FILE
    _require_regular_file(manifest_path, 0o400, MAXIMUM_MANIFEST_BYTES)
    _require_regular_file(action_path, 0o400, MAXIMUM_ACTION_BYTES)
    _require_regular_file(lifecycle_path, 0o400, MAXIMUM_LIFECYCLE_BYTES)
    try:
        manifest = StrongLeaderPullbackEvidenceBlockerCensusManifestV1.model_validate_json(
            manifest_path.read_bytes()
        )
        action_table = pq.ParquetFile(action_path).read()
        lifecycle_table = pq.ParquetFile(lifecycle_path).read()
    except Exception as exc:
        raise StrongLeaderPullbackEvidenceBlockerCensusError(
            "strategy blocker output is invalid"
        ) from exc
    if action_table.schema != ACTION_SCHEMA or lifecycle_table.schema != LIFECYCLE_SCHEMA:
        raise StrongLeaderPullbackEvidenceBlockerCensusError(
            "strategy blocker output schema differs"
        )
    try:
        actions = tuple(ActionExposureV1.model_validate(row) for row in action_table.to_pylist())
        lifecycle = tuple(
            LifecycleExposureV1.model_validate(row) for row in lifecycle_table.to_pylist()
        )
    except Exception as exc:
        raise StrongLeaderPullbackEvidenceBlockerCensusError(
            "strategy blocker records are invalid"
        ) from exc
    if (
        _file_sha256(action_path) != manifest.action_file_sha256
        or action_path.stat().st_size != manifest.action_file_bytes
        or _record_fingerprint(actions) != manifest.action_logical_fingerprint
        or _file_sha256(lifecycle_path) != manifest.lifecycle_file_sha256
        or lifecycle_path.stat().st_size != manifest.lifecycle_file_bytes
        or _record_fingerprint(lifecycle) != manifest.lifecycle_logical_fingerprint
    ):
        raise StrongLeaderPullbackEvidenceBlockerCensusError(
            "strategy blocker artifact binding differs"
        )
    _verify_output_aggregates(manifest, actions, lifecycle)
    return StrongLeaderPullbackEvidenceBlockerCensusResult(
        output_root=root,
        manifest=manifest,
        action_records=actions,
        lifecycle_records=lifecycle,
        manifest_sha256=_file_sha256(manifest_path),
        status="already_present",
    )


def _read_included_paths(
    *, root: Path, sessions: tuple[date, ...], report: object,
    session_index: dict[date, int]
) -> tuple[dict[UUID, tuple[int, ...]], str, int]:
    signals: defaultdict[UUID, list[int]] = defaultdict(list)
    bindings = []
    primary_decisions = 0
    report_sessions = {item.session_date: item for item in report.sessions}
    for session in sessions:
        current = read_canonical_research_universe_membership(
            data_root=root,
            methodology_version=STRONG_LEADER_PULLBACK_CENSUS_MEMBERSHIP_METHODOLOGY,
            session_date=session,
            read_records=True,
        )
        expected = report_sessions.get(session)
        if (
            expected is None
            or current.membership_manifest.logical_fingerprint
            != expected.membership_logical_fingerprint
            or current.membership_manifest.physical_sha256
            != expected.membership_physical_sha256
            or current.custody.membership_manifest_sha256
            != expected.membership_manifest_sha256
        ):
            raise StrongLeaderPullbackEvidenceBlockerCensusError(
                "Membership evidence differs from development census"
            )
        primary = tuple(
            item
            for item in current.records
            if item.universe_id == STRONG_LEADER_PULLBACK_CENSUS_PRIMARY_UNIVERSE
        )
        included = tuple(
            item
            for item in primary
            if item.disposition is UniverseMembershipDisposition.INCLUDED
        )
        if len(included) != expected.primary_included_count:
            raise StrongLeaderPullbackEvidenceBlockerCensusError(
                "Membership included count differs from development census"
            )
        primary_decisions += len(primary)
        for item in included:
            signals[item.instrument_id].append(session_index[session])
        bindings.append(
            {
                "session_date": session.isoformat(),
                "custody_sha256": current.custody_sha256,
                "manifest_sha256": current.custody.membership_manifest_sha256,
                "logical_fingerprint": current.membership_manifest.logical_fingerprint,
                "record_count": current.membership_manifest.record_count,
            }
        )
    return (
        {key: tuple(values) for key, values in signals.items()},
        _fingerprint(bindings),
        primary_decisions,
    )


def _action_exposures(
    *, source_rows: tuple[object, ...], unresolved_records: tuple[object, ...],
    residual_records: tuple[object, ...], signals: dict[UUID, tuple[int, ...]],
    session_index: dict[date, int], scoped_sessions: frozenset[date],
    scoped_first: date, scoped_last: date,
) -> tuple[tuple[ActionExposureV1, ...], dict[str, object]]:
    unresolved_by_ticker = {item.provider_ticker: item for item in unresolved_records}
    residual_by_key = {
        (item.source_action_id, item.source_revision): item
        for item in residual_records
    }
    records = []
    unique_paths = {"feature": set(), 1: set(), 3: set(), 5: set()}
    scoped_unresolved = 0
    scoped_zero = 0
    scoped_non_session = 0
    scoped_relations = 0
    scoped_relations_to_included = 0
    global_zero = 0
    for item in unresolved_records:
        if item.classification == "zero_historical_candidates":
            global_zero += item.unresolved_source_record_count
    for source in source_rows:
        index = session_index.get(source.effective_date)
        unresolved = source.instrument_resolution_status is ResolutionStatus.UNRESOLVED
        candidate_record = unresolved_by_ticker.get(source.provider_ticker) if unresolved else None
        if unresolved and scoped_first <= source.effective_date <= scoped_last:
            if source.effective_date in scoped_sessions:
                scoped_unresolved += 1
                if candidate_record is None or not candidate_record.candidates:
                    scoped_zero += 1
                else:
                    scoped_relations += len(candidate_record.candidates)
                    scoped_relations_to_included += sum(
                        candidate.instrument_id in signals
                        for candidate in candidate_record.candidates
                    )
            else:
                scoped_non_session += 1
        if index is None:
            continue
        if unresolved:
            candidates = () if candidate_record is None else candidate_record.candidates
        elif source.instrument_id is not None:
            candidates = (source,)
        else:
            candidates = ()
        for candidate in candidates:
            candidate_id = (
                candidate.instrument_id if unresolved else source.instrument_id
            )
            if candidate_id not in signals:
                continue
            counts = _path_counts(
                signal_indexes=signals[candidate_id], event_index=index
            )
            if not counts["feature"] and not counts[5]:
                continue
            for signal_index in signals[candidate_id]:
                path = (signal_index, str(candidate_id))
                if signal_index - 20 < index <= signal_index:
                    unique_paths["feature"].add(path)
                for horizon in _HORIZONS:
                    if signal_index < index <= signal_index + horizon:
                        unique_paths[horizon].add(path)
            if unresolved:
                residual = residual_by_key.get(
                    (source.source_action_id, source.source_revision)
                )
                if residual is None or candidate_record is None:
                    raise StrongLeaderPullbackEvidenceBlockerCensusError(
                        "unresolved action lacks residual evidence"
                    )
                record = ActionExposureV1(
                    source_action_id=source.source_action_id,
                    source_revision=source.source_revision,
                    provider_ticker=source.provider_ticker,
                    effective_date=source.effective_date,
                    action_type=source.action_type.value,
                    semantic_requirement=_semantic_requirement(source.action_type.value),
                    identity_evidence_kind="history_candidate_unassigned",
                    candidate_instrument_id=candidate_id,
                    historical_candidate_classification=candidate_record.classification,
                    exact_date_failure_reason=residual.exact_date_failure_reason,
                    feature_path_count=counts["feature"],
                    horizon_1_path_count=counts[1],
                    horizon_3_path_count=counts[3],
                    horizon_5_path_count=counts[5],
                    inactive_source_state=residual.inactive_source_state,
                    inactive_source_type_codes=residual.inactive_source_type_codes,
                    finra_exact_date_symbol_occurrence_count=(
                        residual.finra_exact_date_symbol_occurrence_count
                    ),
                    finra_exact_numeric_occurrence_count=(
                        residual.finra_exact_numeric_occurrence_count
                    ),
                    finra_flag_codes=residual.finra_flag_codes,
                )
            else:
                record = ActionExposureV1(
                    source_action_id=source.source_action_id,
                    source_revision=source.source_revision,
                    provider_ticker=source.provider_ticker,
                    effective_date=source.effective_date,
                    action_type=source.action_type.value,
                    semantic_requirement=_semantic_requirement(source.action_type.value),
                    identity_evidence_kind="exact_event_date_resolved",
                    candidate_instrument_id=candidate_id,
                    historical_candidate_classification="exact_event_date_resolved",
                    feature_path_count=counts["feature"],
                    horizon_1_path_count=counts[1],
                    horizon_3_path_count=counts[3],
                    horizon_5_path_count=counts[5],
                    finra_exact_date_symbol_occurrence_count=0,
                    finra_exact_numeric_occurrence_count=0,
                )
            records.append(record)
    ordered = tuple(
        sorted(
            records,
            key=lambda item: (
                item.source_action_id,
                item.source_revision,
                str(item.candidate_instrument_id),
            ),
        )
    )
    keys = tuple(
        (item.source_action_id, item.source_revision, item.candidate_instrument_id)
        for item in ordered
    )
    if len(keys) != len(set(keys)):
        raise StrongLeaderPullbackEvidenceBlockerCensusError(
            "action exposure records are duplicated"
        )
    identity_counts = Counter(item.identity_evidence_kind for item in ordered)
    type_counts = Counter(
        (item.identity_evidence_kind, item.action_type) for item in ordered
    )
    return ordered, {
        "global_unresolved_source_record_count": len(residual_records),
        "global_zero_candidate_source_record_count": global_zero,
        "scoped_session_unresolved_source_record_count": scoped_unresolved,
        "scoped_session_zero_candidate_source_record_count": scoped_zero,
        "scoped_non_session_unresolved_source_record_count": scoped_non_session,
        "scoped_candidate_relation_count": scoped_relations,
        "scoped_candidate_relation_to_included_instrument_count": (
            scoped_relations_to_included
        ),
        "action_exposure_record_count": len(ordered),
        "resolved_action_exposure_record_count": identity_counts[
            "exact_event_date_resolved"
        ],
        "unassigned_action_candidate_exposure_record_count": identity_counts[
            "history_candidate_unassigned"
        ],
        "action_exposure_type_counts": tuple(
            (kind, action, count)
            for (kind, action), count in sorted(type_counts.items())
        ),
        "feature_action_path_relation_count": sum(
            item.feature_path_count for item in ordered
        ),
        "feature_action_unique_path_count": len(unique_paths["feature"]),
        **{
            f"horizon_{horizon}_action_path_relation_count": sum(
                getattr(item, f"horizon_{horizon}_path_count") for item in ordered
            )
            for horizon in _HORIZONS
        },
        **{
            f"horizon_{horizon}_action_unique_path_count": len(
                unique_paths[horizon]
            )
            for horizon in _HORIZONS
        },
    }


def _path_counts(
    *, signal_indexes: tuple[int, ...], event_index: int
) -> dict[object, int]:
    left = bisect.bisect_left(signal_indexes, event_index - 5)
    right = bisect.bisect_right(signal_indexes, event_index + 19)
    counts: Counter[object] = Counter()
    for signal_index in signal_indexes[left:right]:
        if signal_index - 20 < event_index <= signal_index:
            counts["feature"] += 1
        for horizon in _HORIZONS:
            if signal_index < event_index <= signal_index + horizon:
                counts[horizon] += 1
    return {"feature": counts["feature"], **{h: counts[h] for h in _HORIZONS}}


def _lifecycle_exposures(
    *, lifecycle: tuple[object, ...], signals: dict[UUID, tuple[int, ...]],
    sessions: tuple[date, ...]
) -> tuple[tuple[LifecycleExposureV1, ...], dict[str, object]]:
    windows: defaultdict[
        tuple[UUID, date, date, date], set[date]
    ] = defaultdict(set)
    for result in lifecycle:
        for decision in result.decisions:
            if decision.disposition is not InactiveLifecycleDisposition.REVIEW_CANDIDATE:
                continue
            key = (
                decision.canonical_instrument_id,
                decision.canonical_first_observed_date,
                decision.canonical_last_observed_date,
                decision.effective_date_candidate,
            )
            if any(value is None for value in key):
                raise StrongLeaderPullbackEvidenceBlockerCensusError(
                    "lifecycle review candidate lacks required dates or identity"
                )
            windows[key].add(result.manifest.anchor_date)
    records = []
    crossing_paths = {horizon: set() for horizon in _HORIZONS}
    crossing_instruments = {horizon: set() for horizon in _HORIZONS}
    for (instrument_id, first, last, delist), anchors in windows.items():
        signal_indexes = signals.get(instrument_id)
        if not signal_indexes:
            continue
        feature_outside = 0
        crosses = Counter()
        contains = Counter()
        for signal_index in signal_indexes:
            if sessions[signal_index - 20] < first or sessions[signal_index] > last:
                feature_outside += 1
            for horizon in _HORIZONS:
                if sessions[signal_index + horizon] > last:
                    crosses[horizon] += 1
                    crossing_paths[horizon].add((signal_index, instrument_id))
                    crossing_instruments[horizon].add(instrument_id)
                if sessions[signal_index] < delist <= sessions[signal_index + horizon]:
                    contains[horizon] += 1
        records.append(
            LifecycleExposureV1(
                instrument_id=instrument_id,
                source_anchor_dates=tuple(sorted(anchors)),
                canonical_first_observed_date=first,
                canonical_last_observed_date=last,
                provider_delist_date_candidate=delist,
                included_path_count=len(signal_indexes),
                feature_window_outside_observed_span_path_count=feature_outside,
                horizon_1_crosses_last_observed_path_count=crosses[1],
                horizon_3_crosses_last_observed_path_count=crosses[3],
                horizon_5_crosses_last_observed_path_count=crosses[5],
                horizon_1_contains_delist_candidate_path_count=contains[1],
                horizon_3_contains_delist_candidate_path_count=contains[3],
                horizon_5_contains_delist_candidate_path_count=contains[5],
            )
        )
    ordered = tuple(
        sorted(
            records,
            key=lambda item: (
                str(item.instrument_id),
                item.canonical_first_observed_date,
                item.canonical_last_observed_date,
                item.provider_delist_date_candidate,
            ),
        )
    )
    return ordered, {
        "lifecycle_exposure_record_count": len(ordered),
        "lifecycle_instrument_count": len({item.instrument_id for item in ordered}),
        "lifecycle_included_path_count": sum(item.included_path_count for item in ordered),
        **{
            f"horizon_{horizon}_lifecycle_crossing_path_count": len(
                crossing_paths[horizon]
            )
            for horizon in _HORIZONS
        },
        **{
            f"horizon_{horizon}_lifecycle_crossing_instrument_count": len(
                crossing_instruments[horizon]
            )
            for horizon in _HORIZONS
        },
    }


def _verify_output_aggregates(
    manifest: StrongLeaderPullbackEvidenceBlockerCensusManifestV1,
    actions: tuple[ActionExposureV1, ...],
    lifecycle: tuple[LifecycleExposureV1, ...],
) -> None:
    identity_counts = Counter(item.identity_evidence_kind for item in actions)
    type_counts = Counter((item.identity_evidence_kind, item.action_type) for item in actions)
    expected = {
        "action_exposure_record_count": len(actions),
        "resolved_action_exposure_record_count": identity_counts[
            "exact_event_date_resolved"
        ],
        "unassigned_action_candidate_exposure_record_count": identity_counts[
            "history_candidate_unassigned"
        ],
        "action_exposure_type_counts": tuple(
            (kind, action, count)
            for (kind, action), count in sorted(type_counts.items())
        ),
        "feature_action_path_relation_count": sum(
            item.feature_path_count for item in actions
        ),
        **{
            f"horizon_{horizon}_action_path_relation_count": sum(
                getattr(item, f"horizon_{horizon}_path_count") for item in actions
            )
            for horizon in _HORIZONS
        },
        "lifecycle_exposure_record_count": len(lifecycle),
        "lifecycle_instrument_count": len({item.instrument_id for item in lifecycle}),
        "lifecycle_included_path_count": sum(
            item.included_path_count for item in lifecycle
        ),
    }
    if any(getattr(manifest, key) != value for key, value in expected.items()):
        raise StrongLeaderPullbackEvidenceBlockerCensusError(
            "strategy blocker output aggregates differ"
        )


def _semantic_requirement(action_type: str) -> str:
    return (
        "event_context_required"
        if action_type == "cash_dividend"
        else "price_share_adjustment_required"
    )


def _validated_data_root(path: Path) -> Path:
    if not path.is_absolute() or path.is_symlink() or not path.is_dir():
        raise StrongLeaderPullbackEvidenceBlockerCensusError(
            "canonical data root is unavailable"
        )
    root = path.resolve(strict=True)
    if root != APPROVED_DATA_ROOT or path != root:
        raise StrongLeaderPullbackEvidenceBlockerCensusError(
            "canonical data root is not the approved Dell root"
        )
    return root


def _validated_output_target(path: Path, custody_root: Path) -> Path:
    root = custody_root.absolute()
    target = path.absolute()
    if (
        root.is_symlink()
        or not root.is_dir()
        or root.resolve(strict=True) != root
        or root.stat().st_uid != os.getuid()
        or stat.S_IMODE(root.stat().st_mode) != 0o700
        or target.parent != root
        or re.fullmatch(_BUILD_NAME_PATTERN, target.name) is None
    ):
        raise StrongLeaderPullbackEvidenceBlockerCensusError(
            "strategy blocker output custody boundary differs"
        )
    if target.exists() or target.is_symlink():
        if (
            target.is_symlink()
            or not target.is_dir()
            or target.resolve(strict=True) != target
            or target.stat().st_uid != os.getuid()
            or stat.S_IMODE(target.stat().st_mode) != 0o700
        ):
            raise StrongLeaderPullbackEvidenceBlockerCensusError(
                "strategy blocker output target is unsafe"
            )
    return target


def _validated_completed_output(path: Path, custody_root: Path) -> Path:
    target = _validated_output_target(path, custody_root)
    if not target.is_dir():
        raise StrongLeaderPullbackEvidenceBlockerCensusError(
            "completed strategy blocker output is unavailable"
        )
    return target


def _require_regular_file(path: Path, mode: int, maximum_bytes: int) -> None:
    if path.is_symlink() or not path.is_file():
        raise StrongLeaderPullbackEvidenceBlockerCensusError(
            "strategy blocker output file is unsafe"
        )
    metadata = path.stat()
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_uid != os.getuid()
        or stat.S_IMODE(metadata.st_mode) != mode
        or not 0 < metadata.st_size <= maximum_bytes
    ):
        raise StrongLeaderPullbackEvidenceBlockerCensusError(
            "strategy blocker output file custody differs"
        )


def _write_exclusive(path: Path, payload: bytes) -> None:
    if len(payload) > MAXIMUM_MANIFEST_BYTES:
        raise StrongLeaderPullbackEvidenceBlockerCensusError(
            "strategy blocker manifest exceeds byte ceiling"
        )
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o400,
    )
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    except Exception:
        if path.exists() and not path.is_symlink():
            path.unlink()
        raise


def _record_fingerprint(records: tuple[object, ...]) -> str:
    digest = hashlib.sha256()
    for item in records:
        digest.update(_json_bytes(item.model_dump(mode="json")))
    return digest.hexdigest()


def _fingerprint(value: object) -> str:
    return hashlib.sha256(_json_bytes(value)).hexdigest()


def _json_bytes(value: object) -> bytes:
    return (
        json.dumps(
            to_jsonable_python(value),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
        + b"\n"
    )


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


@contextmanager
def _network_prohibited() -> Iterator[None]:
    original_connect = socket.socket.connect
    original_create_connection = socket.create_connection

    def reject(*_args: object, **_kwargs: object) -> None:
        raise StrongLeaderPullbackEvidenceBlockerCensusError(
            "network access is prohibited for the strategy blocker census"
        )

    socket.socket.connect = reject  # type: ignore[method-assign]
    socket.create_connection = reject  # type: ignore[assignment]
    try:
        yield
    finally:
        socket.socket.connect = original_connect  # type: ignore[method-assign]
        socket.create_connection = original_create_connection
