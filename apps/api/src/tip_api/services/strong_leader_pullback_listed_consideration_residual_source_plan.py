"""Freeze the exact residual source path for listed merger consideration."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import socket
import stat
import zipfile
from collections import Counter
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Iterator, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from tip_api.contracts.common import normalize_utc_datetime
from tip_api.providers.sec.submissions_source import (
    ARCHIVE_FILE,
    SecSubmissionsSourceManifestV1,
    read_sec_submissions_source_package,
)
from tip_api.services.strong_leader_pullback_listed_consideration_adjudication import (
    ListedConsiderationIdentityDecisionV1,
    StrongLeaderPullbackListedConsiderationAdjudicationResult,
    read_strong_leader_pullback_listed_consideration_adjudication,
)
from tip_api.services.strong_leader_pullback_listed_consideration_source_plan import (
    ListedConsiderationSourcePlanDecisionV1,
    StrongLeaderPullbackListedConsiderationSourcePlanResult,
    read_strong_leader_pullback_listed_consideration_source_plan,
)
from tip_api.services.strong_leader_pullback_sec_consideration_adjudication import (
    SecCommonShareConsiderationDecisionV1,
    StrongLeaderPullbackSecConsiderationAdjudicationResult,
    _fingerprint,
    _json_bytes,
    _sha256_bytes,
    read_strong_leader_pullback_sec_consideration_adjudication,
)


CONTRACT_VERSION = (
    "strong-leader-pullback-listed-consideration-residual-source-plan/1.0"
)
REPORT_FILE = "listed-consideration-residual-source-plan.json"
EXPECTED_CASE_COUNT = 3
EXPECTED_LOCAL_COMPOSITE_COUNT = 2
EXPECTED_NEW_SOURCE_COUNT = 1
MAXIMUM_REPORT_BYTES = 512 * 1024
MAXIMUM_SUBMISSION_MEMBER_BYTES = 64 * 1024 * 1024
_SHA256_PATTERN = r"^[0-9a-f]{64}$"
_REVISION_PATTERN = r"^[0-9a-f]{40}$"
_CIK_PATTERN = r"^[0-9]{10}$"
_ACCESSION_PATTERN = r"^[0-9]{10}-[0-9]{2}-[0-9]{6}$"
_OUTPUT_NAME_PATTERN = r"^plan=[A-Za-z0-9._-]+$"
_RATIO_PATTERN = r"^(?:0|[1-9][0-9]*)\.[0-9]{6}$"

ResolutionPath = Literal[
    "existing_registration_plus_completion_disclosure",
    "replacement_registration_document_required",
]


@dataclass(frozen=True, slots=True)
class _ResidualSpec:
    expected_ratio: str
    target_security_term: str
    consideration_security_term: str
    prior_resolution_state: str
    resolution_path: ResolutionPath
    replacement_form: str | None = None
    replacement_filing_date: date | None = None
    replacement_acceptance_datetime: datetime | None = None
    replacement_accession_number: str | None = None
    replacement_primary_document: str | None = None


def _dt(value: str) -> datetime:
    return normalize_utc_datetime(datetime.fromisoformat(value))


_RESIDUAL_SPECS = {
    158: _ResidualSpec(
        expected_ratio="0.488300",
        target_security_term="SkyWater common stock",
        consideration_security_term="common stock of IonQ",
        prior_resolution_state=(
            "final_exchange_ratio_absent_from_registration_source"
        ),
        resolution_path="existing_registration_plus_completion_disclosure",
    ),
    174: _ResidualSpec(
        expected_ratio="1.866300",
        target_security_term="Comerica Common Stock",
        consideration_security_term="Fifth Third Common Stock",
        prior_resolution_state="transaction_registration_scope_absent",
        resolution_path="replacement_registration_document_required",
        replacement_form="424B3",
        replacement_filing_date=date(2025, 11, 25),
        replacement_acceptance_datetime=_dt("2025-11-25T21:05:53Z"),
        replacement_accession_number="0001193125-25-297171",
        replacement_primary_document="d942117d424b3.htm",
    ),
    184: _ResidualSpec(
        expected_ratio="0.195500",
        target_security_term="Spirit Common Stock",
        consideration_security_term="Boeing Common Stock",
        prior_resolution_state=(
            "final_exchange_ratio_absent_from_registration_source"
        ),
        resolution_path="existing_registration_plus_completion_disclosure",
    ),
}


class StrongLeaderPullbackListedConsiderationResidualSourcePlanError(
    RuntimeError
):
    """Raised when the three-case residual source plan cannot be proven."""


class _FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class ListedConsiderationResidualSourcePlanDecisionV1(_FrozenModel):
    request_sequence: int = Field(ge=1)
    target_instrument_id: UUID
    proposed_consideration_instrument_id: UUID
    proposed_cik: str = Field(pattern=_CIK_PATTERN)
    original_plan_decision_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    prior_identity_decision_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    prior_identity_resolution_state: str
    original_registration_artifact_fingerprint: str = Field(
        pattern=_SHA256_PATTERN
    )
    original_registration_document_sha256: str = Field(pattern=_SHA256_PATTERN)
    completion_consideration_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    completion_disclosure_accession_number: str = Field(
        pattern=_ACCESSION_PATTERN
    )
    completion_disclosure_acceptance_datetime: datetime
    completion_disclosure_document_sha256: str = Field(pattern=_SHA256_PATTERN)
    completion_consideration_evidence_sha256: str = Field(
        pattern=_SHA256_PATTERN
    )
    expected_exchange_ratio: str = Field(pattern=_RATIO_PATTERN)
    completion_exact_ratio_occurrence_count: Literal[1] = 1
    completion_target_security_match: Literal[True] = True
    completion_consideration_security_match: Literal[True] = True
    resolution_path: ResolutionPath
    replacement_registration_form: Literal["424B3"] | None = None
    replacement_registration_filing_date: date | None = None
    replacement_registration_acceptance_datetime: datetime | None = None
    replacement_registration_accession_number: str | None = Field(
        default=None, pattern=_ACCESSION_PATTERN
    )
    replacement_registration_primary_document: str | None = Field(
        default=None, pattern=r"^[A-Za-z0-9._-]+$"
    )
    replacement_registration_document_url: str | None = Field(
        default=None,
        pattern=(
            r"^https://www\.sec\.gov/Archives/edgar/data/[0-9]+/"
            r"[0-9]+/[A-Za-z0-9._-]+$"
        ),
    )
    new_source_request_count: int = Field(ge=0, le=1)
    consideration_security_identity_assignment_count: Literal[0] = 0
    terminal_value_count: Literal[0] = 0
    strategy_outcome_label_count: Literal[0] = 0
    decision_reasons: tuple[str, ...] = Field(min_length=1)
    logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)

    @field_validator(
        "completion_disclosure_acceptance_datetime",
        "replacement_registration_acceptance_datetime",
    )
    @classmethod
    def times_are_utc(cls, value: datetime | None) -> datetime | None:
        return normalize_utc_datetime(value) if value is not None else None

    @field_validator("decision_reasons", mode="before")
    @classmethod
    def reasons_are_ordered_unique(cls, value: object) -> tuple[object, ...]:
        values = tuple(value)  # type: ignore[arg-type]
        if values != tuple(sorted(set(values))):
            raise ValueError("residual source-plan reasons differ")
        return values

    @model_validator(mode="after")
    def decision_reconciles(
        self,
    ) -> "ListedConsiderationResidualSourcePlanDecisionV1":
        replacement_fields = (
            self.replacement_registration_form,
            self.replacement_registration_filing_date,
            self.replacement_registration_acceptance_datetime,
            self.replacement_registration_accession_number,
            self.replacement_registration_primary_document,
            self.replacement_registration_document_url,
        )
        requests_source = (
            self.resolution_path == "replacement_registration_document_required"
        )
        if (
            (
                requests_source
                and not all(item is not None for item in replacement_fields)
            )
            or (
                not requests_source
                and any(item is not None for item in replacement_fields)
            )
            or requests_source != (self.new_source_request_count == 1)
            or not _decision_matches_registry(self)
            or self.logical_fingerprint
            != _fingerprint(
                self.model_dump(mode="json", exclude={"logical_fingerprint"})
            )
        ):
            raise ValueError("residual source-plan decision differs")
        return self


class StrongLeaderPullbackListedConsiderationResidualSourcePlanV1(_FrozenModel):
    contract_version: Literal[
        "strong-leader-pullback-listed-consideration-residual-source-plan/1.0"
    ] = CONTRACT_VERSION
    completion_status: Literal[
        "listed_consideration_residual_source_plan_frozen"
    ] = "listed_consideration_residual_source_plan_frozen"
    implementation_revision: str = Field(pattern=_REVISION_PATTERN)
    evaluated_at: datetime
    ruleset_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    original_plan_report_sha256: str = Field(pattern=_SHA256_PATTERN)
    original_plan_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    identity_adjudication_report_sha256: str = Field(pattern=_SHA256_PATTERN)
    identity_adjudication_logical_fingerprint: str = Field(
        pattern=_SHA256_PATTERN
    )
    consideration_report_sha256: str = Field(pattern=_SHA256_PATTERN)
    consideration_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    submissions_manifest_sha256: str = Field(pattern=_SHA256_PATTERN)
    submissions_source_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    submissions_archive_sha256: str = Field(pattern=_SHA256_PATTERN)
    residual_case_count: Literal[3] = EXPECTED_CASE_COUNT
    local_composite_evidence_ready_count: Literal[2] = (
        EXPECTED_LOCAL_COMPOSITE_COUNT
    )
    replacement_registration_required_count: Literal[1] = (
        EXPECTED_NEW_SOURCE_COUNT
    )
    planned_source_document_count: Literal[1] = EXPECTED_NEW_SOURCE_COUNT
    resolution_path_counts: tuple[tuple[str, int], ...]
    decisions: tuple[ListedConsiderationResidualSourcePlanDecisionV1, ...]
    source_document_count: Literal[0] = 0
    consideration_security_identity_assignment_count: Literal[0] = 0
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
    ) -> "StrongLeaderPullbackListedConsiderationResidualSourcePlanV1":
        states = Counter(item.resolution_path for item in self.decisions)
        if (
            self.ruleset_fingerprint != _ruleset_fingerprint()
            or len(self.decisions) != EXPECTED_CASE_COUNT
            or tuple(item.request_sequence for item in self.decisions)
            != tuple(sorted(_RESIDUAL_SPECS))
            or self.local_composite_evidence_ready_count
            != states["existing_registration_plus_completion_disclosure"]
            or self.replacement_registration_required_count
            != states["replacement_registration_document_required"]
            or self.planned_source_document_count
            != sum(item.new_source_request_count for item in self.decisions)
            or self.resolution_path_counts != _ordered(states)
            or self.logical_fingerprint
            != _fingerprint(
                self.model_dump(mode="json", exclude={"logical_fingerprint"})
            )
        ):
            raise ValueError("residual source plan differs")
        return self


@dataclass(frozen=True, slots=True)
class StrongLeaderPullbackListedConsiderationResidualSourcePlanResult:
    output_root: Path
    report: StrongLeaderPullbackListedConsiderationResidualSourcePlanV1
    report_sha256: str
    status: Literal["published", "already_present"]


def build_strong_leader_pullback_listed_consideration_residual_source_plan(
    *,
    original_plan_root: Path,
    original_plan_custody_root: Path,
    identity_adjudication_root: Path,
    identity_adjudication_custody_root: Path,
    consideration_root: Path,
    consideration_custody_root: Path,
    submissions_package_root: Path,
    submissions_custody_root: Path,
    output_root: Path,
    output_custody_root: Path,
    implementation_revision: str,
    evaluated_at: datetime,
) -> StrongLeaderPullbackListedConsiderationResidualSourcePlanResult:
    with _network_prohibited():
        original_plan = read_strong_leader_pullback_listed_consideration_source_plan(
            output_root=original_plan_root,
            output_custody_root=original_plan_custody_root,
        )
        identities = read_strong_leader_pullback_listed_consideration_adjudication(
            output_root=identity_adjudication_root,
            output_custody_root=identity_adjudication_custody_root,
        )
        consideration = read_strong_leader_pullback_sec_consideration_adjudication(
            output_root=consideration_root,
            output_custody_root=consideration_custody_root,
        )
        submissions = read_sec_submissions_source_package(
            package_path=submissions_package_root,
            approved_custody_root=submissions_custody_root,
        )
        member_payload, member_sha256 = _read_fifth_third_submission_member(
            submissions_package_root / ARCHIVE_FILE
        )
        report = _build_report(
            original_plan=original_plan,
            identities=identities,
            consideration=consideration,
            submissions=submissions,
            submissions_manifest_sha256=_sha256_file(
                submissions_package_root / "package.json"
            ),
            fifth_third_submission_payload=member_payload,
            fifth_third_submission_member_sha256=member_sha256,
            implementation_revision=implementation_revision,
            evaluated_at=evaluated_at,
        )
        return _write_report(
            output_root=output_root,
            output_custody_root=output_custody_root,
            report=report,
        )


def read_strong_leader_pullback_listed_consideration_residual_source_plan(
    *, output_root: Path, output_custody_root: Path
) -> StrongLeaderPullbackListedConsiderationResidualSourcePlanResult:
    root = _validated_completed_output(output_root, output_custody_root)
    if {item.name for item in root.iterdir()} != {REPORT_FILE}:
        raise StrongLeaderPullbackListedConsiderationResidualSourcePlanError(
            "residual source-plan package members differ"
        )
    path = root / REPORT_FILE
    _require_regular_file(path, 0o400, MAXIMUM_REPORT_BYTES)
    raw = path.read_bytes()
    try:
        model = StrongLeaderPullbackListedConsiderationResidualSourcePlanV1
        report = model.model_validate_json(raw)
    except Exception as exc:
        raise StrongLeaderPullbackListedConsiderationResidualSourcePlanError(
            "residual source plan is invalid"
        ) from exc
    if raw != _json_bytes(report.model_dump(mode="json")):
        raise StrongLeaderPullbackListedConsiderationResidualSourcePlanError(
            "residual source-plan bytes are not canonical"
        )
    return StrongLeaderPullbackListedConsiderationResidualSourcePlanResult(
        output_root=root,
        report=report,
        report_sha256=_sha256_bytes(raw),
        status="already_present",
    )


def _build_report(
    *,
    original_plan: StrongLeaderPullbackListedConsiderationSourcePlanResult,
    identities: StrongLeaderPullbackListedConsiderationAdjudicationResult,
    consideration: StrongLeaderPullbackSecConsiderationAdjudicationResult,
    submissions: SecSubmissionsSourceManifestV1,
    submissions_manifest_sha256: str,
    fifth_third_submission_payload: dict[str, object],
    fifth_third_submission_member_sha256: str,
    implementation_revision: str,
    evaluated_at: datetime,
) -> StrongLeaderPullbackListedConsiderationResidualSourcePlanV1:
    if re.fullmatch(_REVISION_PATTERN, implementation_revision) is None:
        raise StrongLeaderPullbackListedConsiderationResidualSourcePlanError(
            "residual source-plan revision is invalid"
        )
    if (
        identities.report.plan_report_sha256 != original_plan.report_sha256
        or identities.report.plan_logical_fingerprint
        != original_plan.report.logical_fingerprint
        or original_plan.report.submissions_manifest_sha256
        != submissions_manifest_sha256
        or original_plan.report.submissions_source_fingerprint
        != submissions.logical_fingerprint
        or original_plan.report.submissions_archive_sha256
        != submissions.archive_sha256
        or not re.fullmatch(_SHA256_PATTERN, submissions_manifest_sha256)
    ):
        raise StrongLeaderPullbackListedConsiderationResidualSourcePlanError(
            "residual source-plan input bindings differ"
        )
    plans = {item.request_sequence: item for item in original_plan.report.decisions}
    identity_map = {item.request_sequence: item for item in identities.report.decisions}
    consideration_map = {
        item.request_sequence: item for item in consideration.report.decisions
    }
    if not (
        set(_RESIDUAL_SPECS).issubset(plans)
        and set(_RESIDUAL_SPECS).issubset(identity_map)
        and set(_RESIDUAL_SPECS).issubset(consideration_map)
    ):
        raise StrongLeaderPullbackListedConsiderationResidualSourcePlanError(
            "residual source-plan population differs"
        )
    _validate_replacement_registration_row(fifth_third_submission_payload)
    decisions = tuple(
        _document_decision(
            original_plan=plans[sequence],
            identity=identity_map[sequence],
            consideration=consideration_map[sequence],
            fifth_third_submission_member_sha256=(
                fifth_third_submission_member_sha256
            ),
        )
        for sequence in sorted(_RESIDUAL_SPECS)
    )
    paths = Counter(item.resolution_path for item in decisions)
    values = {
        "implementation_revision": implementation_revision,
        "evaluated_at": normalize_utc_datetime(evaluated_at),
        "ruleset_fingerprint": _ruleset_fingerprint(),
        "original_plan_report_sha256": original_plan.report_sha256,
        "original_plan_logical_fingerprint": (
            original_plan.report.logical_fingerprint
        ),
        "identity_adjudication_report_sha256": identities.report_sha256,
        "identity_adjudication_logical_fingerprint": (
            identities.report.logical_fingerprint
        ),
        "consideration_report_sha256": consideration.report_sha256,
        "consideration_logical_fingerprint": (
            consideration.report.logical_fingerprint
        ),
        "submissions_manifest_sha256": submissions_manifest_sha256,
        "submissions_source_fingerprint": submissions.logical_fingerprint,
        "submissions_archive_sha256": submissions.archive_sha256,
        "resolution_path_counts": _ordered(paths),
        "decisions": decisions,
    }
    provisional = (
        StrongLeaderPullbackListedConsiderationResidualSourcePlanV1.model_construct(
            **values, logical_fingerprint="0" * 64
        )
    )
    return StrongLeaderPullbackListedConsiderationResidualSourcePlanV1.model_validate(
        {
            **values,
            "logical_fingerprint": _fingerprint(
                provisional.model_dump(mode="json", exclude={"logical_fingerprint"})
            ),
        }
    )


def _document_decision(
    *,
    original_plan: ListedConsiderationSourcePlanDecisionV1,
    identity: ListedConsiderationIdentityDecisionV1,
    consideration: SecCommonShareConsiderationDecisionV1,
    fifth_third_submission_member_sha256: str,
) -> ListedConsiderationResidualSourcePlanDecisionV1:
    spec = _RESIDUAL_SPECS[identity.request_sequence]
    evidence = consideration.evidence_text
    if (
        original_plan.request_sequence != identity.request_sequence
        or consideration.request_sequence != identity.request_sequence
        or original_plan.target_instrument_id != identity.target_instrument_id
        or consideration.instrument_id != identity.target_instrument_id
        or identity.plan_decision_fingerprint != original_plan.logical_fingerprint
        or identity.resolution_state != spec.prior_resolution_state
        or identity.expected_exchange_ratio != spec.expected_ratio
        or identity.assigned_consideration_instrument_id is not None
        or consideration.resolution_state != "matched"
        or consideration.evidence_sha256 is None
        or evidence is None
        or spec.target_security_term not in evidence
        or spec.consideration_security_term not in evidence
        or len(tuple(_ratio_pattern(spec.expected_ratio).finditer(evidence))) != 1
    ):
        raise StrongLeaderPullbackListedConsiderationResidualSourcePlanError(
            "residual source-plan decision evidence differs"
        )
    if spec.resolution_path == "existing_registration_plus_completion_disclosure":
        if not (
            identity.transaction_match
            and identity.target_common_security_match
            and identity.consideration_security_class_match
            and not identity.registered_exchange_ratio_match
        ):
            raise StrongLeaderPullbackListedConsiderationResidualSourcePlanError(
                "local composite source preconditions differ"
            )
        replacement_values: dict[str, object] = {
            "new_source_request_count": 0,
        }
        reasons = {
            "completion_disclosure_proves_final_ratio_and_security_terms",
            "existing_issuer_registration_proves_transaction_and_share_class",
            "no_new_source_document_required",
        }
    else:
        if (
            identity.transaction_match
            or identity.target_common_security_match
            or identity.consideration_security_class_match
            or identity.registered_exchange_ratio_match
            or original_plan.submissions_member_sha256
            != fifth_third_submission_member_sha256
        ):
            raise StrongLeaderPullbackListedConsiderationResidualSourcePlanError(
                "replacement source preconditions differ"
            )
        replacement_values = {
            "replacement_registration_form": spec.replacement_form,
            "replacement_registration_filing_date": (
                spec.replacement_filing_date
            ),
            "replacement_registration_acceptance_datetime": (
                spec.replacement_acceptance_datetime
            ),
            "replacement_registration_accession_number": (
                spec.replacement_accession_number
            ),
            "replacement_registration_primary_document": (
                spec.replacement_primary_document
            ),
            "replacement_registration_document_url": _replacement_url(
                original_plan.proposed_cik, spec
            ),
            "new_source_request_count": 1,
        }
        reasons = {
            "completion_disclosure_proves_final_ratio_and_security_terms",
            "exact_earlier_424b3_row_is_present_in_retained_submissions_source",
            "one_replacement_registration_document_required",
        }
    reasons.update(
        {
            "identity_assignment_deferred_to_content_adjudication",
            "name_and_ticker_do_not_grant_identity",
            "terminal_value_not_calculated",
        }
    )
    values = {
        "request_sequence": identity.request_sequence,
        "target_instrument_id": identity.target_instrument_id,
        "proposed_consideration_instrument_id": (
            original_plan.proposed_consideration_instrument_id
        ),
        "proposed_cik": original_plan.proposed_cik,
        "original_plan_decision_fingerprint": original_plan.logical_fingerprint,
        "prior_identity_decision_fingerprint": identity.logical_fingerprint,
        "prior_identity_resolution_state": identity.resolution_state,
        "original_registration_artifact_fingerprint": (
            identity.source_artifact_fingerprint
        ),
        "original_registration_document_sha256": (
            identity.source_document_sha256
        ),
        "completion_consideration_fingerprint": consideration.logical_fingerprint,
        "completion_disclosure_accession_number": consideration.accession_number,
        "completion_disclosure_acceptance_datetime": (
            consideration.acceptance_datetime
        ),
        "completion_disclosure_document_sha256": consideration.document_sha256,
        "completion_consideration_evidence_sha256": consideration.evidence_sha256,
        "expected_exchange_ratio": spec.expected_ratio,
        "resolution_path": spec.resolution_path,
        **replacement_values,
        "decision_reasons": tuple(sorted(reasons)),
    }
    provisional = ListedConsiderationResidualSourcePlanDecisionV1.model_construct(
        **values, logical_fingerprint="0" * 64
    )
    return ListedConsiderationResidualSourcePlanDecisionV1.model_validate(
        {
            **values,
            "logical_fingerprint": _fingerprint(
                provisional.model_dump(mode="json", exclude={"logical_fingerprint"})
            ),
        }
    )


def _read_fifth_third_submission_member(
    archive_path: Path,
) -> tuple[dict[str, object], str]:
    member = "CIK0000035527.json"
    try:
        with zipfile.ZipFile(archive_path) as archive:
            info = archive.getinfo(member)
            if info.file_size < 1 or info.file_size > MAXIMUM_SUBMISSION_MEMBER_BYTES:
                raise StrongLeaderPullbackListedConsiderationResidualSourcePlanError(
                    "residual submissions member size differs"
                )
            raw = archive.read(info)
            payload = json.loads(raw)
    except (KeyError, OSError, ValueError, zipfile.BadZipFile) as exc:
        if isinstance(
            exc, StrongLeaderPullbackListedConsiderationResidualSourcePlanError
        ):
            raise
        raise StrongLeaderPullbackListedConsiderationResidualSourcePlanError(
            "residual submissions member read failed"
        ) from exc
    if not isinstance(payload, dict):
        raise StrongLeaderPullbackListedConsiderationResidualSourcePlanError(
            "residual submissions member differs"
        )
    return payload, _sha256_bytes(raw)


def _validate_replacement_registration_row(payload: dict[str, object]) -> None:
    spec = _RESIDUAL_SPECS[174]
    try:
        if str(payload.get("cik", "")).zfill(10) != "0000035527":
            raise ValueError
        recent = payload["filings"]["recent"]  # type: ignore[index]
        fields = (
            recent["form"],  # type: ignore[index]
            recent["filingDate"],  # type: ignore[index]
            recent["acceptanceDateTime"],  # type: ignore[index]
            recent["accessionNumber"],  # type: ignore[index]
            recent["primaryDocument"],  # type: ignore[index]
        )
        if len({len(field) for field in fields}) != 1:
            raise ValueError
        matches = tuple(
            index
            for index, form in enumerate(fields[0])
            if form == spec.replacement_form
            and fields[1][index] == spec.replacement_filing_date.isoformat()
            and _dt(fields[2][index]) == spec.replacement_acceptance_datetime
            and fields[3][index] == spec.replacement_accession_number
            and fields[4][index] == spec.replacement_primary_document
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise StrongLeaderPullbackListedConsiderationResidualSourcePlanError(
            "replacement registration row is invalid"
        ) from exc
    if len(matches) != 1:
        raise StrongLeaderPullbackListedConsiderationResidualSourcePlanError(
            "replacement registration row is not unique"
        )


def _ratio_pattern(value: str) -> re.Pattern[str]:
    whole, fraction = value.split(".")
    numeric = f"{int(whole)}.{fraction.rstrip('0')}".rstrip(".")
    if "." not in numeric:
        return re.compile(rf"(?<![0-9.]){re.escape(numeric)}(?:\.0+)?(?![0-9.])")
    base, decimals = numeric.split(".")
    return re.compile(
        rf"(?<![0-9.]){re.escape(base)}\.{re.escape(decimals)}0*(?![0-9.])"
    )


def _replacement_url(cik: str, spec: _ResidualSpec) -> str:
    if (
        spec.replacement_accession_number is None
        or spec.replacement_primary_document is None
    ):
        raise StrongLeaderPullbackListedConsiderationResidualSourcePlanError(
            "replacement registration source is incomplete"
        )
    return (
        "https://www.sec.gov/Archives/edgar/data/"
        f"{int(cik)}/{spec.replacement_accession_number.replace('-', '')}/"
        f"{spec.replacement_primary_document}"
    )


def _decision_matches_registry(
    decision: ListedConsiderationResidualSourcePlanDecisionV1,
) -> bool:
    spec = _RESIDUAL_SPECS.get(decision.request_sequence)
    if spec is None:
        return False
    return (
        decision.expected_exchange_ratio == spec.expected_ratio
        and decision.prior_identity_resolution_state
        == spec.prior_resolution_state
        and decision.resolution_path == spec.resolution_path
        and decision.replacement_registration_form == spec.replacement_form
        and decision.replacement_registration_filing_date
        == spec.replacement_filing_date
        and decision.replacement_registration_acceptance_datetime
        == spec.replacement_acceptance_datetime
        and decision.replacement_registration_accession_number
        == spec.replacement_accession_number
        and decision.replacement_registration_primary_document
        == spec.replacement_primary_document
        and decision.replacement_registration_document_url
        == (
            _replacement_url(decision.proposed_cik, spec)
            if spec.replacement_accession_number is not None
            else None
        )
    )


def _ruleset_fingerprint() -> str:
    return _fingerprint(
        {
            "contract_version": CONTRACT_VERSION,
            "cases": {
                str(sequence): {
                    "expected_ratio": spec.expected_ratio,
                    "target_security_term": spec.target_security_term,
                    "consideration_security_term": (
                        spec.consideration_security_term
                    ),
                    "prior_resolution_state": spec.prior_resolution_state,
                    "resolution_path": spec.resolution_path,
                    "replacement_form": spec.replacement_form,
                    "replacement_filing_date": (
                        spec.replacement_filing_date.isoformat()
                        if spec.replacement_filing_date is not None
                        else None
                    ),
                    "replacement_acceptance_datetime": (
                        spec.replacement_acceptance_datetime.isoformat()
                        if spec.replacement_acceptance_datetime is not None
                        else None
                    ),
                    "replacement_accession_number": (
                        spec.replacement_accession_number
                    ),
                    "replacement_primary_document": (
                        spec.replacement_primary_document
                    ),
                }
                for sequence, spec in sorted(_RESIDUAL_SPECS.items())
            },
            "identity_authority": "deferred_to_content_adjudication",
            "name_and_ticker_authority": "locator_only",
            "network_request_count": 0,
        }
    )


def _write_report(
    *,
    output_root: Path,
    output_custody_root: Path,
    report: StrongLeaderPullbackListedConsiderationResidualSourcePlanV1,
) -> StrongLeaderPullbackListedConsiderationResidualSourcePlanResult:
    target = _validated_output_target(output_root, output_custody_root)
    if target.exists() or target.is_symlink():
        reader = (
            read_strong_leader_pullback_listed_consideration_residual_source_plan
        )
        existing = reader(
            output_root=target, output_custody_root=output_custody_root
        )
        if existing.report != report:
            raise StrongLeaderPullbackListedConsiderationResidualSourcePlanError(
                "existing residual source plan differs"
            )
        return existing
    partial = target.parent / f".{target.name}.partial.{os.getpid()}"
    if partial.exists() or partial.is_symlink():
        raise StrongLeaderPullbackListedConsiderationResidualSourcePlanError(
            "residual source-plan staging target exists"
        )
    partial.mkdir(mode=0o700)
    try:
        _write_exclusive(
            partial / REPORT_FILE, _json_bytes(report.model_dump(mode="json"))
        )
        _fsync_directory(partial)
        partial.replace(target)
        _fsync_directory(target.parent)
    except Exception:
        if (
            partial.exists()
            and not partial.is_symlink()
            and partial.parent == target.parent
        ):
            shutil.rmtree(partial)
            _fsync_directory(partial.parent)
        raise
    reread = read_strong_leader_pullback_listed_consideration_residual_source_plan(
        output_root=target,
        output_custody_root=output_custody_root,
    )
    return StrongLeaderPullbackListedConsiderationResidualSourcePlanResult(
        output_root=target,
        report=reread.report,
        report_sha256=reread.report_sha256,
        status="published",
    )


def _validated_output_target(path: Path, custody_root: Path) -> Path:
    if not path.is_absolute() or not custody_root.is_absolute():
        raise StrongLeaderPullbackListedConsiderationResidualSourcePlanError(
            "residual source-plan paths must be absolute"
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
        raise StrongLeaderPullbackListedConsiderationResidualSourcePlanError(
            "residual source-plan custody or target is unsafe"
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
        raise StrongLeaderPullbackListedConsiderationResidualSourcePlanError(
            "residual source-plan output is unavailable or unsafe"
        )
    return target


def _require_regular_file(path: Path, mode: int, maximum_bytes: int) -> None:
    if path.is_symlink() or not path.is_file():
        raise StrongLeaderPullbackListedConsiderationResidualSourcePlanError(
            "residual source-plan file is unavailable or unsafe"
        )
    metadata = path.stat()
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_uid != os.getuid()
        or stat.S_IMODE(metadata.st_mode) != mode
        or metadata.st_size < 1
        or metadata.st_size > maximum_bytes
    ):
        raise StrongLeaderPullbackListedConsiderationResidualSourcePlanError(
            "residual source-plan file metadata differs"
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


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _ordered(counter: Counter[object]) -> tuple[tuple[str, int], ...]:
    return tuple(
        sorted((str(key), count) for key, count in counter.items() if count)
    )


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


@contextmanager
def _network_prohibited() -> Iterator[None]:
    original_socket = socket.socket
    original_create_connection = socket.create_connection
    original_getaddrinfo = socket.getaddrinfo

    def denied(*_: object, **__: object) -> object:
        raise StrongLeaderPullbackListedConsiderationResidualSourcePlanError(
            "network access is prohibited during residual source planning"
        )

    socket.socket = denied  # type: ignore[assignment]
    socket.create_connection = denied  # type: ignore[assignment]
    socket.getaddrinfo = denied  # type: ignore[assignment]
    try:
        yield
    finally:
        socket.socket = original_socket  # type: ignore[assignment]
        socket.create_connection = (  # type: ignore[assignment]
            original_create_connection
        )
        socket.getaddrinfo = original_getaddrinfo  # type: ignore[assignment]
