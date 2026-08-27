from __future__ import annotations

from copy import deepcopy
from datetime import date
from uuid import UUID

import pytest
from pydantic import ValidationError

from tip_api.contracts.analytics.v1 import (
    CandidateStrategyEvaluationPolicyV1,
    CandidateStrategyForwardOutcomeV1,
    CandidateStrategySignalV1,
    STRATEGY_EVALUATION_POLICY_FINGERPRINT,
    StrategyChannel,
    candidate_strategy_signal_id,
    strategy_channel_logical_fingerprint,
)


SIGNAL_SESSION = date(2026, 8, 20)
INSTRUMENT_ID = UUID("00000000-0000-4000-8000-000000000001")
ASSESSMENT_FINGERPRINT = "1" * 64


def _signal() -> dict[str, object]:
    payload: dict[str, object] = {
        "schema_version": "1.0",
        "contract_version": "candidate-strategy-signal/1.0",
        "evaluation_policy_fingerprint": STRATEGY_EVALUATION_POLICY_FINGERPRINT,
        "signal_id": candidate_strategy_signal_id(
            as_of_session=SIGNAL_SESSION,
            universe_id="primary",
            instrument_id=INSTRUMENT_ID,
            channel=StrategyChannel.MOMENTUM_BREAKOUT,
            assessment_logical_fingerprint=ASSESSMENT_FINGERPRINT,
        ),
        "as_of_session": SIGNAL_SESSION.isoformat(),
        "universe_id": "primary",
        "instrument_id": str(INSTRUMENT_ID),
        "ticker": "TEST",
        "security_type": "CS",
        "channel": "momentum_breakout",
        "channel_status": "advance_to_research",
        "channel_score": "82.0000",
        "within_channel_rank": 1,
        "assessment_logical_fingerprint": ASSESSMENT_FINGERPRINT,
        "assessment_parameter_fingerprint": "2" * 64,
        "source_candidate_fingerprint": "3" * 64,
        "source_entry_geometry_fingerprint": "4" * 64,
        "source_market_regime_fingerprint": "5" * 64,
        "source_sessions": ["2026-08-18", "2026-08-19", "2026-08-20"],
        "membership_mode": "point_in_time",
        "membership_session": SIGNAL_SESSION.isoformat(),
        "membership_fingerprint": "6" * 64,
        "membership_methodology_version": "primary-point-in-time-v1",
        "evaluation_eligible": True,
        "evaluation_split": "development",
        "limitation_codes": [],
        "sealed_without_outcomes": True,
    }
    payload["logical_fingerprint"] = strategy_channel_logical_fingerprint(payload)
    return payload


def _outcome(status: str = "available") -> dict[str, object]:
    signal = CandidateStrategySignalV1.model_validate(_signal())
    available = status == "available"
    payload: dict[str, object] = {
        "schema_version": "1.0",
        "contract_version": "candidate-strategy-forward-outcome/1.0",
        "evaluation_policy_fingerprint": STRATEGY_EVALUATION_POLICY_FINGERPRINT,
        "signal_id": signal.signal_id,
        "signal_logical_fingerprint": signal.logical_fingerprint,
        "signal_session": SIGNAL_SESSION.isoformat(),
        "universe_id": "primary",
        "instrument_id": str(INSTRUMENT_ID),
        "channel": "momentum_breakout",
        "horizon_sessions": 3,
        "expected_entry_session": "2026-08-21",
        "expected_exit_session": "2026-08-25",
        "expected_path_sessions": ["2026-08-21", "2026-08-24", "2026-08-25"],
        "observed_entry_session": "2026-08-21" if available else None,
        "observed_exit_session": "2026-08-25" if available else None,
        "status": status,
        "return_basis": "next_session_open_to_horizon_session_close",
        "entry_price": "100.0000000000" if available else None,
        "exit_price": "105.0000000000" if available else None,
        "underlying_price_return": "0.0500000000" if available else None,
        "benchmark_price_return": "0.0200000000" if available else None,
        "relative_to_benchmark_return": "0.0300000000" if available else None,
        "maximum_favorable_excursion": "0.0800000000" if available else None,
        "maximum_adverse_excursion": "-0.0200000000" if available else None,
        "corporate_action_status": "clear" if available else "unavailable",
        "source_eod_fingerprint": "7" * 64 if available else None,
        "label_source_max_session": "2026-08-25" if available else None,
        "reason_codes": [] if available else ["outcome_not_yet_mature"],
        "underlying_stock_result_not_option_return": True,
        "transaction_costs_not_applied": True,
    }
    payload["logical_fingerprint"] = strategy_channel_logical_fingerprint(payload)
    return payload


