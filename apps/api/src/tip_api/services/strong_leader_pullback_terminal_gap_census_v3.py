"""Versioned SCS evidence extension for the corrected terminal-gap census."""

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
from tip_api.services import strong_leader_pullback_terminal_gap_census_v2 as prior_reader
from tip_api.services import (
    strong_leader_pullback_terminal_population_listed_reference as reference_reader,
)
from tip_api.services import (
    strong_leader_pullback_terminal_population_payoff_policy as policy_reader,
)


CONTRACT_VERSION = "strong-leader-pullback-terminal-gap-census/3.0"
REPORT_FILE = "terminal-gap-census-v3.json"
MAXIMUM_REPORT_BYTES = 768 * 1024
_SHA256_PATTERN = r"^[0-9a-f]{64}$"
_REVISION_PATTERN = r"^[0-9a-f]{40}$"
_OUTPUT_NAME_PATTERN = r"^census=[A-Za-z0-9._-]+$"


class StrongLeaderPullbackTerminalGapCensusV3Error(RuntimeError):
    """Raised when the SCS evidence extension cannot be reconciled."""


class _FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class StrongLeaderPullbackTerminalGapCensusV3(_FrozenModel):
    contract_version: Literal[
        "strong-leader-pullback-terminal-gap-census/3.0"
    ] = CONTRACT_VERSION
    completion_status: Literal["corrected_terminal_evidence_extended"] = (
        "corrected_terminal_evidence_extended"
    )
    implementation_revision: str = Field(pattern=_REVISION_PATTERN)
    evaluated_at: datetime
    ruleset_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    prior_census_report_sha256: str = Field(pattern=_SHA256_PATTERN)
    prior_census_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    listed_reference_report_sha256: str = Field(pattern=_SHA256_PATTERN)
    listed_reference_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    payoff_policy_report_sha256: str = Field(pattern=_SHA256_PATTERN)
    payoff_policy_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    extension_instrument_count: Literal[1] = 1
    extension_horizon_5_crossing_path_count: Literal[1] = 1
    population_instrument_count: int = Field(ge=1)
    legacy_population_instrument_count: int = Field(ge=1)
    newly_in_scope_instrument_count: int = Field(ge=1)
    structured_case_count: int = Field(ge=1)
    legacy_exception_case_count: int = Field(ge=0)
    new_primary_source_case_count: int = Field(ge=0)
    reference_documented_instrument_count: int = Field(ge=1)
    remaining_gap_instrument_count: int = Field(ge=0)
    horizon_1_crossing_path_count: int = Field(ge=0)
    horizon_3_crossing_path_count: int = Field(ge=0)
    horizon_5_crossing_path_count: int = Field(ge=1)
    documented_horizon_1_crossing_path_count: int = Field(ge=0)
    documented_horizon_3_crossing_path_count: int = Field(ge=0)
    documented_horizon_5_crossing_path_count: int = Field(ge=1)
    remaining_horizon_1_crossing_path_count: int = Field(ge=0)
    remaining_horizon_3_crossing_path_count: int = Field(ge=0)
    remaining_horizon_5_crossing_path_count: int = Field(ge=0)
    state_impacts: tuple[prior_reader.TerminalGapImpactV2, ...]
    priority_order: tuple[prior_reader.GapState, ...]
    decisions: tuple[prior_reader.TerminalGapDecisionV2, ...]
    prior_v2_preserved: Literal[True] = True
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
    def report_reconciles(self) -> "StrongLeaderPullbackTerminalGapCensusV3":
        decisions = self.decisions
        documented = tuple(item for item in decisions if item.reference_evidence_count)
        remaining = tuple(item for item in decisions if not item.reference_evidence_count)
        origins = Counter(item.population_origin for item in decisions)
        if (
            tuple(item.instrument_id for item in decisions)
            != tuple(sorted({item.instrument_id for item in decisions}, key=str))
            or len(decisions) != self.population_instrument_count
            or origins["legacy_identity_boundary_sample"]
            != self.legacy_population_instrument_count
            or origins["corrected_eod_boundary"] != self.newly_in_scope_instrument_count
            or self.structured_case_count
            + self.legacy_exception_case_count
            + self.new_primary_source_case_count
            != self.population_instrument_count
            or len(documented) != self.reference_documented_instrument_count
            or len(remaining) != self.remaining_gap_instrument_count
            or self.state_impacts != prior_reader._impacts(decisions)
            or self.priority_order != prior_reader._PRIORITY_ORDER
            or any(
                getattr(self, f"{prefix}horizon_{horizon}_crossing_path_count")
                != sum(
                    getattr(item, f"horizon_{horizon}_crossing_path_count")
                    for item in subset
                )
                for prefix, subset in (
                    ("", decisions),
                    ("documented_", documented),
                    ("remaining_", remaining),
                )
                for horizon in (1, 3, 5)
            )
            or self.ruleset_fingerprint != _ruleset_fingerprint()
            or self.logical_fingerprint
            != base._fingerprint(
                self.model_dump(mode="json", exclude={"logical_fingerprint"})
            )
        ):
            raise ValueError("terminal-gap V3 report differs")
        return self


