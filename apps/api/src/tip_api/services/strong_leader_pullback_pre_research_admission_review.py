"""Final outcome-blind data gate before the first strategy research run."""

from __future__ import annotations

import os
import re
import shutil
import stat
from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from tip_api.contracts.common import normalize_utc_datetime
from tip_api.persistence.development_admission_decision import (
    DECISION_FILE,
    read_development_admission_decision,
)
from tip_api.persistence.development_coverage_census import (
    REPORT_FILE as DEVELOPMENT_REPORT_FILE,
    read_development_coverage_census,
)
from tip_api.persistence.parquet.canonical_split_adjustment import (
    read_canonical_split_adjustment_publication,
)
from tip_api.services import canonical_split_coverage_diagnostic as split_diagnostic
from tip_api.services import strong_leader_pullback_evidence_blocker_census as blocker_reader
from tip_api.services import strong_leader_pullback_sec_document_content_census as base
from tip_api.services import strong_leader_pullback_sec_document_source as source_base
from tip_api.services import strong_leader_pullback_terminal_gap_census_v4 as terminal_reader


CONTRACT_VERSION = "strong-leader-pullback-pre-research-admission-review/1.0"
REPORT_FILE = "pre-research-admission-review.json"
MAXIMUM_REPORT_BYTES = 512 * 1024
_SHA256_PATTERN = r"^[0-9a-f]{64}$"
_REVISION_PATTERN = r"^[0-9a-f]{40}$"
_OUTPUT_NAME_PATTERN = r"^review=[A-Za-z0-9._-]+$"
_FAMILY_ORDER = (
    "eod_price_bar",
    "point_in_time_identity",
    "universe_membership",
    "corporate_action",
    "adjustment_ledger",
    "instrument_lifecycle",
    "terminal_reference",
    "cost_model",
    "historical_coverage",
)


class StrongLeaderPullbackPreResearchAdmissionReviewError(RuntimeError):
    """Raised when the pre-research decision cannot be proven."""


class _FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class DatasetFamilyReviewV1(_FrozenModel):
    family: Literal[
        "eod_price_bar",
        "point_in_time_identity",
        "universe_membership",
        "corporate_action",
        "adjustment_ledger",
        "instrument_lifecycle",
        "terminal_reference",
        "cost_model",
        "historical_coverage",
    ]
    development_required: bool
    status: Literal[
        "complete_reconstruction_input",
        "reconstructed_not_as_operated",
        "partial_bounded_source_only",
        "partial_reference_evidence",
        "scenario_mechanics_only",
        "absent",
    ]
    development_ready: bool
    evidence_fingerprint: str | None = Field(default=None, pattern=_SHA256_PATTERN)
    reason_codes: tuple[str, ...] = Field(min_length=1)

    @field_validator("reason_codes", mode="before")
    @classmethod
    def codes_are_ordered(cls, value: object) -> tuple[str, ...]:
        values = tuple(value)  # type: ignore[arg-type]
        if values != tuple(sorted(set(values))) or any(not item for item in values):
            raise ValueError("family review reasons differ")
        return values


