from __future__ import annotations

import pytest

from tip_api.contracts.analytics.v1 import (
    CandidateStrategyChannelDiagnosticsV1,
    StrategyChannel,
    StrategyChannelStatus,
)
from tip_api.services.candidate_strategy_channel_diagnostics import (
    build_candidate_strategy_channel_diagnostics,
)
from tip_api.services.candidate_strategy_channels import (
    calculate_candidate_strategy_channels,
)
from tests.services.test_candidate_strategy_channels import _inputs


def test_strategy_diagnostics_reconcile_full_qualifying_sets_without_scores() -> None:
    candidates, entry = _inputs()
    batch = calculate_candidate_strategy_channels(
        candidate_batch=candidates,
        entry_geometry_batch=entry,
    )

    result = build_candidate_strategy_channel_diagnostics(batch)

    qualifying = {
        channel: {
            row.instrument_id
            for row in batch.records
            if row.channel is channel
            and row.status
            in {
                StrategyChannelStatus.ADVANCE_TO_RESEARCH,
                StrategyChannelStatus.WATCH_FOR_TRIGGER,
            }
        }
        for channel in result.channel_order
    }
    assert result.qualifying_counts == {
        channel: len(values) for channel, values in qualifying.items()
    }
    assert result.qualifying_union_count == len(
        set().union(*(qualifying[channel] for channel in result.channel_order))
    )
    assert result.all_three_intersection_count == len(
        set.intersection(*(qualifying[channel] for channel in result.channel_order))
    )
    assert result.cross_channel_scores_compared is False
    assert result.outcome_or_performance_claim is False

    for pair in result.pair_overlaps:
        left = qualifying[pair.left_channel]
        right = qualifying[pair.right_channel]
        assert pair.intersection_count == len(left & right)
        assert pair.left_subset_of_right is (left <= right)
        assert pair.right_subset_of_left is (right <= left)


def test_strategy_diagnostics_are_deterministic() -> None:
    candidates, entry = _inputs()
    batch = calculate_candidate_strategy_channels(
        candidate_batch=candidates,
        entry_geometry_batch=entry,
    )

    first = build_candidate_strategy_channel_diagnostics(batch)
    second = build_candidate_strategy_channel_diagnostics(batch)

    assert first == second
    assert len(first.logical_fingerprint) == 64


def test_strategy_diagnostics_reject_internally_inconsistent_set_totals() -> None:
    candidates, entry = _inputs()
    batch = calculate_candidate_strategy_channels(
        candidate_batch=candidates,
        entry_geometry_batch=entry,
    )
    result = build_candidate_strategy_channel_diagnostics(batch)
    payload = result.model_dump(mode="json")
    payload["qualifying_union_count"] += 1

    with pytest.raises(ValueError, match="set identities do not reconcile"):
        CandidateStrategyChannelDiagnosticsV1.model_validate(payload)