@dataclass(frozen=True, slots=True)
class StrongLeaderPullbackTerminalGapCensusV3Result:
    output_root: Path
    report: StrongLeaderPullbackTerminalGapCensusV3
    report_sha256: str
    status: Literal["published", "already_present"]


def build_strong_leader_pullback_terminal_gap_census_v3(
    *,
    prior_census_root: Path,
    prior_census_custody_root: Path,
    listed_reference_root: Path,
    listed_reference_custody_root: Path,
    payoff_policy_root: Path,
    payoff_policy_custody_root: Path,
    output_root: Path,
    output_custody_root: Path,
    implementation_revision: str,
    evaluated_at: datetime,
) -> StrongLeaderPullbackTerminalGapCensusV3Result:
    with base._network_prohibited():
        prior = prior_reader.read_strong_leader_pullback_terminal_gap_census_v2(
            output_root=prior_census_root,
            output_custody_root=prior_census_custody_root,
        )
        reference = reference_reader.read_strong_leader_pullback_terminal_population_listed_reference(
            output_root=listed_reference_root,
            output_custody_root=listed_reference_custody_root,
        )
        policy = policy_reader.read_strong_leader_pullback_terminal_population_payoff_policy(
            output_root=payoff_policy_root,
            output_custody_root=payoff_policy_custody_root,
        )
        report = _build_report(
            prior=prior,
            reference=reference,
            policy=policy,
            implementation_revision=implementation_revision,
            evaluated_at=evaluated_at,
        )
        return _write_report(
            output_root=output_root,
            output_custody_root=output_custody_root,
            report=report,
        )


def read_strong_leader_pullback_terminal_gap_census_v3(
    *, output_root: Path, output_custody_root: Path
) -> StrongLeaderPullbackTerminalGapCensusV3Result:
    root = _validated_completed_output(output_root, output_custody_root)
    if {item.name for item in root.iterdir()} != {REPORT_FILE}:
        raise StrongLeaderPullbackTerminalGapCensusV3Error(
            "terminal-gap V3 package members differ"
        )
    path = root / REPORT_FILE
    source_base._require_regular_file(path, 0o400, MAXIMUM_REPORT_BYTES)
    raw = path.read_bytes()
    try:
        report = StrongLeaderPullbackTerminalGapCensusV3.model_validate_json(raw)
    except Exception as exc:
        raise StrongLeaderPullbackTerminalGapCensusV3Error(
            "terminal-gap V3 report is invalid"
        ) from exc
    if raw != base._json_bytes(report.model_dump(mode="json")):
        raise StrongLeaderPullbackTerminalGapCensusV3Error(
            "terminal-gap V3 bytes differ"
        )
    return StrongLeaderPullbackTerminalGapCensusV3Result(
        output_root=root,
        report=report,
        report_sha256=base._sha256_bytes(raw),
        status="already_present",
    )


