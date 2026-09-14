"""Core adjudication for the corrected-population SEC case."""

from __future__ import annotations

import os
import re
import shutil
import stat
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from tip_api.contracts.common import normalize_utc_datetime
from tip_api.providers.sec.issuer_evidence import SecIdentityRecord, SecIdentityResolver
from tip_api.services import strong_leader_pullback_sec_case_adjudication as identity
from tip_api.services import strong_leader_pullback_sec_consideration_adjudication as consideration
from tip_api.services import strong_leader_pullback_sec_document_content_census as base
from tip_api.services import strong_leader_pullback_sec_document_source as source_base
from tip_api.services import (
    strong_leader_pullback_sec_termination_reason_adjudication as termination,
)
from tip_api.services import strong_leader_pullback_sec_transaction_event_adjudication as event
from tip_api.services import (
    strong_leader_pullback_terminal_population_sec_field_candidates as field_reader,
)
from tip_api.services import (
    strong_leader_pullback_terminal_population_sec_source as source_reader,
)
from tip_api.services import (
    strong_leader_pullback_terminal_population_sec_source_plan as plan_reader,
)


CONTRACT_VERSION = (
    "strong-leader-pullback-terminal-population-sec-core-adjudication/1.0"
)
REPORT_FILE = "core-adjudication.json"
MAXIMUM_REPORT_BYTES = 1024 * 1024
_SHA256_PATTERN = r"^[0-9a-f]{64}$"
_REVISION_PATTERN = r"^[0-9a-f]{40}$"
_OUTPUT_NAME_PATTERN = r"^adjudication=[A-Za-z0-9._-]+$"


class StrongLeaderPullbackTerminalPopulationSecCoreAdjudicationError(RuntimeError):
    """Raised when corrected-population core evidence cannot be proven."""


class _FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class TerminalPopulationSecCrossFormReconciliationV1(_FrozenModel):
    instrument_id: UUID
    cik: str = Field(pattern=r"^[0-9]{10}$")
    commission_file_number: str = Field(min_length=1)
    common_equity_security_class: str = Field(min_length=1)
    exchange_mic: Literal["XNAS", "XNYS"]
    exchange_notice_signature_date: date
    cover_report_date: date
    transaction_completion_date: date
    form25_cik_agrees: Literal[True] = True
    form15_cik_agrees: Literal[True] = True
    commission_file_number_agrees: Literal[True] = True
    common_equity_class_agrees: Literal[True] = True
    exchange_identity_agrees: Literal[True] = True
    notice_and_completion_date_agree: Literal[True] = True
    ticker_grants_identity_authority: Literal[False] = False
    form25_notice_is_effective_delisting_date: Literal[False] = False
    form15_certification_is_trading_cessation_date: Literal[False] = False
    logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)

    @field_validator("commission_file_number", "common_equity_security_class")
    @classmethod
    def text_is_normalized(cls, value: str) -> str:
        if value != " ".join(value.split()):
            raise ValueError("terminal-population cross-form text differs")
        return value

    @model_validator(mode="after")
    def reconciliation_matches(
        self,
    ) -> "TerminalPopulationSecCrossFormReconciliationV1":
        if (
            self.exchange_notice_signature_date != self.cover_report_date
            or self.cover_report_date != self.transaction_completion_date
            or self.logical_fingerprint
            != base._fingerprint(
                self.model_dump(mode="json", exclude={"logical_fingerprint"})
            )
        ):
            raise ValueError("terminal-population cross-form reconciliation differs")
        return self


