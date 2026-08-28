from __future__ import annotations

from collections import defaultdict

import pytest

from tip_api.contracts.analytics.v1 import (
    CandidateStrategyChannelBatchV1,
    StrategyChannel,
    StrategyChannelStatus,
)
from tip_api.services.candidate_entry_geometry import (
    calculate_candidate_entry_geometry,
)
from tip_api.services.candidate_strategy_channels import (
    CandidateStrategyChannelCalculationError,
    build_candidate_strategy_channel_consumer,
    calculate_candidate_strategy_channels,
)
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
    return candidate_batch, entry


def test_strategy_preview_is_explicit_explainable_and_channel_local() -> None:
    candidates, entry = _inputs()

    batch = calculate_candidate_strategy_channels(
        candidate_batch=candidates,
        entry_geometry_batch=entry,
    )

    assert isinstance(batch, CandidateStrategyChannelBatchV1)
    assert len(batch.records) == len(candidates.candidates) * 6
    grouped = defaultdict(list)
    for row in batch.records:
        grouped[row.instrument_id].append(row)
        assert row.first_rejection_code
        assert row.required_manual_check_codes
        assert row.market_fit.value == "unavailable"
        assert row.market_fit_separate_from_channel_score is True
    assert all(
        tuple(row.channel for row in rows) == tuple(StrategyChannel)
        for rows in grouped.values()
    )

    technical = [
        row
        for row in batch.records
        if row.channel
        in {
            StrategyChannel.MOMENTUM_BREAKOUT,
            StrategyChannel.STRONG_STOCK_PULLBACK,
            StrategyChannel.TREND_CONTINUATION,
        }
    ]
    assessable = [
        row for row in technical if row.status is not StrategyChannelStatus.UNAVAILABLE
    ]
    assert assessable
    assert all(row.channel_score is not None for row in assessable)
    assert all(
        row.channel_score is None
        for row in technical
        if row.status is StrategyChannelStatus.UNAVAILABLE
    )
    assert all(row.evidence for row in technical)
    assert "cross_channel_score_comparison_prohibited" in batch.warnings


def test_unsupported_channels_remain_explicitly_unavailable() -> None:
    candidates, entry = _inputs()
    batch = calculate_candidate_strategy_channels(
        candidate_batch=candidates,
        entry_geometry_batch=entry,
    )

    unavailable_channels = {
        StrategyChannel.TECHNICAL_REVERSAL,
        StrategyChannel.FUNDAMENTAL_VALUE_REVERSAL,
        StrategyChannel.DEFENSIVE_ROTATION,
    }
    rows = [row for row in batch.records if row.channel in unavailable_channels]
    assert rows
    assert all(row.status is StrategyChannelStatus.UNAVAILABLE for row in rows)
    assert all(row.channel_score is None and row.within_channel_rank is None for row in rows)
    assert all(row.missing_required_evidence_codes for row in rows)
    assert all(
        evidence.availability.value == "unavailable"
        for row in rows
        for evidence in row.evidence
    )


def test_rankable_results_are_contiguous_only_inside_each_channel() -> None:
    candidates, entry = _inputs()
    batch = calculate_candidate_strategy_channels(
        candidate_batch=candidates,
        entry_geometry_batch=entry,
    )

    for channel in StrategyChannel:
        ranks = sorted(
            row.within_channel_rank
            for row in batch.records
            if row.channel is channel and row.within_channel_rank is not None
        )
        assert ranks == list(range(1, len(ranks) + 1))


def test_bounded_consumer_keeps_counts_but_displays_at_most_eight() -> None:
    candidates, entry = _inputs()
    batch = calculate_candidate_strategy_channels(
        candidate_batch=candidates,
        entry_geometry_batch=entry,
    )

    consumer = build_candidate_strategy_channel_consumer(batch)

    assert consumer.source_batch_logical_fingerprint == batch.logical_fingerprint
    assert tuple(view.channel for view in consumer.channels) == tuple(StrategyChannel)
    for view in consumer.channels:
        assert view.status_counts == batch.status_counts[view.channel]
        assert len(view.displayed_records) <= 8
        assert tuple(row.within_channel_rank for row in view.displayed_records) == tuple(
            range(1, len(view.displayed_records) + 1)
        )
    unavailable = {
        view.channel: view
        for view in consumer.channels
        if view.channel
        in {
            StrategyChannel.TECHNICAL_REVERSAL,
            StrategyChannel.FUNDAMENTAL_VALUE_REVERSAL,
            StrategyChannel.DEFENSIVE_ROTATION,
        }
    }
    assert all(view.qualifying_count == 0 for view in unavailable.values())
    assert all(not view.displayed_records for view in unavailable.values())


def test_strategy_preview_is_input_permutation_invariant() -> None:
    candidates, entry = _inputs()
    expected = calculate_candidate_strategy_channels(
        candidate_batch=candidates,
        entry_geometry_batch=entry,
    )
    permuted_candidates = candidates.model_copy(
        update={"candidates": tuple(reversed(candidates.candidates))}
    )
    permuted_entry = entry.model_copy(
        update={"records": tuple(reversed(entry.records))}
    )

    actual = calculate_candidate_strategy_channels(
        candidate_batch=permuted_candidates,
        entry_geometry_batch=permuted_entry,
    )

    assert actual == expected


def test_strategy_preview_rejects_cross_batch_entry_geometry() -> None:
    candidates, entry = _inputs()
    mismatched = entry.model_copy(
        update={"source_candidate_batch_fingerprint": "f" * 64}
    )

    with pytest.raises(CandidateStrategyChannelCalculationError, match="not bound"):
        calculate_candidate_strategy_channels(
            candidate_batch=candidates,
            entry_geometry_batch=mismatched,
        )