def _build_report(
    *, prior: object, reference: object, policy: object,
    implementation_revision: str, evaluated_at: datetime,
) -> StrongLeaderPullbackTerminalGapCensusV3:
    if re.fullmatch(_REVISION_PATTERN, implementation_revision) is None:
        raise StrongLeaderPullbackTerminalGapCensusV3Error(
            "terminal-gap V3 revision is invalid"
        )
    if (
        reference.report.payoff_policy_report_sha256 != policy.report_sha256
        or reference.report.payoff_policy_logical_fingerprint
        != policy.report.logical_fingerprint
        or reference.report.identity.source_target_instrument_id
        != reference_reader.TARGET_INSTRUMENT_ID
        or reference.report.terminal_reference_case_count != 1
        or reference.report.canonical_terminal_outcome_count != 0
        or policy.report.party_relation.instrument_id
        != reference_reader.TARGET_INSTRUMENT_ID
    ):
        raise StrongLeaderPullbackTerminalGapCensusV3Error(
            "terminal-gap V3 extension binding differs"
        )
    prior_by_id = {item.instrument_id: item for item in prior.report.decisions}
    current = prior_by_id.get(reference_reader.TARGET_INSTRUMENT_ID)
    if (
        current is None
        or current.gap_state != "newly_in_scope_primary_source_unadjudicated"
        or current.reference_evidence_count != 0
        or current.horizon_1_crossing_path_count != 0
        or current.horizon_3_crossing_path_count != 0
        or current.horizon_5_crossing_path_count != 1
    ):
        raise StrongLeaderPullbackTerminalGapCensusV3Error(
            "terminal-gap V3 prior SCS decision differs"
        )
    replacement_values = {
        **current.model_dump(mode="python", exclude={"logical_fingerprint"}),
        "gap_state": "gross_listed_consideration_reference_documented",
        "reference_kind": "gross_listed_consideration",
        "reference_evidence_count": 1,
        "reference_source_available_at": (
            policy.report.party_relation.acceptance_datetime
        ),
        "reference_quality_flags": reference.report.price_quality_flags,
        "next_required_gate": "lifecycle_fact_and_label_policy_required",
    }
    provisional_decision = prior_reader.TerminalGapDecisionV2.model_construct(
        **replacement_values, logical_fingerprint="0" * 64
    )
    replacement = prior_reader.TerminalGapDecisionV2.model_validate(
        {
            **replacement_values,
            "logical_fingerprint": prior_reader._fingerprint(
                provisional_decision.model_dump(
                    mode="json", exclude={"logical_fingerprint"}
                )
            ),
        }
    )
    decisions = tuple(
        replacement if item.instrument_id == replacement.instrument_id else item
        for item in prior.report.decisions
    )
    documented = tuple(item for item in decisions if item.reference_evidence_count)
    remaining = tuple(item for item in decisions if not item.reference_evidence_count)
    values: dict[str, object] = {
        "implementation_revision": implementation_revision,
        "evaluated_at": normalize_utc_datetime(evaluated_at),
        "ruleset_fingerprint": _ruleset_fingerprint(),
        "prior_census_report_sha256": prior.report_sha256,
        "prior_census_logical_fingerprint": prior.report.logical_fingerprint,
        "listed_reference_report_sha256": reference.report_sha256,
        "listed_reference_logical_fingerprint": reference.report.logical_fingerprint,
        "payoff_policy_report_sha256": policy.report_sha256,
        "payoff_policy_logical_fingerprint": policy.report.logical_fingerprint,
        "population_instrument_count": prior.report.population_instrument_count,
        "legacy_population_instrument_count": (
            prior.report.legacy_population_instrument_count
        ),
        "newly_in_scope_instrument_count": prior.report.newly_in_scope_instrument_count,
        "structured_case_count": prior.report.structured_case_count + 1,
        "legacy_exception_case_count": prior.report.legacy_exception_case_count,
        "new_primary_source_case_count": prior.report.new_primary_source_case_count - 1,
        "reference_documented_instrument_count": len(documented),
        "remaining_gap_instrument_count": len(remaining),
        "state_impacts": prior_reader._impacts(decisions),
        "priority_order": prior_reader._PRIORITY_ORDER,
        "decisions": decisions,
    }
    for prefix, subset in (
        ("", decisions),
        ("documented_", documented),
        ("remaining_", remaining),
    ):
        for horizon in (1, 3, 5):
            values[f"{prefix}horizon_{horizon}_crossing_path_count"] = sum(
                getattr(item, f"horizon_{horizon}_crossing_path_count")
                for item in subset
            )
    provisional = StrongLeaderPullbackTerminalGapCensusV3.model_construct(
        **values, logical_fingerprint="0" * 64
    )
    return StrongLeaderPullbackTerminalGapCensusV3.model_validate(
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
            "contract_version": CONTRACT_VERSION,
            "prior_contract": prior_reader.CONTRACT_VERSION,
            "extension_contract": reference_reader.CONTRACT_VERSION,
            "extension_instrument_id": str(reference_reader.TARGET_INSTRUMENT_ID),
            "replacement_state": "gross_listed_consideration_reference_documented",
            "terminal_outcome": "not_authorized",
        }
    )


def _write_report(
    *, output_root: Path, output_custody_root: Path,
    report: StrongLeaderPullbackTerminalGapCensusV3,
) -> StrongLeaderPullbackTerminalGapCensusV3Result:
    target = _validated_output_target(output_root, output_custody_root)
    if target.exists() or target.is_symlink():
        existing = read_strong_leader_pullback_terminal_gap_census_v3(
            output_root=target, output_custody_root=output_custody_root
        )
        if existing.report != report:
            raise StrongLeaderPullbackTerminalGapCensusV3Error(
                "existing terminal-gap V3 report differs"
            )
        return existing
    partial = target.parent / f".{target.name}.partial.{os.getpid()}"
    if partial.exists() or partial.is_symlink():
        raise StrongLeaderPullbackTerminalGapCensusV3Error(
            "terminal-gap V3 staging exists"
        )
    partial.mkdir(mode=0o700)
    try:
        raw = base._json_bytes(report.model_dump(mode="json"))
        if len(raw) > MAXIMUM_REPORT_BYTES:
            raise StrongLeaderPullbackTerminalGapCensusV3Error(
                "terminal-gap V3 report exceeds byte ceiling"
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
    reread = read_strong_leader_pullback_terminal_gap_census_v3(
        output_root=target, output_custody_root=output_custody_root
    )
    return StrongLeaderPullbackTerminalGapCensusV3Result(
        output_root=target,
        report=reread.report,
        report_sha256=reread.report_sha256,
        status="published",
    )


def _validated_output_target(path: Path, custody_root: Path) -> Path:
    if not path.is_absolute() or not custody_root.is_absolute():
        raise StrongLeaderPullbackTerminalGapCensusV3Error(
            "terminal-gap V3 paths must be absolute"
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
        raise StrongLeaderPullbackTerminalGapCensusV3Error(
            "terminal-gap V3 target is unsafe"
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
        raise StrongLeaderPullbackTerminalGapCensusV3Error(
            "terminal-gap V3 output is unsafe"
        )
    return target