class StrongLeaderPullbackTerminalPopulationSecCoreAdjudicationV1(_FrozenModel):
    contract_version: Literal[
        "strong-leader-pullback-terminal-population-sec-core-adjudication/1.0"
    ] = CONTRACT_VERSION
    completion_status: Literal[
        "core_source_evidence_adjudicated_terminal_policy_unresolved"
    ] = "core_source_evidence_adjudicated_terminal_policy_unresolved"
    implementation_revision: str = Field(pattern=_REVISION_PATTERN)
    evaluated_at: datetime
    ruleset_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    plan_sha256: str = Field(pattern=_SHA256_PATTERN)
    plan_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    source_manifest_sha256: str = Field(pattern=_SHA256_PATTERN)
    source_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    field_candidate_report_sha256: str = Field(pattern=_SHA256_PATTERN)
    field_candidate_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    source_case_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    boundary_identity_effective_from: date
    boundary_identity_effective_to_exclusive: date
    identity_interval_is_full_lifecycle: Literal[False] = False
    lifecycle_case_count: Literal[1] = 1
    adjudicated_evidence_count: Literal[4] = 4
    cross_form_reconciliation: TerminalPopulationSecCrossFormReconciliationV1
    cover_identity: identity.SecCoverDocumentIdentityDecisionV1
    transaction_event: event.SecTransactionEventDecisionV1
    termination_reason: termination.SecTerminationReasonDecisionV1
    common_share_consideration: consideration.SecCommonShareConsiderationDecisionV1
    listed_security_identity_evidence_count: Literal[1] = 1
    issuer_transaction_completion_evidence_count: Literal[1] = 1
    termination_reason_evidence_count: Literal[1] = 1
    common_share_consideration_evidence_count: Literal[1] = 1
    party_relation_adjudication_count: Literal[0] = 0
    first_or_last_tradable_date_count: Literal[0] = 0
    effective_delisting_date_count: Literal[0] = 0
    normalized_payoff_term_count: Literal[0] = 0
    terminal_reference_value_count: Literal[0] = 0
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
    ) -> "StrongLeaderPullbackTerminalPopulationSecCoreAdjudicationV1":
        document_identity = {
            self.cover_identity.instrument_id,
            self.transaction_event.instrument_id,
            self.termination_reason.instrument_id,
            self.common_share_consideration.instrument_id,
            self.cross_form_reconciliation.instrument_id,
        }
        if (
            len(document_identity) != 1
            or self.boundary_identity_effective_from
            >= self.boundary_identity_effective_to_exclusive
            or self.cover_identity.resolution_state
            != "matched_in_source_lifecycle_window"
            or self.transaction_event.resolution_state != "matched"
            or self.termination_reason.resolution_state != "matched"
            or self.common_share_consideration.resolution_state != "matched"
            or self.transaction_event.identity_decision_fingerprint
            != self.cover_identity.logical_fingerprint
            or self.termination_reason.identity_decision_fingerprint
            != self.cover_identity.logical_fingerprint
            or self.termination_reason.transaction_event_fingerprint
            != self.transaction_event.logical_fingerprint
            or self.common_share_consideration.identity_decision_fingerprint
            != self.cover_identity.logical_fingerprint
            or self.common_share_consideration.transaction_event_fingerprint
            != self.transaction_event.logical_fingerprint
            or self.common_share_consideration.termination_reason_fingerprint
            != self.termination_reason.logical_fingerprint
            or self.ruleset_fingerprint != _ruleset_fingerprint()
            or self.logical_fingerprint
            != base._fingerprint(
                self.model_dump(mode="json", exclude={"logical_fingerprint"})
            )
        ):
            raise ValueError("terminal-population SEC core adjudication differs")
        return self


@dataclass(frozen=True, slots=True)
class StrongLeaderPullbackTerminalPopulationSecCoreAdjudicationResult:
    output_root: Path
    report: StrongLeaderPullbackTerminalPopulationSecCoreAdjudicationV1
    report_sha256: str
    status: Literal["published", "already_present"]


