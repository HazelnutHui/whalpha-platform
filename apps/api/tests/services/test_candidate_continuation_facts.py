from __future__ import annotations

import inspect
from dataclasses import replace
from decimal import Decimal

import pytest

from tip_api.contracts.analytics.v1 import ContinuationFactAvailability
from tip_api.services.candidate_continuation_facts import (
    CandidateContinuationFactsCalculationError,
    calculate_candidate_continuation_facts,
)
from tip_api.services.candidate_continuation_facts_oracle import (
    compare_with_independent_continuation_facts_oracle,
)
from tip_api.services.candidate_entry_geometry import calculate_candidate_entry_geometry
from tests.services import test_opportunity_candidate_audit as fixture


def _inputs():
    panel = fixture._panel()
    batches, _, _ = fixture._actuals(panel)
    candidate_batch = batches[0]
    states = []
    for candidate in candidate_batch.candidates:
        single = candidate_batch.model_copy(update={"candidates": (candidate,)})
        states.extend(fixture._state_case(panel, single).actual_records)
    entry = calculate_candidate_entry_geometry(
        panel=panel,
        candidate_batch=candidate_batch,
        state_records=tuple(states),
    )
    return panel, candidate_batch, entry


def test_continuation_facts_are_descriptive_source_bound_and_complete() -> None:
    panel, candidates, entry = _inputs()

    result = calculate_candidate_continuation_facts(
        panel=panel,
        candidate_batch=candidates,
        entry_geometry_batch=entry,
    )

    assert result.assessed_count == len(candidates.candidates)
    assert result.unavailable_count == 0
    assert result.strategy_score_input is False
    assert result.outcome_or_performance_claim is False
    assert result.source_candidate_batch_fingerprint == candidates.logical_fingerprint
    assert result.source_entry_geometry_batch_fingerprint == entry.logical_fingerprint
    assert result.source_history_fingerprint == panel.history_source_fingerprint
    for row in result.records:
        metrics = row.metrics
        assert metrics.availability is ContinuationFactAvailability.AVAILABLE
        assert Decimal("-1") <= Decimal(metrics.information_discreteness_10) <= Decimal("1")
        assert Decimal("0") <= Decimal(metrics.return_path_efficiency_10) <= Decimal("1")
        assert Decimal("0") <= Decimal(metrics.largest_absolute_return_share_10) <= Decimal("1")
        assert Decimal(metrics.atr_5_to_14) > 0
        assert Decimal(metrics.close_drawdown_from_high_20_atr) >= 0


def test_continuation_facts_are_input_permutation_invariant() -> None:
    panel, candidates, entry = _inputs()
    expected = calculate_candidate_continuation_facts(
        panel=panel,
        candidate_batch=candidates,
        entry_geometry_batch=entry,
    )

    actual = calculate_candidate_continuation_facts(
        panel=replace(panel, bars=tuple(reversed(panel.bars))),
        candidate_batch=candidates.model_copy(
            update={"candidates": tuple(reversed(candidates.candidates))}
        ),
        entry_geometry_batch=entry.model_copy(
            update={"records": tuple(reversed(entry.records))}
        ),
    )

    assert actual == expected


def test_continuation_facts_fail_closed_for_missing_history() -> None:
    panel, candidates, entry = _inputs()
    target = candidates.candidates[0].instrument_id
    missing_session = panel.sessions[-1]
    partial_panel = replace(
        panel,
        bars=tuple(
            row
            for row in panel.bars
            if not (row.instrument_id == target and row.session_date == missing_session)
        ),
    )

    result = calculate_candidate_continuation_facts(
        panel=partial_panel,
        candidate_batch=candidates,
        entry_geometry_batch=entry,
    )

    row = next(item for item in result.records if item.instrument_id == target)
    assert row.metrics.availability is ContinuationFactAvailability.UNAVAILABLE
    assert row.metrics.missing_reason_codes == (
        "missing_contiguous_twenty_session_history",
    )


def test_continuation_facts_reject_cross_batch_entry_lineage() -> None:
    panel, candidates, entry = _inputs()

    with pytest.raises(CandidateContinuationFactsCalculationError, match="lineage"):
        calculate_candidate_continuation_facts(
            panel=panel,
            candidate_batch=candidates,
            entry_geometry_batch=entry.model_copy(
                update={"source_candidate_batch_fingerprint": "f" * 64}
            ),
        )


def test_continuation_facts_reject_universe_custody_drift() -> None:
    panel, candidates, entry = _inputs()
    universe = panel.select_universe(candidates.universe_id)
    drifted = replace(
        panel,
        universes=tuple(
            replace(item, membership_fingerprint="f" * 64)
            if item.universe_id == universe.universe_id
            else item
            for item in panel.universes
        ),
    )

    with pytest.raises(CandidateContinuationFactsCalculationError, match="Universe custody"):
        calculate_candidate_continuation_facts(
            panel=drifted,
            candidate_batch=candidates,
            entry_geometry_batch=entry,
        )


def test_independent_continuation_oracle_reconciles_every_metric() -> None:
    panel, candidates, entry = _inputs()
    actual = calculate_candidate_continuation_facts(
        panel=panel,
        candidate_batch=candidates,
        entry_geometry_batch=entry,
    )

    comparison = compare_with_independent_continuation_facts_oracle(
        panel=panel,
        candidate_batch=candidates,
        entry_geometry_batch=entry,
        actual=actual,
    )

    assert comparison.record_count == len(candidates.candidates)
    assert comparison.mismatch_count == 0
    assert not comparison.mismatches
    assert comparison.input_permutation_match is True
    assert comparison.production_calculator_imported is False
    source = inspect.getsource(
        __import__(
            "tip_api.services.candidate_continuation_facts_oracle",
            fromlist=["dummy"],
        )
    )
    assert "from tip_api.services.candidate_continuation_facts import" not in source


def test_independent_continuation_oracle_rejects_parameter_drift() -> None:
    panel, candidates, entry = _inputs()
    actual = calculate_candidate_continuation_facts(
        panel=panel,
        candidate_batch=candidates,
        entry_geometry_batch=entry,
    ).model_copy(update={"parameter_fingerprint": "f" * 64})

    comparison = compare_with_independent_continuation_facts_oracle(
        panel=panel,
        candidate_batch=candidates,
        entry_geometry_batch=entry,
        actual=actual,
    )

    assert comparison.mismatches == ("parameter_fingerprint_mismatch",)
