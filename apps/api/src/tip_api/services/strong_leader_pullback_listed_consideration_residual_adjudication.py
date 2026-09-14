"""Adjudicate the three listed-consideration residual identities."""

from __future__ import annotations

import re
import shutil
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from tip_api.contracts.common import normalize_utc_datetime
from tip_api.services import (
    strong_leader_pullback_listed_consideration_adjudication as prior,
)
from tip_api.services import (
    strong_leader_pullback_listed_consideration_residual_source as residual_source,
)
from tip_api.services import (
    strong_leader_pullback_listed_consideration_residual_source_plan as residual_plan,
)
from tip_api.services import (
    strong_leader_pullback_listed_consideration_source as original_source,
)
from tip_api.services import (
    strong_leader_pullback_listed_consideration_source_plan as original_plan,
)
from tip_api.services import (
    strong_leader_pullback_sec_consideration_adjudication as consideration_source,
)


CONTRACT_VERSION = (
    "strong-leader-pullback-listed-consideration-residual-adjudication/1.0"
)
REPORT_FILE = "listed-consideration-residual-adjudication.json"
EXPECTED_CASE_COUNT = 3
EXPECTED_PRIOR_MATCHED_COUNT = 9
MAXIMUM_REPORT_BYTES = 512 * 1024
_SHA256_PATTERN = r"^[0-9a-f]{64}$"
_REVISION_PATTERN = r"^[0-9a-f]{40}$"

ResolutionState = Literal[
    "matched_existing_registration_plus_completion_disclosure",
    "matched_replacement_registration_plus_completion_disclosure",
    "required_evidence_not_matched",
]


class StrongLeaderPullbackListedConsiderationResidualAdjudicationError(
    RuntimeError
):
    """Raised when the three residual identities cannot be proven."""


class _FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class ListedConsiderationResidualIdentityDecisionV1(_FrozenModel):
    request_sequence: int = Field(ge=1)
    target_instrument_id: UUID
    proposed_consideration_instrument_id: UUID
    proposed_cik: str = Field(pattern=r"^[0-9]{10}$")
    resolution_path: residual_plan.ResolutionPath
    original_plan_decision_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    prior_identity_decision_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    prior_identity_resolution_state: str
    residual_plan_decision_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    original_registration_artifact_fingerprint: str = Field(
        pattern=_SHA256_PATTERN
    )
    original_registration_document_sha256: str = Field(pattern=_SHA256_PATTERN)
    replacement_registration_artifact_fingerprint: str | None = Field(
        default=None, pattern=_SHA256_PATTERN
    )
    replacement_registration_document_sha256: str | None = Field(
        default=None, pattern=_SHA256_PATTERN
    )
    completion_consideration_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    completion_disclosure_accession_number: str = Field(
        pattern=r"^[0-9]{10}-[0-9]{2}-[0-9]{6}$"
    )
    completion_disclosure_acceptance_datetime: datetime
    completion_disclosure_document_sha256: str = Field(pattern=_SHA256_PATTERN)
    completion_consideration_evidence_sha256: str = Field(
        pattern=_SHA256_PATTERN
    )
    expected_exchange_ratio: str = Field(
        pattern=r"^(?:0|[1-9][0-9]*)\.[0-9]{6}$"
    )
    registration_exact_ratio_occurrence_count: int = Field(ge=0)
    completion_exact_ratio_occurrence_count: int = Field(ge=0)
    sec_filer_cik_to_canonical_common_security_match: bool
    registration_transaction_match: bool
    registration_target_common_security_match: bool
    registration_consideration_security_class_match: bool
    registration_direct_final_ratio_match: bool
    completion_target_common_security_match: bool
    completion_consideration_security_class_match: bool
    completion_final_ratio_match: bool
    composite_evidence_match: bool
    registration_evidence: prior.ListedConsiderationEvidenceSpanV1 | None
    resolution_state: ResolutionState
    assigned_consideration_instrument_id: UUID | None
    consideration_security_identity_assignment_count: int = Field(ge=0, le=1)
    terminal_value_count: Literal[0] = 0
    strategy_outcome_label_count: Literal[0] = 0
    canonical_data_write_count: Literal[0] = 0
    historical_coverage_write_count: Literal[0] = 0
    research_admission_count: Literal[0] = 0
    source_name_or_ticker_grants_identity: Literal[False] = False
    decision_reasons: tuple[str, ...] = Field(min_length=1)
    logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)

    @field_validator("completion_disclosure_acceptance_datetime")
    @classmethod
    def acceptance_is_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @field_validator("decision_reasons", mode="before")
    @classmethod
    def reasons_are_ordered_unique(cls, value: object) -> tuple[object, ...]:
        values = tuple(value)  # type: ignore[arg-type]
        if values != tuple(sorted(set(values))):
            raise ValueError("residual identity decision reasons differ")
        return values

    @model_validator(mode="after")
    def decision_reconciles(
        self,
    ) -> "ListedConsiderationResidualIdentityDecisionV1":
        matched = self.resolution_state != "required_evidence_not_matched"
        replacement = (
            self.resolution_path == "replacement_registration_document_required"
        )
        replacement_fields = (
            self.replacement_registration_artifact_fingerprint,
            self.replacement_registration_document_sha256,
        )
        expected_state = (
            "matched_replacement_registration_plus_completion_disclosure"
            if replacement
            else "matched_existing_registration_plus_completion_disclosure"
        )
        common_gates = (
            self.sec_filer_cik_to_canonical_common_security_match
            and self.registration_transaction_match
            and self.registration_target_common_security_match
            and self.registration_consideration_security_class_match
            and self.completion_target_common_security_match
            and self.completion_consideration_security_class_match
            and self.completion_final_ratio_match
            and self.composite_evidence_match
        )
        if (
            replacement != all(item is not None for item in replacement_fields)
            or matched != (self.resolution_state == expected_state)
            or matched != common_gates
            or (
                matched
                and replacement != self.registration_direct_final_ratio_match
            )
            or matched != (self.registration_evidence is not None)
            or matched != (self.assigned_consideration_instrument_id is not None)
            or matched
            != (self.consideration_security_identity_assignment_count == 1)
            or (
                self.assigned_consideration_instrument_id is not None
                and self.assigned_consideration_instrument_id
                != self.proposed_consideration_instrument_id
            )
            or self.logical_fingerprint
            != residual_plan._fingerprint(
                self.model_dump(mode="json", exclude={"logical_fingerprint"})
            )
        ):
            raise ValueError("residual identity decision differs")
        return self