def build_strong_leader_pullback_terminal_population_sec_core_adjudication(
    *,
    plan_root: Path,
    plan_custody_root: Path,
    source_root: Path,
    source_custody_root: Path,
    field_candidate_root: Path,
    field_candidate_custody_root: Path,
    output_root: Path,
    output_custody_root: Path,
    implementation_revision: str,
    evaluated_at: datetime,
) -> StrongLeaderPullbackTerminalPopulationSecCoreAdjudicationResult:
    """Adjudicate four bounded source-evidence fields without outcomes."""

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
        fields = field_reader.read_strong_leader_pullback_terminal_population_sec_field_candidates(
            output_root=field_candidate_root,
            output_custody_root=field_candidate_custody_root,
        )
        report = _build_report(
            plan=plan,
            source=source,
            fields=fields,
            implementation_revision=implementation_revision,
            evaluated_at=evaluated_at,
        )
        return _write_report(
            output_root=output_root,
            output_custody_root=output_custody_root,
            report=report,
        )


def read_strong_leader_pullback_terminal_population_sec_core_adjudication(
    *, output_root: Path, output_custody_root: Path
) -> StrongLeaderPullbackTerminalPopulationSecCoreAdjudicationResult:
    root = _validated_completed_output(output_root, output_custody_root)
    if {item.name for item in root.iterdir()} != {REPORT_FILE}:
        raise StrongLeaderPullbackTerminalPopulationSecCoreAdjudicationError(
            "terminal-population SEC core-adjudication members differ"
        )
    path = root / REPORT_FILE
    source_base._require_regular_file(path, 0o400, MAXIMUM_REPORT_BYTES)
    raw = path.read_bytes()
    try:
        report = StrongLeaderPullbackTerminalPopulationSecCoreAdjudicationV1.model_validate_json(
            raw
        )
    except Exception as exc:
        raise StrongLeaderPullbackTerminalPopulationSecCoreAdjudicationError(
            "terminal-population SEC core adjudication is invalid"
        ) from exc
    if raw != base._json_bytes(report.model_dump(mode="json")):
        raise StrongLeaderPullbackTerminalPopulationSecCoreAdjudicationError(
            "terminal-population SEC core-adjudication bytes differ"
        )
    return StrongLeaderPullbackTerminalPopulationSecCoreAdjudicationResult(
        output_root=root,
        report=report,
        report_sha256=base._sha256_bytes(raw),
        status="already_present",
    )


