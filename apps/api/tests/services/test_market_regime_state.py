from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
from datetime import UTC, date, datetime
from decimal import Decimal, Inexact, ROUND_DOWN, ROUND_HALF_EVEN, ROUND_UP, Rounded, localcontext
from pathlib import Path
from uuid import UUID, uuid5

import pytest

from tip_api.contracts.analytics.v1 import (
    AvailabilityStatus,
    MarketRegimeCompositeV1,
    MarketRegimeDimensionV1,
    RegimeState,
)
from tip_api.parameters.market_regime.state_v1_0_1 import (
    FROZEN_PHASE1A_AUDIT_FINGERPRINT,
    STATE_PARAMETER_FINGERPRINT,
    state_parameter_payload,
)
from tip_api.services.market_calendar import ExchangeCalendar
from tip_api.services.market_regime_sources import (
    MarketRegimeInputPanel,
    MarketRegimeSourceSession,
    MarketRegimeUniverseSource,
)
from tip_api.services.market_regime_history import _prefix_panel
from tip_api.services.market_regime_state import (
    MarketRegimeStateError,
    append_regime_state_history,
    instantaneous_regime_candidate,
    replay_regime_state_history,
    state_history_fingerprint,
)
from tip_api.services.market_regime_state_audit import (
    MarketRegimeStateAuditError,
    STATE_ARTIFACT_FILES,
    _validate_tmp_output_dir,
    read_market_regime_state_audit,
    write_market_regime_state_audit,
)
from tip_api.services.market_regime_state_oracle import compare_with_independent_state_oracle


PRIMARY = "provider_classified_common_shares_v1"
SECONDARY = "provider_classified_common_shares_plus_adrs_v1"
NS = UUID("e82a72c3-d853-5f6c-ab25-23ce91703188")
CALENDAR = ExchangeCalendar()
SESSIONS = CALENDAR.sessions_before(date(2026, 8, 21), 11) + (date(2026, 8, 21),)


def _fingerprint(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    ).hexdigest()


def _composite(session: date, score: str, universe_id: str = PRIMARY) -> MarketRegimeCompositeV1:
    value = Decimal(score)
    dimension_values = (
        min(Decimal("100"), value + Decimal("10")),
        value,
        min(Decimal("100"), value + Decimal("5")),
        max(Decimal("0"), value - Decimal("25")),
        min(Decimal("100"), value + Decimal("15")),
    )
    ids_weights = (
        ("trend", 30),
        ("breadth", 25),
        ("volatility", 20),
        ("liquidity_participation", 15),
        ("leadership_dispersion", 10),
    )
    dimensions = tuple(
        MarketRegimeDimensionV1(
            universe_id=universe_id,
            dimension_id=identifier,
            as_of_session=session,
            configured_weight=f"{weight}.0000",
            effective_weight=f"{weight}.0000",
            internal_configured_weight_available="100.0000",
            score=f"{dimension_values[index]:.4f}",
            score_contribution=f"{dimension_values[index] * Decimal(weight) / Decimal(100):.4f}",
            minimum_observations=1,
            actual_observations=1,
            coverage_ratio="1.0000000000",
            missing_count=0,
            availability=AvailabilityStatus.AVAILABLE,
            support_status=("supporting" if dimension_values[index] >= 60 else "conflicting" if dimension_values[index] <= 40 else "neutral"),
            explanation_template_id=f"fixture_{identifier}",
            rendered_explanation="fixture",
            raw_metrics=(),
            warnings=(),
            reason_codes=("dimension_available",),
        )
        for index, (identifier, weight) in enumerate(ids_weights)
    )
    logical = _fingerprint([session.isoformat(), score, universe_id])
    return MarketRegimeCompositeV1(
        parameter_set_fingerprint="a" * 64,
        as_of_session=session,
        universe_id=universe_id,
        universe_member_count=10,
        membership_fingerprint=("b" if universe_id == PRIMARY else "c") * 64,
        activation_pointer_fingerprint="d" * 64,
        identity_logical_fingerprint="e" * 64,
        eod_content_fingerprint="f" * 64,
        history_source_fingerprint="1" * 64,
        history_sessions_used=(session,),
        regime_score=f"{value:.4f}",
        configured_weight_available="100.0000",
        dimensions=dimensions,
        missing_metric_ids=(),
        unavailable_dimension_ids=(),
        warnings=("state_and_hysteresis_deferred_phase_1a",),
        reason_codes=("composite_available",),
        logical_fingerprint=logical,
    )