class StrongLeaderPullbackPreResearchAdmissionReviewV1(_FrozenModel):
    contract_version: Literal[
        "strong-leader-pullback-pre-research-admission-review/1.0"
    ] = CONTRACT_VERSION
    decision_status: Literal["rejected_data_blocked"] = "rejected_data_blocked"
    implementation_revision: str = Field(pattern=_REVISION_PATTERN)
    evaluated_at: datetime
    first_signal_session: Literal["2025-06-23"] = "2025-06-23"
    last_signal_session: Literal["2026-08-12"] = "2026-08-12"
    signal_session_count: Literal[287] = 287
    minimum_complete_session_count: Literal[252] = 252
    complete_cross_section_session_count: Literal[0] = 0
    included_path_count: Literal[437402] = 437402
    complete_evidence_path_count: Literal[0] = 0
    development_census_sha256: str = Field(pattern=_SHA256_PATTERN)
    development_census_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    prior_admission_sha256: str = Field(pattern=_SHA256_PATTERN)
    prior_admission_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    blocker_census_manifest_sha256: str = Field(pattern=_SHA256_PATTERN)
    blocker_census_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    membership_binding_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    membership_session_count: Literal[287] = 287
    membership_as_operated: Literal[False] = False
    action_exposure_record_count: Literal[4643] = 4643
    resolved_action_exposure_record_count: Literal[4623] = 4623
    unassigned_action_exposure_record_count: Literal[20] = 20
    unassigned_split_like_exposure_record_count: Literal[1] = 1
    split_diagnostic_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    split_diagnostic_source_session_count: int = Field(ge=287)
    known_split_residual_extreme_count: Literal[0] = 0
    unexplained_price_discontinuity_count: Literal[387] = 387
    unexplained_price_discontinuity_instrument_count: Literal[321] = 321
    adjustment_publication_sha256: str = Field(pattern=_SHA256_PATTERN)
    adjustment_publication_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    adjustment_record_count: Literal[101321] = 101321
    adjustment_clear_record_count: Literal[98291] = 98291
    adjustment_quarantined_record_count: Literal[3030] = 3030
    absent_adjustment_row_neutrality_authorized: Literal[False] = False
    lifecycle_exposure_instrument_count: Literal[89] = 89
    lifecycle_horizon_5_crossing_instrument_count: Literal[64] = 64
    lifecycle_horizon_5_crossing_path_count: Literal[252] = 252
    terminal_census_report_sha256: str = Field(pattern=_SHA256_PATTERN)
    terminal_census_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    terminal_population_instrument_count: Literal[65] = 65
    terminal_reference_documented_instrument_count: Literal[47] = 47
    terminal_reference_gap_instrument_count: Literal[18] = 18
    terminal_reference_documented_horizon_5_path_count: Literal[214] = 214
    terminal_reference_gap_horizon_5_path_count: Literal[88] = 88
    family_reviews: tuple[DatasetFamilyReviewV1, ...] = Field(min_length=9, max_length=9)
    blocker_codes: tuple[str, ...] = Field(min_length=1)
    limitation_codes: tuple[str, ...] = Field(min_length=1)
    required_external_capabilities: tuple[str, ...] = Field(min_length=1)
    next_action: Literal[
        "acquire_targeted_point_in_time_lifecycle_and_action_evidence"
    ] = "acquire_targeted_point_in_time_lifecycle_and_action_evidence"
    historical_coverage_manifest_published: Literal[False] = False
    development_authorized: Literal[False] = False
    true_return_labels_authorized: Literal[False] = False
    strategy_research_started: Literal[False] = False
    strategy_trigger_count: Literal[0] = 0
    forward_outcome_count: Literal[0] = 0
    performance_metric_count: Literal[0] = 0
    parameter_selection_count: Literal[0] = 0
    canonical_data_write_count: Literal[0] = 0
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

    @field_validator(
        "blocker_codes", "limitation_codes", "required_external_capabilities",
        mode="before",
    )
    @classmethod
    def ordered_text(cls, value: object) -> tuple[str, ...]:
        values = tuple(value)  # type: ignore[arg-type]
        if values != tuple(sorted(set(values))) or any(not item for item in values):
            raise ValueError("pre-research review codes differ")
        return values

    @model_validator(mode="after")
    def report_reconciles(self) -> "StrongLeaderPullbackPreResearchAdmissionReviewV1":
        if (
            tuple(item.family for item in self.family_reviews) != _FAMILY_ORDER
            or self.resolved_action_exposure_record_count
            + self.unassigned_action_exposure_record_count
            != self.action_exposure_record_count
            or self.adjustment_clear_record_count
            + self.adjustment_quarantined_record_count
            != self.adjustment_record_count
            or self.terminal_reference_documented_instrument_count
            + self.terminal_reference_gap_instrument_count
            != self.terminal_population_instrument_count
            or self.terminal_reference_documented_horizon_5_path_count
            + self.terminal_reference_gap_horizon_5_path_count
            != 302
            or not any(
                item.development_required and not item.development_ready
                for item in self.family_reviews
            )
            or self.blocker_codes != _blocker_codes()
            or self.limitation_codes != _limitation_codes()
            or self.required_external_capabilities != _required_external_capabilities()
            or self.logical_fingerprint
            != base._fingerprint(
                self.model_dump(mode="json", exclude={"logical_fingerprint"})
            )
        ):
            raise ValueError("pre-research admission review differs")
        return self


