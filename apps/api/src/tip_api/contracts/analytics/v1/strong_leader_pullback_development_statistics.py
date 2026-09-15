"""Contracts for bounded reconstructed Strong-Leader Pullback development statistics."""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .candidate_strategy_research import STRONG_STOCK_PULLBACK_RESEARCH_FINGERPRINT
from .candidate_strategy_research_statistics import (
    MINIMUM_COMPARABLE_SESSIONS,
    MINIMUM_SIGNAL_OBSERVATIONS,
    RESEARCH_BLOCK_LENGTH_SESSIONS,
    RESEARCH_BOOTSTRAP_REPLICATES,
)
from .strong_leader_pullback_method import (
    STRONG_LEADER_PULLBACK_METHOD_FINGERPRINT,
    STRONG_LEADER_PULLBACK_METHOD_VERSION,
)


DEVELOPMENT_STATISTICS_CONTRACT_VERSION = (
    "strong-leader-pullback-reconstructed-development-statistics/1.0"
)
DEVELOPMENT_STATISTICS_POLICY_VERSION = (
    "strong-leader-pullback-reconstructed-development-statistics-policy/1.0.0"
)
DEVELOPMENT_STATISTICS_COST_SCENARIOS_BPS_PER_SIDE = (0, 10, 25, 50)
DEVELOPMENT_STATISTICS_PRIMARY_HORIZON_SESSIONS = 3
DEVELOPMENT_STATISTICS_PARAMETER_BUDGET = 24
DEVELOPMENT_STATISTICS_REGIME_OBSERVATION_FLOOR = 60
DEVELOPMENT_STATISTICS_ENDPOINT_SCENARIOS = (
    "all_lower",
    "all_upper",
    "contrast_adverse",
)
_SHA256_PATTERN = r"^[0-9a-f]{64}$"
_GIT_REVISION_PATTERN = r"^[0-9a-f]{40}$"
_RETURN_PATTERN = r"^-?(?:0|[1-9][0-9]*)\.[0-9]{10}$"
_PROBABILITY_PATTERN = r"^(?:0\.[0-9]{6}|1\.000000)$"
_RATIO_PATTERN = r"^(?:0\.[0-9]{10}|1\.0000000000)$"


