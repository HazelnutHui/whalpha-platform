"""Form-aware candidates for corrected-population SEC documents."""

from __future__ import annotations

import os
import re
import shutil
import stat
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from tip_api.contracts.common import normalize_utc_datetime
from tip_api.services import strong_leader_pullback_sec_document_content_census as base
from tip_api.services import strong_leader_pullback_sec_document_source as source_base
from tip_api.services import strong_leader_pullback_sec_form15_candidates as form15
from tip_api.services import strong_leader_pullback_sec_form25_candidates as form25
from tip_api.services import strong_leader_pullback_sec_transaction_candidates as transaction
from tip_api.services import (
    strong_leader_pullback_terminal_population_sec_content_census as census_reader,
)
from tip_api.services import (
    strong_leader_pullback_terminal_population_sec_source as source_reader,
)
from tip_api.services import (
    strong_leader_pullback_terminal_population_sec_source_plan as plan_reader,
)
from tip_api.services.strong_leader_pullback_source_acceptance_sample import (
    LIFECYCLE_REQUIRED_FIELDS,
)


CONTRACT_VERSION = (
    "strong-leader-pullback-terminal-population-sec-field-candidates/1.0"
)
REPORT_FILE = "field-candidates.json"
MAXIMUM_REPORT_BYTES = 1024 * 1024
_SHA256_PATTERN = r"^[0-9a-f]{64}$"
_REVISION_PATTERN = r"^[0-9a-f]{40}$"
_OUTPUT_NAME_PATTERN = r"^extraction=[A-Za-z0-9._-]+$"


class StrongLeaderPullbackTerminalPopulationSecFieldCandidatesError(RuntimeError):
    """Raised when corrected-population SEC candidates cannot be proven."""


class _FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class StrongLeaderPullbackTerminalPopulationSecFieldCandidatesV1(_FrozenModel):
    contract_version: Literal[
        "strong-leader-pullback-terminal-population-sec-field-candidates/1.0"
    ] = CONTRACT_VERSION
    completion_status: Literal[
        "form_aware_candidates_complete_facts_unresolved"
    ] = "form_aware_candidates_complete_facts_unresolved"
    implementation_revision: str = Field(pattern=_REVISION_PATTERN)
    evaluated_at: datetime
    extraction_ruleset_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    plan_sha256: str = Field(pattern=_SHA256_PATTERN)
    plan_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    source_manifest_sha256: str = Field(pattern=_SHA256_PATTERN)
    source_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    source_artifact_binding_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    content_census_sha256: str = Field(pattern=_SHA256_PATTERN)
    content_census_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    source_document_count: Literal[3] = 3
    structured_candidate_count: Literal[3] = 3
    instrument_count: Literal[1] = 1
    form_counts: tuple[tuple[str, int], ...]
    transaction_structure_counts: tuple[tuple[str, int], ...]
    partial_field_candidate_document_counts: tuple[tuple[str, int], ...]
    complete_field_support_counts: tuple[tuple[str, int], ...]
    form25_candidates: tuple[form25.SecForm25CandidateV1, ...] = Field(
        min_length=1, max_length=1
    )
    form15_candidates: tuple[form15.SecForm15CandidateV1, ...] = Field(
        min_length=1, max_length=1
    )
    transaction_candidates: tuple[
        transaction.SecTransactionDocumentCandidateV1, ...
    ] = Field(min_length=1, max_length=1)
    listed_security_identity_assignment_count: Literal[0] = 0
    transaction_completion_fact_count: Literal[0] = 0
    lifecycle_fact_count: Literal[0] = 0
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
    def report_reconciles(
        self,
    ) -> "StrongLeaderPullbackTerminalPopulationSecFieldCandidatesV1":
        candidates = (
            *self.form25_candidates,
            *self.form15_candidates,
            *self.transaction_candidates,
        )
        ids = {item.instrument_id for item in candidates}
        partial_counts = tuple(
            (
                field,
                sum(field in item.partial_field_candidates for item in candidates),
            )
            for field in LIFECYCLE_REQUIRED_FIELDS
        )
        expected_ruleset = _ruleset_fingerprint()
        if (
            len(candidates) != self.source_document_count
            or len(ids) != self.instrument_count
            or tuple(sorted(item.request_sequence for item in candidates)) != (1, 2, 3)
            or self.form_counts
            != source_base._ordered(Counter(item.form for item in candidates))
            or self.transaction_structure_counts
            != source_base._ordered(
                Counter(item.structure_state for item in self.transaction_candidates)
            )
            or self.partial_field_candidate_document_counts != partial_counts
            or self.complete_field_support_counts
            != tuple((field, 0) for field in LIFECYCLE_REQUIRED_FIELDS)
            or self.extraction_ruleset_fingerprint != expected_ruleset
            or self.logical_fingerprint
            != base._fingerprint(
                self.model_dump(mode="json", exclude={"logical_fingerprint"})
            )
        ):
            raise ValueError("terminal-population SEC field candidates differ")
        return self