class StrongLeaderPullbackPreResearchAdmissionReviewResult(_FrozenModel):
    output_root: Path
    report: StrongLeaderPullbackPreResearchAdmissionReviewV1
    report_sha256: str = Field(pattern=_SHA256_PATTERN)
    status: Literal["published", "already_present"]


def build_strong_leader_pullback_pre_research_admission_review(
    *,
    development_census_root: Path,
    prior_admission_root: Path,
    blocker_census_root: Path,
    blocker_census_custody_root: Path,
    terminal_census_root: Path,
    terminal_census_custody_root: Path,
    data_root: Path,
    canonical_action_publication_root: Path,
    adjustment_publication_root: Path,
    eod_evidence_path: Path,
    output_root: Path,
    output_custody_root: Path,
    implementation_revision: str,
    evaluated_at: datetime,
) -> StrongLeaderPullbackPreResearchAdmissionReviewResult:
    if re.fullmatch(_REVISION_PATTERN, implementation_revision) is None:
        raise StrongLeaderPullbackPreResearchAdmissionReviewError(
            "pre-research review revision differs"
        )
    development = read_development_coverage_census(
        output_root=development_census_root
    )
    prior_admission = read_development_admission_decision(
        output_root=prior_admission_root
    )
    blocker = blocker_reader.read_strong_leader_pullback_evidence_blocker_census(
        output_root=blocker_census_root,
        output_custody_root=blocker_census_custody_root,
    )
    terminal = terminal_reader.read_strong_leader_pullback_terminal_gap_census_v4(
        output_root=terminal_census_root,
        output_custody_root=terminal_census_custody_root,
    )
    adjustment = read_canonical_split_adjustment_publication(
        data_root=data_root,
        publication_root=adjustment_publication_root,
    )
    diagnostic = split_diagnostic.diagnose_canonical_split_coverage(
        data_root=data_root,
        canonical_action_publication_root=canonical_action_publication_root,
        eod_evidence_path=eod_evidence_path,
        source_revision=implementation_revision,
        calculated_at=evaluated_at,
    )
    report = _build_report(
        development=development,
        development_sha256=base._sha256_bytes(
            (development_census_root / DEVELOPMENT_REPORT_FILE).read_bytes()
        ),
        prior_admission=prior_admission,
        prior_admission_sha256=base._sha256_bytes(
            (prior_admission_root / DECISION_FILE).read_bytes()
        ),
        blocker=blocker,
        terminal=terminal,
        adjustment=adjustment,
        diagnostic=diagnostic,
        implementation_revision=implementation_revision,
        evaluated_at=evaluated_at,
    )
    return _write_report(
        output_root=output_root,
        output_custody_root=output_custody_root,
        report=report,
    )


def read_strong_leader_pullback_pre_research_admission_review(
    *, output_root: Path, output_custody_root: Path
) -> StrongLeaderPullbackPreResearchAdmissionReviewResult:
    root = _validated_completed_output(output_root, output_custody_root)
    if {item.name for item in root.iterdir()} != {REPORT_FILE}:
        raise StrongLeaderPullbackPreResearchAdmissionReviewError(
            "pre-research review package members differ"
        )
    path = root / REPORT_FILE
    source_base._require_regular_file(path, 0o400, MAXIMUM_REPORT_BYTES)
    raw = path.read_bytes()
    try:
        report = StrongLeaderPullbackPreResearchAdmissionReviewV1.model_validate_json(
            raw
        )
    except Exception as exc:
        raise StrongLeaderPullbackPreResearchAdmissionReviewError(
            "pre-research review report is invalid"
        ) from exc
    if raw != base._json_bytes(report.model_dump(mode="json")):
        raise StrongLeaderPullbackPreResearchAdmissionReviewError(
            "pre-research review bytes differ"
        )
    return StrongLeaderPullbackPreResearchAdmissionReviewResult(
        output_root=root,
        report=report,
        report_sha256=base._sha256_bytes(raw),
        status="already_present",
    )