_POLICY_PAYLOAD = {
    "policy_version": DEVELOPMENT_STATISTICS_POLICY_VERSION,
    "method_fingerprint": STRONG_LEADER_PULLBACK_METHOD_FINGERPRINT,
    "parameter_budget": DEVELOPMENT_STATISTICS_PARAMETER_BUDGET,
    "horizons": (1, 3, 5),
    "primary_horizon": DEVELOPMENT_STATISTICS_PRIMARY_HORIZON_SESSIONS,
    "endpoint_scenarios": DEVELOPMENT_STATISTICS_ENDPOINT_SCENARIOS,
    "endpoint_rule": {
        "all_lower": "lower_endpoint_for_every_finite_interval",
        "all_upper": "upper_endpoint_for_every_finite_interval",
        "contrast_adverse": "signal_lower_and_control_upper_endpoint",
    },
    "selection_rule": (
        "same_winner_in_all_endpoint_scenarios_then_lock_contrast_adverse_"
        "maximum_lower_90pct_session_balanced_3s_contrast"
    ),
    "selection_tiebreaks": (
        "session_balanced_mean_contrast",
        "numeric_signal_count",
        "stable_combination_id",
    ),
    "unavailable_evidence_rule": (
        "any_primary_horizon_signal_or_control_unavailable_evidence_blocks_lock"
    ),
    "unexecutable_rule": (
        "retain_and_count_as_no_next_open_without_numeric_return_or_imputation"
    ),
    "evidence_floors": {
        "signal_observations": MINIMUM_SIGNAL_OBSERVATIONS,
        "control_observations": MINIMUM_SIGNAL_OBSERVATIONS,
        "comparable_sessions": MINIMUM_COMPARABLE_SESSIONS,
        "reported_regime_signal_observations": (
            DEVELOPMENT_STATISTICS_REGIME_OBSERVATION_FLOOR
        ),
    },
    "inference": {
        "unit": "equal_weight_within_session_signal_minus_control",
        "bootstrap": "deterministic_circular_moving_block",
        "block_length_sessions": RESEARCH_BLOCK_LENGTH_SESSIONS,
        "replicates": RESEARCH_BOOTSTRAP_REPLICATES,
        "interval": "percentile_90pct",
        "probability": "one_sided_centered_null_add_one",
    },
    "multiplicity": "none_in_development_selection_validation_retains_holm_24",
    "cost_scenarios_bps_per_side": (
        DEVELOPMENT_STATISTICS_COST_SCENARIOS_BPS_PER_SIDE
    ),
    "portfolio_construction_defined": False,
    "validation_or_holdout_access": False,
    "performance_claim_authorized": False,
}
DEVELOPMENT_STATISTICS_POLICY_FINGERPRINT = hashlib.sha256(
    json.dumps(
        _POLICY_PAYLOAD,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
).hexdigest()


class DevelopmentEndpointScenario(StrEnum):
    ALL_LOWER = "all_lower"
    ALL_UPPER = "all_upper"
    CONTRAST_ADVERSE = "contrast_adverse"


class DevelopmentSelectionStatus(StrEnum):
    LOCKED = "locked"
    BLOCKED_UNAVAILABLE_EVIDENCE = "blocked_unavailable_evidence"
    INCONCLUSIVE_EVIDENCE_FLOOR = "inconclusive_evidence_floor"
    REJECTED_ENDPOINT_INSTABILITY = "rejected_endpoint_instability"


class _FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class DevelopmentDispositionCountsV1(_FrozenModel):
    assigned_count: int = Field(ge=0)
    observed_eod_exact_count: int = Field(ge=0)
    terminal_reference_exact_count: int = Field(ge=0)
    terminal_reference_interval_count: int = Field(ge=0)
    unavailable_evidence_count: int = Field(ge=0)
    unexecutable_no_next_open_count: int = Field(ge=0)
    numeric_count: int = Field(ge=0)

    @model_validator(mode="after")
    def counts_reconcile(self) -> "DevelopmentDispositionCountsV1":
        if self.numeric_count != (
            self.observed_eod_exact_count
            + self.terminal_reference_exact_count
            + self.terminal_reference_interval_count
        ) or self.assigned_count != (
            self.numeric_count
            + self.unavailable_evidence_count
            + self.unexecutable_no_next_open_count
        ):
            raise ValueError("development disposition counts differ")
        return self


class DevelopmentCostMetricsV1(_FrozenModel):
    basis_points_per_side: Literal[0, 10, 25, 50]
    signal_mean_underlying_return_net: str | None = Field(
        default=None, pattern=_RETURN_PATTERN
    )
    signal_median_underlying_return_net: str | None = Field(
        default=None, pattern=_RETURN_PATTERN
    )
    signal_median_spy_relative_return_net: str | None = Field(
        default=None, pattern=_RETURN_PATTERN
    )
    signal_win_rate_net: str | None = Field(default=None, pattern=_RATIO_PATTERN)
    signal_average_win_net: str | None = Field(default=None, pattern=_RETURN_PATTERN)
    signal_average_loss_net: str | None = Field(default=None, pattern=_RETURN_PATTERN)
    signal_payoff_ratio_net: str | None = Field(default=None, pattern=_RETURN_PATTERN)
    signal_profit_factor_net: str | None = Field(default=None, pattern=_RETURN_PATTERN)

    @model_validator(mode="after")
    def metrics_reconcile(self) -> "DevelopmentCostMetricsV1":
        for value in (
            self.signal_mean_underlying_return_net,
            self.signal_median_underlying_return_net,
            self.signal_median_spy_relative_return_net,
            self.signal_average_win_net,
            self.signal_average_loss_net,
            self.signal_payoff_ratio_net,
            self.signal_profit_factor_net,
        ):
            if value is not None:
                _decimal(value, "cost metric")
        if self.signal_win_rate_net is not None:
            _probability(self.signal_win_rate_net, "net win rate", scale=10)
        if (
            self.signal_average_win_net is not None
            and Decimal(self.signal_average_win_net) <= 0
        ) or (
            self.signal_average_loss_net is not None
            and Decimal(self.signal_average_loss_net) >= 0
        ) or (
            self.signal_payoff_ratio_net is not None
            and Decimal(self.signal_payoff_ratio_net) < 0
        ) or (
            self.signal_profit_factor_net is not None
            and Decimal(self.signal_profit_factor_net) < 0
        ):
            raise ValueError("cost metric signs differ")
        return self


class DevelopmentStabilitySliceV1(_FrozenModel):
    slice_type: Literal["chronological_half", "market_regime"]
    slice_code: str
    signal_numeric_count: int = Field(ge=0)
    control_numeric_count: int = Field(ge=0)
    paired_session_count: int = Field(ge=0)
    session_balanced_mean_contrast: str | None = Field(
        default=None, pattern=_RETURN_PATTERN
    )


class StrongLeaderPullbackDevelopmentParameterSummaryV1(_FrozenModel):
    parameter_combination_id: str = Field(pattern=_SHA256_PATTERN)
    leadership_gate: str
    pullback_depth_atr_band: str
    recovery_trigger: str
    volume_contraction_ratio_max: str
    horizon_sessions: Literal[1, 3, 5]
    endpoint_scenario: DevelopmentEndpointScenario
    signal_disposition: DevelopmentDispositionCountsV1
    control_disposition: DevelopmentDispositionCountsV1
    paired_session_count: int = Field(ge=0)
    signal_market_regime_counts: dict[str, int]
    reported_regime_floor_met: bool
    inference_available: bool
    signal_mean_underlying_return: str | None = Field(
        default=None, pattern=_RETURN_PATTERN
    )
    signal_median_underlying_return: str | None = Field(
        default=None, pattern=_RETURN_PATTERN
    )
    signal_median_spy_relative_return: str | None = Field(
        default=None, pattern=_RETURN_PATTERN
    )
    signal_win_rate: str | None = Field(default=None, pattern=_RATIO_PATTERN)
    signal_average_win: str | None = Field(default=None, pattern=_RETURN_PATTERN)
    signal_average_loss: str | None = Field(default=None, pattern=_RETURN_PATTERN)
    signal_payoff_ratio: str | None = Field(default=None, pattern=_RETURN_PATTERN)
    signal_profit_factor: str | None = Field(default=None, pattern=_RETURN_PATTERN)
    signal_mean_maximum_favorable_excursion: str | None = Field(
        default=None, pattern=_RETURN_PATTERN
    )
    signal_mean_maximum_adverse_excursion: str | None = Field(
        default=None, pattern=_RETURN_PATTERN
    )
    signal_excursion_count: int = Field(ge=0)
    session_balanced_mean_contrast: str | None = Field(
        default=None, pattern=_RETURN_PATTERN
    )
    contrast_lower_90pct: str | None = Field(default=None, pattern=_RETURN_PATTERN)
    contrast_upper_90pct: str | None = Field(default=None, pattern=_RETURN_PATTERN)
    one_sided_raw_p_value: str | None = Field(
        default=None, pattern=_PROBABILITY_PATTERN
    )
    bootstrap_replicates: int = Field(ge=0)
    positive_paired_session_ratio: str | None = Field(
        default=None, pattern=_RATIO_PATTERN
    )
    largest_absolute_session_contrast_share: str | None = Field(
        default=None, pattern=_RATIO_PATTERN
    )
    cost_metrics: tuple[DevelopmentCostMetricsV1, ...]
    stability_slices: tuple[DevelopmentStabilitySliceV1, ...]
    reason_codes: tuple[str, ...]
    logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)

    @model_validator(mode="after")
    def summary_reconciles(
        self,
    ) -> "StrongLeaderPullbackDevelopmentParameterSummaryV1":
        if tuple(item.basis_points_per_side for item in self.cost_metrics) != (
            DEVELOPMENT_STATISTICS_COST_SCENARIOS_BPS_PER_SIDE
        ):
            raise ValueError("development cost scenarios differ")
        if sum(self.signal_market_regime_counts.values()) != (
            self.signal_disposition.numeric_count
        ) or tuple(sorted(self.signal_market_regime_counts)) != (
            "Balanced",
            "Defensive",
            "Risk-on",
            "Stress",
        ):
            raise ValueError("development Regime counts differ")
        observed_regimes = [
            count for count in self.signal_market_regime_counts.values() if count
        ]
        expected_regime_floor = bool(observed_regimes) and min(observed_regimes) >= (
            DEVELOPMENT_STATISTICS_REGIME_OBSERVATION_FLOOR
        )
        if self.reported_regime_floor_met != expected_regime_floor:
            raise ValueError("development Regime floor differs")
        inferential = (
            self.contrast_lower_90pct,
            self.contrast_upper_90pct,
            self.one_sided_raw_p_value,
        )
        if self.inference_available != all(value is not None for value in inferential):
            raise ValueError("development inference availability differs")
        if self.inference_available:
            if self.bootstrap_replicates != RESEARCH_BOOTSTRAP_REPLICATES:
                raise ValueError("development bootstrap count differs")
        elif self.bootstrap_replicates or any(value is not None for value in inferential):
            raise ValueError("inconclusive development summary carries inference")
        for value in (
            self.signal_mean_underlying_return,
            self.signal_median_underlying_return,
            self.signal_median_spy_relative_return,
            self.signal_average_win,
            self.signal_average_loss,
            self.signal_payoff_ratio,
            self.signal_profit_factor,
            self.signal_mean_maximum_favorable_excursion,
            self.signal_mean_maximum_adverse_excursion,
            self.session_balanced_mean_contrast,
            self.contrast_lower_90pct,
            self.contrast_upper_90pct,
        ):
            if value is not None:
                _decimal(value, "development statistic")
        for value in (
            self.signal_win_rate,
            self.positive_paired_session_ratio,
            self.largest_absolute_session_contrast_share,
        ):
            if value is not None:
                _probability(value, "development ratio", scale=10)
        if self.one_sided_raw_p_value is not None:
            _probability(self.one_sided_raw_p_value, "development probability", scale=6)
        if self.signal_excursion_count > self.signal_disposition.numeric_count:
            raise ValueError("development excursion count exceeds numeric signals")
        if self.reason_codes != tuple(sorted(set(self.reason_codes))):
            raise ValueError("development summary reasons differ")
        if development_statistics_fingerprint(self) != self.logical_fingerprint:
            raise ValueError("development summary fingerprint differs")
        return self