class StrongLeaderPullbackListedConsiderationResidualAdjudicationV1(
    _FrozenModel
):
    contract_version: Literal[
        "strong-leader-pullback-listed-consideration-residual-adjudication/1.0"
    ] = CONTRACT_VERSION
    completion_status: Literal[
        "listed_consideration_residual_identity_adjudicated"
    ] = "listed_consideration_residual_identity_adjudicated"
    implementation_revision: str = Field(pattern=_REVISION_PATTERN)
    evaluated_at: datetime
    ruleset_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    original_plan_report_sha256: str = Field(pattern=_SHA256_PATTERN)
    original_plan_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    original_source_manifest_sha256: str = Field(pattern=_SHA256_PATTERN)
    original_source_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    prior_identity_report_sha256: str = Field(pattern=_SHA256_PATTERN)
    prior_identity_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    residual_plan_report_sha256: str = Field(pattern=_SHA256_PATTERN)
    residual_plan_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    residual_source_manifest_sha256: str = Field(pattern=_SHA256_PATTERN)
    residual_source_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    consideration_report_sha256: str = Field(pattern=_SHA256_PATTERN)
    consideration_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    residual_case_count: Literal[3] = EXPECTED_CASE_COUNT
    prior_matched_identity_count: Literal[9] = EXPECTED_PRIOR_MATCHED_COUNT
    residual_matched_identity_count: int = Field(ge=0, le=EXPECTED_CASE_COUNT)
    cumulative_matched_identity_count: int = Field(
        ge=EXPECTED_PRIOR_MATCHED_COUNT,
        le=EXPECTED_PRIOR_MATCHED_COUNT + EXPECTED_CASE_COUNT,
    )
    required_evidence_not_matched_count: int = Field(
        ge=0, le=EXPECTED_CASE_COUNT
    )
    resolution_state_counts: tuple[tuple[str, int], ...]
    decisions: tuple[ListedConsiderationResidualIdentityDecisionV1, ...]
    consideration_security_identity_assignment_count: int = Field(
        ge=0, le=EXPECTED_CASE_COUNT
    )
    terminal_value_count: Literal[0] = 0
    strategy_outcome_label_count: Literal[0] = 0
    canonical_data_write_count: Literal[0] = 0
    historical_coverage_write_count: Literal[0] = 0
    research_admission_count: Literal[0] = 0
    candidate_write_count: Literal[0] = 0
    publication_count: Literal[0] = 0
    deployment_count: Literal[0] = 0
    scheduler_change_count: Literal[0] = 0
    logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)

    @field_validator("evaluated_at")
    @classmethod
    def evaluated_at_is_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @model_validator(mode="after")
    def report_reconciles(
        self,
    ) -> "StrongLeaderPullbackListedConsiderationResidualAdjudicationV1":
        states = Counter(item.resolution_state for item in self.decisions)
        if (
            len(self.decisions) != EXPECTED_CASE_COUNT
            or tuple(item.request_sequence for item in self.decisions)
            != tuple(sorted(residual_plan._RESIDUAL_SPECS))
            or self.residual_matched_identity_count
            != EXPECTED_CASE_COUNT - states["required_evidence_not_matched"]
            or self.required_evidence_not_matched_count
            != states["required_evidence_not_matched"]
            or self.cumulative_matched_identity_count
            != self.prior_matched_identity_count
            + self.residual_matched_identity_count
            or self.resolution_state_counts != _ordered(states)
            or self.consideration_security_identity_assignment_count
            != sum(
                item.consideration_security_identity_assignment_count
                for item in self.decisions
            )
            or self.consideration_security_identity_assignment_count
            != self.residual_matched_identity_count
            or self.logical_fingerprint
            != residual_plan._fingerprint(
                self.model_dump(mode="json", exclude={"logical_fingerprint"})
            )
        ):
            raise ValueError("residual identity adjudication report differs")
        return self


