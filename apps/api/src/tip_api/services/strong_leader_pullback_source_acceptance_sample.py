"""Freeze the provider-neutral first-strategy action/lifecycle query sample."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import socket
import stat
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Iterable, Iterator, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic_core import to_jsonable_python

from tip_api.contracts.common import normalize_utc_datetime
from tip_api.contracts.market_data.v1.historical_inactive_lifecycle import (
    InactiveLifecycleDisposition,
)
from tip_api.services.historical_inactive_lifecycle_resolution_shadow import (
    read_historical_inactive_lifecycle_resolution_shadow,
)
from tip_api.services.strong_leader_pullback_evidence_blocker_census import (
    read_strong_leader_pullback_evidence_blocker_census,
)


CONTRACT_VERSION = "strong-leader-pullback-source-acceptance-sample/1.0"
REPORT_FILE = "sample.json"
EXPECTED_ACTION_CASE_COUNT = 20
EXPECTED_ACTION_INSTRUMENT_COUNT = 4
EXPECTED_LIFECYCLE_CASE_COUNT = 64
EXPECTED_COMBINED_INSTRUMENT_COUNT = 68
EXPECTED_OVERLAP_INSTRUMENT_COUNT = 0
EXPECTED_LIFECYCLE_SOURCE_OCCURRENCE_COUNT = 122
FIXED_LIFECYCLE_ANCHORS = (date(2026, 7, 16), date(2026, 9, 3))
MAXIMUM_REPORT_BYTES = 2 * 1024 * 1024
_SHA256_PATTERN = r"^[0-9a-f]{64}$"
_REVISION_PATTERN = r"^[0-9a-f]{40}$"
_BUILD_NAME_PATTERN = r"^build=[A-Za-z0-9._-]+$"

ACTION_REQUIRED_FIELDS = tuple(
    sorted(
        {
            "action_status_and_type",
            "announcement_effective_ex_record_pay_dates_as_applicable",
            "correction_and_cancellation_history",
            "exact_ratio_or_consideration",
            "predecessor_and_successor_identities",
            "provider_event_id_and_revision_chain",
            "source_availability_time",
            "stable_security_and_listing_identifiers",
        }
    )
)
LIFECYCLE_REQUIRED_FIELDS = tuple(
    sorted(
        {
            "bankruptcy_liquidation_or_otc_continuation",
            "cash_and_stock_consideration",
            "first_and_last_tradable_dates",
            "predecessor_successor_and_acquirer",
            "source_availability_time_and_revision_history",
            "stable_security_and_listing_identifiers",
            "suspension_and_delisting_status_effective_dates",
            "termination_reason",
        }
    )
)
REQUIRED_PROVIDER_RESULT_STATES = (
    "absent",
    "conflicting",
    "matched",
    "unsupported",
)


class StrongLeaderPullbackSourceAcceptanceSampleError(RuntimeError):
    """Raised when the finite source-acceptance sample cannot be proven."""


class _FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class SourceBindingV1(_FrozenModel):
    name: str
    manifest_sha256: str = Field(pattern=_SHA256_PATTERN)
    logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    record_count: int = Field(ge=1)


class ActionSourceAcceptanceCaseV1(_FrozenModel):
    case_type: Literal["unassigned_action_relation"] = "unassigned_action_relation"
    source_action_id: str
    source_revision: int = Field(ge=1)
    provider_ticker_locator: str
    effective_date: date
    action_type: Literal["cash_dividend", "reverse_split"]
    candidate_instrument_id: UUID
    candidate_classification: Literal[
        "one_historical_candidate", "multiple_historical_candidates"
    ]
    exact_date_failure_reason: Literal[
        "event_date_identity_unavailable", "unresolved_ticker"
    ]
    feature_path_count: int = Field(ge=0)
    horizon_1_path_count: int = Field(ge=0)
    horizon_3_path_count: int = Field(ge=0)
    horizon_5_path_count: int = Field(ge=0)
    inactive_source_state: str
    inactive_source_type_codes: tuple[str, ...]
    finra_exact_date_symbol_occurrence_count: int = Field(ge=0)
    finra_exact_numeric_occurrence_count: int = Field(ge=0)
    finra_flag_codes: tuple[str, ...]
    stable_identity_assignment_authorized: Literal[False] = False

    @field_validator(
        "source_action_id", "provider_ticker_locator", "inactive_source_state"
    )
    @classmethod
    def required_text(cls, value: str) -> str:
        if not value or value != value.strip():
            raise ValueError("action sample text is invalid")
        return value

    @field_validator("inactive_source_type_codes", "finra_flag_codes", mode="before")
    @classmethod
    def ordered_codes(cls, value: object) -> tuple[str, ...]:
        values = tuple(value)  # type: ignore[arg-type]
        if values != tuple(sorted(set(values))):
            raise ValueError("action sample codes are not ordered and unique")
        return values

    @model_validator(mode="after")
    def reconcile(self) -> "ActionSourceAcceptanceCaseV1":
        if not self.feature_path_count and not self.horizon_5_path_count:
            raise ValueError("action sample case does not affect a declared path")
        if not (
            self.horizon_1_path_count
            <= self.horizon_3_path_count
            <= self.horizon_5_path_count
        ):
            raise ValueError("action sample horizon counts are not monotone")
        if (
            self.finra_exact_numeric_occurrence_count
            > self.finra_exact_date_symbol_occurrence_count
        ):
            raise ValueError("action sample FINRA numeric count exceeds symbol count")
        return self


class LifecycleSourceAcceptanceCaseV1(_FrozenModel):
    case_type: Literal["five_session_lifecycle_crossing"] = (
        "five_session_lifecycle_crossing"
    )
    instrument_id: UUID
    source_anchor_dates: tuple[date, ...] = Field(min_length=1)
    source_observation_fingerprints: tuple[str, ...] = Field(min_length=1)
    source_occurrence_count: int = Field(ge=1)
    selected_identity_types: tuple[
        Literal["share_class_figi", "composite_figi"], ...
    ] = Field(min_length=1)
    selected_identity_values: tuple[str, ...] = Field(min_length=1)
    provider_ticker_locators: tuple[str, ...] = Field(min_length=1)
    provider_name_locators: tuple[str, ...] = Field(min_length=1)
    cik_locators: tuple[str, ...] = Field(min_length=1)
    primary_exchange_locators: tuple[str, ...] = Field(min_length=1)
    source_type_codes: tuple[str, ...] = Field(min_length=1)
    canonical_first_observed_date: date
    canonical_last_observed_date: date
    provider_delist_date_candidate: date
    included_path_count: int = Field(ge=1)
    horizon_1_crossing_path_count: int = Field(ge=0)
    horizon_3_crossing_path_count: int = Field(ge=0)
    horizon_5_crossing_path_count: int = Field(ge=1)
    locator_fact_authority: Literal[False] = False
    terminal_outcome_authorized: Literal[False] = False

    @field_validator(
        "source_anchor_dates",
        "source_observation_fingerprints",
        "selected_identity_types",
        "selected_identity_values",
        "provider_ticker_locators",
        "provider_name_locators",
        "cik_locators",
        "primary_exchange_locators",
        "source_type_codes",
        mode="before",
    )
    @classmethod
    def ordered_values(cls, value: object) -> tuple[object, ...]:
        values = tuple(value)  # type: ignore[arg-type]
        if not values or values != tuple(sorted(set(values))):
            raise ValueError("lifecycle sample values are not ordered and unique")
        return values

    @field_validator("source_observation_fingerprints")
    @classmethod
    def fingerprint_values(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if any(re.fullmatch(_SHA256_PATTERN, item) is None for item in value):
            raise ValueError("lifecycle source fingerprint is invalid")
        return value

    @model_validator(mode="after")
    def reconcile(self) -> "LifecycleSourceAcceptanceCaseV1":
        if self.source_occurrence_count != len(self.source_observation_fingerprints):
            raise ValueError("lifecycle source occurrence count differs")
        if not (
            self.canonical_first_observed_date
            <= self.canonical_last_observed_date
            <= self.provider_delist_date_candidate
        ):
            raise ValueError("lifecycle sample dates are invalid")
        if not (
            self.horizon_1_crossing_path_count
            <= self.horizon_3_crossing_path_count
            <= self.horizon_5_crossing_path_count
        ):
            raise ValueError("lifecycle crossing counts are not monotone")
        return self


class StrongLeaderPullbackSourceAcceptanceSampleV1(_FrozenModel):
    contract_version: Literal[
        "strong-leader-pullback-source-acceptance-sample/1.0"
    ] = CONTRACT_VERSION
    completion_status: Literal["completed"] = "completed"
    dataset_name: Literal[
        "strong-leader-pullback-source-acceptance-sample"
    ] = "strong-leader-pullback-source-acceptance-sample"
    implementation_revision: str = Field(pattern=_REVISION_PATTERN)
    evaluated_at: datetime
    outcome_blind: Literal[True] = True
    provider_neutral: Literal[True] = True
    complete_population_retained: Literal[True] = True
    source_bindings: tuple[SourceBindingV1, ...] = Field(min_length=3)
    action_required_fields: tuple[str, ...]
    lifecycle_required_fields: tuple[str, ...]
    required_provider_result_states: tuple[str, ...]
    action_cases: tuple[ActionSourceAcceptanceCaseV1, ...]
    lifecycle_cases: tuple[LifecycleSourceAcceptanceCaseV1, ...]
    action_case_count: Literal[20] = EXPECTED_ACTION_CASE_COUNT
    action_source_record_count: Literal[20] = EXPECTED_ACTION_CASE_COUNT
    action_instrument_count: Literal[4] = EXPECTED_ACTION_INSTRUMENT_COUNT
    lifecycle_case_count: Literal[64] = EXPECTED_LIFECYCLE_CASE_COUNT
    lifecycle_source_occurrence_count: Literal[122] = (
        EXPECTED_LIFECYCLE_SOURCE_OCCURRENCE_COUNT
    )
    lifecycle_instrument_count: Literal[64] = EXPECTED_LIFECYCLE_CASE_COUNT
    overlapping_instrument_count: Literal[0] = EXPECTED_OVERLAP_INSTRUMENT_COUNT
    combined_instrument_count: Literal[68] = EXPECTED_COMBINED_INSTRUMENT_COUNT
    stable_identity_assignment_count: Literal[0] = 0
    terminal_outcome_count: Literal[0] = 0
    strategy_trigger_count: Literal[0] = 0
    forward_outcome_count: Literal[0] = 0
    performance_metric_count: Literal[0] = 0
    parameter_selection_count: Literal[0] = 0
    cohort_selection_count: Literal[0] = 0
    provider_request_count: Literal[0] = 0
    credential_read_count: Literal[0] = 0
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
    def time_is_utc(cls, value: datetime) -> datetime:
        return normalize_utc_datetime(value)

    @model_validator(mode="after")
    def reconcile(self) -> "StrongLeaderPullbackSourceAcceptanceSampleV1":
        if tuple(item.name for item in self.source_bindings) != tuple(
            sorted({item.name for item in self.source_bindings})
        ):
            raise ValueError("source sample bindings are not ordered and unique")
        if self.action_required_fields != ACTION_REQUIRED_FIELDS:
            raise ValueError("action source requirements differ")
        if self.lifecycle_required_fields != LIFECYCLE_REQUIRED_FIELDS:
            raise ValueError("lifecycle source requirements differ")
        if self.required_provider_result_states != REQUIRED_PROVIDER_RESULT_STATES:
            raise ValueError("provider result states differ")
        action_keys = tuple(
            (item.source_action_id, item.source_revision, item.candidate_instrument_id)
            for item in self.action_cases
        )
        if action_keys != tuple(
            sorted(action_keys, key=lambda item: (item[0], item[1], str(item[2])))
        ):
            raise ValueError("action cases are not ordered")
        lifecycle_ids = tuple(item.instrument_id for item in self.lifecycle_cases)
        if lifecycle_ids != tuple(sorted(lifecycle_ids, key=str)):
            raise ValueError("lifecycle cases are not ordered")
        action_ids = {item.candidate_instrument_id for item in self.action_cases}
        lifecycle_id_set = set(lifecycle_ids)
        if (
            len(self.action_cases) != self.action_case_count
            or len({item.source_action_id for item in self.action_cases})
            != self.action_source_record_count
            or len(action_ids) != self.action_instrument_count
            or len(self.lifecycle_cases) != self.lifecycle_case_count
            or sum(item.source_occurrence_count for item in self.lifecycle_cases)
            != self.lifecycle_source_occurrence_count
            or len(lifecycle_id_set) != self.lifecycle_instrument_count
            or len(action_ids & lifecycle_id_set) != self.overlapping_instrument_count
            or len(action_ids | lifecycle_id_set) != self.combined_instrument_count
        ):
            raise ValueError("source sample population counts differ")
        values = self.model_dump(mode="json", exclude={"logical_fingerprint"})
        if self.logical_fingerprint != _fingerprint(values):
            raise ValueError("source sample logical fingerprint differs")
        return self


@dataclass(frozen=True, slots=True)
class StrongLeaderPullbackSourceAcceptanceSampleResult:
    output_root: Path
    report: StrongLeaderPullbackSourceAcceptanceSampleV1
    report_sha256: str
    status: Literal["published", "already_present"]


def build_strong_leader_pullback_source_acceptance_sample(
    *,
    blocker_census_root: Path,
    blocker_census_custody_root: Path,
    lifecycle_shadow_root: Path,
    lifecycle_shadow_custody_root: Path,
    output_root: Path,
    output_custody_root: Path,
    implementation_revision: str,
    evaluated_at: datetime,
) -> StrongLeaderPullbackSourceAcceptanceSampleResult:
    """Build one immutable query sample without network or provider access."""

    with _network_prohibited():
        blocker = read_strong_leader_pullback_evidence_blocker_census(
            output_root=blocker_census_root,
            output_custody_root=blocker_census_custody_root,
        )
        lifecycle = tuple(
            read_historical_inactive_lifecycle_resolution_shadow(
                root=lifecycle_shadow_root,
                anchor_date=anchor,
                approved_custody_root=lifecycle_shadow_custody_root,
            )
            for anchor in FIXED_LIFECYCLE_ANCHORS
        )
        report = _compose_report(
            blocker=blocker,
            lifecycle=lifecycle,
            implementation_revision=implementation_revision,
            evaluated_at=evaluated_at,
        )
        return _write_report(
            output_root=output_root,
            output_custody_root=output_custody_root,
            report=report,
        )


def read_strong_leader_pullback_source_acceptance_sample(
    *, output_root: Path, output_custody_root: Path
) -> StrongLeaderPullbackSourceAcceptanceSampleResult:
    """Formally reread a completed source-acceptance sample."""

    root = _validated_completed_output(output_root, output_custody_root)
    if {item.name for item in root.iterdir()} != {REPORT_FILE}:
        raise StrongLeaderPullbackSourceAcceptanceSampleError(
            "source sample package members differ"
        )
    report_path = root / REPORT_FILE
    _require_regular_file(report_path, 0o400, MAXIMUM_REPORT_BYTES)
    raw = report_path.read_bytes()
    try:
        report = StrongLeaderPullbackSourceAcceptanceSampleV1.model_validate_json(raw)
    except Exception as exc:
        raise StrongLeaderPullbackSourceAcceptanceSampleError(
            "source sample report is invalid"
        ) from exc
    if raw != _json_bytes(report.model_dump(mode="json")):
        raise StrongLeaderPullbackSourceAcceptanceSampleError(
            "source sample report bytes are not canonical"
        )
    return StrongLeaderPullbackSourceAcceptanceSampleResult(
        output_root=root,
        report=report,
        report_sha256=hashlib.sha256(raw).hexdigest(),
        status="already_present",
    )


def _compose_report(
    *, blocker: object, lifecycle: tuple[object, ...],
    implementation_revision: str, evaluated_at: datetime,
) -> StrongLeaderPullbackSourceAcceptanceSampleV1:
    if re.fullmatch(_REVISION_PATTERN, implementation_revision) is None:
        raise StrongLeaderPullbackSourceAcceptanceSampleError(
            "implementation revision is invalid"
        )
    action_cases = tuple(
        sorted(
            (
                ActionSourceAcceptanceCaseV1(
                    source_action_id=item.source_action_id,
                    source_revision=item.source_revision,
                    provider_ticker_locator=item.provider_ticker,
                    effective_date=item.effective_date,
                    action_type=item.action_type,
                    candidate_instrument_id=item.candidate_instrument_id,
                    candidate_classification=item.historical_candidate_classification,
                    exact_date_failure_reason=item.exact_date_failure_reason,
                    feature_path_count=item.feature_path_count,
                    horizon_1_path_count=item.horizon_1_path_count,
                    horizon_3_path_count=item.horizon_3_path_count,
                    horizon_5_path_count=item.horizon_5_path_count,
                    inactive_source_state=item.inactive_source_state,
                    inactive_source_type_codes=item.inactive_source_type_codes,
                    finra_exact_date_symbol_occurrence_count=(
                        item.finra_exact_date_symbol_occurrence_count
                    ),
                    finra_exact_numeric_occurrence_count=(
                        item.finra_exact_numeric_occurrence_count
                    ),
                    finra_flag_codes=item.finra_flag_codes,
                )
                for item in blocker.action_records
                if item.identity_evidence_kind == "history_candidate_unassigned"
            ),
            key=lambda item: (
                item.source_action_id,
                item.source_revision,
                str(item.candidate_instrument_id),
            ),
        )
    )
    lifecycle_targets = {
        (
            item.instrument_id,
            item.canonical_first_observed_date,
            item.canonical_last_observed_date,
            item.provider_delist_date_candidate,
        ): item
        for item in blocker.lifecycle_records
        if item.horizon_5_crosses_last_observed_path_count > 0
    }
    lifecycle_evidence: dict[tuple[object, ...], list[tuple[object, object]]] = {
        key: [] for key in lifecycle_targets
    }
    for result in lifecycle:
        source_by_fingerprint = {
            item.source_observation_fingerprint: item
            for item in result.source_observations
        }
        if len(source_by_fingerprint) != len(result.source_observations):
            raise StrongLeaderPullbackSourceAcceptanceSampleError(
                "lifecycle source observations are duplicated"
            )
        for decision in result.decisions:
            if (
                decision.disposition
                is not InactiveLifecycleDisposition.REVIEW_CANDIDATE
            ):
                continue
            key = (
                decision.canonical_instrument_id,
                decision.canonical_first_observed_date,
                decision.canonical_last_observed_date,
                decision.effective_date_candidate,
            )
            if key not in lifecycle_targets:
                continue
            source = source_by_fingerprint.get(decision.source_observation_fingerprint)
            if source is None:
                raise StrongLeaderPullbackSourceAcceptanceSampleError(
                    "lifecycle decision lacks its source occurrence"
                )
            lifecycle_evidence[key].append((decision, source))
    lifecycle_cases = []
    for key, target in lifecycle_targets.items():
        evidence = lifecycle_evidence[key]
        if not evidence:
            raise StrongLeaderPullbackSourceAcceptanceSampleError(
                "lifecycle target lacks exact source evidence"
            )
        anchors = tuple(sorted({item[0].anchor_date for item in evidence}))
        if anchors != target.source_anchor_dates:
            raise StrongLeaderPullbackSourceAcceptanceSampleError(
                "lifecycle target anchor recovery differs"
            )
        lifecycle_cases.append(
            LifecycleSourceAcceptanceCaseV1(
                instrument_id=target.instrument_id,
                source_anchor_dates=anchors,
                source_observation_fingerprints=_values(
                    item[0].source_observation_fingerprint for item in evidence
                ),
                source_occurrence_count=len(evidence),
                selected_identity_types=_values(
                    item[0].selected_identity_type.value for item in evidence
                ),
                selected_identity_values=_values(
                    item[0].selected_identity_value for item in evidence
                ),
                provider_ticker_locators=_values(item[1].ticker for item in evidence),
                provider_name_locators=_values(item[1].name for item in evidence),
                cik_locators=_values(item[1].cik for item in evidence),
                primary_exchange_locators=_values(
                    item[1].primary_exchange for item in evidence
                ),
                source_type_codes=_values(item[1].type for item in evidence),
                canonical_first_observed_date=target.canonical_first_observed_date,
                canonical_last_observed_date=target.canonical_last_observed_date,
                provider_delist_date_candidate=target.provider_delist_date_candidate,
                included_path_count=target.included_path_count,
                horizon_1_crossing_path_count=(
                    target.horizon_1_crosses_last_observed_path_count
                ),
                horizon_3_crossing_path_count=(
                    target.horizon_3_crosses_last_observed_path_count
                ),
                horizon_5_crossing_path_count=(
                    target.horizon_5_crosses_last_observed_path_count
                ),
            )
        )
    ordered_lifecycle = tuple(
        sorted(lifecycle_cases, key=lambda item: str(item.instrument_id))
    )
    bindings = tuple(
        sorted(
            (
                SourceBindingV1(
                    name="strong_leader_pullback_evidence_blocker_census",
                    manifest_sha256=blocker.manifest_sha256,
                    logical_fingerprint=blocker.manifest.logical_fingerprint,
                    record_count=(
                        blocker.manifest.action_exposure_record_count
                        + blocker.manifest.lifecycle_exposure_record_count
                    ),
                ),
                *(
                    SourceBindingV1(
                        name=(
                            "inactive_lifecycle_"
                            f"{item.manifest.anchor_date.isoformat()}"
                        ),
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
    values = {
        "implementation_revision": implementation_revision,
        "evaluated_at": normalize_utc_datetime(evaluated_at),
        "source_bindings": bindings,
        "action_required_fields": ACTION_REQUIRED_FIELDS,
        "lifecycle_required_fields": LIFECYCLE_REQUIRED_FIELDS,
        "required_provider_result_states": REQUIRED_PROVIDER_RESULT_STATES,
        "action_cases": action_cases,
        "lifecycle_cases": ordered_lifecycle,
    }
    provisional = StrongLeaderPullbackSourceAcceptanceSampleV1.model_construct(
        **values, logical_fingerprint="0" * 64
    )
    return StrongLeaderPullbackSourceAcceptanceSampleV1.model_validate(
        {
            **values,
            "logical_fingerprint": _fingerprint(
                provisional.model_dump(mode="json", exclude={"logical_fingerprint"})
            ),
        }
    )


def _values(values: Iterable[object]) -> tuple[str, ...]:
    try:
        raw = tuple(values)  # type: ignore[arg-type]
    except TypeError as exc:
        raise StrongLeaderPullbackSourceAcceptanceSampleError(
            "source locator values are unavailable"
        ) from exc
    if any(item is None or not str(item).strip() for item in raw):
        raise StrongLeaderPullbackSourceAcceptanceSampleError(
            "source locator value is missing"
        )
    return tuple(sorted({str(item).strip() for item in raw}))


def _write_report(
    *, output_root: Path, output_custody_root: Path,
    report: StrongLeaderPullbackSourceAcceptanceSampleV1,
) -> StrongLeaderPullbackSourceAcceptanceSampleResult:
    target = _validated_output_target(output_root, output_custody_root)
    if target.exists() or target.is_symlink():
        existing = read_strong_leader_pullback_source_acceptance_sample(
            output_root=target,
            output_custody_root=output_custody_root,
        )
        if existing.report != report:
            raise StrongLeaderPullbackSourceAcceptanceSampleError(
                "existing source sample differs"
            )
        return existing
    partial = target.parent / f".{target.name}.partial.{os.getpid()}"
    if partial.exists() or partial.is_symlink():
        raise StrongLeaderPullbackSourceAcceptanceSampleError(
            "source sample staging target exists"
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
        if (
            partial.exists()
            and not partial.is_symlink()
            and partial.parent == target.parent
        ):
            shutil.rmtree(partial)
            _fsync_directory(partial.parent)
        raise
    reread = read_strong_leader_pullback_source_acceptance_sample(
        output_root=target,
        output_custody_root=output_custody_root,
    )
    if reread.report != report:
        raise StrongLeaderPullbackSourceAcceptanceSampleError(
            "source sample formal reread differs"
        )
    return StrongLeaderPullbackSourceAcceptanceSampleResult(
        output_root=target,
        report=reread.report,
        report_sha256=reread.report_sha256,
        status="published",
    )


def _validated_output_target(path: Path, custody_root: Path) -> Path:
    if not path.is_absolute() or not custody_root.is_absolute():
        raise StrongLeaderPullbackSourceAcceptanceSampleError(
            "source sample paths must be absolute"
        )
    custody = custody_root.resolve(strict=True)
    if (
        custody_root != custody
        or custody.is_symlink()
        or not custody.is_dir()
        or custody.stat().st_uid != os.getuid()
        or stat.S_IMODE(custody.stat().st_mode) != 0o700
        or path.parent != custody
        or re.fullmatch(_BUILD_NAME_PATTERN, path.name) is None
    ):
        raise StrongLeaderPullbackSourceAcceptanceSampleError(
            "source sample custody or target is unsafe"
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
        raise StrongLeaderPullbackSourceAcceptanceSampleError(
            "source sample output is unavailable or unsafe"
        )
    return target


def _require_regular_file(path: Path, mode: int, maximum_bytes: int) -> None:
    if path.is_symlink() or not path.is_file():
        raise StrongLeaderPullbackSourceAcceptanceSampleError(
            "source sample file is unavailable or unsafe"
        )
    metadata = path.stat()
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_uid != os.getuid()
        or stat.S_IMODE(metadata.st_mode) != mode
        or metadata.st_size < 1
        or metadata.st_size > maximum_bytes
    ):
        raise StrongLeaderPullbackSourceAcceptanceSampleError(
            "source sample file metadata differs"
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


def _json_bytes(value: object) -> bytes:
    return (
        json.dumps(
            to_jsonable_python(value),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        )
        + "\n"
    ).encode("utf-8")


def _fingerprint(value: object) -> str:
    return hashlib.sha256(_json_bytes(value).rstrip(b"\n")).hexdigest()


@contextmanager
def _network_prohibited() -> Iterator[None]:
    original_socket = socket.socket
    original_create_connection = socket.create_connection
    original_getaddrinfo = socket.getaddrinfo

    def blocked(*_args: object, **_kwargs: object) -> object:
        raise StrongLeaderPullbackSourceAcceptanceSampleError(
            "network access is prohibited for source sample construction"
        )

    socket.socket = blocked  # type: ignore[assignment]
    socket.create_connection = blocked  # type: ignore[assignment]
    socket.getaddrinfo = blocked  # type: ignore[assignment]
    try:
        yield
    finally:
        socket.socket = original_socket  # type: ignore[assignment]
        socket.create_connection = (  # type: ignore[assignment]
            original_create_connection
        )
        socket.getaddrinfo = original_getaddrinfo  # type: ignore[assignment]
