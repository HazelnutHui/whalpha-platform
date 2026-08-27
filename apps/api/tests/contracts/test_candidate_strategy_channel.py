from __future__ import annotations

from copy import deepcopy
from datetime import date

import pytest
from pydantic import ValidationError

from tip_api.contracts.analytics.v1 import (
    CandidateStrategyChannelAssessmentV1,
    CandidateStrategyChannelBatchV1,
    STRATEGY_CHANNEL_ORDER,
    STRATEGY_CHANNEL_PARAMETER_FINGERPRINT,
    StrategyChannel,
    strategy_channel_logical_fingerprint,
)


SESSION = date(2026, 8, 26)
INSTRUMENT_ID = "00000000-0000-4000-8000-000000000001"
DIGEST = STRATEGY_CHANNEL_PARAMETER_FINGERPRINT


def _evidence(
    source_kind: str = "price_volume",
    *,
    role: str = "primary",
    evidence_type: str = "fact",
    source_session: str = "2026-08-26",
    evidence_kind: str = "supporting",
) -> dict[str, object]:
    return {
        "evidence_id": f"{source_kind}_{evidence_kind}_fact",
        "evidence_kind": evidence_kind,
        "role": role,
        "source_kind": source_kind,
        "evidence_type": evidence_type,
        "availability": "available",
        "observed_value": "1.0000",
        "raw_unit": "ratio",
        "source_session": source_session,
        "missing_reason_code": None,
        "reason_codes": ["observed_without_forward_outcome"],
    }


