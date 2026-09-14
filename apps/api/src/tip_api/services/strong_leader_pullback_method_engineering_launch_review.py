"""Outcome-blind launch boundary for first-strategy method engineering."""

from __future__ import annotations

import os
import re
import shutil
import stat
from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from tip_api.contracts.analytics.v1 import (
    STRONG_STOCK_PULLBACK_EXPERIMENT_ID,
    STRONG_STOCK_PULLBACK_RESEARCH_FINGERPRINT,
    strong_stock_pullback_research_experiment_v1,
)
from tip_api.contracts.common import normalize_utc_datetime
from tip_api.services import strong_leader_pullback_pre_research_admission_review as upstream
from tip_api.services import strong_leader_pullback_sec_document_content_census as base
from tip_api.services import strong_leader_pullback_sec_document_source as source_base


CONTRACT_VERSION = "strong-leader-pullback-method-engineering-launch-review/1.0"
REPORT_FILE = "method-engineering-launch-review.json"
MAXIMUM_REPORT_BYTES = 128 * 1024
_SHA256_PATTERN = r"^[0-9a-f]{64}$"
_REVISION_PATTERN = r"^[0-9a-f]{40}$"
_OUTPUT_NAME_PATTERN = r"^review=[A-Za-z0-9._-]+$"
_METHOD_INPUT_FAMILY_ORDER = (
    "eod_price_bar",
    "point_in_time_identity",
    "universe_membership",
)


class StrongLeaderPullbackMethodEngineeringLaunchReviewError(RuntimeError):
    """Raised when the method-engineering boundary cannot be proven."""


class _FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class MethodEngineeringInputFamilyV1(_FrozenModel):
    family: Literal[
        "eod_price_bar",
        "point_in_time_identity",
        "universe_membership",
    ]
    status: Literal[
        "complete_reconstruction_input",
        "reconstructed_not_as_operated",
    ]
    evidence_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    formal_performance_authority: Literal[False] = False


class StrongLeaderPullbackMethodEngineeringLaunchReviewV1(_FrozenModel):
    contract_version: Literal[
        "strong-leader-pullback-method-engineering-launch-review/1.0"
    ] = CONTRACT_VERSION
    decision_status: Literal[
        "ready_for_outcome_blind_method_engineering"
    ] = "ready_for_outcome_blind_method_engineering"
    implementation_revision: str = Field(pattern=_REVISION_PATTERN)
    reviewed_at: datetime
    experiment_id: Literal[STRONG_STOCK_PULLBACK_EXPERIMENT_ID] = (
        STRONG_STOCK_PULLBACK_EXPERIMENT_ID
    )
    experiment_fingerprint: Literal[STRONG_STOCK_PULLBACK_RESEARCH_FINGERPRINT] = (
        STRONG_STOCK_PULLBACK_RESEARCH_FINGERPRINT
    )
    evaluation_policy_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    experiment_lifecycle_state: Literal[
        "preregistered_data_blocked"
    ] = "preregistered_data_blocked"
    evidence_tier: Literal[
        "reconstructed_latest_vintage_method_engineering_only"
    ] = "reconstructed_latest_vintage_method_engineering_only"
    pre_research_review_sha256: str = Field(pattern=_SHA256_PATTERN)
    pre_research_review_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    formal_data_gate_status: Literal["rejected_data_blocked"] = (
        "rejected_data_blocked"
    )
    first_signal_session: Literal["2025-06-23"] = "2025-06-23"
    last_signal_session: Literal["2026-08-12"] = "2026-08-12"
    signal_session_count: Literal[287] = 287
    included_path_count: Literal[437402] = 437402
    complete_cross_section_session_count: Literal[0] = 0
    method_input_families: tuple[MethodEngineeringInputFamilyV1, ...] = Field(
        min_length=3, max_length=3
    )
    unresolved_formal_blocker_codes: tuple[str, ...] = Field(min_length=1)
    allowed_action_codes: tuple[str, ...] = Field(min_length=1)
    prohibited_action_codes: tuple[str, ...] = Field(min_length=1)
    next_action: Literal[
        "implement_first_strategy_and_lab_method_surface_without_opening_outcomes"
    ] = "implement_first_strategy_and_lab_method_surface_without_opening_outcomes"
    method_engineering_authorized: Literal[True] = True
    private_outcome_blind_feature_diagnostics_authorized: Literal[True] = True
    quant_research_lab_method_surface_authorized: Literal[True] = True
    selection_reuse_prohibited: Literal[True] = True
    true_return_labels_authorized: Literal[False] = False
    parameter_selection_authorized: Literal[False] = False
    formal_development_stage_authorized: Literal[False] = False
    validation_authorized: Literal[False] = False
    holdout_access_authorized: Literal[False] = False
    performance_claims_authorized: Literal[False] = False
    candidate_activation_authorized: Literal[False] = False
    canonical_data_write_count: Literal[0] = 0
    publication_count: Literal[0] = 0
    deployment_count: Literal[0] = 0
    network_request_count: Literal[0] = 0
    logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)

    @field_validator("reviewed_at")
    @classmethod
    def reviewed_at_is_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @field_validator(
        "unresolved_formal_blocker_codes",
        "allowed_action_codes",
        "prohibited_action_codes",
        mode="before",
    )
    @classmethod
    def codes_are_ordered(cls, value: object) -> tuple[str, ...]:
        values = tuple(value)  # type: ignore[arg-type]
        if values != tuple(sorted(set(values))) or any(not item for item in values):
            raise ValueError("method-engineering launch codes differ")
        return values

    @model_validator(mode="after")
    def report_reconciles(
        self,
    ) -> "StrongLeaderPullbackMethodEngineeringLaunchReviewV1":
        if (
            tuple(item.family for item in self.method_input_families)
            != _METHOD_INPUT_FAMILY_ORDER
            or self.allowed_action_codes != _allowed_action_codes()
            or self.prohibited_action_codes != _prohibited_action_codes()
            or set(self.allowed_action_codes) & set(self.prohibited_action_codes)
            or self.logical_fingerprint
            != base._fingerprint(
                self.model_dump(mode="json", exclude={"logical_fingerprint"})
            )
        ):
            raise ValueError("method-engineering launch review differs")
        return self