@dataclass(frozen=True, slots=True)
class StrongLeaderPullbackListedConsiderationResidualAdjudicationResult:
    output_root: Path
    report: StrongLeaderPullbackListedConsiderationResidualAdjudicationV1
    report_sha256: str
    status: Literal["published", "already_present"]


def build_strong_leader_pullback_listed_consideration_residual_adjudication(
    *,
    original_plan_root: Path,
    original_plan_custody_root: Path,
    original_source_root: Path,
    original_source_custody_root: Path,
    prior_identity_root: Path,
    prior_identity_custody_root: Path,
    residual_plan_root: Path,
    residual_plan_custody_root: Path,
    residual_source_root: Path,
    residual_source_custody_root: Path,
    consideration_root: Path,
    consideration_custody_root: Path,
    output_root: Path,
    output_custody_root: Path,
    implementation_revision: str,
    evaluated_at: datetime,
) -> StrongLeaderPullbackListedConsiderationResidualAdjudicationResult:
    with prior._network_prohibited():
        plan = original_plan.read_strong_leader_pullback_listed_consideration_source_plan(
            output_root=original_plan_root,
            output_custody_root=original_plan_custody_root,
        )
        source = original_source.read_strong_leader_pullback_listed_consideration_source(
            plan_root=original_plan_root,
            plan_custody_root=original_plan_custody_root,
            output_root=original_source_root,
            output_custody_root=original_source_custody_root,
        )
        identities = prior.read_strong_leader_pullback_listed_consideration_adjudication(
            output_root=prior_identity_root,
            output_custody_root=prior_identity_custody_root,
        )
        plan_reader = (
            residual_plan.read_strong_leader_pullback_listed_consideration_residual_source_plan
        )
        planned = plan_reader(
            output_root=residual_plan_root,
            output_custody_root=residual_plan_custody_root,
        )
        retained = residual_source.read_strong_leader_pullback_listed_consideration_residual_source(
            plan_root=residual_plan_root,
            plan_custody_root=residual_plan_custody_root,
            output_root=residual_source_root,
            output_custody_root=residual_source_custody_root,
        )
        consideration_reader = (
            consideration_source.read_strong_leader_pullback_sec_consideration_adjudication
        )
        consideration = consideration_reader(
            output_root=consideration_root,
            output_custody_root=consideration_custody_root,
        )
        report = _build_report(
            plan=plan,
            source=source,
            identities=identities,
            planned=planned,
            retained=retained,
            consideration=consideration,
            implementation_revision=implementation_revision,
            evaluated_at=evaluated_at,
        )
        return _write_report(
            output_root=output_root,
            output_custody_root=output_custody_root,
            report=report,
        )


