"""Cross-channel set diagnostics without comparing strategy scores."""

from __future__ import annotations

import hashlib
import json
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .candidate_strategy_channel import StrategyChannel


STRATEGY_DIAGNOSTICS_CONTRACT_VERSION = "candidate-strategy-channel-diagnostics/1.0"
TECHNICAL_CHANNEL_ORDER = (
    StrategyChannel.MOMENTUM_BREAKOUT,
    StrategyChannel.STRONG_STOCK_PULLBACK,
    StrategyChannel.TREND_CONTINUATION,
)


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class StrategyChannelPairOverlapV1(FrozenModel):
    left_channel: StrategyChannel
    right_channel: StrategyChannel
    left_qualifying_count: int = Field(ge=0)
    right_qualifying_count: int = Field(ge=0)
    intersection_count: int = Field(ge=0)
    union_count: int = Field(ge=0)
    left_only_count: int = Field(ge=0)
    right_only_count: int = Field(ge=0)
    jaccard_overlap: str
    left_subset_of_right: bool
    right_subset_of_left: bool

    @model_validator(mode="after")
    def counts_reconcile(self) -> "StrategyChannelPairOverlapV1":
        if self.left_channel == self.right_channel:
            raise ValueError("strategy overlap requires two different channels")
        if (
            self.left_only_count != self.left_qualifying_count - self.intersection_count
            or self.right_only_count
            != self.right_qualifying_count - self.intersection_count
            or self.union_count
            != self.left_qualifying_count
            + self.right_qualifying_count
            - self.intersection_count
            or self.left_subset_of_right != (self.left_only_count == 0)
            or self.right_subset_of_left != (self.right_only_count == 0)
        ):
            raise ValueError("strategy overlap counts do not reconcile")
        try:
            observed = Decimal(self.jaccard_overlap)
        except (InvalidOperation, ValueError) as exc:
            raise ValueError("strategy Jaccard overlap is malformed") from exc
        expected = (
            Decimal("0")
            if self.union_count == 0
            else (Decimal(self.intersection_count) / Decimal(self.union_count)).quantize(
                Decimal("0.0001")
            )
        )
        if self.jaccard_overlap != format(expected, "f") or observed != expected:
            raise ValueError("strategy Jaccard overlap differs from its counts")
        return self


class CandidateStrategyChannelDiagnosticsV1(FrozenModel):
    schema_version: Literal["1.0"] = "1.0"
    contract_version: Literal[STRATEGY_DIAGNOSTICS_CONTRACT_VERSION] = (
        STRATEGY_DIAGNOSTICS_CONTRACT_VERSION
    )
    as_of_session: date
    universe_id: str
    source_strategy_batch_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    channel_order: tuple[StrategyChannel, StrategyChannel, StrategyChannel] = (
        TECHNICAL_CHANNEL_ORDER
    )
    qualifying_counts: dict[StrategyChannel, int]
    pair_overlaps: tuple[
        StrategyChannelPairOverlapV1,
        StrategyChannelPairOverlapV1,
        StrategyChannelPairOverlapV1,
    ]
    all_three_intersection_count: int = Field(ge=0)
    qualifying_union_count: int = Field(ge=0)
    exclusive_counts: dict[StrategyChannel, int]
    multi_channel_member_count: int = Field(ge=0)
    cross_channel_scores_compared: Literal[False] = False
    outcome_or_performance_claim: Literal[False] = False
    logical_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def diagnostics_reconcile(self) -> "CandidateStrategyChannelDiagnosticsV1":
        if self.channel_order != TECHNICAL_CHANNEL_ORDER:
            raise ValueError("strategy diagnostic channel order differs")
        if set(self.qualifying_counts) != set(self.channel_order) or set(
            self.exclusive_counts
        ) != set(self.channel_order):
            raise ValueError("strategy diagnostic channel coverage differs")
        expected_pairs = (
            (self.channel_order[0], self.channel_order[1]),
            (self.channel_order[0], self.channel_order[2]),
            (self.channel_order[1], self.channel_order[2]),
        )
        if tuple(
            (item.left_channel, item.right_channel) for item in self.pair_overlaps
        ) != expected_pairs:
            raise ValueError("strategy diagnostic pair order differs")
        if any(
            item.left_qualifying_count != self.qualifying_counts[item.left_channel]
            or item.right_qualifying_count
            != self.qualifying_counts[item.right_channel]
            for item in self.pair_overlaps
        ):
            raise ValueError("strategy diagnostic pair totals differ")
        pair_intersections = {
            (item.left_channel, item.right_channel): item.intersection_count
            for item in self.pair_overlaps
        }
        first, second, third = self.channel_order
        first_second = pair_intersections[(first, second)]
        first_third = pair_intersections[(first, third)]
        second_third = pair_intersections[(second, third)]
        if self.all_three_intersection_count > min(
            first_second,
            first_third,
            second_third,
        ):
            raise ValueError("strategy diagnostic three-way intersection is impossible")
        expected_union = (
            sum(self.qualifying_counts.values())
            - first_second
            - first_third
            - second_third
            + self.all_three_intersection_count
        )
        expected_exclusive = {
            first: self.qualifying_counts[first]
            - first_second
            - first_third
            + self.all_three_intersection_count,
            second: self.qualifying_counts[second]
            - first_second
            - second_third
            + self.all_three_intersection_count,
            third: self.qualifying_counts[third]
            - first_third
            - second_third
            + self.all_three_intersection_count,
        }
        expected_multi = (
            first_second
            + first_third
            + second_third
            - 2 * self.all_three_intersection_count
        )
        if (
            self.qualifying_union_count != expected_union
            or self.exclusive_counts != expected_exclusive
            or self.multi_channel_member_count != expected_multi
            or any(value < 0 for value in expected_exclusive.values())
        ):
            raise ValueError("strategy diagnostic set identities do not reconcile")
        if strategy_diagnostics_fingerprint(
            self, exclude={"logical_fingerprint"}
        ) != self.logical_fingerprint:
            raise ValueError("strategy diagnostic logical fingerprint mismatch")
        return self


def strategy_diagnostics_fingerprint(
    value: BaseModel | dict[str, object], *, exclude: set[str] | None = None
) -> str:
    payload = (
        value.model_dump(mode="json", exclude=exclude or set())
        if isinstance(value, BaseModel)
        else {key: item for key, item in value.items() if key not in (exclude or set())}
    )
    return hashlib.sha256(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()
