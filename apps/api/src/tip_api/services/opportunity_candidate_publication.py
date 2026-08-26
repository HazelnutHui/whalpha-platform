"""Build the bounded, language-neutral Candidate consumer view from one verified audit."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

from tip_api.contracts.analytics.v1 import (
    CandidateOpportunityStage,
    CandidatePublicationEvidenceV1,
    CandidatePublicationStateV1,
    CandidateRiskDispositionV1,
    CandidateRiskMode,
    CandidateRiskModePublicationV1,
    CandidateRiskModeResultV1,
    OpportunityCandidateBatchV1,
    OpportunityCandidatePublicationItemV1,
    OpportunityCandidatePublicationSourceV1,
    OpportunityCandidatePublicationV1,
    OpportunityCandidateStateRecordV1,
    OpportunityCandidateUniversePublicationV1,
)
from tip_api.parameters.market_regime.candidate_v1_1_1 import RISK_MODE_PARAMETERS
from tip_api.services.opportunity_candidate_audit import read_opportunity_candidate_audit


class OpportunityCandidatePublicationError(RuntimeError):
    """Raised when a verified Candidate audit cannot form a safe consumer view."""


def build_opportunity_candidate_publication(
    audit_path: Path,
) -> OpportunityCandidatePublicationV1:
    """Reread one immutable audit and project only bounded, current-session product facts."""

    manifest = read_opportunity_candidate_audit(audit_path)
    as_of_session = manifest["as_of_session"]
    batches = tuple(
        OpportunityCandidateBatchV1.model_validate(row)
        for row in _artifact(audit_path, "candidate-score-history.json")["records"]
        if row["as_of_session"] == as_of_session
    )
    states = tuple(
        OpportunityCandidateStateRecordV1.model_validate(row)
        for row in _artifact(audit_path, "candidate-state-history.json")["records"]
        if row["as_of_session"] == as_of_session
    )
    risks = tuple(
        CandidateRiskModeResultV1.model_validate(row)
        for row in _artifact(audit_path, "current-risk-mode-results.json")["records"]
        if row["as_of_session"] == as_of_session
    )
    source_payload = _artifact(audit_path, "source-input-manifest.json")
    current_panel = source_payload["panels"][-1]
    universe_order = tuple(manifest["universe_ids"])
    if len(universe_order) != 2 or current_panel["as_of_session"] != as_of_session:
        raise OpportunityCandidatePublicationError("Candidate current source panel is inconsistent")
    batch_by_universe = {row.universe_id: row for row in batches}
    if tuple(batch_by_universe) != universe_order:
        raise OpportunityCandidatePublicationError("Candidate current batch Universe order differs")
    risk_by_key = {(row.universe_id, row.risk_mode): row for row in risks}
    expected_risk_keys = tuple(
        (universe_id, mode) for universe_id in universe_order for mode in CandidateRiskMode
    )
    if tuple(risk_by_key) != expected_risk_keys:
        raise OpportunityCandidatePublicationError("Candidate current risk result order differs")
    state_by_universe: dict[str, dict[str, OpportunityCandidateStateRecordV1]] = {}
    for universe_id in universe_order:
        rows = [row for row in states if row.universe_id == universe_id]
        state_by_universe[universe_id] = {str(row.instrument_id): row for row in rows}
        if len(rows) != len(state_by_universe[universe_id]):
            raise OpportunityCandidatePublicationError("Candidate state stable IDs are duplicated")

    universe_sources = {row["universe_id"]: row for row in current_panel["universes"]}
    publications = tuple(
        _universe_publication(
            batch=batch_by_universe[universe_id],
            states=state_by_universe[universe_id],
            risks={mode: risk_by_key[(universe_id, mode)] for mode in CandidateRiskMode},
            membership_fingerprint=universe_sources[universe_id]["membership_fingerprint"],
        )
        for universe_id in universe_order
    )
    flags = manifest["equivalence_flags"]
    source = OpportunityCandidatePublicationSourceV1(
        candidate_audit_manifest_sha256=_sha256(audit_path / "candidate-audit-manifest.json"),
        candidate_audit_logical_fingerprint=manifest["logical_content_fingerprint"],
        candidate_history_fingerprint=manifest["candidate_history_fingerprint"],
        candidate_state_history_fingerprint=manifest["candidate_state_history_fingerprint"],
        risk_results_fingerprint=manifest["risk_results_fingerprint"],
        oracle_fingerprint=manifest["oracle_fingerprint"],
        oracle_mismatch_count=manifest["oracle_mismatch_count"],
        shared_raw_fact_match=manifest["shared_raw_fact_match"],
        input_permutation_match=manifest["input_permutation_match"],
        append_full_replay_match=flags["append_full_replay_match"],
        restart_replay_match=flags["restart_replay_match"],
        future_prefix_stable=flags["future_prefix_stable"],
        candidate_contract_version=manifest["candidate_contract_version"],
        candidate_calculation_version=manifest["candidate_calculation_version"],
        candidate_parameter_set_id=manifest["candidate_parameter_set_id"],
        candidate_parameter_fingerprint=manifest["candidate_parameter_fingerprint"],
        candidate_state_contract_version=manifest["candidate_state_contract_version"],
        candidate_state_calculation_version=manifest["candidate_state_calculation_version"],
        candidate_state_parameter_set_id=manifest["candidate_state_parameter_set_id"],
        candidate_state_parameter_fingerprint=manifest["candidate_state_parameter_fingerprint"],
        activation_pointer_fingerprint=current_panel["activation_pointer_fingerprint"],
        identity_logical_fingerprint=current_panel["identity_logical_fingerprint"],
        eod_content_fingerprint=current_panel["eod_content_fingerprint"],
        eod_business_key_fingerprint=current_panel["eod_business_key_fingerprint"],
        history_source_fingerprint=current_panel["history_source_fingerprint"],
        current_candidate_batch_fingerprints=tuple(row.logical_fingerprint for row in batches),
        current_risk_result_fingerprints=tuple(row.logical_fingerprint for row in risks),
    )
    body: dict[str, Any] = {
        "schema_version": "1.0",
        "contract_version": "opportunity-candidate-publication/1.0",
        "as_of_session": as_of_session,
        "default_universe_id": universe_order[0],
        "universe_order": universe_order,
        "risk_mode_order": tuple(mode.value for mode in CandidateRiskMode),
        "source": source.model_dump(mode="json"),
        "universes": [row.model_dump(mode="json") for row in publications],
        "language_neutral": True,
        "research_priority_only": True,
        "underlying_stock_result_not_option_return": True,
        "price_volume_not_fund_flow": True,
        "warnings": (
            "current_as_of_constituent_replay",
            "short_candidate_state_history",
            "research_candidate_not_trade_recommendation",
            "underlying_stock_result_not_option_return",
            "price_volume_proxies_not_fund_flow",
        ),
    }
    return OpportunityCandidatePublicationV1(
        **body,
        logical_fingerprint=_fingerprint(body),
    )


def _universe_publication(
    *,
    batch: OpportunityCandidateBatchV1,
    states: dict[str, OpportunityCandidateStateRecordV1],
    risks: dict[CandidateRiskMode, CandidateRiskModeResultV1],
    membership_fingerprint: str,
) -> OpportunityCandidateUniversePublicationV1:
    if batch.membership_fingerprint != membership_fingerprint:
        raise OpportunityCandidatePublicationError("Candidate membership source differs")
    score_by_id = {str(row.instrument_id): row for row in batch.candidates}
    assessment_by_mode = {
        mode: {str(row.instrument_id): row for row in result.assessments}
        for mode, result in risks.items()
    }
    if any(set(rows) != set(score_by_id) for rows in assessment_by_mode.values()):
        raise OpportunityCandidatePublicationError("Candidate risk assessment population differs")
    if not set(score_by_id).issubset(states):
        raise OpportunityCandidatePublicationError("Candidate current state population is incomplete")

    caps = {row.risk_mode: row.candidate_display_cap for row in RISK_MODE_PARAMETERS}
    mode_publications: list[CandidateRiskModePublicationV1] = []
    included: set[str] = set()
    for mode in CandidateRiskMode:
        result = risks[mode]
        ranked = sorted(
            (row for row in result.assessments if row.eligible),
            key=lambda row: row.risk_adjusted_rank or 0,
        )
        ids = tuple(row.instrument_id for row in ranked[: caps[mode.value]])
        included.update(str(value) for value in ids)
        mode_publications.append(
            CandidateRiskModePublicationV1(
                risk_mode=mode,
                eligible_count=result.eligible_count,
                rejected_count=result.rejected_count,
                display_cap=caps[mode.value],
                displayed_instrument_ids=ids,
                logical_fingerprint=result.logical_fingerprint,
            )
        )
    included.update(
        instrument_id
        for instrument_id, state in states.items()
        if state.final_stage in {
            CandidateOpportunityStage.PREPARE,
            CandidateOpportunityStage.ENTER,
            CandidateOpportunityStage.INVALIDATED,
        }
        and instrument_id in score_by_id
    )
    cards = tuple(
        _candidate_item(
            score_by_id[instrument_id],
            states[instrument_id],
            tuple(assessment_by_mode[mode][instrument_id] for mode in CandidateRiskMode),
        )
        for instrument_id in sorted(included)
    )
    quality_counts = Counter(row.data_quality_status for row in batch.candidates)
    stage_counts = Counter(
        state.final_stage.value if state.final_stage is not None else "unavailable"
        for state in states.values()
    )
    return OpportunityCandidateUniversePublicationV1(
        universe_id=batch.universe_id,
        universe_member_count=batch.universe_member_count,
        membership_fingerprint=batch.membership_fingerprint,
        bar_covered_member_count=batch.bar_covered_member_count,
        missing_member_count=len(batch.missing_member_ids),
        quality_counts=dict(quality_counts),
        stage_counts=dict(stage_counts),
        risk_modes=tuple(mode_publications),
        candidates=cards,
        candidate_batch_logical_fingerprint=batch.logical_fingerprint,
    )


def _candidate_item(score, state, assessments) -> OpportunityCandidatePublicationItemV1:
    if (
        score.instrument_id != state.instrument_id
        or score.ticker != state.ticker
        or score.security_type != state.security_type
        or state.source_candidate_fingerprint != score.logical_fingerprint
    ):
        raise OpportunityCandidatePublicationError("Candidate score and state identity differ")
    evidence = tuple(
        _evidence(value, "supporting") for value in score.supporting_evidence
    ) + tuple(_evidence(value, "counterevidence") for value in score.counterevidence)
    return OpportunityCandidatePublicationItemV1(
        instrument_id=score.instrument_id,
        ticker=score.ticker,
        security_type=score.security_type,
        base_score=score.base_score,
        adjusted_score=score.adjusted_score,
        configured_weight_available=score.configured_weight_available,
        missingness_penalty=score.missingness_penalty,
        confidence=score.confidence,
        latest_price=score.latest_price,
        median_dollar_volume_20=score.median_dollar_volume_20,
        annualized_volatility_10=score.annualized_volatility_10,
        maximum_absolute_open_gap_5=score.maximum_absolute_open_gap_5,
        current_volume_ratio=score.current_volume_ratio,
        primary_driver_instrument_id=score.primary_driver_instrument_id,
        primary_driver_ticker=score.primary_driver_ticker,
        driver_correlation_20=score.driver_correlation_20,
        relationship_kind=score.relationship_kind,
        data_quality_status=score.data_quality_status,
        components=score.components,
        evidence=evidence,
        invalidation_condition_codes=score.invalidation_conditions,
        reason_codes=score.reason_codes,
        warning_codes=score.warnings,
        state=CandidatePublicationStateV1(
            final_stage=state.final_stage,
            transition_status=state.transition_status,
            transition_rule_id=state.transition_rule_id,
            pending_target_stage=state.pending_target_stage,
            stage_confirmation_count=state.stage_confirmation_count_after,
            required_confirmation_sessions=state.required_confirmation_sessions,
            breakout_triggered=state.breakout_triggered,
            stale_state=state.stale_state,
            manual_review_required=state.manual_review_required,
            gate_results=state.gate_results,
            reason_codes=state.reason_codes,
            logical_fingerprint=state.logical_fingerprint,
        ),
        risk_dispositions=tuple(
            CandidateRiskDispositionV1(
                risk_mode=row.risk_mode,
                eligible=row.eligible,
                risk_adjusted_rank=row.risk_adjusted_rank,
                rejection_reason_codes=row.rejection_reason_codes,
            )
            for row in assessments
        ),
        score_logical_fingerprint=score.logical_fingerprint,
    )


def _evidence(value: str, kind: str) -> CandidatePublicationEvidenceV1:
    parts = value.split(":")
    if len(parts) == 2 and parts[0] == "missing_component":
        parts.append(None)
    if len(parts) != 3 or parts[0] not in {
        "positive_component",
        "weak_component",
        "missing_component",
    }:
        raise OpportunityCandidatePublicationError("Candidate evidence encoding is unknown")
    return CandidatePublicationEvidenceV1(
        evidence_kind=kind,
        evidence_id=parts[0],
        component_id=parts[1],
        observed_value=parts[2],
    )


def _artifact(path: Path, name: str) -> dict[str, Any]:
    return json.loads((path / name).read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _fingerprint(value: object) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()