class StrongLeaderPullbackMethodEngineeringLaunchReviewResult(_FrozenModel):
    output_root: Path
    report: StrongLeaderPullbackMethodEngineeringLaunchReviewV1
    report_sha256: str = Field(pattern=_SHA256_PATTERN)
    status: Literal["published", "already_present"]


def build_strong_leader_pullback_method_engineering_launch_review(
    *,
    pre_research_review_root: Path,
    pre_research_review_custody_root: Path,
    output_root: Path,
    output_custody_root: Path,
    implementation_revision: str,
    reviewed_at: datetime,
) -> StrongLeaderPullbackMethodEngineeringLaunchReviewResult:
    if re.fullmatch(_REVISION_PATTERN, implementation_revision) is None:
        raise StrongLeaderPullbackMethodEngineeringLaunchReviewError(
            "method-engineering launch revision differs"
        )
    pre_research = (
        upstream.read_strong_leader_pullback_pre_research_admission_review(
            output_root=pre_research_review_root,
            output_custody_root=pre_research_review_custody_root,
        )
    )
    report = _build_report(
        pre_research=pre_research.report,
        pre_research_sha256=pre_research.report_sha256,
        implementation_revision=implementation_revision,
        reviewed_at=reviewed_at,
    )
    return _write_report(
        output_root=output_root,
        output_custody_root=output_custody_root,
        report=report,
    )


def read_strong_leader_pullback_method_engineering_launch_review(
    *, output_root: Path, output_custody_root: Path
) -> StrongLeaderPullbackMethodEngineeringLaunchReviewResult:
    root = _validated_completed_output(output_root, output_custody_root)
    if {item.name for item in root.iterdir()} != {REPORT_FILE}:
        raise StrongLeaderPullbackMethodEngineeringLaunchReviewError(
            "method-engineering launch package members differ"
        )
    path = root / REPORT_FILE
    source_base._require_regular_file(path, 0o400, MAXIMUM_REPORT_BYTES)
    raw = path.read_bytes()
    try:
        report = StrongLeaderPullbackMethodEngineeringLaunchReviewV1.model_validate_json(
            raw
        )
    except Exception as exc:
        raise StrongLeaderPullbackMethodEngineeringLaunchReviewError(
            "method-engineering launch report is invalid"
        ) from exc
    if raw != base._json_bytes(report.model_dump(mode="json")):
        raise StrongLeaderPullbackMethodEngineeringLaunchReviewError(
            "method-engineering launch bytes differ"
        )
    return StrongLeaderPullbackMethodEngineeringLaunchReviewResult(
        output_root=root,
        report=report,
        report_sha256=base._sha256_bytes(raw),
        status="already_present",
    )