class StrongLeaderPullbackDevelopmentParameterLockV1(_FrozenModel):
    parameter_combination_id: str = Field(pattern=_SHA256_PATTERN)
    development_evidence_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    selection_objective: Literal[
        "maximum_contrast_adverse_lower_90pct_session_balanced_3s_contrast"
    ] = "maximum_contrast_adverse_lower_90pct_session_balanced_3s_contrast"
    objective_value: str = Field(pattern=_RETURN_PATTERN)
    secondary_tiebreak_value: str = Field(pattern=_RETURN_PATTERN)
    endpoint_winner_ids: dict[str, str]
    selected_before_validation: Literal[True] = True
    validation_cannot_change_parameters: Literal[True] = True
    holdout_cannot_change_parameters: Literal[True] = True
    logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)

    @model_validator(mode="after")
    def lock_reconciles(self) -> "StrongLeaderPullbackDevelopmentParameterLockV1":
        if tuple(sorted(self.endpoint_winner_ids)) != tuple(
            sorted(DEVELOPMENT_STATISTICS_ENDPOINT_SCENARIOS)
        ) or set(self.endpoint_winner_ids.values()) != {self.parameter_combination_id}:
            raise ValueError("development endpoint winners do not support the lock")
        if development_statistics_fingerprint(self) != self.logical_fingerprint:
            raise ValueError("development lock fingerprint differs")
        return self


