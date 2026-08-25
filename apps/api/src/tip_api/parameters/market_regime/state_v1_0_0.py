"""Immutable deterministic parameters for Market Regime Phase 1b state classification."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass


STATE_CONTRACT_VERSION = "market-regime-state/1.0"
STATE_CALCULATION_VERSION = "market-regime-opportunity-map-state-v1.0.0"
STATE_PARAMETER_SET_ID = "mrom-regime-state-v1-fixed-baseline-1"
PHASE1A_CALCULATION_VERSION = "market-regime-opportunity-map-v1.0.0"
PHASE1A_PARAMETER_SET_ID = "mrom-v1-fixed-baseline-1"
PHASE1A_PARAMETER_FINGERPRINT = "69f9cb4744f4d133c72ba872588a87821b3445cabdd6fc129785f06232407759"
FROZEN_PHASE1A_AUDIT_FINGERPRINT = "d915e86efc14f9bebadfdc4c029afc3d6f0885adaa757f8e9330357d15b22dbf"


@dataclass(frozen=True, slots=True)
class CandidateBand:
    state: str
    lower: str | None
    lower_operator: str | None
    upper: str | None
    upper_operator: str | None
    defensive_rank: int


@dataclass(frozen=True, slots=True)
class TransitionRule:
    rule_id: str
    current_state: str
    target_state: str
    operator: str
    threshold: str
    confirmation_sessions: int
    priority: int
    immediate: bool = False


CANDIDATE_BANDS = (
    CandidateBand("risk_on", "70.0000", ">=", None, None, 0),
    CandidateBand("balanced", "50.0000", ">=", "70.0000", "<", 1),
    CandidateBand("defensive", "30.0000", ">=", "50.0000", "<", 2),
    CandidateBand("stress", None, None, "30.0000", "<", 3),
)

TRANSITION_RULES = (
    TransitionRule(
        "non_stress_to_stress_immediate",
        "any_non_stress",
        "stress",
        "<=",
        "20.0000",
        1,
        0,
        True,
    ),
    TransitionRule("risk_on_to_balanced", "risk_on", "balanced", "<", "65.0000", 2, 10),
    TransitionRule("balanced_to_risk_on", "balanced", "risk_on", ">=", "70.0000", 2, 20),
    TransitionRule("balanced_to_defensive", "balanced", "defensive", "<", "45.0000", 2, 21),
    TransitionRule("defensive_to_balanced", "defensive", "balanced", ">=", "55.0000", 2, 30),
    TransitionRule("defensive_to_stress", "defensive", "stress", "<", "30.0000", 2, 31),
    TransitionRule("stress_to_defensive", "stress", "defensive", ">=", "35.0000", 3, 40),
)

BOOTSTRAP_CONFIRMATION_SESSIONS = 2
BOOTSTRAP_DISAGREEMENT_POLICY = "more_defensive_confirmed_provisional"
PROVISIONAL_CLEAR_MATCH_SESSIONS = 1
MISSING_COMPOSITE_POLICY = "pause_confirmation_hold_prior_state_stale"
SESSION_GAP_POLICY = "explicit_unavailable_row_required"
CROSS_LEVEL_POLICY = "adjacent_only_except_immediate_stress_override"
STATE_ORDER = tuple(item.state for item in CANDIDATE_BANDS)
DEFENSIVE_RANK = {item.state: item.defensive_rank for item in CANDIDATE_BANDS}


def _payload() -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "state_contract_version": STATE_CONTRACT_VERSION,
        "state_calculation_version": STATE_CALCULATION_VERSION,
        "state_parameter_set_id": STATE_PARAMETER_SET_ID,
        "phase1a_calculation_version": PHASE1A_CALCULATION_VERSION,
        "phase1a_parameter_set_id": PHASE1A_PARAMETER_SET_ID,
        "phase1a_parameter_fingerprint": PHASE1A_PARAMETER_FINGERPRINT,
        "candidate_bands": [asdict(item) for item in CANDIDATE_BANDS],
        "transition_rules": [asdict(item) for item in TRANSITION_RULES],
        "bootstrap_confirmation_sessions": BOOTSTRAP_CONFIRMATION_SESSIONS,
        "bootstrap_disagreement_policy": BOOTSTRAP_DISAGREEMENT_POLICY,
        "provisional_clear_match_sessions": PROVISIONAL_CLEAR_MATCH_SESSIONS,
        "missing_composite_policy": MISSING_COMPOSITE_POLICY,
        "session_gap_policy": SESSION_GAP_POLICY,
        "cross_level_policy": CROSS_LEVEL_POLICY,
        "confirmation_clock": "completed_xnys_sessions_only",
        "candidate_confirmed_state_separation": True,
        "first_candidate_auto_confirms": False,
        "parameter_selection_basis": (
            "accepted_product_hysteresis_table_plus_minimal_explicit_bootstrap_and_pause_rules"
        ),
        "parameter_validation_status": "implementation_baseline_not_predictive_validation",
    }


STATE_PARAMETER_FINGERPRINT = hashlib.sha256(
    json.dumps(_payload(), sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
).hexdigest()


def state_parameter_payload() -> dict[str, object]:
    """Return a detached JSON-compatible parameter contract."""

    return json.loads(json.dumps(_payload(), sort_keys=True, separators=(",", ":")))