def _build_report(
    *,
    pre_research: upstream.StrongLeaderPullbackPreResearchAdmissionReviewV1,
    pre_research_sha256: str,
    implementation_revision: str,
    reviewed_at: datetime,
) -> StrongLeaderPullbackMethodEngineeringLaunchReviewV1:
    experiment = strong_stock_pullback_research_experiment_v1()
    if (
        pre_research.decision_status != "rejected_data_blocked"
        or pre_research.historical_coverage_manifest_published
        or pre_research.development_authorized
        or pre_research.true_return_labels_authorized
        or pre_research.strategy_research_started
        or pre_research.strategy_trigger_count != 0
        or pre_research.forward_outcome_count != 0
        or pre_research.performance_metric_count != 0
        or pre_research.parameter_selection_count != 0
        or pre_research.complete_cross_section_session_count != 0
        or pre_research.signal_session_count < 252
        or pre_research.included_path_count <= 0
    ):
        raise StrongLeaderPullbackMethodEngineeringLaunchReviewError(
            "pre-research rejection is not a safe method-engineering boundary"
        )
    by_family = {item.family: item for item in pre_research.family_reviews}
    method_families = tuple(
        MethodEngineeringInputFamilyV1(
            family=family,
            status=by_family[family].status,
            evidence_fingerprint=by_family[family].evidence_fingerprint,
        )
        for family in _METHOD_INPUT_FAMILY_ORDER
    )
    if (
        any(not by_family[family].development_ready for family in _METHOD_INPUT_FAMILY_ORDER)
        or tuple(item.status for item in method_families)
        != (
            "complete_reconstruction_input",
            "complete_reconstruction_input",
            "reconstructed_not_as_operated",
        )
    ):
        raise StrongLeaderPullbackMethodEngineeringLaunchReviewError(
            "method-engineering input families are not ready"
        )
    values = {
        "implementation_revision": implementation_revision,
        "reviewed_at": normalize_utc_datetime(reviewed_at),
        "experiment_id": experiment.experiment_id,
        "experiment_fingerprint": experiment.logical_fingerprint,
        "evaluation_policy_fingerprint": experiment.evaluation_policy_fingerprint,
        "experiment_lifecycle_state": experiment.stage.value,
        "pre_research_review_sha256": pre_research_sha256,
        "pre_research_review_logical_fingerprint": pre_research.logical_fingerprint,
        "formal_data_gate_status": pre_research.decision_status,
        "first_signal_session": pre_research.first_signal_session,
        "last_signal_session": pre_research.last_signal_session,
        "signal_session_count": pre_research.signal_session_count,
        "included_path_count": pre_research.included_path_count,
        "complete_cross_section_session_count": (
            pre_research.complete_cross_section_session_count
        ),
        "method_input_families": method_families,
        "unresolved_formal_blocker_codes": pre_research.blocker_codes,
        "allowed_action_codes": _allowed_action_codes(),
        "prohibited_action_codes": _prohibited_action_codes(),
    }
    provisional = StrongLeaderPullbackMethodEngineeringLaunchReviewV1.model_construct(
        **values, logical_fingerprint="0" * 64
    )
    return StrongLeaderPullbackMethodEngineeringLaunchReviewV1.model_validate(
        {
            **values,
            "logical_fingerprint": base._fingerprint(
                provisional.model_dump(mode="json", exclude={"logical_fingerprint"})
            ),
        }
    )


def _allowed_action_codes() -> tuple[str, ...]:
    return tuple(sorted((
        "build_private_outcome_blind_feature_quality_diagnostics",
        "implement_registered_feature_and_signal_code",
        "implement_quant_research_lab_method_and_readiness_views",
        "prepare_provider_neutral_label_and_sensitivity_interfaces",
        "run_synthetic_adversarial_and_property_tests",
    )))


def _prohibited_action_codes() -> tuple[str, ...]:
    return tuple(sorted((
        "access_or_construct_real_forward_outcomes",
        "activate_or_replace_candidate_model",
        "advance_formal_development_validation_or_holdout_state",
        "publish_or_claim_real_performance",
        "select_or_rank_parameters_using_real_outcomes",
        "treat_missing_action_or_terminal_evidence_as_neutral",
        "treat_reconstructed_membership_as_as_operated",
    )))


def _write_report(
    *,
    output_root: Path,
    output_custody_root: Path,
    report: StrongLeaderPullbackMethodEngineeringLaunchReviewV1,
) -> StrongLeaderPullbackMethodEngineeringLaunchReviewResult:
    target = _validated_output_target(output_root, output_custody_root)
    if target.exists() or target.is_symlink():
        existing = read_strong_leader_pullback_method_engineering_launch_review(
            output_root=target,
            output_custody_root=output_custody_root,
        )
        if existing.report != report:
            raise StrongLeaderPullbackMethodEngineeringLaunchReviewError(
                "existing method-engineering launch review differs"
            )
        return existing
    partial = target.parent / f".{target.name}.partial.{os.getpid()}"
    if partial.exists() or partial.is_symlink():
        raise StrongLeaderPullbackMethodEngineeringLaunchReviewError(
            "method-engineering launch staging exists"
        )
    partial.mkdir(mode=0o700)
    try:
        raw = base._json_bytes(report.model_dump(mode="json"))
        if len(raw) > MAXIMUM_REPORT_BYTES:
            raise StrongLeaderPullbackMethodEngineeringLaunchReviewError(
                "method-engineering launch review exceeds size limit"
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
    reread = read_strong_leader_pullback_method_engineering_launch_review(
        output_root=target,
        output_custody_root=output_custody_root,
    )
    return StrongLeaderPullbackMethodEngineeringLaunchReviewResult(
        output_root=target,
        report=reread.report,
        report_sha256=reread.report_sha256,
        status="published",
    )


def _validated_output_target(path: Path, custody_root: Path) -> Path:
    if not path.is_absolute() or not custody_root.is_absolute():
        raise StrongLeaderPullbackMethodEngineeringLaunchReviewError(
            "method-engineering launch paths must be absolute"
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
        raise StrongLeaderPullbackMethodEngineeringLaunchReviewError(
            "method-engineering launch target is unsafe"
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
        raise StrongLeaderPullbackMethodEngineeringLaunchReviewError(
            "method-engineering launch output is unsafe"
        )
    return target