class StrongLeaderPullbackDevelopmentStatisticsReportV1(_FrozenModel):
    schema_version: Literal["1.0"] = "1.0"
    contract_version: Literal[
        "strong-leader-pullback-reconstructed-development-statistics/1.0"
    ] = DEVELOPMENT_STATISTICS_CONTRACT_VERSION
    policy_version: Literal[
        "strong-leader-pullback-reconstructed-development-statistics-policy/1.0.0"
    ] = DEVELOPMENT_STATISTICS_POLICY_VERSION
    policy_fingerprint: Literal[DEVELOPMENT_STATISTICS_POLICY_FINGERPRINT] = (
        DEVELOPMENT_STATISTICS_POLICY_FINGERPRINT
    )
    experiment_fingerprint: Literal[STRONG_STOCK_PULLBACK_RESEARCH_FINGERPRINT] = (
        STRONG_STOCK_PULLBACK_RESEARCH_FINGERPRINT
    )
    method_version: Literal[STRONG_LEADER_PULLBACK_METHOD_VERSION] = (
        STRONG_LEADER_PULLBACK_METHOD_VERSION
    )
    method_fingerprint: Literal[STRONG_LEADER_PULLBACK_METHOD_FINGERPRINT] = (
        STRONG_LEADER_PULLBACK_METHOD_FINGERPRINT
    )
    implementation_revision: str = Field(pattern=_GIT_REVISION_PATTERN)
    created_at: datetime
    source_dataset_manifest_sha256: str = Field(pattern=_SHA256_PATTERN)
    source_dataset_logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)
    source_observation_count: int = Field(ge=1)
    source_label_count: int = Field(ge=3)
    first_signal_session: date
    last_signal_session: date
    parameter_combination_count: Literal[24] = 24
    summary_count: Literal[216] = 216
    endpoint_winner_ids: dict[str, str | None]
    selection_status: DevelopmentSelectionStatus
    selected_parameter_combination_id: str | None = Field(
        default=None, pattern=_SHA256_PATTERN
    )
    parameter_lock: StrongLeaderPullbackDevelopmentParameterLockV1 | None
    summaries: tuple[StrongLeaderPullbackDevelopmentParameterSummaryV1, ...]
    reconstructed_latest_vintage: Literal[True] = True
    as_operated: Literal[False] = False
    development_only: Literal[True] = True
    validation_data_accessed: Literal[False] = False
    holdout_data_accessed: Literal[False] = False
    formal_validation_review_required: Literal[True] = True
    validation_transition_authorized: Literal[False] = False
    performance_claim_authorized: Literal[False] = False
    candidate_activation_authorized: Literal[False] = False
    publication_authorized: Literal[False] = False
    production_write_count: Literal[0] = 0
    network_request_count: Literal[0] = 0
    canonical_data_write_count: Literal[0] = 0
    reason_codes: tuple[str, ...]
    logical_fingerprint: str = Field(pattern=_SHA256_PATTERN)

    @model_validator(mode="after")
    def report_reconciles(
        self,
    ) -> "StrongLeaderPullbackDevelopmentStatisticsReportV1":
        if self.created_at.tzinfo is None or self.created_at.utcoffset() is None:
            raise ValueError("development report creation time must be timezone-aware")
        if self.first_signal_session > self.last_signal_session:
            raise ValueError("development report period is reversed")
        summary_keys = {
            (item.parameter_combination_id, item.horizon_sessions, item.endpoint_scenario)
            for item in self.summaries
        }
        if len(self.summaries) != self.summary_count or len(summary_keys) != (
            self.summary_count
        ):
            raise ValueError("development report summary scope differs")
        if len({item.parameter_combination_id for item in self.summaries}) != 24:
            raise ValueError("development report parameter budget differs")
        if tuple(sorted(self.endpoint_winner_ids)) != tuple(
            sorted(DEVELOPMENT_STATISTICS_ENDPOINT_SCENARIOS)
        ):
            raise ValueError("development report endpoint scenarios differ")
        locked = self.selection_status is DevelopmentSelectionStatus.LOCKED
        if locked != (self.parameter_lock is not None) or locked != (
            self.selected_parameter_combination_id is not None
        ):
            raise ValueError("development report lock state differs")
        if self.parameter_lock is not None and (
            self.parameter_lock.parameter_combination_id
            != self.selected_parameter_combination_id
        ):
            raise ValueError("development report selected parameter differs")
        if self.reason_codes != tuple(sorted(set(self.reason_codes))):
            raise ValueError("development report reasons differ")
        if development_statistics_fingerprint(self) != self.logical_fingerprint:
            raise ValueError("development report fingerprint differs")
        return self