def read_strong_leader_pullback_listed_consideration_residual_adjudication(
    *, output_root: Path, output_custody_root: Path
) -> StrongLeaderPullbackListedConsiderationResidualAdjudicationResult:
    root = prior._validated_completed_output(output_root, output_custody_root)
    if {item.name for item in root.iterdir()} != {REPORT_FILE}:
        raise StrongLeaderPullbackListedConsiderationResidualAdjudicationError(
            "residual identity adjudication members differ"
        )
    path = root / REPORT_FILE
    prior._require_regular_file(path, 0o400, MAXIMUM_REPORT_BYTES)
    raw = path.read_bytes()
    try:
        model = StrongLeaderPullbackListedConsiderationResidualAdjudicationV1
        report = model.model_validate_json(raw)
    except Exception as exc:
        raise StrongLeaderPullbackListedConsiderationResidualAdjudicationError(
            "residual identity adjudication report is invalid"
        ) from exc
    if raw != residual_plan._json_bytes(report.model_dump(mode="json")):
        raise StrongLeaderPullbackListedConsiderationResidualAdjudicationError(
            "residual identity adjudication bytes are not canonical"
        )
    return StrongLeaderPullbackListedConsiderationResidualAdjudicationResult(
        output_root=root,
        report=report,
        report_sha256=residual_plan._sha256_bytes(raw),
        status="already_present",
    )


def _build_report(
    *,
    plan: original_plan.StrongLeaderPullbackListedConsiderationSourcePlanResult,
    source: original_source.StrongLeaderPullbackListedConsiderationSourceResult,
    identities: prior.StrongLeaderPullbackListedConsiderationAdjudicationResult,
    planned: residual_plan.StrongLeaderPullbackListedConsiderationResidualSourcePlanResult,
    retained: residual_source.StrongLeaderPullbackListedConsiderationResidualSourceResult,
    consideration: consideration_source.StrongLeaderPullbackSecConsiderationAdjudicationResult,
    implementation_revision: str,
    evaluated_at: datetime,
) -> StrongLeaderPullbackListedConsiderationResidualAdjudicationV1:
    if re.fullmatch(_REVISION_PATTERN, implementation_revision) is None:
        raise StrongLeaderPullbackListedConsiderationResidualAdjudicationError(
            "residual identity adjudication revision is invalid"
        )
    if source.manifest is None or source.manifest_sha256 is None:
        raise StrongLeaderPullbackListedConsiderationResidualAdjudicationError(
            "original listed-consideration source is incomplete"
        )
    _validate_report_bindings(
        plan=plan,
        source=source,
        identities=identities,
        planned=planned,
        retained=retained,
        consideration=consideration,
    )
    plan_map = {item.request_sequence: item for item in plan.report.decisions}
    identity_map = {
        item.request_sequence: item for item in identities.report.decisions
    }
    planned_map = {
        item.request_sequence: item for item in planned.report.decisions
    }
    consideration_map = {
        item.request_sequence: item for item in consideration.report.decisions
    }
    sequences = set(residual_plan._RESIDUAL_SPECS)
    if not all(
        sequences.issubset(mapping)
        for mapping in (plan_map, identity_map, planned_map, consideration_map)
    ):
        raise StrongLeaderPullbackListedConsiderationResidualAdjudicationError(
            "residual identity population differs"
        )
    decisions = []
    for sequence in sorted(sequences):
        source_plan = plan_map[sequence]
        original_artifact = original_source._read_artifact_directory(
            source.output_root / f"request={sequence:06d}", source_plan
        )
        replacement_artifact = None
        replacement_path = None
        if sequence == residual_source.EXPECTED_REQUEST_SEQUENCE:
            adapter = residual_source._download_adapter(planned_map[sequence])
            replacement_artifact = original_source._read_artifact_directory(
                retained.output_root / f"request={sequence:06d}", adapter
            )
            replacement_path = (
                retained.output_root
                / f"request={sequence:06d}"
                / original_source.DOCUMENT_FILE
            )
        decisions.append(
            _adjudicate_decision(
                plan=source_plan,
                original_artifact=original_artifact,
                identity=identity_map[sequence],
                planned=planned_map[sequence],
                consideration=consideration_map[sequence],
                replacement_artifact=replacement_artifact,
                replacement_document_path=replacement_path,
            )
        )
    decision_tuple = tuple(decisions)
    states = Counter(item.resolution_state for item in decision_tuple)
    residual_matched = sum(
        item.consideration_security_identity_assignment_count
        for item in decision_tuple
    )
    values = {
        "implementation_revision": implementation_revision,
        "evaluated_at": normalize_utc_datetime(evaluated_at),
        "ruleset_fingerprint": _ruleset_fingerprint(),
        "original_plan_report_sha256": plan.report_sha256,
        "original_plan_logical_fingerprint": plan.report.logical_fingerprint,
        "original_source_manifest_sha256": source.manifest_sha256,
        "original_source_logical_fingerprint": source.manifest.logical_fingerprint,
        "prior_identity_report_sha256": identities.report_sha256,
        "prior_identity_logical_fingerprint": identities.report.logical_fingerprint,
        "residual_plan_report_sha256": planned.report_sha256,
        "residual_plan_logical_fingerprint": planned.report.logical_fingerprint,
        "residual_source_manifest_sha256": retained.manifest_sha256,
        "residual_source_logical_fingerprint": retained.manifest.logical_fingerprint,
        "consideration_report_sha256": consideration.report_sha256,
        "consideration_logical_fingerprint": consideration.report.logical_fingerprint,
        "residual_matched_identity_count": residual_matched,
        "cumulative_matched_identity_count": (
            EXPECTED_PRIOR_MATCHED_COUNT + residual_matched
        ),
        "required_evidence_not_matched_count": states[
            "required_evidence_not_matched"
        ],
        "resolution_state_counts": _ordered(states),
        "decisions": decision_tuple,
        "consideration_security_identity_assignment_count": residual_matched,
    }
    model = StrongLeaderPullbackListedConsiderationResidualAdjudicationV1
    provisional = model.model_construct(**values, logical_fingerprint="0" * 64)
    return model.model_validate(
        {
            **values,
            "logical_fingerprint": residual_plan._fingerprint(
                provisional.model_dump(mode="json", exclude={"logical_fingerprint"})
            ),
        }
    )