def _build_report(
    *, plan: object, source: object, fields: object,
    implementation_revision: str, evaluated_at: datetime,
) -> StrongLeaderPullbackTerminalPopulationSecCoreAdjudicationV1:
    if re.fullmatch(_REVISION_PATTERN, implementation_revision) is None:
        raise StrongLeaderPullbackTerminalPopulationSecCoreAdjudicationError(
            "terminal-population SEC core-adjudication revision is invalid"
        )
    if (
        len(plan.report.cases) != 1
        or fields.report.plan_sha256 != plan.report_sha256
        or fields.report.plan_logical_fingerprint != plan.report.logical_fingerprint
        or fields.report.source_manifest_sha256 != source.manifest_sha256
        or fields.report.source_logical_fingerprint
        != source.manifest.logical_fingerprint
        or len(fields.report.form25_candidates) != 1
        or len(fields.report.form15_candidates) != 1
        or len(fields.report.transaction_candidates) != 1
    ):
        raise StrongLeaderPullbackTerminalPopulationSecCoreAdjudicationError(
            "terminal-population SEC core-adjudication inputs differ"
        )
    case = plan.report.cases[0]
    if (
        case.selected_identity_type != "share_class_figi"
        or len(case.provider_ticker_locators) != 1
        or case.primary_exchange not in {"XNAS", "XNYS"}
    ):
        raise StrongLeaderPullbackTerminalPopulationSecCoreAdjudicationError(
            "terminal-population SEC boundary identity is unsupported"
        )
    boundary_end = case.provider_delist_date_candidate + timedelta(days=1)
    resolver = SecIdentityResolver(
        (
            SecIdentityRecord(
                instrument_id=case.instrument_id,
                effective_from=case.strategy_window_last_eod_observed_date,
                effective_to=boundary_end,
                cik=case.cik,
                ticker=case.provider_ticker_locators[0],
                exchange=case.primary_exchange,
                share_class_figi=case.selected_identity_value,
            ),
        )
    )
    source_case = SimpleNamespace(
        instrument_id=case.instrument_id,
        cik_locators=(case.cik,),
        provider_ticker_locators=case.provider_ticker_locators,
        primary_exchange_locators=(case.primary_exchange,),
        selected_identity_values=(case.selected_identity_value,),
        provider_delist_date_candidate=case.provider_delist_date_candidate,
    )
    transaction_candidate = fields.report.transaction_candidates[0]
    path = _document_path(source.output_root, transaction_candidate.request_sequence)
    cover = identity._document_decision(
        candidate=transaction_candidate,
        source_case=source_case,
        resolver=resolver,
        path=path,
    )
    transaction_event = event._document_decision(
        candidate=transaction_candidate,
        identity_decision=cover,
        path=path,
    )
    termination_reason = termination._document_decision(
        event=transaction_event,
        identity=cover,
        path=path,
    )
    common_share_consideration = consideration._document_decision(
        event=transaction_event,
        identity=cover,
        termination=termination_reason,
        path=path,
    )
    cross_form = _cross_form_reconciliation(
        case=case,
        form25_candidate=fields.report.form25_candidates[0],
        form15_candidate=fields.report.form15_candidates[0],
        cover=cover,
        transaction_event=transaction_event,
    )
    values = {
        "implementation_revision": implementation_revision,
        "evaluated_at": normalize_utc_datetime(evaluated_at),
        "ruleset_fingerprint": _ruleset_fingerprint(),
        "plan_sha256": plan.report_sha256,
        "plan_logical_fingerprint": plan.report.logical_fingerprint,
        "source_manifest_sha256": source.manifest_sha256,
        "source_logical_fingerprint": source.manifest.logical_fingerprint,
        "field_candidate_report_sha256": fields.report_sha256,
        "field_candidate_logical_fingerprint": fields.report.logical_fingerprint,
        "source_case_fingerprint": base._fingerprint(case.model_dump(mode="json")),
        "boundary_identity_effective_from": (
            case.strategy_window_last_eod_observed_date
        ),
        "boundary_identity_effective_to_exclusive": boundary_end,
        "cross_form_reconciliation": cross_form,
        "cover_identity": cover,
        "transaction_event": transaction_event,
        "termination_reason": termination_reason,
        "common_share_consideration": common_share_consideration,
    }
    provisional = StrongLeaderPullbackTerminalPopulationSecCoreAdjudicationV1.model_construct(
        **values, logical_fingerprint="0" * 64
    )
    return StrongLeaderPullbackTerminalPopulationSecCoreAdjudicationV1.model_validate(
        {
            **values,
            "logical_fingerprint": base._fingerprint(
                provisional.model_dump(mode="json", exclude={"logical_fingerprint"})
            ),
        }
    )


