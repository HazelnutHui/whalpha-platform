"""Deterministic qualifying-set overlap diagnostics for strategy channels."""

from __future__ import annotations

from collections import Counter
from decimal import Decimal

from tip_api.contracts.analytics.v1.candidate_strategy_channel import (
    CandidateStrategyChannelBatchV1,
    StrategyChannel,
    StrategyChannelStatus,
)
from tip_api.contracts.analytics.v1.candidate_strategy_diagnostics import (
    CandidateStrategyChannelDiagnosticsV1,
    TECHNICAL_CHANNEL_ORDER,
    strategy_diagnostics_fingerprint,
)


QUALIFYING_STATUSES = {
    StrategyChannelStatus.ADVANCE_TO_RESEARCH,
    StrategyChannelStatus.WATCH_FOR_TRIGGER,
}


def build_candidate_strategy_channel_diagnostics(
    batch: CandidateStrategyChannelBatchV1,
) -> CandidateStrategyChannelDiagnosticsV1:
    """Measure set overlap without comparing incomparable channel scores."""

    sets = {
        channel: {
            row.instrument_id
            for row in batch.records
            if row.channel is channel and row.status in QUALIFYING_STATUSES
        }
        for channel in TECHNICAL_CHANNEL_ORDER
    }
    pair_order = (
        (TECHNICAL_CHANNEL_ORDER[0], TECHNICAL_CHANNEL_ORDER[1]),
        (TECHNICAL_CHANNEL_ORDER[0], TECHNICAL_CHANNEL_ORDER[2]),
        (TECHNICAL_CHANNEL_ORDER[1], TECHNICAL_CHANNEL_ORDER[2]),
    )
    pairs = []
    for left, right in pair_order:
        intersection = sets[left] & sets[right]
        union = sets[left] | sets[right]
        pairs.append(
            {
                "left_channel": left.value,
                "right_channel": right.value,
                "left_qualifying_count": len(sets[left]),
                "right_qualifying_count": len(sets[right]),
                "intersection_count": len(intersection),
                "union_count": len(union),
                "left_only_count": len(sets[left] - sets[right]),
                "right_only_count": len(sets[right] - sets[left]),
                "jaccard_overlap": format(
                    (
                        Decimal("0")
                        if not union
                        else Decimal(len(intersection)) / Decimal(len(union))
                    ).quantize(Decimal("0.0001")),
                    "f",
                ),
                "left_subset_of_right": sets[left] <= sets[right],
                "right_subset_of_left": sets[right] <= sets[left],
            }
        )
    union = set().union(*(sets[channel] for channel in TECHNICAL_CHANNEL_ORDER))
    membership_counts = Counter(
        instrument_id
        for channel in TECHNICAL_CHANNEL_ORDER
        for instrument_id in sets[channel]
    )
    body = {
        "schema_version": "1.0",
        "contract_version": "candidate-strategy-channel-diagnostics/1.0",
        "as_of_session": batch.as_of_session.isoformat(),
        "universe_id": batch.universe_id,
        "source_strategy_batch_fingerprint": batch.logical_fingerprint,
        "channel_order": [channel.value for channel in TECHNICAL_CHANNEL_ORDER],
        "qualifying_counts": {
            channel.value: len(sets[channel]) for channel in TECHNICAL_CHANNEL_ORDER
        },
        "pair_overlaps": pairs,
        "all_three_intersection_count": len(
            set.intersection(*(sets[channel] for channel in TECHNICAL_CHANNEL_ORDER))
        ),
        "qualifying_union_count": len(union),
        "exclusive_counts": {
            channel.value: len(
                sets[channel]
                - set().union(
                    *(sets[other] for other in TECHNICAL_CHANNEL_ORDER if other is not channel)
                )
            )
            for channel in TECHNICAL_CHANNEL_ORDER
        },
        "multi_channel_member_count": sum(
            count >= 2 for count in membership_counts.values()
        ),
        "cross_channel_scores_compared": False,
        "outcome_or_performance_claim": False,
    }
    body["logical_fingerprint"] = strategy_diagnostics_fingerprint(body)
    return CandidateStrategyChannelDiagnosticsV1.model_validate(body)