def _validate_report_bindings(
    *,
    plan: original_plan.StrongLeaderPullbackListedConsiderationSourcePlanResult,
    source: original_source.StrongLeaderPullbackListedConsiderationSourceResult,
    identities: prior.StrongLeaderPullbackListedConsiderationAdjudicationResult,
    planned: residual_plan.StrongLeaderPullbackListedConsiderationResidualSourcePlanResult,
    retained: residual_source.StrongLeaderPullbackListedConsiderationResidualSourceResult,
    consideration: consideration_source.StrongLeaderPullbackSecConsiderationAdjudicationResult,
) -> None:
    manifest = source.manifest
    if manifest is None or source.manifest_sha256 is None:
        raise StrongLeaderPullbackListedConsiderationResidualAdjudicationError(
            "original source manifest is unavailable"
        )
    if (
        manifest.plan_report_sha256 != plan.report_sha256
        or manifest.plan_logical_fingerprint != plan.report.logical_fingerprint
        or identities.report.plan_report_sha256 != plan.report_sha256
        or identities.report.source_manifest_sha256 != source.manifest_sha256
        or identities.report.matched_identity_count != EXPECTED_PRIOR_MATCHED_COUNT
        or planned.report.original_plan_report_sha256 != plan.report_sha256
        or planned.report.original_plan_logical_fingerprint
        != plan.report.logical_fingerprint
        or planned.report.identity_adjudication_report_sha256
        != identities.report_sha256
        or planned.report.identity_adjudication_logical_fingerprint
        != identities.report.logical_fingerprint
        or planned.report.consideration_report_sha256 != consideration.report_sha256
        or planned.report.consideration_logical_fingerprint
        != consideration.report.logical_fingerprint
        or retained.manifest.plan_report_sha256 != planned.report_sha256
        or retained.manifest.plan_logical_fingerprint
        != planned.report.logical_fingerprint
    ):
        raise StrongLeaderPullbackListedConsiderationResidualAdjudicationError(
            "residual identity input bindings differ"
        )