def _build_report(
    *, development: object, development_sha256: str,
    prior_admission: object, prior_admission_sha256: str,
    blocker: object, terminal: object, adjustment: object,
    diagnostic: split_diagnostic.CanonicalSplitCoverageDiagnosticReport,
    implementation_revision: str, evaluated_at: datetime,
) -> StrongLeaderPullbackPreResearchAdmissionReviewV1:
    blocker_manifest = blocker.manifest
    terminal_report = terminal.report
    adjustment_report = adjustment.publication
    if (
        prior_admission.census_logical_fingerprint != development.logical_fingerprint
        or blocker_manifest.development_census_logical_fingerprint
        != development.logical_fingerprint
        or blocker_manifest.rejected_admission_logical_fingerprint
        != prior_admission.logical_fingerprint
        or blocker_manifest.signal_session_count != development.session_count
        or blocker_manifest.included_path_count
        != development.raw_feature_path_complete_count
        or diagnostic.first_session > str(development.first_session)
        or diagnostic.last_session < str(development.last_session)
        or diagnostic.canonical_action_publication_fingerprint
        != adjustment_report.canonical_action_publication_fingerprint
        or diagnostic.eod_evidence_fingerprint
        != adjustment_report.eod_evidence_fingerprint
    ):
        raise StrongLeaderPullbackPreResearchAdmissionReviewError(
            "pre-research upstream evidence does not reconcile"
        )
    unassigned_split_like = sum(
        item.action_type != "cash_dividend"
        for item in blocker.action_records
        if item.identity_evidence_kind == "history_candidate_unassigned"
    )
    values = {
        "implementation_revision": implementation_revision,
        "evaluated_at": normalize_utc_datetime(evaluated_at),
        "first_signal_session": str(development.first_session),
        "last_signal_session": str(development.last_session),
        "signal_session_count": development.session_count,
        "minimum_complete_session_count": prior_admission.minimum_admitted_session_count,
        "complete_cross_section_session_count": (
            prior_admission.complete_cross_section_session_count
        ),
        "included_path_count": blocker_manifest.included_path_count,
        "complete_evidence_path_count": development.all_required_evidence_complete_count,
        "development_census_sha256": development_sha256,
        "development_census_logical_fingerprint": development.logical_fingerprint,
        "prior_admission_sha256": prior_admission_sha256,
        "prior_admission_logical_fingerprint": prior_admission.logical_fingerprint,
        "blocker_census_manifest_sha256": blocker.manifest_sha256,
        "blocker_census_logical_fingerprint": blocker_manifest.logical_fingerprint,
        "membership_binding_fingerprint": blocker_manifest.membership_binding_fingerprint,
        "membership_session_count": blocker_manifest.signal_session_count,
        "membership_as_operated": blocker_manifest.as_operated,
        "action_exposure_record_count": blocker_manifest.action_exposure_record_count,
        "resolved_action_exposure_record_count": (
            blocker_manifest.resolved_action_exposure_record_count
        ),
        "unassigned_action_exposure_record_count": (
            blocker_manifest.unassigned_action_candidate_exposure_record_count
        ),
        "split_diagnostic_fingerprint": diagnostic.logical_fingerprint,
        "split_diagnostic_source_session_count": diagnostic.source_session_count,
        "known_split_residual_extreme_count": (
            diagnostic.active_split_residual_extreme_count
        ),
        "unexplained_price_discontinuity_count": (
            diagnostic.unexplained_price_discontinuity_count
        ),
        "unexplained_price_discontinuity_instrument_count": (
            diagnostic.unexplained_price_discontinuity_instrument_count
        ),
        "adjustment_publication_sha256": adjustment.manifest_sha256,
        "adjustment_publication_fingerprint": adjustment_report.logical_fingerprint,
        "adjustment_record_count": adjustment_report.record_count,
        "adjustment_clear_record_count": adjustment_report.clear_record_count,
        "adjustment_quarantined_record_count": (
            adjustment_report.quarantined_record_count
        ),
        "absent_adjustment_row_neutrality_authorized": (
            adjustment_report.absent_row_neutrality_authorized
        ),
        "unassigned_split_like_exposure_record_count": unassigned_split_like,
        "lifecycle_exposure_instrument_count": (
            blocker_manifest.lifecycle_instrument_count
        ),
        "lifecycle_horizon_5_crossing_instrument_count": (
            blocker_manifest.horizon_5_lifecycle_crossing_instrument_count
        ),
        "lifecycle_horizon_5_crossing_path_count": (
            blocker_manifest.horizon_5_lifecycle_crossing_path_count
        ),
        "terminal_census_report_sha256": terminal.report_sha256,
        "terminal_census_logical_fingerprint": terminal_report.logical_fingerprint,
        "terminal_population_instrument_count": (
            terminal_report.population_instrument_count
        ),
        "terminal_reference_documented_instrument_count": (
            terminal_report.reference_documented_instrument_count
        ),
        "terminal_reference_gap_instrument_count": (
            terminal_report.remaining_gap_instrument_count
        ),
        "terminal_reference_documented_horizon_5_path_count": (
            terminal_report.documented_horizon_5_crossing_path_count
        ),
        "terminal_reference_gap_horizon_5_path_count": (
            terminal_report.remaining_horizon_5_crossing_path_count
        ),
        "family_reviews": _family_reviews(
            development=development,
            blocker_manifest=blocker_manifest,
            terminal_report=terminal_report,
            adjustment_report=adjustment_report,
        ),
        "blocker_codes": _blocker_codes(),
        "limitation_codes": _limitation_codes(),
        "required_external_capabilities": _required_external_capabilities(),
    }
    provisional = StrongLeaderPullbackPreResearchAdmissionReviewV1.model_construct(
        **values, logical_fingerprint="0" * 64
    )
    return StrongLeaderPullbackPreResearchAdmissionReviewV1.model_validate(
        {
            **values,
            "logical_fingerprint": base._fingerprint(
                provisional.model_dump(mode="json", exclude={"logical_fingerprint"})
            ),
        }
    )