def _run(scores, *, universe_id=PRIMARY, sessions=None):
    selected = tuple(sessions or SESSIONS[: len(scores)])
    composites = tuple(
        _composite(session, score, universe_id)
        for session, score in zip(selected, scores, strict=True)
        if score is not None
    )
    return replay_regime_state_history(
        composites=composites,
        expected_sessions=selected,
        universe_id=universe_id,
        calendar=CALENDAR,
    )


@pytest.mark.parametrize(
    ("score", "expected"),
    (
        ("70.0000", RegimeState.RISK_ON),
        ("69.9999", RegimeState.BALANCED),
        ("50.0000", RegimeState.BALANCED),
        ("49.9999", RegimeState.DEFENSIVE),
        ("30.0000", RegimeState.DEFENSIVE),
        ("29.9999", RegimeState.STRESS),
    ),
)
def test_instantaneous_candidate_exact_boundaries(score: str, expected: RegimeState) -> None:
    assert instantaneous_regime_candidate(Decimal(score)) is expected


def test_every_transition_threshold_inclusive_exclusive_boundary() -> None:
    risk_on_exact, _ = _run(("72", "73", "65.0000"))
    assert risk_on_exact[-1].transition_status == "hysteresis_held"
    risk_on_below, _ = _run(("72", "73", "64.9999"))
    assert risk_on_below[-1].transition_rule_id == "risk_on_to_balanced"
    assert risk_on_below[-1].transition_status == "pending"

    balanced_defensive_exact, _ = _run(("60", "61", "45.0000"))
    assert balanced_defensive_exact[-1].transition_status == "hysteresis_held"
    balanced_defensive_below, _ = _run(("60", "61", "44.9999"))
    assert balanced_defensive_below[-1].transition_rule_id == "balanced_to_defensive"
    balanced_risk_on_exact, _ = _run(("60", "61", "70.0000"))
    assert balanced_risk_on_exact[-1].transition_rule_id == "balanced_to_risk_on"
    balanced_risk_on_below, _ = _run(("60", "61", "69.9999"))
    assert balanced_risk_on_below[-1].transition_status == "held"

    defensive_balanced_exact, _ = _run(("40", "40", "55.0000"))
    assert defensive_balanced_exact[-1].transition_rule_id == "defensive_to_balanced"
    defensive_balanced_below, _ = _run(("40", "40", "54.9999"))
    assert defensive_balanced_below[-1].transition_status == "hysteresis_held"
    defensive_stress_exact, _ = _run(("40", "40", "30.0000"))
    assert defensive_stress_exact[-1].transition_status == "held"
    defensive_stress_below, _ = _run(("40", "40", "29.9999"))
    assert defensive_stress_below[-1].transition_rule_id == "defensive_to_stress"

    immediate_exact, _ = _run(("60", "61", "20.0000"))
    assert immediate_exact[-1].transition_status == "immediate_stress_override"
    immediate_above, _ = _run(("60", "61", "20.0001"))
    assert immediate_above[-1].transition_rule_id == "balanced_to_defensive"
    assert immediate_above[-1].transition_status == "pending"

    stress_recovery_exact, _ = _run(("10", "10", "35.0000"))
    assert stress_recovery_exact[-1].transition_rule_id == "stress_to_defensive"
    stress_recovery_below, _ = _run(("10", "10", "34.9999"))
    assert stress_recovery_below[-1].transition_status == "hysteresis_held"


@pytest.mark.parametrize("invalid", ("NaN", "Infinity", "-0.0001", "100.0001"))
def test_invalid_or_nonfinite_composite_fails_closed(invalid: str) -> None:
    with pytest.raises(MarketRegimeStateError):
        instantaneous_regime_candidate(Decimal(invalid))


