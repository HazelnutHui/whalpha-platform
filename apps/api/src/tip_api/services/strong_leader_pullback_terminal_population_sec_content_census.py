"""Deterministic content census for corrected-population SEC custody."""

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
from tip_api.services import (
    strong_leader_pullback_terminal_population_sec_source as source_reader,
)
from tip_api.services import (
    strong_leader_pullback_terminal_population_sec_source_plan as plan_reader,
)


CONTRACT_VERSION = (
    "strong-leader-pullback-terminal-population-sec-content-census/1.0"
)
REPORT_FILE = "content-census.json"
MAXIMUM_REPORT_BYTES = 512 * 1024
_SHA256_PATTERN = r"^[0-9a-f]{64}$"
_REVISION_PATTERN = r"^[0-9a-f]{40}$"
_OUTPUT_NAME_PATTERN = r"^census=[A-Za-z0-9._-]+$"


class StrongLeaderPullbackTerminalPopulationSecContentCensusError(RuntimeError):
    """Raised when the corrected-population content census cannot be proven."""


class _FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class StrongLeaderPullbackTerminalPopulationSecContentCensusV1(_FrozenModel):
    contract_version: Literal[
        "strong-leader-pullback-terminal-population-sec-content-census/1.0"
    ] = CONTRACT_VERSION
    completion_status: Literal["content_parsed_candidates_unresolved"] = (
        "content_parsed_candidates_unresolved"
    )
    implementation_revision: str = Field(pattern=_REVISION_PATTERN)
    evaluated_at: datetime
    plan_sha256: str = Field(pattern=_SHA256_PATTERN)
    plan_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    source_manifest_sha256: str = Field(pattern=_SHA256_PATTERN)
    source_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    source_artifact_binding_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    marker_ruleset_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    document_count: int = Field(ge=1)
    parsed_document_count: int = Field(ge=1)
    form_counts: tuple[tuple[str, int], ...]
    decoding_counts: tuple[tuple[str, int], ...]
    markup_profile_counts: tuple[tuple[str, int], ...]
    field_marker_document_counts: tuple[tuple[str, int], ...]
    field_marker_occurrence_counts: tuple[tuple[str, int], ...]
    total_document_bytes: int = Field(ge=1)
    total_normalized_text_characters: int = Field(ge=1)
    records: tuple[base.SecDocumentContentCensusRecordV1, ...] = Field(
        min_length=1
    )
    full_document_text_retained: Literal[False] = False
    lexical_marker_is_fact: Literal[False] = False
    listed_security_identity_assignment_count: Literal[0] = 0
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
    def census_reconciles(
        self,
    ) -> "StrongLeaderPullbackTerminalPopulationSecContentCensusV1":
        records = self.records
        if (
            self.document_count != len(records)
            or self.parsed_document_count != len(records)
            or tuple(item.request_sequence for item in records)
            != tuple(range(1, len(records) + 1))
            or self.form_counts
            != source_base._ordered(Counter(item.form for item in records))
            or self.decoding_counts
            != source_base._ordered(Counter(item.decoding for item in records))
            or self.markup_profile_counts
            != source_base._ordered(Counter(item.markup_profile for item in records))
            or self.total_document_bytes
            != sum(item.document_byte_count for item in records)
            or self.total_normalized_text_characters
            != sum(item.normalized_text_character_count for item in records)
        ):
            raise ValueError("terminal-population SEC content aggregates differ")
        document_counts = Counter(
            marker.field_name
            for record in records
            for marker in record.field_markers
            if marker.occurrence_count
        )
        occurrence_counts = Counter()
        for record in records:
            occurrence_counts.update(
                {
                    marker.field_name: marker.occurrence_count
                    for marker in record.field_markers
                    if marker.occurrence_count
                }
            )
        if (
            self.field_marker_document_counts
            != base._all_field_counts(document_counts)
            or self.field_marker_occurrence_counts
            != base._all_field_counts(occurrence_counts)
            or self.marker_ruleset_fingerprint != base._fingerprint(base._FIELD_PATTERNS)
            or self.logical_fingerprint
            != base._fingerprint(
                self.model_dump(mode="json", exclude={"logical_fingerprint"})
            )
        ):
            raise ValueError("terminal-population SEC content markers differ")
        return self