def _assessment(
    channel: str,
    status: str,
    *,
    score: str | None,
    rank: int | None,
    evidence: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    unavailable = status == "unavailable"
    payload: dict[str, object] = {
        "schema_version": "1.0",
        "contract_version": "candidate-strategy-channel-shadow/1.0",
        "calculation_version": "candidate-strategy-channel-shadow-v1.0.0",
        "parameter_set_id": "candidate-strategy-channel-taxonomy-v1",
        "parameter_fingerprint": DIGEST,
        "as_of_session": SESSION.isoformat(),
        "universe_id": "primary",
        "instrument_id": INSTRUMENT_ID,
        "ticker": "TEST",
        "security_type": "CS",
        "channel": channel,
        "status": status,
        "channel_score": score,
        "within_channel_rank": rank,
        "score_meaning": "within_channel_research_priority_not_return_probability",
        "market_fit": "unavailable" if unavailable else "neutral",
        "market_fit_reason_codes": ["market_fit_not_yet_calibrated"] if unavailable else ["market_fit_neutral"],
        "market_fit_separate_from_channel_score": True,
        "first_rejection_is_risk_not_status_reason": True,
        "source_candidate_fingerprint": "2" * 64,
        "source_entry_geometry_fingerprint": "3" * 64,
        "evidence": evidence or [],
        "missing_required_evidence_codes": [f"{channel}_required_evidence_unavailable"] if unavailable else [],
        "why_surfaced_codes": [f"{channel}_screen_flag"] if status == "advance_to_research" else [],
        "first_rejection_code": f"{channel}_first_smart_rejection_risk",
        "what_would_make_researchable_codes": [] if status == "advance_to_research" else [f"{channel}_needs_confirmation"],
        "invalidation_codes": [f"{channel}_setup_invalidated"] if status == "advance_to_research" else [],
        "required_manual_check_codes": ["screen_is_not_trade_recommendation"],
        "warning_codes": [],
    }
    payload["logical_fingerprint"] = strategy_channel_logical_fingerprint(payload)
    return payload


def _records() -> list[dict[str, object]]:
    price = [_evidence(), _evidence(evidence_kind="counterevidence")]
    return [
        _assessment("momentum_breakout", "advance_to_research", score="82.0000", rank=1, evidence=price),
        _assessment("strong_stock_pullback", "watch_for_trigger", score="71.0000", rank=1, evidence=price),
        _assessment("trend_continuation", "deprioritized", score="45.0000", rank=None, evidence=price),
        _assessment("technical_reversal", "deprioritized", score="30.0000", rank=None, evidence=price),
        _assessment("fundamental_value_reversal", "unavailable", score=None, rank=None),
        _assessment("defensive_rotation", "unavailable", score=None, rank=None),
    ]


def _batch(records: list[dict[str, object]] | None = None) -> dict[str, object]:
    rows = records or _records()
    counts: dict[str, dict[str, int]] = {}
    for channel in STRATEGY_CHANNEL_ORDER:
        channel_rows = [row for row in rows if row["channel"] == channel]
        channel_counts: dict[str, int] = {}
        for row in channel_rows:
            status = str(row["status"])
            channel_counts[status] = channel_counts.get(status, 0) + 1
        counts[channel] = channel_counts
    payload: dict[str, object] = {
        "schema_version": "1.0",
        "contract_version": "candidate-strategy-channel-shadow/1.0",
        "calculation_version": "candidate-strategy-channel-shadow-v1.0.0",
        "parameter_set_id": "candidate-strategy-channel-taxonomy-v1",
        "parameter_fingerprint": DIGEST,
        "as_of_session": SESSION.isoformat(),
        "universe_id": "primary",
        "source_candidate_batch_fingerprint": "4" * 64,
        "source_entry_geometry_batch_fingerprint": "5" * 64,
        "channel_order": list(STRATEGY_CHANNEL_ORDER),
        "records": rows,
        "status_counts": counts,
        "cross_channel_score_prohibited": True,
        "research_priority_only": True,
        "event_context_is_auxiliary": True,
        "underlying_stock_result_not_option_return": True,
        "price_volume_not_fund_flow": True,
        "warnings": ["taxonomy_only_thresholds_not_validated"],
    }
    payload["logical_fingerprint"] = strategy_channel_logical_fingerprint(payload)
    return payload


def test_strategy_channel_batch_requires_explicit_independent_channel_results() -> None:
    batch = CandidateStrategyChannelBatchV1.model_validate(_batch())

    assert tuple(item.value for item in batch.channel_order) == STRATEGY_CHANNEL_ORDER
    assert batch.cross_channel_score_prohibited is True
    assert batch.research_priority_only is True
    assert batch.event_context_is_auxiliary is True
    assert batch.underlying_stock_result_not_option_return is True
    assert batch.price_volume_not_fund_flow is True


def test_strategy_channel_batch_rejects_silent_channel_omission() -> None:
    rows = _records()[:-1]
    with pytest.raises(ValidationError, match="at least 6|every strategy channel"):
        CandidateStrategyChannelBatchV1.model_validate(_batch(rows))


def test_strategy_channel_rejects_future_evidence() -> None:
    row = _assessment(
        "momentum_breakout",
        "advance_to_research",
        score="82.0000",
        rank=1,
        evidence=[_evidence(source_session="2026-08-27")],
    )
    with pytest.raises(ValidationError, match="future session"):
        CandidateStrategyChannelAssessmentV1.model_validate(row)


def test_event_evidence_cannot_be_primary_strategy_evidence() -> None:
    with pytest.raises(ValidationError, match="auxiliary context"):
        CandidateStrategyChannelAssessmentV1.model_validate(
            _assessment(
                "momentum_breakout",
                "advance_to_research",
                score="82.0000",
                rank=1,
                evidence=[_evidence("event")],
            )
        )


def test_fundamental_value_reversal_cannot_be_assessed_from_price_alone() -> None:
    with pytest.raises(ValidationError, match="required primary evidence"):
        CandidateStrategyChannelAssessmentV1.model_validate(
            _assessment(
                "fundamental_value_reversal",
                "watch_for_trigger",
                score="60.0000",
                rank=1,
                evidence=[_evidence()],
            )
        )


def test_advanced_strategy_result_requires_explicit_counterevidence() -> None:
    with pytest.raises(ValidationError, match="counterevidence"):
        CandidateStrategyChannelAssessmentV1.model_validate(
            _assessment(
                "momentum_breakout",
                "advance_to_research",
                score="82.0000",
                rank=1,
                evidence=[_evidence()],
            )
        )


def test_strategy_channel_fingerprint_fails_closed_after_tamper() -> None:
    payload = _batch()
    tampered = deepcopy(payload)
    tampered["records"][0]["channel_score"] = "99.0000"  # type: ignore[index]
    with pytest.raises(ValidationError, match="logical fingerprint mismatch"):
        CandidateStrategyChannelBatchV1.model_validate(tampered)


def test_defensive_rotation_preserves_relationship_proxy_label() -> None:
    evidence = [
        _evidence("price_volume"),
        _evidence("market_regime"),
        _evidence("price_derived_relationship_proxy", evidence_type="proxy"),
        _evidence("price_volume", evidence_kind="counterevidence"),
    ]
    row = CandidateStrategyChannelAssessmentV1.model_validate(
        _assessment(
            "defensive_rotation",
            "advance_to_research",
            score="78.0000",
            rank=1,
            evidence=evidence,
        )
    )

    assert row.channel is StrategyChannel.DEFENSIVE_ROTATION