def _adjudicate_decision(
    *,
    plan: original_plan.ListedConsiderationSourcePlanDecisionV1,
    original_artifact: original_source.ListedConsiderationDocumentArtifactV1,
    identity: prior.ListedConsiderationIdentityDecisionV1,
    planned: residual_plan.ListedConsiderationResidualSourcePlanDecisionV1,
    consideration: consideration_source.SecCommonShareConsiderationDecisionV1,
    replacement_artifact: original_source.ListedConsiderationDocumentArtifactV1
    | None,
    replacement_document_path: Path | None,
) -> ListedConsiderationResidualIdentityDecisionV1:
    spec = residual_plan._RESIDUAL_SPECS[plan.request_sequence]
    _validate_decision_bindings(
        plan=plan,
        original_artifact=original_artifact,
        identity=identity,
        planned=planned,
        consideration=consideration,
        spec=spec,
    )
    completion_text = consideration.evidence_text or ""
    completion_ratio_count = len(
        tuple(residual_plan._ratio_pattern(spec.expected_ratio).finditer(completion_text))
    )
    completion_target = _contains(completion_text, spec.target_security_term)
    completion_security = _contains(
        completion_text, spec.consideration_security_term
    )
    completion_ratio = completion_ratio_count == 1
    identifier_match = (
        plan.canonical_cik == plan.proposed_cik
        and plan.canonical_source_instrument_id.startswith("share_class_figi:")
        and identity.sec_filer_cik_to_canonical_common_security_match
    )
    replacement = (
        planned.resolution_path == "replacement_registration_document_required"
    )
    evidence: prior.ListedConsiderationEvidenceSpanV1 | None
    registration_ratio_count: int
    if replacement:
        if replacement_artifact is None or replacement_document_path is None:
            raise StrongLeaderPullbackListedConsiderationResidualAdjudicationError(
                "replacement registration artifact is unavailable"
            )
        raw = replacement_document_path.read_bytes()
        if residual_plan._sha256_bytes(raw) != replacement_artifact.physical_sha256:
            raise StrongLeaderPullbackListedConsiderationResidualAdjudicationError(
                "replacement registration source differs"
            )
        normalized = prior._normalized_document(raw)
        exact_matches = tuple(
            prior._ratio_pattern(spec.expected_ratio).finditer(normalized)
        )
        selected = _direct_evidence(normalized, spec, exact_matches)
        evidence = (
            prior._evidence_span(
                normalized,
                *selected,
                "direct_registered_exchange_clause",
            )
            if selected is not None
            else None
        )
        registration_ratio_count = len(exact_matches)
        registration_transaction = selected is not None
        registration_target = selected is not None
        registration_security = selected is not None
        registration_direct_ratio = selected is not None
    else:
        evidence = identity.evidence
        registration_ratio_count = identity.exact_ratio_occurrence_count
        registration_transaction = identity.transaction_match
        registration_target = identity.target_common_security_match
        registration_security = identity.consideration_security_class_match
        registration_direct_ratio = identity.registered_exchange_ratio_match
    registration_match = (
        registration_transaction
        and registration_target
        and registration_security
        and (
            registration_direct_ratio
            if replacement
            else not registration_direct_ratio
        )
    )
    completion_match = completion_target and completion_security and completion_ratio
    matched = identifier_match and registration_match and completion_match
    if matched:
        state: ResolutionState = (
            "matched_replacement_registration_plus_completion_disclosure"
            if replacement
            else "matched_existing_registration_plus_completion_disclosure"
        )
        reasons = {
            "candidate_identity_bound_to_cik_and_stable_common_security",
            "completion_disclosure_matches_final_ratio_and_both_security_terms",
            "name_and_ticker_used_only_as_source_locators",
        }
        reasons.add(
            "replacement_registration_matches_transaction_classes_and_final_ratio"
            if replacement
            else "existing_registration_and_completion_disclosure_form_complete_chain"
        )
    else:
        state = "required_evidence_not_matched"
        reasons = {
            "candidate_stable_id_remains_unassigned",
            "complete_composite_evidence_chain_required",
            "name_and_ticker_used_only_as_source_locators",
        }
        if not identifier_match:
            reasons.add("cik_to_stable_common_security_chain_not_matched")
        if not registration_match:
            reasons.add("registration_transaction_class_or_ratio_not_matched")
        if not completion_match:
            reasons.add("completion_ratio_or_security_terms_not_matched")
    values = {
        "request_sequence": plan.request_sequence,
        "target_instrument_id": plan.target_instrument_id,
        "proposed_consideration_instrument_id": (
            plan.proposed_consideration_instrument_id
        ),
        "proposed_cik": plan.proposed_cik,
        "resolution_path": planned.resolution_path,
        "original_plan_decision_fingerprint": plan.logical_fingerprint,
        "prior_identity_decision_fingerprint": identity.logical_fingerprint,
        "prior_identity_resolution_state": identity.resolution_state,
        "residual_plan_decision_fingerprint": planned.logical_fingerprint,
        "original_registration_artifact_fingerprint": (
            original_artifact.logical_fingerprint
        ),
        "original_registration_document_sha256": original_artifact.physical_sha256,
        "replacement_registration_artifact_fingerprint": (
            replacement_artifact.logical_fingerprint
            if replacement_artifact is not None
            else None
        ),
        "replacement_registration_document_sha256": (
            replacement_artifact.physical_sha256
            if replacement_artifact is not None
            else None
        ),
        "completion_consideration_fingerprint": consideration.logical_fingerprint,
        "completion_disclosure_accession_number": consideration.accession_number,
        "completion_disclosure_acceptance_datetime": (
            consideration.acceptance_datetime
        ),
        "completion_disclosure_document_sha256": consideration.document_sha256,
        "completion_consideration_evidence_sha256": consideration.evidence_sha256,
        "expected_exchange_ratio": spec.expected_ratio,
        "registration_exact_ratio_occurrence_count": registration_ratio_count,
        "completion_exact_ratio_occurrence_count": completion_ratio_count,
        "sec_filer_cik_to_canonical_common_security_match": identifier_match,
        "registration_transaction_match": registration_transaction,
        "registration_target_common_security_match": registration_target,
        "registration_consideration_security_class_match": registration_security,
        "registration_direct_final_ratio_match": registration_direct_ratio,
        "completion_target_common_security_match": completion_target,
        "completion_consideration_security_class_match": completion_security,
        "completion_final_ratio_match": completion_ratio,
        "composite_evidence_match": matched,
        "registration_evidence": evidence if matched else None,
        "resolution_state": state,
        "assigned_consideration_instrument_id": (
            plan.proposed_consideration_instrument_id if matched else None
        ),
        "consideration_security_identity_assignment_count": int(matched),
        "decision_reasons": tuple(sorted(reasons)),
    }
    model = ListedConsiderationResidualIdentityDecisionV1
    provisional = model.model_construct(**values, logical_fingerprint="0" * 64)
    return model.model_validate(
        {
            **values,
            "logical_fingerprint": residual_plan._fingerprint(
                provisional.model_dump(mode="json", exclude={"logical_fingerprint"})
            ),
        }
    )