@dataclass(frozen=True, slots=True)
class StrongLeaderPullbackTerminalPopulationSecContentCensusResult:
    output_root: Path
    report: StrongLeaderPullbackTerminalPopulationSecContentCensusV1
    report_sha256: str
    status: Literal["published", "already_present"]


def build_strong_leader_pullback_terminal_population_sec_content_census(
    *,
    plan_root: Path,
    plan_custody_root: Path,
    source_root: Path,
    source_custody_root: Path,
    output_root: Path,
    output_custody_root: Path,
    implementation_revision: str,
    evaluated_at: datetime,
) -> StrongLeaderPullbackTerminalPopulationSecContentCensusResult:
    """Parse only the corrected-population source package without facts."""

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
        report = _build_report(
            plan=plan,
            source=source,
            implementation_revision=implementation_revision,
            evaluated_at=evaluated_at,
        )
        return _write_report(
            output_root=output_root,
            output_custody_root=output_custody_root,
            report=report,
        )


def read_strong_leader_pullback_terminal_population_sec_content_census(
    *, output_root: Path, output_custody_root: Path
) -> StrongLeaderPullbackTerminalPopulationSecContentCensusResult:
    root = _validated_completed_output(output_root, output_custody_root)
    if {item.name for item in root.iterdir()} != {REPORT_FILE}:
        raise StrongLeaderPullbackTerminalPopulationSecContentCensusError(
            "terminal-population SEC content-census members differ"
        )
    path = root / REPORT_FILE
    source_base._require_regular_file(path, 0o400, MAXIMUM_REPORT_BYTES)
    raw = path.read_bytes()
    try:
        report = StrongLeaderPullbackTerminalPopulationSecContentCensusV1.model_validate_json(
            raw
        )
    except Exception as exc:
        raise StrongLeaderPullbackTerminalPopulationSecContentCensusError(
            "terminal-population SEC content census is invalid"
        ) from exc
    if raw != base._json_bytes(report.model_dump(mode="json")):
        raise StrongLeaderPullbackTerminalPopulationSecContentCensusError(
            "terminal-population SEC content-census bytes differ"
        )
    return StrongLeaderPullbackTerminalPopulationSecContentCensusResult(
        output_root=root,
        report=report,
        report_sha256=base._sha256_bytes(raw),
        status="already_present",
    )


