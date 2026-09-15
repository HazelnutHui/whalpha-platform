"""Source-driven V2 admission review for Strong-Leader Pullback.

This review opens only reconstructed development.  It formally rereads the
frozen feature diagnostic, split-source vintages, private resolution shadow,
canonical split publications, and final terminal bounds.  It never reads a
forward outcome or selects a parameter.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import socket
import stat
from collections import Counter
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Iterator, Literal, Mapping

from pydantic import BaseModel, ConfigDict, Field, model_validator

from tip_api.contracts.analytics.v1 import DiagnosticConcentrationAxis
from tip_api.persistence.development_coverage_census import (
    REPORT_FILE as DEVELOPMENT_CENSUS_FILE,
    read_development_coverage_census,
)
from tip_api.persistence.parquet.canonical_corporate_action import (
    read_canonical_split_action_publication,
)
from tip_api.persistence.parquet.canonical_split_adjustment import (
    read_canonical_split_adjustment_publication,
)
from tip_api.persistence.strong_leader_pullback_diagnostics import (
    REPORT_FILE as DIAGNOSTICS_FILE,
    read_strong_leader_pullback_diagnostics,
)
from tip_api.services.historical_corporate_action_resolution_shadow import (
    read_historical_corporate_action_resolution_shadow,
)
from tip_api.services.historical_corporate_action_source import (
    CorporateActionSourceKind,
    ValidatedCorporateActionSourcePackage,
    read_historical_corporate_action_source_package,
)
from tip_api.services.strong_leader_pullback_research_admission_v2 import (
    FeatureSessionExclusionV1,
    MechanicalAdjustmentEvidenceV1,
    ReconstructedFeatureEvidenceV1,
    ResearchControlEvidenceV1,
    StrongLeaderPullbackResearchAdmissionV2,
    TerminalReferenceEvidenceV1,
    assess_strong_leader_pullback_research_admission_v2,
)
from tip_api.services.strong_leader_pullback_terminal_reference_final_review import (
    read_strong_leader_pullback_terminal_reference_final_review,
)


CONTRACT_VERSION = "strong-leader-pullback-research-admission-v2-review/1.0"
REPORT_FILE = "research-admission-v2.json"
MAXIMUM_REPORT_BYTES = 256 * 1024
_SHA256_PATTERN = r"^[0-9a-f]{64}$"
_REVISION_PATTERN = r"^[0-9a-f]{40}$"
_OUTPUT_PREFIX = "review="
_SOURCE_START = date(2021, 8, 11)
_SOURCE_END = date(2026, 9, 9)
_PRIOR_START = date(2025, 6, 23)
_PRIOR_END = date(2026, 9, 4)
_ANNUAL_RANGES = (
    (date(2021, 8, 11), date(2021, 12, 31)),
    (date(2022, 1, 1), date(2022, 12, 31)),
    (date(2023, 1, 1), date(2023, 12, 31)),
    (date(2024, 1, 1), date(2024, 12, 31)),
    (date(2025, 1, 1), date(2025, 12, 31)),
    (date(2026, 1, 1), date(2026, 9, 9)),
)


class StrongLeaderPullbackResearchAdmissionV2ReviewError(RuntimeError):
    """Raised when the V2 admission evidence cannot be reproduced."""


class _FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class StrongLeaderPullbackResearchAdmissionV2Review(_FrozenModel):
    contract_version: Literal[
        "strong-leader-pullback-research-admission-v2-review/1.0"
    ] = CONTRACT_VERSION
    reviewed_at: datetime
    implementation_revision: str = Field(pattern=_REVISION_PATTERN)
    development_census_report_sha256: str = Field(pattern=_SHA256_PATTERN)
    development_census_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    diagnostics_report_sha256: str = Field(pattern=_SHA256_PATTERN)
    diagnostics_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    current_split_source_manifest_sha256: str = Field(pattern=_SHA256_PATTERN)
    current_split_source_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    repeat_split_source_manifest_sha256: str = Field(pattern=_SHA256_PATTERN)
    repeat_split_source_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    annual_split_source_package_count: Literal[6] = 6
    prior_split_source_manifest_sha256: str = Field(pattern=_SHA256_PATTERN)
    prior_split_source_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    split_resolution_shadow_manifest_sha256: str = Field(pattern=_SHA256_PATTERN)
    split_resolution_shadow_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    canonical_split_action_manifest_sha256: str = Field(pattern=_SHA256_PATTERN)
    canonical_split_action_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    canonical_split_adjustment_manifest_sha256: str = Field(pattern=_SHA256_PATTERN)
    canonical_split_adjustment_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    final_terminal_report_sha256: str = Field(pattern=_SHA256_PATTERN)
    final_terminal_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    provider_adjustment_factor_revision_count: Literal[12] = 12
    added_split_term_count: Literal[2] = 2
    removed_split_term_count: Literal[0] = 0
    added_split_term_primary_included_path_count: Literal[0] = 0
    feature_evidence: ReconstructedFeatureEvidenceV1
    adjustment_evidence: MechanicalAdjustmentEvidenceV1
    terminal_evidence: TerminalReferenceEvidenceV1
    control_evidence: ResearchControlEvidenceV1
    decision: StrongLeaderPullbackResearchAdmissionV2
    contains_forward_outcomes: Literal[False] = False
    contains_performance_metrics: Literal[False] = False
    parameter_selection_count: Literal[0] = 0
    validation_authorized: Literal[False] = False
    holdout_access_authorized: Literal[False] = False
    candidate_activation_authorized: Literal[False] = False
    network_request_count: Literal[0] = 0
    canonical_data_write_count: Literal[0] = 0
    production_write_count: Literal[0] = 0
    logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)

    @model_validator(mode="after")
    def report_reconciles(self) -> "StrongLeaderPullbackResearchAdmissionV2Review":
        expected = assess_strong_leader_pullback_research_admission_v2(
            features=self.feature_evidence,
            adjustments=self.adjustment_evidence,
            terminal_references=self.terminal_evidence,
            controls=self.control_evidence,
        )
        if self.reviewed_at.tzinfo is None or self.reviewed_at.utcoffset() is None:
            raise ValueError("research admission review time must be timezone-aware")
        if self.reviewed_at.astimezone(UTC) != self.reviewed_at:
            raise ValueError("research admission review time must be UTC")
        if self.decision != expected:
            raise ValueError("research admission decision differs from evidence")
        if self.logical_fingerprint != _fingerprint(
            self.model_dump(mode="json", exclude={"logical_fingerprint"})
        ):
            raise ValueError("research admission review fingerprint differs")
        return self


@dataclass(frozen=True, slots=True)
class StrongLeaderPullbackResearchAdmissionV2ReviewResult:
    output_root: Path
    report: StrongLeaderPullbackResearchAdmissionV2Review
    report_sha256: str
    status: Literal["published", "already_present"]


def publish_strong_leader_pullback_research_admission_v2_review(
    *,
    development_census_root: Path,
    diagnostics_root: Path,
    diagnostics_custody_root: Path,
    corporate_action_source_root: Path,
    prior_split_source_root: Path,
    split_resolution_shadow_root: Path,
    split_resolution_shadow_custody_root: Path,
    canonical_data_root: Path,
    canonical_split_action_root: Path,
    canonical_split_adjustment_root: Path,
    final_terminal_root: Path,
    final_terminal_custody_root: Path,
    output_root: Path,
    output_custody_root: Path,
    reviewed_at: datetime,
    implementation_revision: str,
) -> StrongLeaderPullbackResearchAdmissionV2ReviewResult:
    """Reread every V2 input and publish one immutable admission decision."""

    with _network_disabled():
        report = _build_report(
            development_census_root=development_census_root,
            diagnostics_root=diagnostics_root,
            diagnostics_custody_root=diagnostics_custody_root,
            corporate_action_source_root=corporate_action_source_root,
            prior_split_source_root=prior_split_source_root,
            split_resolution_shadow_root=split_resolution_shadow_root,
            split_resolution_shadow_custody_root=split_resolution_shadow_custody_root,
            canonical_data_root=canonical_data_root,
            canonical_split_action_root=canonical_split_action_root,
            canonical_split_adjustment_root=canonical_split_adjustment_root,
            final_terminal_root=final_terminal_root,
            final_terminal_custody_root=final_terminal_custody_root,
            reviewed_at=reviewed_at,
            implementation_revision=implementation_revision,
        )
    return _publish(
        report=report,
        output_root=output_root,
        output_custody_root=output_custody_root,
    )


def read_strong_leader_pullback_research_admission_v2_review(
    *, output_root: Path, output_custody_root: Path
) -> StrongLeaderPullbackResearchAdmissionV2ReviewResult:
    root = _validated_target(output_root, output_custody_root, require_exists=True)
    if {item.name for item in root.iterdir()} != {REPORT_FILE}:
        raise StrongLeaderPullbackResearchAdmissionV2ReviewError(
            "research admission review members differ"
        )
    raw = _read_regular(root / REPORT_FILE, mode=0o400, maximum=MAXIMUM_REPORT_BYTES)
    try:
        report = StrongLeaderPullbackResearchAdmissionV2Review.model_validate_json(raw)
    except Exception as exc:
        raise StrongLeaderPullbackResearchAdmissionV2ReviewError(
            "research admission review is invalid"
        ) from exc
    if raw != _json_bytes(report.model_dump(mode="json")):
        raise StrongLeaderPullbackResearchAdmissionV2ReviewError(
            "research admission review bytes differ"
        )
    return StrongLeaderPullbackResearchAdmissionV2ReviewResult(
        output_root=root,
        report=report,
        report_sha256=_sha256(raw),
        status="already_present",
    )


def _build_report(
    *,
    development_census_root: Path,
    diagnostics_root: Path,
    diagnostics_custody_root: Path,
    corporate_action_source_root: Path,
    prior_split_source_root: Path,
    split_resolution_shadow_root: Path,
    split_resolution_shadow_custody_root: Path,
    canonical_data_root: Path,
    canonical_split_action_root: Path,
    canonical_split_adjustment_root: Path,
    final_terminal_root: Path,
    final_terminal_custody_root: Path,
    reviewed_at: datetime,
    implementation_revision: str,
) -> StrongLeaderPullbackResearchAdmissionV2Review:
    census = read_development_coverage_census(output_root=development_census_root)
    diagnostics = read_strong_leader_pullback_diagnostics(
        output_root=diagnostics_root,
        output_custody_root=diagnostics_custody_root,
    )
    current, repeat, annual = _read_current_split_sources(corporate_action_source_root)
    prior = read_historical_corporate_action_source_package(
        package_path=prior_split_source_root,
        expected_action_kind=CorporateActionSourceKind.SPLIT,
        expected_start_date=_PRIOR_START,
        expected_end_date=_PRIOR_END,
    )
    shadow = read_historical_corporate_action_resolution_shadow(
        output_root=split_resolution_shadow_root,
        output_custody_root=split_resolution_shadow_custody_root,
    )
    action = read_canonical_split_action_publication(
        data_root=canonical_data_root,
        publication_root=canonical_split_action_root,
    )
    adjustment = read_canonical_split_adjustment_publication(
        data_root=canonical_data_root,
        publication_root=canonical_split_adjustment_root,
    )
    terminal = read_strong_leader_pullback_terminal_reference_final_review(
        output_root=final_terminal_root,
        output_custody_root=final_terminal_custody_root,
    )

    diagnostics_sha256 = _file_sha256(diagnostics_root / DIAGNOSTICS_FILE)
    feature_evidence = _feature_evidence(
        census=census,
        diagnostics=diagnostics,
        diagnostics_sha256=diagnostics_sha256,
    )
    source_check = _split_source_check(
        current=current,
        repeat=repeat,
        annual=annual,
        prior=prior,
        shadow=shadow,
        census=census,
        diagnostics=diagnostics,
        action=action,
        adjustment=adjustment,
    )
    adjustment_evidence = MechanicalAdjustmentEvidenceV1(
        source_fingerprint=source_check["source_fingerprint"],
        source_range_naturally_complete=True,
        independent_range_composition_matches=True,
        repeated_economic_rows_match=True,
        source_vintage_frozen=True,
        unresolved_action_hazard_sessions_excluded=True,
    )
    terminal_evidence = terminal.report.to_admission_evidence()
    control_evidence = ResearchControlEvidenceV1(
        chronological_plan_fingerprint=diagnostics.chronological_plan_fingerprint,
        holdout_sealed_and_unconsumed=True,
    )
    decision = assess_strong_leader_pullback_research_admission_v2(
        features=feature_evidence,
        adjustments=adjustment_evidence,
        terminal_references=terminal_evidence,
        controls=control_evidence,
    )
    values: dict[str, object] = {
        "reviewed_at": reviewed_at.astimezone(UTC),
        "implementation_revision": implementation_revision,
        "development_census_report_sha256": _file_sha256(
            development_census_root / DEVELOPMENT_CENSUS_FILE
        ),
        "development_census_logical_fingerprint": census.logical_fingerprint,
        "diagnostics_report_sha256": diagnostics_sha256,
        "diagnostics_logical_fingerprint": diagnostics.logical_fingerprint,
        "current_split_source_manifest_sha256": current.manifest_sha256,
        "current_split_source_logical_fingerprint": current.manifest.logical_fingerprint,
        "repeat_split_source_manifest_sha256": repeat.manifest_sha256,
        "repeat_split_source_logical_fingerprint": repeat.manifest.logical_fingerprint,
        "prior_split_source_manifest_sha256": prior.manifest_sha256,
        "prior_split_source_logical_fingerprint": prior.manifest.logical_fingerprint,
        "split_resolution_shadow_manifest_sha256": shadow.manifest_sha256,
        "split_resolution_shadow_logical_fingerprint": shadow.manifest.logical_fingerprint,
        "canonical_split_action_manifest_sha256": action.manifest_sha256,
        "canonical_split_action_logical_fingerprint": action.publication.logical_fingerprint,
        "canonical_split_adjustment_manifest_sha256": adjustment.manifest_sha256,
        "canonical_split_adjustment_logical_fingerprint": adjustment.publication.logical_fingerprint,
        "final_terminal_report_sha256": terminal.report_sha256,
        "final_terminal_logical_fingerprint": terminal.report.logical_fingerprint,
        "feature_evidence": feature_evidence,
        "adjustment_evidence": adjustment_evidence,
        "terminal_evidence": terminal_evidence,
        "control_evidence": control_evidence,
        "decision": decision,
    }
    provisional = StrongLeaderPullbackResearchAdmissionV2Review.model_construct(
        **values, logical_fingerprint="0" * 64
    )
    return StrongLeaderPullbackResearchAdmissionV2Review.model_validate(
        {
            **values,
            "logical_fingerprint": _fingerprint(
                provisional.model_dump(mode="json", exclude={"logical_fingerprint"})
            ),
        }
    )


def _feature_evidence(
    *, census: object, diagnostics: object, diagnostics_sha256: str
) -> ReconstructedFeatureEvidenceV1:
    session_axis = next(
        item
        for item in diagnostics.observation_concentration
        if item.axis is DiagnosticConcentrationAxis.SESSION
    )
    warmup = tuple(item for item in census.sessions if item.primary_included_count == 0)
    rankable = tuple(item for item in census.sessions if item.primary_included_count > 0)
    split_exclusions = tuple(
        item for item in rankable if item.split_quarantined_path_count > 0
    )
    split_paths = sum(item.primary_included_count for item in split_exclusions)
    regime_paths = diagnostics.excluded_path_count - split_paths
    price = next(item for item in diagnostics.feature_coverage if item.feature_id == "adjusted_ohlcv_panel")
    regime = next(item for item in diagnostics.feature_coverage if item.feature_id == "market_regime_state")
    if (
        len(census.sessions) != diagnostics.session_count
        or census.primary_included_count != diagnostics.expected_path_count
        or len(warmup) != 20
        or tuple(item.session_date for item in warmup) != tuple(
            item.session_date for item in census.sessions[:20]
        )
        or len(rankable) != 267
        or session_axis.group_count != 254
        or len(split_exclusions) != 12
        or split_paths != 18_646
        or regime_paths != 1_547
        or price.source_unavailable_count != split_paths
        or {
            item.reason_code: item.count
            for item in price.unavailable_reason_counts
        }.get("complete_cross_section_split_evidence_quarantined")
        != split_paths
        or regime.source_unavailable_count != diagnostics.excluded_path_count
        or diagnostics.complete_observation_count + diagnostics.excluded_path_count
        != diagnostics.expected_path_count
    ):
        raise StrongLeaderPullbackResearchAdmissionV2ReviewError(
            "feature-session evidence does not reconcile"
        )
    return ReconstructedFeatureEvidenceV1(
        diagnostics_report_sha256=diagnostics_sha256,
        diagnostics_logical_fingerprint=diagnostics.logical_fingerprint,
        total_session_count=diagnostics.session_count,
        feature_window_warmup_session_count=len(warmup),
        rankable_cross_section_session_count=len(rankable),
        complete_cross_section_session_count=session_axis.group_count,
        excluded_session_count=len(rankable) - session_axis.group_count,
        expected_path_count=diagnostics.expected_path_count,
        complete_path_count=diagnostics.complete_observation_count,
        excluded_path_count=diagnostics.excluded_path_count,
        exclusions=(
            FeatureSessionExclusionV1(
                reason_code="feature_regime_bootstrap_unavailable",
                session_count=1,
                path_count=regime_paths,
            ),
            FeatureSessionExclusionV1(
                reason_code="split_evidence_quarantined",
                session_count=len(split_exclusions),
                path_count=split_paths,
            ),
        ),
    )


def _read_current_split_sources(
    root: Path,
) -> tuple[
    ValidatedCorporateActionSourcePackage,
    ValidatedCorporateActionSourcePackage,
    tuple[ValidatedCorporateActionSourcePackage, ...],
]:
    current = _read_persistent_source(
        root, "baseline", _SOURCE_START, _SOURCE_END
    )
    repeat = _read_persistent_source(root, "repeat", _SOURCE_START, _SOURCE_END)
    annual = tuple(
        _read_persistent_source(root, "baseline", start, end)
        for start, end in _ANNUAL_RANGES
    )
    return current, repeat, annual


def _read_persistent_source(
    root: Path, branch: str, start: date, end: date
) -> ValidatedCorporateActionSourcePackage:
    custody = root / branch
    return read_historical_corporate_action_source_package(
        package_path=custody / f"split={start.isoformat()}_{end.isoformat()}",
        expected_action_kind=CorporateActionSourceKind.SPLIT,
        expected_start_date=start,
        expected_end_date=end,
        approved_custody_root=custody,
    )


def _split_source_check(
    *, current: object, repeat: object, annual: tuple[object, ...], prior: object,
    shadow: object, census: object, diagnostics: object, action: object,
    adjustment: object,
) -> dict[str, str]:
    current_rows = _rows(current)
    repeat_rows = _rows(repeat)
    annual_rows = tuple(row for package in annual for row in _rows(package))
    prior_rows = _rows(prior)
    current_scope = tuple(
        row for row in current_rows
        if _PRIOR_START <= date.fromisoformat(str(row["execution_date"])) <= _PRIOR_END
    )
    if (
        len(current_rows) != 6_491
        or len(repeat_rows) != 6_491
        or len(annual_rows) != 6_491
        or Counter(_row_key(row) for row in annual_rows)
        != Counter(_row_key(row) for row in repeat_rows)
        or Counter(_term_key(row) for row in current_rows)
        != Counter(_term_key(row) for row in repeat_rows)
        or not current.manifest.pagination_complete
        or not repeat.manifest.pagination_complete
        or shadow.manifest.split_source_logical_fingerprint
        != current.manifest.logical_fingerprint
        or action.publication.start_date > diagnostics.first_session
        or action.publication.end_date < diagnostics.last_session
        or adjustment.publication.first_source_session > diagnostics.first_session
        or adjustment.publication.last_source_session < diagnostics.last_session
    ):
        raise StrongLeaderPullbackResearchAdmissionV2ReviewError(
            "split-source range or repeat evidence differs"
        )
    prior_terms = Counter(_term_key(row) for row in prior_rows)
    current_terms = Counter(_term_key(row) for row in current_scope)
    added_terms = current_terms - prior_terms
    removed_terms = prior_terms - current_terms
    prior_by_id = {str(row["id"]): row for row in prior_rows}
    current_by_id = {str(row["id"]): row for row in current_scope}
    factor_revisions = sum(
        _term_key(prior_by_id[source_id]) == _term_key(current_by_id[source_id])
        and prior_by_id[source_id].get("historical_adjustment_factor")
        != current_by_id[source_id].get("historical_adjustment_factor")
        for source_id in set(prior_by_id) & set(current_by_id)
    )
    added_rows = _counter_rows(current_scope, added_terms)
    shadow_by_source_id = {
        item.source_action_id: item
        for item in shadow.records
        if item.action_type.value != "cash_dividend"
    }
    census_by_id = {item.instrument_id: item for item in census.instruments}
    added_primary_paths = 0
    for row in added_rows:
        resolved = shadow_by_source_id.get(str(row["id"]))
        if resolved is None or resolved.instrument_id is None or resolved.record_status.value != "active":
            raise StrongLeaderPullbackResearchAdmissionV2ReviewError(
                "new split term lacks exact-date resolution"
            )
        instrument = census_by_id.get(resolved.instrument_id)
        added_primary_paths += 0 if instrument is None else instrument.included_session_count
    if (
        sum(added_terms.values()) != 2
        or sum(removed_terms.values()) != 0
        or factor_revisions != 12
        or added_primary_paths != 0
    ):
        raise StrongLeaderPullbackResearchAdmissionV2ReviewError(
            "split-source revision affects the admitted Primary population"
        )
    return {
        "source_fingerprint": _fingerprint(
            {
                "current": current.manifest.logical_fingerprint,
                "repeat": repeat.manifest.logical_fingerprint,
                "annual": [item.manifest.logical_fingerprint for item in annual],
                "prior": prior.manifest.logical_fingerprint,
                "shadow": shadow.manifest.logical_fingerprint,
                "canonical_action": action.publication.logical_fingerprint,
                "canonical_adjustment": adjustment.publication.logical_fingerprint,
                "provider_adjustment_factor_revision_count": factor_revisions,
                "added_split_term_count": sum(added_terms.values()),
                "removed_split_term_count": sum(removed_terms.values()),
                "added_split_term_primary_included_path_count": added_primary_paths,
                "diagnostic_split_excluded_path_count": 18_646,
            }
        )
    }


def _rows(package: object) -> tuple[Mapping[str, object], ...]:
    rows: list[Mapping[str, object]] = []
    for page in package.pages:
        values = page.sanitized_response.get("results")
        if not isinstance(values, list) or any(not isinstance(row, Mapping) for row in values):
            raise StrongLeaderPullbackResearchAdmissionV2ReviewError(
                "split-source rows differ"
            )
        rows.extend(values)
    return tuple(rows)


def _row_key(row: Mapping[str, object]) -> str:
    return json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _term_key(row: Mapping[str, object]) -> str:
    return _row_key(
        {
            key: value
            for key, value in row.items()
            if key not in {"id", "historical_adjustment_factor"}
        }
    )


def _counter_rows(
    rows: tuple[Mapping[str, object], ...], wanted: Counter[str]
) -> tuple[Mapping[str, object], ...]:
    remaining = wanted.copy()
    output = []
    for row in rows:
        key = _term_key(row)
        if remaining[key] > 0:
            remaining[key] -= 1
            output.append(row)
    if any(remaining.values()):
        raise StrongLeaderPullbackResearchAdmissionV2ReviewError(
            "split-source revision rows do not reconcile"
        )
    return tuple(output)


def _publish(
    *, report: StrongLeaderPullbackResearchAdmissionV2Review,
    output_root: Path, output_custody_root: Path,
) -> StrongLeaderPullbackResearchAdmissionV2ReviewResult:
    target = _validated_target(output_root, output_custody_root, require_exists=False)
    if target.exists() or target.is_symlink():
        existing = read_strong_leader_pullback_research_admission_v2_review(
            output_root=target, output_custody_root=output_custody_root
        )
        if existing.report != report:
            raise StrongLeaderPullbackResearchAdmissionV2ReviewError(
                "existing research admission review differs"
            )
        return existing
    partial = target.parent / f".{target.name}.partial.{os.getpid()}"
    if partial.exists() or partial.is_symlink():
        raise StrongLeaderPullbackResearchAdmissionV2ReviewError(
            "research admission staging exists"
        )
    partial.mkdir(mode=0o700)
    try:
        raw = _json_bytes(report.model_dump(mode="json"))
        if len(raw) > MAXIMUM_REPORT_BYTES:
            raise StrongLeaderPullbackResearchAdmissionV2ReviewError(
                "research admission report exceeds byte ceiling"
            )
        _write_exclusive(partial / REPORT_FILE, raw)
        _fsync_directory(partial)
        partial.replace(target)
        _fsync_directory(target.parent)
    except Exception:
        if partial.exists() and not partial.is_symlink() and partial.parent == target.parent:
            shutil.rmtree(partial)
        raise
    reread = read_strong_leader_pullback_research_admission_v2_review(
        output_root=target, output_custody_root=output_custody_root
    )
    return StrongLeaderPullbackResearchAdmissionV2ReviewResult(
        output_root=target,
        report=reread.report,
        report_sha256=reread.report_sha256,
        status="published",
    )


def _validated_target(
    output_root: Path, output_custody_root: Path, *, require_exists: bool
) -> Path:
    custody = output_custody_root.absolute()
    target = output_root.absolute()
    if (
        custody.is_symlink() or not custody.is_dir()
        or custody.resolve(strict=True) != custody
        or custody.stat().st_uid != os.getuid()
        or stat.S_IMODE(custody.stat().st_mode) != 0o700
        or target.parent != custody
        or not target.name.startswith(_OUTPUT_PREFIX)
        or target.name == _OUTPUT_PREFIX
    ):
        raise StrongLeaderPullbackResearchAdmissionV2ReviewError(
            "research admission custody differs"
        )
    if require_exists and (
        target.is_symlink() or not target.is_dir()
        or target.resolve(strict=True) != target
        or target.stat().st_uid != os.getuid()
        or stat.S_IMODE(target.stat().st_mode) != 0o700
    ):
        raise StrongLeaderPullbackResearchAdmissionV2ReviewError(
            "research admission review is unavailable"
        )
    return target


def _read_regular(path: Path, *, mode: int, maximum: int) -> bytes:
    if (
        path.is_symlink() or not path.is_file() or path.stat().st_uid != os.getuid()
        or stat.S_IMODE(path.stat().st_mode) != mode
        or not 0 < path.stat().st_size <= maximum
    ):
        raise StrongLeaderPullbackResearchAdmissionV2ReviewError(
            "research admission artifact custody differs"
        )
    return path.read_bytes()


def _write_exclusive(path: Path, raw: bytes) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o400)
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())


@contextmanager
def _network_disabled() -> Iterator[None]:
    original = socket.socket

    def prohibited(*args: object, **kwargs: object) -> object:
        raise StrongLeaderPullbackResearchAdmissionV2ReviewError(
            "network access is prohibited during research admission review"
        )

    socket.socket = prohibited  # type: ignore[assignment]
    try:
        yield
    finally:
        socket.socket = original  # type: ignore[assignment]


def _json_bytes(value: object) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        + "\n"
    ).encode("utf-8")


def _fingerprint(value: object) -> str:
    return _sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    )


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