def _cross_form_reconciliation(
    *, case: object, form25_candidate: object, form15_candidate: object,
    cover: identity.SecCoverDocumentIdentityDecisionV1,
    transaction_event: event.SecTransactionEventDecisionV1,
) -> TerminalPopulationSecCrossFormReconciliationV1:
    matching_rows = tuple(
        item
        for item in cover.security_rows
        if item.logical_fingerprint == cover.matched_row_fingerprint
    )
    expected_class = "Class A Common Stock"
    if (
        len(matching_rows) != 1
        or form25_candidate.instrument_id != case.instrument_id
        or form15_candidate.instrument_id != case.instrument_id
        or form25_candidate.issuer_cik_locator != case.cik
        or form15_candidate.issuer_cik_locator != case.cik
        or cover.issuer_cik != case.cik
        or form15_candidate.commission_file_number_candidates
        != (form25_candidate.commission_file_number,)
        or form25_candidate.security_class_descriptions != (expected_class,)
        or expected_class not in form15_candidate.security_class_text_fragments
        or matching_rows[0].security_title != expected_class
        or matching_rows[0].exchange_mic != case.primary_exchange
        or transaction_event.selected_event_date is None
        or form25_candidate.notice_signature_date != cover.report_date
        or cover.report_date != transaction_event.selected_event_date
    ):
        raise StrongLeaderPullbackTerminalPopulationSecCoreAdjudicationError(
            "terminal-population SEC cross-form reconciliation differs"
        )
    values = {
        "instrument_id": case.instrument_id,
        "cik": case.cik,
        "commission_file_number": form25_candidate.commission_file_number,
        "common_equity_security_class": expected_class,
        "exchange_mic": matching_rows[0].exchange_mic,
        "exchange_notice_signature_date": form25_candidate.notice_signature_date,
        "cover_report_date": cover.report_date,
        "transaction_completion_date": transaction_event.selected_event_date,
    }
    provisional = TerminalPopulationSecCrossFormReconciliationV1.model_construct(
        **values, logical_fingerprint="0" * 64
    )
    return TerminalPopulationSecCrossFormReconciliationV1.model_validate(
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
            "identity": identity.CONTRACT_VERSION,
            "transaction_event": event.CONTRACT_VERSION,
            "termination_reason": termination.CONTRACT_VERSION,
            "consideration": consideration.CONTRACT_VERSION,
            "identity_interval": (
                "strategy_last_eod_through_provider_delist_candidate_inclusive"
            ),
            "cross_form": (
                "cik_commission_file_common_equity_exchange_notice_completion"
            ),
            "ticker_only": "forbidden",
        }
    )


def _document_path(source_root: Path, sequence: int) -> Path:
    return source_root / f"request={sequence:06d}" / source_reader.DOCUMENT_FILE


def _write_report(
    *, output_root: Path, output_custody_root: Path,
    report: StrongLeaderPullbackTerminalPopulationSecCoreAdjudicationV1,
) -> StrongLeaderPullbackTerminalPopulationSecCoreAdjudicationResult:
    target = _validated_output_target(output_root, output_custody_root)
    if target.exists() or target.is_symlink():
        existing = read_strong_leader_pullback_terminal_population_sec_core_adjudication(
            output_root=target, output_custody_root=output_custody_root
        )
        if existing.report != report:
            raise StrongLeaderPullbackTerminalPopulationSecCoreAdjudicationError(
                "existing terminal-population SEC core adjudication differs"
            )
        return existing
    partial = target.parent / f".{target.name}.partial.{os.getpid()}"
    if partial.exists() or partial.is_symlink():
        raise StrongLeaderPullbackTerminalPopulationSecCoreAdjudicationError(
            "terminal-population SEC core-adjudication staging exists"
        )
    partial.mkdir(mode=0o700)
    try:
        raw = base._json_bytes(report.model_dump(mode="json"))
        if len(raw) > MAXIMUM_REPORT_BYTES:
            raise StrongLeaderPullbackTerminalPopulationSecCoreAdjudicationError(
                "terminal-population SEC core report exceeds byte ceiling"
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
    reread = read_strong_leader_pullback_terminal_population_sec_core_adjudication(
        output_root=target, output_custody_root=output_custody_root
    )
    return StrongLeaderPullbackTerminalPopulationSecCoreAdjudicationResult(
        output_root=target,
        report=reread.report,
        report_sha256=reread.report_sha256,
        status="published",
    )


def _validated_output_target(path: Path, custody_root: Path) -> Path:
    if not path.is_absolute() or not custody_root.is_absolute():
        raise StrongLeaderPullbackTerminalPopulationSecCoreAdjudicationError(
            "terminal-population SEC core-adjudication paths must be absolute"
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
        raise StrongLeaderPullbackTerminalPopulationSecCoreAdjudicationError(
            "terminal-population SEC core-adjudication target is unsafe"
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
        raise StrongLeaderPullbackTerminalPopulationSecCoreAdjudicationError(
            "terminal-population SEC core-adjudication output is unsafe"
        )
    return target