def _validate_decision_bindings(
    *,
    plan: original_plan.ListedConsiderationSourcePlanDecisionV1,
    original_artifact: original_source.ListedConsiderationDocumentArtifactV1,
    identity: prior.ListedConsiderationIdentityDecisionV1,
    planned: residual_plan.ListedConsiderationResidualSourcePlanDecisionV1,
    consideration: consideration_source.SecCommonShareConsiderationDecisionV1,
    spec: residual_plan._ResidualSpec,
) -> None:
    if (
        identity.request_sequence != plan.request_sequence
        or planned.request_sequence != plan.request_sequence
        or consideration.request_sequence != plan.request_sequence
        or identity.target_instrument_id != plan.target_instrument_id
        or planned.target_instrument_id != plan.target_instrument_id
        or consideration.instrument_id != plan.target_instrument_id
        or identity.proposed_consideration_instrument_id
        != plan.proposed_consideration_instrument_id
        or planned.proposed_consideration_instrument_id
        != plan.proposed_consideration_instrument_id
        or identity.proposed_cik != plan.proposed_cik
        or planned.proposed_cik != plan.proposed_cik
        or identity.plan_decision_fingerprint != plan.logical_fingerprint
        or planned.original_plan_decision_fingerprint != plan.logical_fingerprint
        or planned.prior_identity_decision_fingerprint
        != identity.logical_fingerprint
        or planned.prior_identity_resolution_state != identity.resolution_state
        or planned.original_registration_artifact_fingerprint
        != original_artifact.logical_fingerprint
        or planned.original_registration_document_sha256
        != original_artifact.physical_sha256
        or original_artifact.plan_decision_fingerprint != plan.logical_fingerprint
        or planned.completion_consideration_fingerprint
        != consideration.logical_fingerprint
        or planned.completion_disclosure_document_sha256
        != consideration.document_sha256
        or planned.completion_disclosure_accession_number
        != consideration.accession_number
        or planned.completion_disclosure_acceptance_datetime
        != consideration.acceptance_datetime
        or planned.completion_consideration_evidence_sha256
        != consideration.evidence_sha256
        or planned.expected_exchange_ratio != spec.expected_ratio
        or identity.expected_exchange_ratio != spec.expected_ratio
        or consideration.resolution_state != "matched"
        or consideration.evidence_text is None
        or consideration.evidence_sha256 is None
    ):
        raise StrongLeaderPullbackListedConsiderationResidualAdjudicationError(
            "residual identity decision bindings differ"
        )