def test_bootstrap_requires_two_and_disagreement_is_more_defensive_provisional() -> None:
    records, _ = _run(("72", "73"))
    assert records[0].confirmed_state is None
    assert records[0].pending_target_state is RegimeState.RISK_ON
    assert records[0].transition_status == "initialization_pending"
    assert records[1].confirmed_state is RegimeState.RISK_ON
    assert not records[1].state_is_provisional

    records, _ = _run(("72", "60", "61"))
    assert records[1].confirmed_state is RegimeState.BALANCED
    assert records[1].state_is_provisional
    assert records[1].transition_status == "initialized_provisional"
    assert records[2].transition_status == "provisional_cleared"
    assert not records[2].state_is_provisional


def test_pending_confirmation_reversal_and_hysteresis_hold() -> None:
    records, _ = _run(("60", "61", "70", "69", "70", "71"))
    assert records[2].pending_target_state is RegimeState.RISK_ON
    assert records[2].consecutive_confirmation_sessions == 1
    assert records[3].transition_status == "pending_reversed"
    assert records[5].confirmed_state is RegimeState.RISK_ON
    assert records[5].transition_status == "switched"

    records, _ = _run(("72", "73", "68", "68"))
    assert records[-1].confirmed_state is RegimeState.RISK_ON
    assert records[-1].instantaneous_candidate_state is RegimeState.BALANCED
    assert records[-1].transition_status == "hysteresis_held"
    assert records[-1].in_hysteresis_band


def test_immediate_stress_override_and_adjacent_only_recovery() -> None:
    records, _ = _run(("60", "61", "19"))
    assert records[-1].confirmed_state is RegimeState.STRESS
    assert records[-1].transition_status == "immediate_stress_override"
    assert records[-1].required_confirmation_sessions == 1

    records, _ = _run(("10", "11", "80", "80", "80"))
    assert records[1].confirmed_state is RegimeState.STRESS
    assert records[-1].confirmed_state is RegimeState.DEFENSIVE
    assert records[-1].instantaneous_candidate_state is RegimeState.RISK_ON
    assert records[-1].transition_rule_id == "stress_to_defensive"


def test_missing_composite_pauses_bootstrap_and_pending_transition() -> None:
    records, _ = _run(("60", None, "61", "70", None, "71"))
    assert records[1].state_availability == "unavailable"
    assert records[1].pending_target_state is RegimeState.BALANCED
    assert records[1].consecutive_confirmation_sessions == 1
    assert records[2].confirmed_state is RegimeState.BALANCED
    assert records[4].pending_target_state is RegimeState.RISK_ON
    assert records[4].consecutive_confirmation_sessions == 1
    assert records[5].confirmed_state is RegimeState.RISK_ON


def test_gap_duplicate_non_xnys_and_universe_mix_fail_closed() -> None:
    with pytest.raises(MarketRegimeStateError, match="XNYS gap"):
        replay_regime_state_history(
            composites=(_composite(SESSIONS[0], "60"), _composite(SESSIONS[2], "60")),
            expected_sessions=(SESSIONS[0], SESSIONS[2]),
            universe_id=PRIMARY,
            calendar=CALENDAR,
        )
    composite = _composite(SESSIONS[0], "60")
    with pytest.raises(MarketRegimeStateError, match="duplicate"):
        replay_regime_state_history(
            composites=(composite, composite),
            expected_sessions=(SESSIONS[0],),
            universe_id=PRIMARY,
            calendar=CALENDAR,
        )
    saturday = date(2026, 8, 15)
    with pytest.raises(MarketRegimeStateError, match="non-XNYS"):
        replay_regime_state_history(
            composites=(_composite(saturday, "60"),),
            expected_sessions=(saturday,),
            universe_id=PRIMARY,
            calendar=CALENDAR,
        )
    with pytest.raises(MarketRegimeStateError, match="mix Universes"):
        replay_regime_state_history(
            composites=(_composite(SESSIONS[0], "60", SECONDARY),),
            expected_sessions=(SESSIONS[0],),
            universe_id=PRIMARY,
            calendar=CALENDAR,
        )


