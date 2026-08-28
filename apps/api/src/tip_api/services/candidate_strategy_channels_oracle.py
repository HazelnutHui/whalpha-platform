"""Independent Oracle for Candidate strategy-channel scores, statuses, and ranks.

This module intentionally does not import the production strategy-channel service.
It repeats the fixed baseline from typed source contracts so a shared helper defect
cannot make the production calculation and its Oracle agree accidentally.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, Decimal

from tip_api.contracts.analytics.v1 import (
    CandidateDataQualityStatus,
    CandidateEntryGeometryBatchV1,
    CandidateExtensionRisk,
    CandidateMetricAvailability,
    CandidateOpportunityStage,
    CandidateStrategyChannelBatchV1,
    CandidateTechnicalSetup,
    EntryGeometryAvailability,
    OpportunityCandidateBatchV1,
    StrategyChannel,
    StrategyChannelStatus,
)
from tip_api.parameters.market_regime.candidate_strategy_preview_v1_0_0 import (
    CHANNEL_GEOMETRY_SCORES,
    CHANNEL_SCORE_WEIGHTS,
    STRATEGY_CHANNEL_ORDER,
    TREND_CONTINUATION_ADVANCE_COMPONENT_FLOOR,
    TREND_CONTINUATION_WATCH_BASE_FLOOR,
    TREND_CONTINUATION_WATCH_COMPONENT_FLOOR,
)


SCORE_QUANTUM = Decimal("0.0001")
TECHNICAL_CHANNELS = frozenset(
    {
        StrategyChannel.MOMENTUM_BREAKOUT,
        StrategyChannel.STRONG_STOCK_PULLBACK,
        StrategyChannel.TREND_CONTINUATION,
    }
)


@dataclass(frozen=True, slots=True)
class CandidateStrategyChannelOracleComparisonV1:
    record_count: int
    mismatch_count: int
    mismatches: tuple[str, ...]
    input_permutation_match: bool
    production_calculator_imported: bool
    oracle_fingerprint: str


def compare_with_independent_strategy_channel_oracle(
    *,
    candidate_batch: OpportunityCandidateBatchV1,
    entry_geometry_batch: CandidateEntryGeometryBatchV1,
    actual: CandidateStrategyChannelBatchV1,
) -> CandidateStrategyChannelOracleComparisonV1:
    """Compare production output with an independently ordered fixed-baseline result."""

    expected = _expected_rows(candidate_batch, entry_geometry_batch)
    actual_rows = {
        (str(row.instrument_id), row.channel.value): {
            "status": row.status.value,
            "channel_score": row.channel_score,
            "within_channel_rank": row.within_channel_rank,
        }
        for row in actual.records
    }
    mismatches: list[str] = []
    if set(actual_rows) != set(expected):
        mismatches.append("record_stable_id_channel_set_mismatch")
    for key in sorted(set(actual_rows) & set(expected)):
        for field in ("status", "channel_score", "within_channel_rank"):
            if actual_rows[key][field] != expected[key][field]:
                mismatches.append(f"{key[0]}:{key[1]}:{field}")
    if actual.source_candidate_batch_fingerprint != candidate_batch.logical_fingerprint:
        mismatches.append("source_candidate_batch_fingerprint_mismatch")
    if actual.source_entry_geometry_batch_fingerprint != entry_geometry_batch.logical_fingerprint:
        mismatches.append("source_entry_geometry_batch_fingerprint_mismatch")

    permuted_expected = _expected_rows(
        candidate_batch.model_copy(
            update={"candidates": tuple(reversed(candidate_batch.candidates))}
        ),
        entry_geometry_batch.model_copy(
            update={"records": tuple(reversed(entry_geometry_batch.records))}
        ),
    )
    canonical_expected = _canonical_rows(expected)
    canonical_permuted = _canonical_rows(permuted_expected)
    permutation_match = _fingerprint(canonical_expected) == _fingerprint(
        canonical_permuted
    )
    if not permutation_match:
        mismatches.append("input_permutation_changed_oracle_output")
    fingerprint = _fingerprint(
        {
            "rows": canonical_expected,
            "input_permutation_match": permutation_match,
            "production_calculator_imported": False,
        }
    )
    return CandidateStrategyChannelOracleComparisonV1(
        record_count=len(expected),
        mismatch_count=len(mismatches),
        mismatches=tuple(mismatches),
        input_permutation_match=permutation_match,
        production_calculator_imported=False,
        oracle_fingerprint=fingerprint,
    )


def _expected_rows(candidate_batch, entry_geometry_batch):
    if (
        candidate_batch.as_of_session != entry_geometry_batch.as_of_session
        or candidate_batch.universe_id != entry_geometry_batch.universe_id
        or entry_geometry_batch.source_candidate_batch_fingerprint
        != candidate_batch.logical_fingerprint
    ):
        raise ValueError("strategy Oracle source binding differs")
    candidates = {row.instrument_id: row for row in candidate_batch.candidates}
    entries = {row.instrument_id: row for row in entry_geometry_batch.records}
    if (
        len(candidates) != len(candidate_batch.candidates)
        or len(entries) != len(entry_geometry_batch.records)
        or set(candidates) != set(entries)
    ):
        raise ValueError("strategy Oracle requires exact unique source coverage")

    rows: dict[tuple[str, str], dict[str, object]] = {}
    for instrument_id in sorted(candidates, key=str):
        candidate, entry = candidates[instrument_id], entries[instrument_id]
        if (
            entry.source_candidate_fingerprint != candidate.logical_fingerprint
            or entry.ticker != candidate.ticker
            or entry.security_type != candidate.security_type
            or entry.candidate_base_score != candidate.base_score
        ):
            raise ValueError("strategy Oracle source record binding differs")
        components = {item.component_id: item for item in candidate.components}
        for channel in StrategyChannel:
            status, score = _row(candidate, entry, components, channel)
            rows[(str(instrument_id), channel.value)] = {
                "status": status.value,
                "channel_score": score,
                "within_channel_rank": None,
                "ticker": candidate.ticker,
            }

    priority = {
        StrategyChannelStatus.ADVANCE_TO_RESEARCH.value: 0,
        StrategyChannelStatus.WATCH_FOR_TRIGGER.value: 1,
    }
    for channel in StrategyChannel:
        rankable = [
            (key, row)
            for key, row in rows.items()
            if key[1] == channel.value and row["status"] in priority
        ]
        rankable.sort(
            key=lambda item: (
                priority[str(item[1]["status"])],
                -Decimal(str(item[1]["channel_score"])),
                str(item[1]["ticker"]),
                item[0][0],
            )
        )
        for rank, (_, row) in enumerate(rankable, start=1):
            row["within_channel_rank"] = rank
    return {
        key: {name: value for name, value in row.items() if name != "ticker"}
        for key, row in sorted(rows.items())
    }


def _row(candidate, entry, components, channel):
    if channel not in TECHNICAL_CHANNELS:
        return StrategyChannelStatus.UNAVAILABLE, None
    weights = CHANNEL_SCORE_WEIGHTS[channel.value]
    missing = any(
        component_id != "entry_geometry"
        and (
            component_id not in components
            or components[component_id].availability
            is not CandidateMetricAvailability.AVAILABLE
            or components[component_id].score is None
        )
        for component_id in weights
    )
    if (
        missing
        or candidate.data_quality_status
        in {CandidateDataQualityStatus.QUARANTINED, CandidateDataQualityStatus.FAILED}
        or entry.metrics.availability is EntryGeometryAvailability.UNAVAILABLE
        or entry.technical_setup is CandidateTechnicalSetup.UNAVAILABLE
    ):
        return StrategyChannelStatus.UNAVAILABLE, None

    total = Decimal("0")
    for component_id, weight in weights.items():
        value = (
            Decimal(CHANNEL_GEOMETRY_SCORES[channel.value][entry.technical_setup.value])
            if component_id == "entry_geometry"
            else Decimal(components[component_id].score)
        )
        total += Decimal(weight) * value
    score = format(total.quantize(SCORE_QUANTUM, rounding=ROUND_HALF_EVEN), "f")
    return _status(candidate, entry, components, channel), score


def _status(candidate, entry, components, channel):
    if entry.candidate_stage is CandidateOpportunityStage.INVALIDATED:
        return StrategyChannelStatus.DEPRIORITIZED
    setup = entry.technical_setup
    if channel is StrategyChannel.MOMENTUM_BREAKOUT:
        if setup is CandidateTechnicalSetup.BREAKOUT_CONFIRMED:
            return StrategyChannelStatus.ADVANCE_TO_RESEARCH
        if setup in {
            CandidateTechnicalSetup.BREAKOUT_WATCH,
            CandidateTechnicalSetup.STRONG_BUT_EXTENDED,
        }:
            return StrategyChannelStatus.WATCH_FOR_TRIGGER
        return StrategyChannelStatus.DEPRIORITIZED
    if channel is StrategyChannel.STRONG_STOCK_PULLBACK:
        if setup is CandidateTechnicalSetup.PULLBACK:
            return StrategyChannelStatus.ADVANCE_TO_RESEARCH
        if setup is CandidateTechnicalSetup.STRONG_BUT_EXTENDED:
            return StrategyChannelStatus.WATCH_FOR_TRIGGER
        return StrategyChannelStatus.DEPRIORITIZED

    relative = Decimal(components["stock_relative_strength"].score)
    trend = Decimal(components["trend_quality"].score)
    base = Decimal(candidate.base_score) if candidate.base_score is not None else Decimal("0")
    non_high_extension = entry.extension_risk in {
        CandidateExtensionRisk.LOW,
        CandidateExtensionRisk.MODERATE,
    }
    if (
        entry.candidate_stage
        in {CandidateOpportunityStage.PREPARE, CandidateOpportunityStage.ENTER}
        and non_high_extension
        and relative >= Decimal(TREND_CONTINUATION_ADVANCE_COMPONENT_FLOOR)
        and trend >= Decimal(TREND_CONTINUATION_ADVANCE_COMPONENT_FLOOR)
    ):
        return StrategyChannelStatus.ADVANCE_TO_RESEARCH
    if (
        base >= Decimal(TREND_CONTINUATION_WATCH_BASE_FLOOR)
        and relative >= Decimal(TREND_CONTINUATION_WATCH_COMPONENT_FLOOR)
        and trend >= Decimal(TREND_CONTINUATION_WATCH_COMPONENT_FLOOR)
    ):
        return StrategyChannelStatus.WATCH_FOR_TRIGGER
    return StrategyChannelStatus.DEPRIORITIZED


def _fingerprint(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _canonical_rows(rows):
    return [
        {"instrument_id": key[0], "channel": key[1], **rows[key]}
        for key in sorted(rows)
    ]