def _build_report(
    *, plan: object, source: object, implementation_revision: str,
    evaluated_at: datetime,
) -> StrongLeaderPullbackTerminalPopulationSecContentCensusV1:
    if re.fullmatch(_REVISION_PATTERN, implementation_revision) is None:
        raise StrongLeaderPullbackTerminalPopulationSecContentCensusError(
            "terminal-population SEC content-census revision is invalid"
        )
    planned_count = plan.report.planned_request_count
    if (
        planned_count != len(plan.report.items)
        or source.completed_document_count != planned_count
        or source.manifest.completed_document_count != planned_count
    ):
        raise StrongLeaderPullbackTerminalPopulationSecContentCensusError(
            "terminal-population SEC content-census source count differs"
        )
    records = tuple(
        base._parse_document(
            path=source.output_root
            / f"request={item.request_sequence:06d}"
            / source_reader.DOCUMENT_FILE,
            item=item,
        )
        for item in plan.report.items
    )
    document_counts = Counter(
        marker.field_name
        for record in records
        for marker in record.field_markers
        if marker.occurrence_count
    )
    occurrence_counts = Counter()
    for record in records:
        occurrence_counts.update(
            {
                marker.field_name: marker.occurrence_count
                for marker in record.field_markers
                if marker.occurrence_count
            }
        )
    values = {
        "implementation_revision": implementation_revision,
        "evaluated_at": normalize_utc_datetime(evaluated_at),
        "plan_sha256": plan.report_sha256,
        "plan_logical_fingerprint": plan.report.logical_fingerprint,
        "source_manifest_sha256": source.manifest_sha256,
        "source_logical_fingerprint": source.manifest.logical_fingerprint,
        "source_artifact_binding_fingerprint": (
            source.manifest.artifact_binding_fingerprint
        ),
        "marker_ruleset_fingerprint": base._fingerprint(base._FIELD_PATTERNS),
        "document_count": len(records),
        "parsed_document_count": len(records),
        "form_counts": source_base._ordered(Counter(item.form for item in records)),
        "decoding_counts": source_base._ordered(
            Counter(item.decoding for item in records)
        ),
        "markup_profile_counts": source_base._ordered(
            Counter(item.markup_profile for item in records)
        ),
        "field_marker_document_counts": base._all_field_counts(document_counts),
        "field_marker_occurrence_counts": base._all_field_counts(
            occurrence_counts
        ),
        "total_document_bytes": sum(item.document_byte_count for item in records),
        "total_normalized_text_characters": sum(
            item.normalized_text_character_count for item in records
        ),
        "records": records,
    }
    provisional = StrongLeaderPullbackTerminalPopulationSecContentCensusV1.model_construct(
        **values, logical_fingerprint="0" * 64
    )
    return StrongLeaderPullbackTerminalPopulationSecContentCensusV1.model_validate(
        {
            **values,
            "logical_fingerprint": base._fingerprint(
                provisional.model_dump(mode="json", exclude={"logical_fingerprint"})
            ),
        }
    )


def _write_report(
    *, output_root: Path, output_custody_root: Path,
    report: StrongLeaderPullbackTerminalPopulationSecContentCensusV1,
) -> StrongLeaderPullbackTerminalPopulationSecContentCensusResult:
    target = _validated_output_target(output_root, output_custody_root)
    if target.exists() or target.is_symlink():
        existing = read_strong_leader_pullback_terminal_population_sec_content_census(
            output_root=target, output_custody_root=output_custody_root
        )
        if existing.report != report:
            raise StrongLeaderPullbackTerminalPopulationSecContentCensusError(
                "existing terminal-population SEC content census differs"
            )
        return existing
    partial = target.parent / f".{target.name}.partial.{os.getpid()}"
    if partial.exists() or partial.is_symlink():
        raise StrongLeaderPullbackTerminalPopulationSecContentCensusError(
            "terminal-population SEC content-census staging exists"
        )
    partial.mkdir(mode=0o700)
    try:
        raw = base._json_bytes(report.model_dump(mode="json"))
        if len(raw) > MAXIMUM_REPORT_BYTES:
            raise StrongLeaderPullbackTerminalPopulationSecContentCensusError(
                "terminal-population SEC content census exceeds byte ceiling"
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
    reread = read_strong_leader_pullback_terminal_population_sec_content_census(
        output_root=target, output_custody_root=output_custody_root
    )
    return StrongLeaderPullbackTerminalPopulationSecContentCensusResult(
        output_root=target,
        report=reread.report,
        report_sha256=reread.report_sha256,
        status="published",
    )


def _validated_output_target(path: Path, custody_root: Path) -> Path:
    if not path.is_absolute() or not custody_root.is_absolute():
        raise StrongLeaderPullbackTerminalPopulationSecContentCensusError(
            "terminal-population SEC content-census paths must be absolute"
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
        raise StrongLeaderPullbackTerminalPopulationSecContentCensusError(
            "terminal-population SEC content-census target is unsafe"
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
        raise StrongLeaderPullbackTerminalPopulationSecContentCensusError(
            "terminal-population SEC content-census output is unsafe"
        )
    return target