def test_input_permutation_append_restart_and_future_prefix_equivalence() -> None:
    scores = ("60", "61", "70", "71", "68", "64")
    composites = tuple(_composite(session, score) for session, score in zip(SESSIONS, scores, strict=False))
    sessions = SESSIONS[: len(scores)]
    full, _ = replay_regime_state_history(composites=composites, expected_sessions=sessions, universe_id=PRIMARY, calendar=CALENDAR)
    shuffled, _ = replay_regime_state_history(composites=tuple(reversed(composites)), expected_sessions=sessions, universe_id=PRIMARY, calendar=CALENDAR)
    assert state_history_fingerprint(full) == state_history_fingerprint(shuffled)

    prefix, _ = replay_regime_state_history(composites=composites[:3], expected_sessions=sessions[:3], universe_id=PRIMARY, calendar=CALENDAR)
    suffix, _ = append_regime_state_history(existing_history=prefix, composites=composites[3:], expected_sessions=sessions[3:], universe_id=PRIMARY, calendar=CALENDAR)
    assert tuple(item.logical_fingerprint for item in prefix + suffix) == tuple(item.logical_fingerprint for item in full)
    assert tuple(item.logical_fingerprint for item in full[:-1]) == tuple(
        item.logical_fingerprint
        for item in replay_regime_state_history(composites=composites[:-1], expected_sessions=sessions[:-1], universe_id=PRIMARY, calendar=CALENDAR)[0]
    )


def test_phase1a_history_prefix_keeps_rolling_source_window_without_dropping_state_start() -> None:
    sessions = CALENDAR.sessions_before(date(2026, 8, 26), 28) + (date(2026, 8, 26),)
    panel = _audit_panel(sessions)
    first = _prefix_panel(panel, 20)
    later = _prefix_panel(panel, 28)
    assert first.sessions == sessions[:21]
    assert later.sessions == sessions[-26:]
    assert later.as_of_session == sessions[-1]


@pytest.mark.parametrize("precision", (9, 28, 50))
@pytest.mark.parametrize("rounding", (ROUND_DOWN, ROUND_HALF_EVEN, ROUND_UP))
def test_decimal_context_and_traps_do_not_change_state(precision: int, rounding: str) -> None:
    scores = ("49.9999", "50.0000", "69.9999", "70.0000", "20.0000")
    expected, _ = _run(scores)
    with localcontext() as context:
        context.prec = precision
        context.rounding = rounding
        context.traps[Inexact] = True
        context.traps[Rounded] = True
        actual, _ = _run(scores)
    assert state_history_fingerprint(actual) == state_history_fingerprint(expected)


def test_independent_oracle_compares_every_state_and_explanation_field() -> None:
    scores = ("60", "61", "70", "71", "68", "64")
    sessions = SESSIONS[: len(scores)]
    composites = tuple(_composite(session, score) for session, score in zip(sessions, scores, strict=True))
    records, explanations = replay_regime_state_history(composites=composites, expected_sessions=sessions, universe_id=PRIMARY, calendar=CALENDAR)
    report = compare_with_independent_state_oracle(
        composites=composites,
        expected_sessions=sessions,
        universe_id=PRIMARY,
        records=records,
        explanations=explanations,
        append_full_replay_match=True,
        restart_replay_match=True,
        input_permutation_match=True,
        future_prefix_stable=True,
        calendar=CALENDAR,
    )
    assert report.mismatch_count == 0
    perturbed = records[0].model_copy(update={"transition_rule_id": "wrong"})
    bad = compare_with_independent_state_oracle(
        composites=composites,
        expected_sessions=sessions,
        universe_id=PRIMARY,
        records=(perturbed,) + records[1:],
        explanations=explanations,
        append_full_replay_match=True,
        restart_replay_match=True,
        input_permutation_match=True,
        future_prefix_stable=True,
        calendar=CALENDAR,
    )
    assert bad.mismatch_count > 0
    assert any("transition_rule_id" in item for item in bad.mismatches)


