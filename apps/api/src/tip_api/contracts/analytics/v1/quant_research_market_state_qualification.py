"""Frozen outcome-blind qualification for the reusable market-state panel."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import date
from decimal import Context, Decimal, ROUND_HALF_EVEN, localcontext
from enum import StrEnum
from functools import lru_cache
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .quant_research_market_state_vector import (
    QUANT_RESEARCH_MARKET_STATE_METRIC_ORDER,
    QuantResearchMarketStateAvailability,
    QuantResearchMarketStateMetricValueV1,
    quant_research_market_state_vector_definition_v1,
)
from .quant_research_reusable_artifacts import (
    QuantResearchArtifactKind,
    QuantResearchReusableArtifactDescriptorV1,
)


QUANT_RESEARCH_MARKET_STATE_QUALIFICATION_PROTOCOL_CONTRACT_VERSION = (
    "quant-research-market-state-qualification-protocol/1.0"
)
QUANT_RESEARCH_MARKET_STATE_QUALIFICATION_PROTOCOL_VERSION = (
    "whalpha.quant-research.market-state-qualification/1.0.0"
)
QUANT_RESEARCH_MARKET_STATE_QUALIFICATION_REPORT_CONTRACT_VERSION = (
    "quant-research-market-state-qualification-report/1.0"
)
QUANT_RESEARCH_MARKET_STATE_EXPECTED_SESSION_COUNT = 287
QUANT_RESEARCH_MARKET_STATE_FIRST_HALF_SESSION_COUNT = 143
QUANT_RESEARCH_MARKET_STATE_FIRST_SESSION = date(2025, 6, 23)
QUANT_RESEARCH_MARKET_STATE_LAST_SESSION = date(2026, 8, 12)
QUANT_RESEARCH_MARKET_STATE_SESSION_PARTITION_FINGERPRINT = (
    "1d2151281b6ed45c352294529d544d58bb5e41c19798a73a0ef5d72fc54c1eff"
)
QUANT_RESEARCH_MARKET_STATE_MEMBERSHIP_METHODOLOGY = (
    "provider-form-complete-base-point-in-time-v3"
)
QUANT_RESEARCH_MARKET_STATE_REQUIRED_LIMITATIONS = (
    "close_only_price_state_not_total_return",
    "daily_bars_do_not_observe_intraday_state",
    "historical_classification_unavailable",
    "reconstructed_membership_not_as_operated",
)
QUANT_RESEARCH_MARKET_STATE_SOURCE_CONTRACT_VERSIONS = tuple(
    sorted(
        {
            "quant-research-historical-split-extension/1.0",
            "quant-research-market-state-vector/1.1",
            "reconciled-eod-price-bar-edition-session/1.2",
            "strong-leader-pullback-development-coverage-census/1.0",
            "universe-membership-partition-manifest/1.1",
        }
    )
)
DECIMAL_QUANTUM = Decimal("0.0000000001")


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class QuantResearchMarketStateQualificationStatus(StrEnum):
    READY_FOR_CAMPAIGN_PROTOCOL_DESIGN = "ready_for_campaign_protocol_design"
    REJECTED_DATA_OR_IMPLEMENTATION = "rejected_data_or_implementation"


class QuantResearchMarketStateMetricGateV1(FrozenModel):
    metric_id: str
    minimum_distinct_values: int = Field(ge=2, le=287)


class QuantResearchMarketStateQualificationProtocolV1(FrozenModel):
    schema_version: Literal["1.0"] = "1.0"
    contract_version: Literal[
        QUANT_RESEARCH_MARKET_STATE_QUALIFICATION_PROTOCOL_CONTRACT_VERSION
    ] = QUANT_RESEARCH_MARKET_STATE_QUALIFICATION_PROTOCOL_CONTRACT_VERSION
    protocol_version: Literal[
        QUANT_RESEARCH_MARKET_STATE_QUALIFICATION_PROTOCOL_VERSION
    ] = QUANT_RESEARCH_MARKET_STATE_QUALIFICATION_PROTOCOL_VERSION
    registered_date: Literal[date(2026, 9, 16)] = date(2026, 9, 16)
    vector_definition_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    expected_signal_session_count: Literal[287] = 287
    first_signal_session: Literal[date(2025, 6, 23)] = date(2025, 6, 23)
    last_signal_session: Literal[date(2026, 8, 12)] = date(2026, 8, 12)
    calendar_id: Literal["XNYS"] = "XNYS"
    calendar_version: Literal["4.13.2"] = "4.13.2"
    expected_session_partition_fingerprint: Literal[
        QUANT_RESEARCH_MARKET_STATE_SESSION_PARTITION_FINGERPRINT
    ] = QUANT_RESEARCH_MARKET_STATE_SESSION_PARTITION_FINGERPRINT
    membership_methodology: Literal[
        QUANT_RESEARCH_MARKET_STATE_MEMBERSHIP_METHODOLOGY
    ] = QUANT_RESEARCH_MARKET_STATE_MEMBERSHIP_METHODOLOGY
    source_window_sessions: Literal[21] = 21
    benchmark_required_session_count: Literal[287] = 287
    reconstructed_minimum_session_count: Literal[250] = 250
    reconstructed_minimum_first_half_session_count: Literal[120] = 120
    reconstructed_minimum_second_half_session_count: Literal[120] = 120
    minimum_median_crossing_count: Literal[4] = 4
    maximum_longest_same_side_run: Literal[100] = 100
    metric_gates: tuple[QuantResearchMarketStateMetricGateV1, ...] = Field(
        min_length=10,
        max_length=10,
    )
    distribution_quantiles: tuple[
        Literal["p05"],
        Literal["p25"],
        Literal["p50"],
        Literal["p75"],
        Literal["p95"],
    ] = ("p05", "p25", "p50", "p75", "p95")
    reconstructed_membership_not_as_operated: Literal[True] = True
    full_panel_quantiles_may_define_historical_state_thresholds: Literal[False] = (
        False
    )
    thresholds_select_data_quality_not_market_states: Literal[True] = True
    state_thresholds_selected: Literal[False] = False
    interactions_registered: Literal[False] = False
    campaign_three_registered: Literal[False] = False
    contains_forward_outcomes: Literal[False] = False
    development_outcome_read_authorized: Literal[False] = False
    canonical_data_write_authorized: Literal[False] = False
    production_write_authorized: Literal[False] = False
    logical_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def protocol_reconciles(
        self,
    ) -> "QuantResearchMarketStateQualificationProtocolV1":
        if (
            self.vector_definition_fingerprint
            != quant_research_market_state_vector_definition_v1().logical_fingerprint
            or self.metric_gates != _metric_gates()
            or qualification_fingerprint(self) != self.logical_fingerprint
        ):
            raise ValueError("market-state qualification protocol differs")
        return self


class QuantResearchMarketStateReasonCountV1(FrozenModel):
    reason_code: str = Field(pattern=r"^[a-z0-9][a-z0-9_]*$")
    count: int = Field(ge=1)


class QuantResearchMarketStateCoverageV1(FrozenModel):
    metric_id: str
    expected_session_count: Literal[287] = 287
    available_session_count: int = Field(ge=0, le=287)
    unavailable_session_count: int = Field(ge=0, le=287)
    first_half_available_session_count: int = Field(ge=0, le=143)
    second_half_available_session_count: int = Field(ge=0, le=144)
    availability_rate: str
    unavailable_reason_counts: tuple[QuantResearchMarketStateReasonCountV1, ...]


class QuantResearchMarketStateDistributionV1(FrozenModel):
    metric_id: str
    observation_count: int = Field(ge=0, le=287)
    distinct_value_count: int = Field(ge=0, le=287)
    first_half_distinct_value_count: int = Field(ge=0, le=143)
    second_half_distinct_value_count: int = Field(ge=0, le=144)
    minimum: str | None = None
    p05: str | None = None
    p25: str | None = None
    median: str | None = None
    p75: str | None = None
    p95: str | None = None
    maximum: str | None = None


class QuantResearchMarketStateTemporalDiagnosticV1(FrozenModel):
    metric_id: str
    lag_one_pair_count: int = Field(ge=0, le=286)
    lag_one_autocorrelation: str | None = None
    median_crossing_count: int = Field(ge=0, le=286)
    same_side_episode_count: int = Field(ge=0, le=287)
    longest_same_side_run: int = Field(ge=0, le=287)


class QuantResearchMarketStatePairCorrelationV1(FrozenModel):
    left_metric_id: str
    right_metric_id: str
    observation_count: int = Field(ge=0, le=287)
    pearson_correlation: str | None = None


class QuantResearchMarketStateBenchmarkIdentityV1(FrozenModel):
    ticker: Literal["SPY", "QQQ", "IWM", "DIA"]
    instrument_id: UUID


class QuantResearchMarketStateSessionV1(FrozenModel):
    as_of_session: date
    benchmark_identities: tuple[
        QuantResearchMarketStateBenchmarkIdentityV1, ...
    ] = Field(min_length=4, max_length=4)
    membership_methodology: Literal[
        QUANT_RESEARCH_MARKET_STATE_MEMBERSHIP_METHODOLOGY
    ] = QUANT_RESEARCH_MARKET_STATE_MEMBERSHIP_METHODOLOGY
    membership_logical_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    membership_manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    declared_member_ids_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    declared_member_count: int = Field(ge=0)
    complete_member_count: int = Field(ge=0)
    metrics: tuple[QuantResearchMarketStateMetricValueV1, ...] = Field(
        min_length=10,
        max_length=10,
    )

    @model_validator(mode="after")
    def session_reconciles(self) -> "QuantResearchMarketStateSessionV1":
        benchmark_expected = (21, 20, 21, 21, 21, 21)
        if (
            self.complete_member_count > self.declared_member_count
            or tuple(item.ticker for item in self.benchmark_identities)
            != ("SPY", "QQQ", "IWM", "DIA")
            or len({item.instrument_id for item in self.benchmark_identities}) != 4
            or tuple(item.metric_id for item in self.metrics)
            != QUANT_RESEARCH_MARKET_STATE_METRIC_ORDER
            or any(
                item.expected_observations != expected
                or (
                    item.availability
                    is QuantResearchMarketStateAvailability.AVAILABLE
                    and item.actual_observations != expected
                )
                for item, expected in zip(self.metrics[:6], benchmark_expected)
            )
            or any(
                item.expected_observations != max(self.declared_member_count, 1)
                or item.actual_observations != self.complete_member_count
                for item in self.metrics[6:]
            )
        ):
            raise ValueError("market-state session differs")
        return self


class QuantResearchMarketStateQualificationReportV1(FrozenModel):
    schema_version: Literal["1.0"] = "1.0"
    contract_version: Literal[
        QUANT_RESEARCH_MARKET_STATE_QUALIFICATION_REPORT_CONTRACT_VERSION
    ] = QUANT_RESEARCH_MARKET_STATE_QUALIFICATION_REPORT_CONTRACT_VERSION
    protocol_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    vector_definition_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_revision: str = Field(pattern=r"^[0-9a-f]{40}$")
    source_eod_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_membership_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_action_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_adjustment_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_census_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_population_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    calculation_code_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    session_partition_fingerprint: Literal[
        QUANT_RESEARCH_MARKET_STATE_SESSION_PARTITION_FINGERPRINT
    ] = QUANT_RESEARCH_MARKET_STATE_SESSION_PARTITION_FINGERPRINT
    artifact: QuantResearchReusableArtifactDescriptorV1
    first_session: date
    last_session: date
    signal_session_count: Literal[287] = 287
    coverage: tuple[QuantResearchMarketStateCoverageV1, ...] = Field(
        min_length=10,
        max_length=10,
    )
    distributions: tuple[QuantResearchMarketStateDistributionV1, ...] = Field(
        min_length=10,
        max_length=10,
    )
    temporal_diagnostics: tuple[
        QuantResearchMarketStateTemporalDiagnosticV1, ...
    ] = Field(min_length=10, max_length=10)
    pair_correlations: tuple[QuantResearchMarketStatePairCorrelationV1, ...] = Field(
        min_length=45,
        max_length=45,
    )
    sessions: tuple[QuantResearchMarketStateSessionV1, ...] = Field(
        min_length=287,
        max_length=287,
    )
    status: QuantResearchMarketStateQualificationStatus
    reconstructed_joint_available_session_count: int = Field(ge=0, le=287)
    reconstructed_joint_first_half_session_count: int = Field(ge=0, le=143)
    reconstructed_joint_second_half_session_count: int = Field(ge=0, le=144)
    limitation_codes: tuple[
        Literal[
            "close_only_price_state_not_total_return",
            "daily_bars_do_not_observe_intraday_state",
            "historical_classification_unavailable",
            "reconstructed_membership_not_as_operated",
        ],
        ...,
    ]
    contains_forward_outcomes: Literal[False] = False
    contains_performance_metrics: Literal[False] = False
    state_thresholds_selected: Literal[False] = False
    interactions_registered: Literal[False] = False
    campaign_three_registered: Literal[False] = False
    development_outcome_read_count: Literal[0] = 0
    external_request_count: Literal[0] = 0
    canonical_data_write_count: Literal[0] = 0
    production_write_count: Literal[0] = 0
    logical_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def report_reconciles(self) -> "QuantResearchMarketStateQualificationReportV1":
        protocol = quant_research_market_state_qualification_protocol_v1()
        sessions = tuple(item.as_of_session for item in self.sessions)
        benchmark_identities = {
            tuple((item.ticker, item.instrument_id) for item in session.benchmark_identities)
            for session in self.sessions
        }
        expected_coverage = market_state_coverage(self.sessions)
        expected_distributions = market_state_distributions(self.sessions)
        expected_temporal = market_state_temporal_diagnostics(self.sessions)
        expected_pairs = market_state_pair_correlations(self.sessions)
        joint = market_state_joint_coverage(self.sessions)
        ready = market_state_qualification_ready(
            expected_coverage,
            expected_distributions,
            joint,
            expected_temporal,
        )
        expected_status = (
            QuantResearchMarketStateQualificationStatus.READY_FOR_CAMPAIGN_PROTOCOL_DESIGN
            if ready
            else QuantResearchMarketStateQualificationStatus.REJECTED_DATA_OR_IMPLEMENTATION
        )
        if (
            self.protocol_fingerprint != protocol.logical_fingerprint
            or self.vector_definition_fingerprint
            != protocol.vector_definition_fingerprint
            or _fingerprint([item.isoformat() for item in sessions])
            != protocol.expected_session_partition_fingerprint
            or self.first_session != sessions[0]
            or self.last_session != sessions[-1]
            or self.first_session != protocol.first_signal_session
            or self.last_session != protocol.last_signal_session
            or len(benchmark_identities) != 1
            or self.coverage != expected_coverage
            or self.distributions != expected_distributions
            or self.temporal_diagnostics != expected_temporal
            or self.pair_correlations != expected_pairs
            or self.status is not expected_status
            or (
                self.reconstructed_joint_available_session_count,
                self.reconstructed_joint_first_half_session_count,
                self.reconstructed_joint_second_half_session_count,
            )
            != joint
            or self.artifact.record_count != len(self.sessions)
            or self.artifact.first_session != self.first_session
            or self.artifact.last_session != self.last_session
            or self.artifact.content_sha256 != market_state_panel_sha256(self.sessions)
            or self.limitation_codes
            != QUANT_RESEARCH_MARKET_STATE_REQUIRED_LIMITATIONS
            or self.source_population_fingerprint
            != market_state_population_fingerprint(self.sessions)
            or not _artifact_identity_reconciles(self)
            or qualification_fingerprint(self) != self.logical_fingerprint
        ):
            raise ValueError("market-state qualification report differs")
        return self


@lru_cache(maxsize=1)
def quant_research_market_state_qualification_protocol_v1() -> (
    QuantResearchMarketStateQualificationProtocolV1
):
    payload = {
        "vector_definition_fingerprint": (
            quant_research_market_state_vector_definition_v1().logical_fingerprint
        ),
        "metric_gates": _metric_gates(),
    }
    provisional = QuantResearchMarketStateQualificationProtocolV1.model_construct(
        **payload,
        logical_fingerprint="0" * 64,
    )
    return QuantResearchMarketStateQualificationProtocolV1.model_validate(
        {
            **payload,
            "logical_fingerprint": qualification_fingerprint(provisional),
        }
    )


def market_state_coverage(
    sessions: tuple[QuantResearchMarketStateSessionV1, ...],
) -> tuple[QuantResearchMarketStateCoverageV1, ...]:
    output = []
    for position, metric_id in enumerate(QUANT_RESEARCH_MARKET_STATE_METRIC_ORDER):
        values = tuple(item.metrics[position] for item in sessions)
        available = sum(
            item.availability is QuantResearchMarketStateAvailability.AVAILABLE
            for item in values
        )
        first = sum(
            item.availability is QuantResearchMarketStateAvailability.AVAILABLE
            for item in values[:QUANT_RESEARCH_MARKET_STATE_FIRST_HALF_SESSION_COUNT]
        )
        reasons = Counter(
            reason
            for item in values
            for reason in item.reason_codes
        )
        output.append(
            QuantResearchMarketStateCoverageV1(
                metric_id=metric_id,
                available_session_count=available,
                unavailable_session_count=len(values) - available,
                first_half_available_session_count=first,
                second_half_available_session_count=available - first,
                availability_rate=_render_ratio(available, len(values)),
                unavailable_reason_counts=tuple(
                    QuantResearchMarketStateReasonCountV1(
                        reason_code=reason,
                        count=count,
                    )
                    for reason, count in sorted(reasons.items())
                ),
            )
        )
    return tuple(output)


def market_state_distributions(
    sessions: tuple[QuantResearchMarketStateSessionV1, ...],
) -> tuple[QuantResearchMarketStateDistributionV1, ...]:
    output = []
    for position, metric_id in enumerate(QUANT_RESEARCH_MARKET_STATE_METRIC_ORDER):
        ordered_values = tuple(
            Decimal(item.metrics[position].value)
            for item in sessions
            if item.metrics[position].value is not None
        )
        values = tuple(sorted(ordered_values))
        if not values:
            output.append(
                QuantResearchMarketStateDistributionV1(
                    metric_id=metric_id,
                    observation_count=0,
                    distinct_value_count=0,
                    first_half_distinct_value_count=0,
                    second_half_distinct_value_count=0,
                )
            )
            continue
        first_values = tuple(
            Decimal(item.metrics[position].value)
            for item in sessions[:QUANT_RESEARCH_MARKET_STATE_FIRST_HALF_SESSION_COUNT]
            if item.metrics[position].value is not None
        )
        second_values = tuple(
            Decimal(item.metrics[position].value)
            for item in sessions[QUANT_RESEARCH_MARKET_STATE_FIRST_HALF_SESSION_COUNT:]
            if item.metrics[position].value is not None
        )
        output.append(
            QuantResearchMarketStateDistributionV1(
                metric_id=metric_id,
                observation_count=len(values),
                distinct_value_count=len(set(values)),
                first_half_distinct_value_count=len(set(first_values)),
                second_half_distinct_value_count=len(set(second_values)),
                minimum=_render_decimal(values[0]),
                p05=_render_decimal(_linear_quantile(values, Decimal("0.05"))),
                p25=_render_decimal(_linear_quantile(values, Decimal("0.25"))),
                median=_render_decimal(_linear_quantile(values, Decimal("0.50"))),
                p75=_render_decimal(_linear_quantile(values, Decimal("0.75"))),
                p95=_render_decimal(_linear_quantile(values, Decimal("0.95"))),
                maximum=_render_decimal(values[-1]),
            )
        )
    return tuple(output)


def market_state_qualification_ready(
    coverage: tuple[QuantResearchMarketStateCoverageV1, ...],
    distributions: tuple[QuantResearchMarketStateDistributionV1, ...],
    joint_coverage: tuple[int, int, int],
    temporal_diagnostics: tuple[
        QuantResearchMarketStateTemporalDiagnosticV1, ...
    ],
) -> bool:
    protocol = quant_research_market_state_qualification_protocol_v1()
    if tuple(item.metric_id for item in coverage) != QUANT_RESEARCH_MARKET_STATE_METRIC_ORDER:
        return False
    if tuple(item.metric_id for item in distributions) != QUANT_RESEARCH_MARKET_STATE_METRIC_ORDER:
        return False
    if (
        tuple(item.metric_id for item in temporal_diagnostics)
        != QUANT_RESEARCH_MARKET_STATE_METRIC_ORDER
    ):
        return False
    benchmark_ready = all(
        item.available_session_count == protocol.benchmark_required_session_count
        for item in coverage[:6]
    )
    reconstructed_ready = all(
        item.available_session_count >= protocol.reconstructed_minimum_session_count
        and item.first_half_available_session_count
        >= protocol.reconstructed_minimum_first_half_session_count
        and item.second_half_available_session_count
        >= protocol.reconstructed_minimum_second_half_session_count
        for item in coverage[6:]
    ) and all(
        actual >= required
        for actual, required in zip(joint_coverage, (250, 120, 120))
    )
    gate_by_metric = {
        item.metric_id: item.minimum_distinct_values
        for item in protocol.metric_gates
    }
    diverse = all(
        item.distinct_value_count >= gate_by_metric[item.metric_id]
        and item.first_half_distinct_value_count >= 2
        and item.second_half_distinct_value_count >= 2
        for item in distributions
    )
    temporally_supported = all(
        item.median_crossing_count >= protocol.minimum_median_crossing_count
        and item.longest_same_side_run <= protocol.maximum_longest_same_side_run
        for item in temporal_diagnostics
    )
    return benchmark_ready and reconstructed_ready and diverse and temporally_supported


def market_state_joint_coverage(
    sessions: tuple[QuantResearchMarketStateSessionV1, ...],
) -> tuple[int, int, int]:
    available = tuple(
        all(
            metric.availability is QuantResearchMarketStateAvailability.AVAILABLE
            for metric in item.metrics[6:]
        )
        for item in sessions
    )
    first = sum(available[:QUANT_RESEARCH_MARKET_STATE_FIRST_HALF_SESSION_COUNT])
    total = sum(available)
    return total, first, total - first


def market_state_temporal_diagnostics(
    sessions: tuple[QuantResearchMarketStateSessionV1, ...],
) -> tuple[QuantResearchMarketStateTemporalDiagnosticV1, ...]:
    output = []
    for position, metric_id in enumerate(QUANT_RESEARCH_MARKET_STATE_METRIC_ORDER):
        ordered = tuple(
            None
            if item.metrics[position].value is None
            else Decimal(item.metrics[position].value)
            for item in sessions
        )
        available = tuple(value for value in ordered if value is not None)
        if not available:
            output.append(
                QuantResearchMarketStateTemporalDiagnosticV1(
                    metric_id=metric_id,
                    lag_one_pair_count=0,
                    median_crossing_count=0,
                    same_side_episode_count=0,
                    longest_same_side_run=0,
                )
            )
            continue
        median = _linear_quantile(tuple(sorted(available)), Decimal("0.50"))
        sides = tuple(None if value is None else value >= median for value in ordered)
        crossings = sum(
            left is not None and right is not None and left != right
            for left, right in zip(sides, sides[1:])
        )
        episodes, longest = _episode_summary(sides)
        lag_pairs = tuple(
            (left, right)
            for left, right in zip(ordered, ordered[1:])
            if left is not None and right is not None
        )
        correlation = _pearson(
            tuple(item[0] for item in lag_pairs),
            tuple(item[1] for item in lag_pairs),
        )
        output.append(
            QuantResearchMarketStateTemporalDiagnosticV1(
                metric_id=metric_id,
                lag_one_pair_count=len(lag_pairs),
                lag_one_autocorrelation=(
                    None if correlation is None else _render_decimal(correlation)
                ),
                median_crossing_count=crossings,
                same_side_episode_count=episodes,
                longest_same_side_run=longest,
            )
        )
    return tuple(output)


def market_state_pair_correlations(
    sessions: tuple[QuantResearchMarketStateSessionV1, ...],
) -> tuple[QuantResearchMarketStatePairCorrelationV1, ...]:
    output = []
    for left_position, left_id in enumerate(QUANT_RESEARCH_MARKET_STATE_METRIC_ORDER):
        for right_position in range(left_position + 1, 10):
            right_id = QUANT_RESEARCH_MARKET_STATE_METRIC_ORDER[right_position]
            pairs = tuple(
                (
                    Decimal(item.metrics[left_position].value),
                    Decimal(item.metrics[right_position].value),
                )
                for item in sessions
                if item.metrics[left_position].value is not None
                and item.metrics[right_position].value is not None
            )
            correlation = _pearson(
                tuple(item[0] for item in pairs),
                tuple(item[1] for item in pairs),
            )
            output.append(
                QuantResearchMarketStatePairCorrelationV1(
                    left_metric_id=left_id,
                    right_metric_id=right_id,
                    observation_count=len(pairs),
                    pearson_correlation=(
                        None if correlation is None else _render_decimal(correlation)
                    ),
                )
            )
    return tuple(output)


def market_state_panel_sha256(
    sessions: tuple[QuantResearchMarketStateSessionV1, ...],
) -> str:
    return _fingerprint([item.model_dump(mode="json") for item in sessions])


def market_state_population_fingerprint(
    sessions: tuple[QuantResearchMarketStateSessionV1, ...],
) -> str:
    return _fingerprint(
        [
            {
                "session": item.as_of_session.isoformat(),
                "membership_logical_fingerprint": (
                    item.membership_logical_fingerprint
                ),
                "membership_manifest_sha256": item.membership_manifest_sha256,
                "declared_member_ids_fingerprint": (
                    item.declared_member_ids_fingerprint
                ),
                "declared_member_count": item.declared_member_count,
            }
            for item in sessions
        ]
    )


def qualification_fingerprint(value: BaseModel | dict[str, object]) -> str:
    payload = (
        value.model_dump(mode="json", exclude={"logical_fingerprint"})
        if isinstance(value, BaseModel)
        else {key: item for key, item in value.items() if key != "logical_fingerprint"}
    )
    return _fingerprint(payload)


def _linear_quantile(values: tuple[Decimal, ...], probability: Decimal) -> Decimal:
    if len(values) == 1:
        return values[0]
    with localcontext(_decimal_context()):
        position = Decimal(len(values) - 1) * probability
        lower = int(position)
        upper = min(lower + 1, len(values) - 1)
        fraction = position - Decimal(lower)
        return values[lower] + (values[upper] - values[lower]) * fraction


def _pearson(
    left: tuple[Decimal, ...],
    right: tuple[Decimal, ...],
) -> Decimal | None:
    if len(left) < 2 or len(left) != len(right):
        return None
    with localcontext(_decimal_context()):
        left_mean = sum(left, Decimal("0")) / Decimal(len(left))
        right_mean = sum(right, Decimal("0")) / Decimal(len(right))
        numerator = sum(
            (
                (left_value - left_mean) * (right_value - right_mean)
                for left_value, right_value in zip(left, right)
            ),
            Decimal("0"),
        )
        left_sum = sum(
            ((value - left_mean) ** 2 for value in left),
            Decimal("0"),
        )
        right_sum = sum(
            ((value - right_mean) ** 2 for value in right),
            Decimal("0"),
        )
        if left_sum == 0 or right_sum == 0:
            return None
        return numerator / (left_sum * right_sum).sqrt()


def _episode_summary(sides: tuple[bool | None, ...]) -> tuple[int, int]:
    episodes = 0
    longest = 0
    current_side: bool | None = None
    current_length = 0
    for side in sides:
        if side is None:
            current_side = None
            current_length = 0
            continue
        if side != current_side:
            episodes += 1
            current_side = side
            current_length = 1
        else:
            current_length += 1
        longest = max(longest, current_length)
    return episodes, longest


def _render_ratio(numerator: int, denominator: int) -> str:
    with localcontext(_decimal_context()):
        value = (
            Decimal(numerator) / Decimal(denominator)
            if denominator
            else Decimal("0")
        )
        return _render_decimal(value)


def _render_decimal(value: Decimal) -> str:
    with localcontext(_decimal_context()):
        quantized = value.quantize(DECIMAL_QUANTUM, rounding=ROUND_HALF_EVEN)
        if quantized == Decimal("0"):
            quantized = abs(quantized)
        return format(quantized, "f")


def _decimal_context() -> Context:
    return Context(prec=50, rounding=ROUND_HALF_EVEN)


def _fingerprint(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
            default=str,
        ).encode("utf-8")
    ).hexdigest()


def _metric_gates() -> tuple[QuantResearchMarketStateMetricGateV1, ...]:
    return tuple(
        QuantResearchMarketStateMetricGateV1(
            metric_id=metric_id,
            minimum_distinct_values=20,
        )
        for metric_id in QUANT_RESEARCH_MARKET_STATE_METRIC_ORDER
    )


def _artifact_identity_reconciles(
    report: QuantResearchMarketStateQualificationReportV1,
) -> bool:
    identity = report.artifact.identity
    expected_sources = tuple(
        sorted(
            {
                report.source_eod_fingerprint,
                report.source_membership_fingerprint,
                report.source_action_fingerprint,
                report.source_adjustment_fingerprint,
                report.source_census_fingerprint,
            }
        )
    )
    return bool(
        identity.artifact_kind is QuantResearchArtifactKind.MARKET_STATE
        and identity.source_logical_fingerprints == expected_sources
        and identity.source_contract_versions
        == QUANT_RESEARCH_MARKET_STATE_SOURCE_CONTRACT_VERSIONS
        and identity.stable_universe_fingerprint
        == report.source_population_fingerprint
        and identity.knowledge_time_cutoff
        == "completed_session_close_each_row_earliest_next_open"
        and identity.session_partition_fingerprint
        == report.session_partition_fingerprint
        and identity.calculation_code_sha256 == report.calculation_code_sha256
        and identity.parameter_fingerprint
        == report.vector_definition_fingerprint
        and identity.upstream_artifact_fingerprints
        == (report.protocol_fingerprint,)
    )