def _family_reviews(
    *, development: object, blocker_manifest: object,
    terminal_report: object, adjustment_report: object,
) -> tuple[DatasetFamilyReviewV1, ...]:
    development_evidence = {
        item.family: item for item in development.dataset_evidence
    }
    return (
        DatasetFamilyReviewV1(
            family="eod_price_bar", development_required=True,
            status="complete_reconstruction_input", development_ready=True,
            evidence_fingerprint=development_evidence["eod_price_bar"].logical_fingerprint,
            reason_codes=("fixed_strategy_interval_physically_bound",),
        ),
        DatasetFamilyReviewV1(
            family="point_in_time_identity", development_required=True,
            status="complete_reconstruction_input", development_ready=True,
            evidence_fingerprint=development_evidence["point_in_time_identity"].logical_fingerprint,
            reason_codes=("stable_instrument_id_bound_for_fixed_interval",),
        ),
        DatasetFamilyReviewV1(
            family="universe_membership", development_required=True,
            status="reconstructed_not_as_operated", development_ready=True,
            evidence_fingerprint=blocker_manifest.membership_binding_fingerprint,
            reason_codes=("development_only", "latest_vintage_not_as_operated"),
        ),
        DatasetFamilyReviewV1(
            family="corporate_action", development_required=True,
            status="partial_bounded_source_only", development_ready=False,
            evidence_fingerprint=blocker_manifest.action_logical_fingerprint,
            reason_codes=(
                "absence_neutrality_unproven",
                "one_split_like_path_exposure_unassigned",
            ),
        ),
        DatasetFamilyReviewV1(
            family="adjustment_ledger", development_required=True,
            status="partial_bounded_source_only", development_ready=False,
            evidence_fingerprint=adjustment_report.logical_fingerprint,
            reason_codes=(
                "affected_rows_only",
                "omitted_factor_one_rows_unauthorized",
                "total_return_unauthorized",
            ),
        ),
        DatasetFamilyReviewV1(
            family="instrument_lifecycle", development_required=True,
            status="partial_bounded_source_only", development_ready=False,
            evidence_fingerprint=blocker_manifest.lifecycle_logical_fingerprint,
            reason_codes=("canonical_terminal_outcomes_absent",),
        ),
        DatasetFamilyReviewV1(
            family="terminal_reference", development_required=True,
            status="partial_reference_evidence", development_ready=False,
            evidence_fingerprint=terminal_report.logical_fingerprint,
            reason_codes=("eighteen_instruments_quarantined", "reference_is_not_outcome"),
        ),
        DatasetFamilyReviewV1(
            family="cost_model", development_required=False,
            status="scenario_mechanics_only", development_ready=True,
            evidence_fingerprint=None,
            reason_codes=("empirical_spread_and_impact_calibration_absent",),
        ),
        DatasetFamilyReviewV1(
            family="historical_coverage", development_required=True,
            status="absent", development_ready=False,
            evidence_fingerprint=None,
            reason_codes=("mandatory_families_not_admissible",),
        ),
    )