def test_fixed_evaluation_policy_prohibits_random_split_and_option_claims() -> None:
    policy = CandidateStrategyEvaluationPolicyV1()

    assert policy.forward_horizons_sessions == (1, 3, 5)
    assert policy.embargo_sessions == 5
    assert policy.random_split_prohibited is True
    assert policy.signals_sealed_before_outcomes is True
    assert policy.underlying_stock_result_not_option_return is True


def test_point_in_time_signal_is_sealed_without_outcomes() -> None:
    signal = CandidateStrategySignalV1.model_validate(_signal())

    assert signal.evaluation_eligible is True
    assert signal.membership_session == signal.as_of_session
    assert signal.sealed_without_outcomes is True


def test_signal_rejects_future_feature_session() -> None:
    payload = _signal()
    payload["source_sessions"] = ["2026-08-20", "2026-08-21"]
    payload["logical_fingerprint"] = strategy_channel_logical_fingerprint(
        payload,
        exclude={"logical_fingerprint"},
    )
    with pytest.raises(ValidationError, match="future source session"):
        CandidateStrategySignalV1.model_validate(payload)


def test_current_constituent_replay_cannot_be_performance_eligible() -> None:
    payload = _signal()
    payload["membership_mode"] = "current_as_of_constituent_replay"
    payload["membership_session"] = "2026-08-26"
    payload["limitation_codes"] = ["current_constituent_replay_not_performance_eligible"]
    payload["logical_fingerprint"] = strategy_channel_logical_fingerprint(
        payload,
        exclude={"logical_fingerprint"},
    )
    with pytest.raises(ValidationError, match="research-only"):
        CandidateStrategySignalV1.model_validate(payload)


def test_signal_id_is_bound_to_sealed_assessment_identity() -> None:
    payload = _signal()
    payload["signal_id"] = "f" * 64
    payload["logical_fingerprint"] = strategy_channel_logical_fingerprint(
        payload,
        exclude={"logical_fingerprint"},
    )
    with pytest.raises(ValidationError, match="business identity"):
        CandidateStrategySignalV1.model_validate(payload)


def test_available_forward_outcome_reconciles_price_and_benchmark_returns() -> None:
    outcome = CandidateStrategyForwardOutcomeV1.model_validate(_outcome())

    assert outcome.underlying_price_return == "0.0500000000"
    assert outcome.relative_to_benchmark_return == "0.0300000000"
    assert outcome.underlying_stock_result_not_option_return is True
    assert outcome.transaction_costs_not_applied is True


def test_pending_outcome_cannot_leak_future_labels() -> None:
    pending = CandidateStrategyForwardOutcomeV1.model_validate(_outcome("pending"))
    assert pending.label_source_max_session is None

    leaked = _outcome("pending")
    leaked["exit_price"] = "105.0000000000"
    leaked["logical_fingerprint"] = strategy_channel_logical_fingerprint(
        leaked,
        exclude={"logical_fingerprint"},
    )
    with pytest.raises(ValidationError, match="cannot carry future labels"):
        CandidateStrategyForwardOutcomeV1.model_validate(leaked)


def test_forward_outcome_arithmetic_and_path_fail_closed() -> None:
    tampered = deepcopy(_outcome())
    tampered["relative_to_benchmark_return"] = "0.0400000000"
    tampered["logical_fingerprint"] = strategy_channel_logical_fingerprint(
        tampered,
        exclude={"logical_fingerprint"},
    )
    with pytest.raises(ValidationError, match="arithmetic"):
        CandidateStrategyForwardOutcomeV1.model_validate(tampered)

    wrong_path = _outcome()
    wrong_path["expected_path_sessions"] = ["2026-08-21", "2026-08-25"]
    wrong_path["logical_fingerprint"] = strategy_channel_logical_fingerprint(
        wrong_path,
        exclude={"logical_fingerprint"},
    )
    with pytest.raises(ValidationError, match="exact ordered future horizon"):
        CandidateStrategyForwardOutcomeV1.model_validate(wrong_path)