def _direct_evidence(
    text: str,
    spec: residual_plan._ResidualSpec,
    matches: tuple[re.Match[str], ...],
) -> tuple[int, int] | None:
    for match in matches:
        start, end = prior._window(text, match.start(), match.end())
        candidate = text[start:end]
        if (
            _contains(candidate, spec.target_security_term)
            and _contains(candidate, spec.consideration_security_term)
            and re.search(r"\bmerger\b", candidate, re.IGNORECASE)
            and re.search(
                r"\b(?:receive|converted|exchange for)\b",
                candidate,
                re.IGNORECASE,
            )
        ):
            return start, end
    return None


def _contains(text: str, value: str) -> bool:
    return value.casefold() in text.casefold()


def _ruleset_fingerprint() -> str:
    return residual_plan._fingerprint(
        {
            "contract_version": CONTRACT_VERSION,
            "residual_cases": {
                str(sequence): {
                    "expected_ratio": spec.expected_ratio,
                    "target_security_term": spec.target_security_term,
                    "consideration_security_term": spec.consideration_security_term,
                    "prior_resolution_state": spec.prior_resolution_state,
                    "resolution_path": spec.resolution_path,
                }
                for sequence, spec in sorted(
                    residual_plan._RESIDUAL_SPECS.items()
                )
            },
            "local_composite_rule": (
                "issuer_registration_transaction_and_classes_plus_"
                "target_completion_final_ratio_and_security_terms"
            ),
            "replacement_rule": (
                "direct_registration_transaction_classes_and_final_ratio_plus_"
                "target_completion_corroboration"
            ),
            "identity_rule": "cik_to_point_in_time_stable_common_security",
            "name_and_ticker_authority": "locator_only",
            "terminal_value_count": 0,
        }
    )


def _ordered(counter: Counter[str]) -> tuple[tuple[str, int], ...]:
    return tuple(sorted((key, count) for key, count in counter.items() if count))


def _write_report(
    *,
    output_root: Path,
    output_custody_root: Path,
    report: StrongLeaderPullbackListedConsiderationResidualAdjudicationV1,
) -> StrongLeaderPullbackListedConsiderationResidualAdjudicationResult:
    target = prior._validated_output_target(output_root, output_custody_root)
    if target.exists() or target.is_symlink():
        existing = read_strong_leader_pullback_listed_consideration_residual_adjudication(
            output_root=target,
            output_custody_root=output_custody_root,
        )
        if existing.report != report:
            raise StrongLeaderPullbackListedConsiderationResidualAdjudicationError(
                "existing residual identity adjudication differs"
            )
        return existing
    partial = target.parent / f".{target.name}.partial"
    if partial.exists() or partial.is_symlink():
        raise StrongLeaderPullbackListedConsiderationResidualAdjudicationError(
            "residual identity adjudication staging target exists"
        )
    partial.mkdir(mode=0o700)
    try:
        prior._write_exclusive(
            partial / REPORT_FILE,
            residual_plan._json_bytes(report.model_dump(mode="json")),
        )
        prior._fsync_directory(partial)
        partial.replace(target)
        prior._fsync_directory(target.parent)
    except Exception:
        if partial.exists() and not partial.is_symlink():
            shutil.rmtree(partial)
        raise
    result = read_strong_leader_pullback_listed_consideration_residual_adjudication(
        output_root=target,
        output_custody_root=output_custody_root,
    )
    return StrongLeaderPullbackListedConsiderationResidualAdjudicationResult(
        output_root=result.output_root,
        report=result.report,
        report_sha256=result.report_sha256,
        status="published",
    )