def development_statistics_fingerprint(
    value: BaseModel | dict[str, object],
    *,
    exclude: set[str] | None = None,
) -> str:
    if isinstance(value, BaseModel):
        payload = value.model_dump(
            mode="json", exclude=exclude or {"logical_fingerprint"}
        )
    else:
        payload = dict(value)
        for key in exclude or {"logical_fingerprint"}:
            payload.pop(key, None)
    return hashlib.sha256(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            default=str,
        ).encode("utf-8")
    ).hexdigest()


def _decimal(value: str, label: str) -> Decimal:
    try:
        parsed = Decimal(value)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{label} must be a decimal") from exc
    if not parsed.is_finite() or value != format(
        parsed.quantize(Decimal("0.0000000001")), "f"
    ):
        raise ValueError(f"{label} must be finite and use scale 10")
    return parsed


def _probability(value: str, label: str, *, scale: int) -> Decimal:
    parsed = _decimal(value, label) if scale == 10 else Decimal(value)
    if scale == 6 and (
        not parsed.is_finite()
        or value != format(parsed.quantize(Decimal("0.000001")), "f")
    ):
        raise ValueError(f"{label} must use scale 6")
    if not Decimal("0") <= parsed <= Decimal("1"):
        raise ValueError(f"{label} must be within [0,1]")
    return parsed