@dataclass(frozen=True, slots=True)
class StrongLeaderPullbackTerminalPopulationSecFieldCandidatesResult:
    output_root: Path
    report: StrongLeaderPullbackTerminalPopulationSecFieldCandidatesV1
    report_sha256: str
    status: Literal["published", "already_present"]


def build_strong_leader_pullback_terminal_population_sec_field_candidates(
    *,
    plan_root: Path,
    plan_custody_root: Path,
    source_root: Path,
    source_custody_root: Path,
    content_census_root: Path,
    content_census_custody_root: Path,
    output_root: Path,
    output_custody_root: Path,
    implementation_revision: str,
    evaluated_at: datetime,
) -> StrongLeaderPullbackTerminalPopulationSecFieldCandidatesResult:
    """Extract all registered form candidates without assigning a fact."""

    with base._network_prohibited():
        plan = plan_reader.read_strong_leader_pullback_terminal_population_sec_source_plan(
            output_root=plan_root, output_custody_root=plan_custody_root
        )
        source = source_reader.read_strong_leader_pullback_terminal_population_sec_source(
            plan_root=plan_root,
            plan_custody_root=plan_custody_root,
            output_root=source_root,
            output_custody_root=source_custody_root,
        )
        census = census_reader.read_strong_leader_pullback_terminal_population_sec_content_census(
            output_root=content_census_root,
            output_custody_root=content_census_custody_root,
        )
        report = _build_report(
            plan=plan,
            source=source,
            census=census,
            implementation_revision=implementation_revision,
            evaluated_at=evaluated_at,
        )
        return _write_report(
            output_root=output_root,
            output_custody_root=output_custody_root,
            report=report,
        )


def read_strong_leader_pullback_terminal_population_sec_field_candidates(
    *, output_root: Path, output_custody_root: Path
) -> StrongLeaderPullbackTerminalPopulationSecFieldCandidatesResult:
    root = _validated_completed_output(output_root, output_custody_root)
    if {item.name for item in root.iterdir()} != {REPORT_FILE}:
        raise StrongLeaderPullbackTerminalPopulationSecFieldCandidatesError(
            "terminal-population SEC field-candidate members differ"
        )
    path = root / REPORT_FILE
    source_base._require_regular_file(path, 0o400, MAXIMUM_REPORT_BYTES)
    raw = path.read_bytes()
    try:
        report = StrongLeaderPullbackTerminalPopulationSecFieldCandidatesV1.model_validate_json(
            raw
        )
    except Exception as exc:
        raise StrongLeaderPullbackTerminalPopulationSecFieldCandidatesError(
            "terminal-population SEC field candidates are invalid"
        ) from exc
    if raw != base._json_bytes(report.model_dump(mode="json")):
        raise StrongLeaderPullbackTerminalPopulationSecFieldCandidatesError(
            "terminal-population SEC field-candidate bytes differ"
        )
    return StrongLeaderPullbackTerminalPopulationSecFieldCandidatesResult(
        output_root=root,
        report=report,
        report_sha256=base._sha256_bytes(raw),
        status="already_present",
    )