def _blocker_codes() -> tuple[str, ...]:
    return tuple(sorted((
        "complete_primary_session_cross_section_count_zero",
        "corporate_action_absence_neutrality_unproven",
        "historical_coverage_manifest_absent",
        "instrument_lifecycle_outcomes_unavailable",
        "minimum_252_complete_sessions_not_met",
        "sparse_adjustment_ledger_not_complete_coverage",
        "terminal_reference_gaps_present",
        "unexplained_split_like_price_discontinuities_present",
    )))


def _limitation_codes() -> tuple[str, ...]:
    return tuple(sorted((
        "cash_dividends_are_event_context_not_total_return",
        "costs_are_scenario_only",
        "membership_is_reconstructed_latest_vintage_not_as_operated",
        "references_are_not_terminal_outcomes_or_execution_prices",
    )))


def _required_external_capabilities() -> tuple[str, ...]:
    return tuple(sorted((
        "complete_effective_dated_split_and_complex_corporate_action_history_with_availability_time",
        "point_in_time_security_lifecycle_with_delisted_acquired_bankrupt_otc_and_symbol_history",
        "revision_aware_terminal_merger_consideration_and_last_tradable_session_evidence",
    )))


def _write_report(
    *, output_root: Path, output_custody_root: Path,
    report: StrongLeaderPullbackPreResearchAdmissionReviewV1,
) -> StrongLeaderPullbackPreResearchAdmissionReviewResult:
    target = _validated_output_target(output_root, output_custody_root)
    if target.exists() or target.is_symlink():
        existing = read_strong_leader_pullback_pre_research_admission_review(
            output_root=target, output_custody_root=output_custody_root
        )
        if existing.report != report:
            raise StrongLeaderPullbackPreResearchAdmissionReviewError(
                "existing pre-research review differs"
            )
        return existing
    partial = target.parent / f".{target.name}.partial.{os.getpid()}"
    if partial.exists() or partial.is_symlink():
        raise StrongLeaderPullbackPreResearchAdmissionReviewError(
            "pre-research review staging exists"
        )
    partial.mkdir(mode=0o700)
    try:
        raw = base._json_bytes(report.model_dump(mode="json"))
        if len(raw) > MAXIMUM_REPORT_BYTES:
            raise StrongLeaderPullbackPreResearchAdmissionReviewError(
                "pre-research review exceeds size limit"
            )
        source_base._write_exclusive(partial / REPORT_FILE, raw)
        source_base._fsync_directory(partial)
        partial.replace(target)
        source_base._fsync_directory(target.parent)
    except Exception:
        if partial.exists() and not partial.is_symlink() and partial.parent == target.parent:
            shutil.rmtree(partial)
            source_base._fsync_directory(partial.parent)
        raise
    reread = read_strong_leader_pullback_pre_research_admission_review(
        output_root=target, output_custody_root=output_custody_root
    )
    return StrongLeaderPullbackPreResearchAdmissionReviewResult(
        output_root=target,
        report=reread.report,
        report_sha256=reread.report_sha256,
        status="published",
    )


def _validated_output_target(path: Path, custody_root: Path) -> Path:
    if not path.is_absolute() or not custody_root.is_absolute():
        raise StrongLeaderPullbackPreResearchAdmissionReviewError(
            "pre-research review paths must be absolute"
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
        raise StrongLeaderPullbackPreResearchAdmissionReviewError(
            "pre-research review target is unsafe"
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
        raise StrongLeaderPullbackPreResearchAdmissionReviewError(
            "pre-research review output is unsafe"
        )
    return target