def _audit_panel(sessions) -> MarketRegimeInputPanel:
    source_sessions = tuple(
        MarketRegimeSourceSession(
            session_date=session,
            dataset_path=f"market-data/eod/session={session.isoformat()}",
            record_count=1,
            content_fingerprint=f"{index + 1:064x}",
            parquet_sha256=f"{index + 101:064x}",
            identity_snapshot_date=session,
            identity_snapshot_fingerprint=f"{index + 201:064x}",
        )
        for index, session in enumerate(sessions)
    )
    universe = MarketRegimeUniverseSource(
        PRIMARY,
        "Common Shares",
        True,
        0,
        frozenset({uuid5(NS, "stock")}),
        "b" * 64,
    )
    return MarketRegimeInputPanel(
        as_of_session=sessions[-1],
        calendar_id="XNYS",
        calendar_version="fixture",
        sessions=tuple(sessions),
        source_sessions=source_sessions,
        bars=(),
        universes=(universe,),
        activation_pointer_fingerprint="d" * 64,
        identity_logical_fingerprint="e" * 64,
        eod_content_fingerprint="f" * 64,
        eod_business_key_fingerprint="1" * 64,
        history_source_fingerprint="2" * 64,
    )


def test_state_audit_is_canonical_rereadable_and_non_time_deterministic() -> None:
    scores = ("60", "61", "70", "71")
    sessions = SESSIONS[-len(scores):]
    composites = tuple(_composite(session, score) for session, score in zip(sessions, scores, strict=True))
    records, explanations = replay_regime_state_history(composites=composites, expected_sessions=sessions, universe_id=PRIMARY, calendar=CALENDAR)
    oracle = compare_with_independent_state_oracle(
        composites=composites,
        expected_sessions=sessions,
        universe_id=PRIMARY,
        records=records,
        explanations=explanations,
        append_full_replay_match=True,
        restart_replay_match=True,
        input_permutation_match=True,
        future_prefix_stable=True,
        calendar=CALENDAR,
    )
    phase1a = {
        "logical_content_fingerprint": FROZEN_PHASE1A_AUDIT_FINGERPRINT,
        "composite_fingerprints": [composites[-1].logical_fingerprint],
    }
    panel = _audit_panel(sessions)
    first = Path(tempfile.mkdtemp(prefix="mrom-state-a-", dir="/tmp"))
    second = Path(tempfile.mkdtemp(prefix="mrom-state-b-", dir="/tmp"))
    try:
        manifests = []
        for target, generated in ((first, datetime(2026, 8, 25, tzinfo=UTC)), (second, datetime(2026, 8, 26, tzinfo=UTC))):
            manifests.append(
                write_market_regime_state_audit(
                    output_dir=target,
                    panel=panel,
                    phase1a_audit_manifest=phase1a,
                    histories={PRIMARY: records},
                    explanations={PRIMARY: explanations},
                    oracle_reports=(oracle,),
                    first_calculable_session=sessions[0],
                    generated_at=generated,
                    timings={"phase1a_history_calculation_seconds": "1.000000"},
                    peak_memory_kib=123,
                )
            )
        assert manifests[0]["logical_content_fingerprint"] == manifests[1]["logical_content_fingerprint"]
        for name in STATE_ARTIFACT_FILES:
            assert (first / name).read_bytes() == (second / name).read_bytes()
        assert read_market_regime_state_audit(first)["oracle_mismatch_count"] == 0
    finally:
        shutil.rmtree(first, ignore_errors=True)
        shutil.rmtree(second, ignore_errors=True)


def test_state_output_path_and_parameter_contract_are_fail_closed(tmp_path: Path) -> None:
    assert len(STATE_PARAMETER_FINGERPRINT) == 64
    assert state_parameter_payload()["first_candidate_auto_confirms"] is False
    with pytest.raises(MarketRegimeStateAuditError):
        _validate_tmp_output_dir(Path("/data/state-audit"))
    with pytest.raises(MarketRegimeStateAuditError):
        _validate_tmp_output_dir(Path("/home/hui/projects/trading-intelligence-platform/state-audit"))
    symlink = Path(tempfile.mkdtemp(prefix="mrom-state-link-target-", dir="/tmp") + "-link")
    try:
        symlink.symlink_to(tmp_path, target_is_directory=True)
        with pytest.raises(MarketRegimeStateAuditError):
            _validate_tmp_output_dir(symlink)
    finally:
        symlink.unlink(missing_ok=True)