def _build_report(
    *, plan: object, source: object, census: object,
    implementation_revision: str, evaluated_at: datetime,
) -> StrongLeaderPullbackTerminalPopulationSecFieldCandidatesV1:
    if re.fullmatch(_REVISION_PATTERN, implementation_revision) is None:
        raise StrongLeaderPullbackTerminalPopulationSecFieldCandidatesError(
            "terminal-population SEC field-candidate revision is invalid"
        )
    if (
        plan.report.planned_request_count != 3
        or len(plan.report.items) != 3
        or source.completed_document_count != 3
        or source.manifest.completed_document_count != 3
        or census.report.document_count != 3
        or census.report.plan_sha256 != plan.report_sha256
        or census.report.plan_logical_fingerprint != plan.report.logical_fingerprint
        or census.report.source_manifest_sha256 != source.manifest_sha256
        or census.report.source_logical_fingerprint
        != source.manifest.logical_fingerprint
        or census.report.source_artifact_binding_fingerprint
        != source.manifest.artifact_binding_fingerprint
    ):
        raise StrongLeaderPullbackTerminalPopulationSecFieldCandidatesError(
            "terminal-population SEC field-candidate input bindings differ"
        )
    form_counts = Counter(item.form for item in plan.report.items)
    if form_counts != Counter({"25-NSE": 1, "8-K": 1, "15-12G": 1}):
        raise StrongLeaderPullbackTerminalPopulationSecFieldCandidatesError(
            "terminal-population SEC field-candidate form set differs"
        )
    census_by_sequence = {
        item.request_sequence: item for item in census.report.records
    }
    form25_candidates = tuple(
        form25._extract_candidate(
            item=item,
            path=_document_path(source.output_root, item.request_sequence),
        )
        for item in plan.report.items
        if item.form == "25-NSE"
    )
    form15_candidates = tuple(
        form15._extract_candidate(
            item=item,
            path=_document_path(source.output_root, item.request_sequence),
        )
        for item in plan.report.items
        if item.form == "15-12G"
    )
    transaction_candidates = tuple(
        transaction._extract_candidate(
            item=item,
            census_record=census_by_sequence[item.request_sequence],
            path=_document_path(source.output_root, item.request_sequence),
        )
        for item in plan.report.items
        if item.form == "8-K"
    )
    candidates = (*form25_candidates, *form15_candidates, *transaction_candidates)
    if any(
        candidate.document_sha256
        != census_by_sequence[candidate.request_sequence].document_sha256
        for candidate in candidates
    ):
        raise StrongLeaderPullbackTerminalPopulationSecFieldCandidatesError(
            "terminal-population SEC candidate document binding differs"
        )
    partial_counts = tuple(
        (
            field,
            sum(field in item.partial_field_candidates for item in candidates),
        )
        for field in LIFECYCLE_REQUIRED_FIELDS
    )
    values = {
        "implementation_revision": implementation_revision,
        "evaluated_at": normalize_utc_datetime(evaluated_at),
        "extraction_ruleset_fingerprint": _ruleset_fingerprint(),
        "plan_sha256": plan.report_sha256,
        "plan_logical_fingerprint": plan.report.logical_fingerprint,
        "source_manifest_sha256": source.manifest_sha256,
        "source_logical_fingerprint": source.manifest.logical_fingerprint,
        "source_artifact_binding_fingerprint": (
            source.manifest.artifact_binding_fingerprint
        ),
        "content_census_sha256": census.report_sha256,
        "content_census_logical_fingerprint": census.report.logical_fingerprint,
        "form_counts": source_base._ordered(Counter(item.form for item in candidates)),
        "transaction_structure_counts": source_base._ordered(
            Counter(item.structure_state for item in transaction_candidates)
        ),
        "partial_field_candidate_document_counts": partial_counts,
        "complete_field_support_counts": tuple(
            (field, 0) for field in LIFECYCLE_REQUIRED_FIELDS
        ),
        "form25_candidates": form25_candidates,
        "form15_candidates": form15_candidates,
        "transaction_candidates": transaction_candidates,
    }
    provisional = StrongLeaderPullbackTerminalPopulationSecFieldCandidatesV1.model_construct(
        **values, logical_fingerprint="0" * 64
    )
    return StrongLeaderPullbackTerminalPopulationSecFieldCandidatesV1.model_validate(
        {
            **values,
            "logical_fingerprint": base._fingerprint(
                provisional.model_dump(mode="json", exclude={"logical_fingerprint"})
            ),
        }
    )


def _ruleset_fingerprint() -> str:
    return base._fingerprint(
        {
            "form25_extractor": form25.CONTRACT_VERSION,
            "form15_extractor": form15.CONTRACT_VERSION,
            "transaction_extractor": transaction.CONTRACT_VERSION,
            "dispatcher": (
                ("15-12G", "form15"),
                ("25-NSE", "form25"),
                ("8-K", "transaction"),
            ),
            "all_complete_fields_unresolved": LIFECYCLE_REQUIRED_FIELDS,
        }
    )


def _document_path(source_root: Path, sequence: int) -> Path:
    return source_root / f"request={sequence:06d}" / source_reader.DOCUMENT_FILE


def _write_report(
    *, output_root: Path, output_custody_root: Path,
    report: StrongLeaderPullbackTerminalPopulationSecFieldCandidatesV1,
) -> StrongLeaderPullbackTerminalPopulationSecFieldCandidatesResult:
    target = _validated_output_target(output_root, output_custody_root)
    if target.exists() or target.is_symlink():
        existing = read_strong_leader_pullback_terminal_population_sec_field_candidates(
            output_root=target, output_custody_root=output_custody_root
        )
        if existing.report != report:
            raise StrongLeaderPullbackTerminalPopulationSecFieldCandidatesError(
                "existing terminal-population SEC field candidates differ"
            )
        return existing
    partial = target.parent / f".{target.name}.partial.{os.getpid()}"
    if partial.exists() or partial.is_symlink():
        raise StrongLeaderPullbackTerminalPopulationSecFieldCandidatesError(
            "terminal-population SEC field-candidate staging exists"
        )
    partial.mkdir(mode=0o700)
    try:
        raw = base._json_bytes(report.model_dump(mode="json"))
        if len(raw) > MAXIMUM_REPORT_BYTES:
            raise StrongLeaderPullbackTerminalPopulationSecFieldCandidatesError(
                "terminal-population SEC field-candidate report exceeds byte ceiling"
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
    reread = read_strong_leader_pullback_terminal_population_sec_field_candidates(
        output_root=target, output_custody_root=output_custody_root
    )
    return StrongLeaderPullbackTerminalPopulationSecFieldCandidatesResult(
        output_root=target,
        report=reread.report,
        report_sha256=reread.report_sha256,
        status="published",
    )


def _validated_output_target(path: Path, custody_root: Path) -> Path:
    if not path.is_absolute() or not custody_root.is_absolute():
        raise StrongLeaderPullbackTerminalPopulationSecFieldCandidatesError(
            "terminal-population SEC field-candidate paths must be absolute"
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
        raise StrongLeaderPullbackTerminalPopulationSecFieldCandidatesError(
            "terminal-population SEC field-candidate target is unsafe"
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
        raise StrongLeaderPullbackTerminalPopulationSecFieldCandidatesError(
            "terminal-population SEC field-candidate output is unsafe"
        )
    return target
