"""Typed shadow contract for independent Candidate strategy channels."""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from datetime import date
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from tip_api.parameters.market_regime.candidate_strategy_preview_v1_0_0 import (
    REQUIRED_PRIMARY_EVIDENCE as REQUIRED_PRIMARY_EVIDENCE_BY_CHANNEL,
    STRATEGY_CHANNEL_CALCULATION_VERSION,
    STRATEGY_CHANNEL_CONSUMER_CONTRACT_VERSION,
    STRATEGY_CHANNEL_CONTRACT_VERSION,
    STRATEGY_CHANNEL_DISPLAY_CAP,
    STRATEGY_CHANNEL_ORDER,
    STRATEGY_CHANNEL_PARAMETER_FINGERPRINT,
    STRATEGY_CHANNEL_PARAMETER_SET_ID,
)


class StrategyChannel(StrEnum):
    MOMENTUM_BREAKOUT = "momentum_breakout"
    STRONG_STOCK_PULLBACK = "strong_stock_pullback"
    TREND_CONTINUATION = "trend_continuation"
    TECHNICAL_REVERSAL = "technical_reversal"
    FUNDAMENTAL_VALUE_REVERSAL = "fundamental_value_reversal"
    DEFENSIVE_ROTATION = "defensive_rotation"


REQUIRED_PRIMARY_EVIDENCE = {
    StrategyChannel(channel): values
    for channel, values in REQUIRED_PRIMARY_EVIDENCE_BY_CHANNEL.items()
}


class StrategyChannelStatus(StrEnum):
    ADVANCE_TO_RESEARCH = "advance_to_research"
    WATCH_FOR_TRIGGER = "watch_for_trigger"
    DEPRIORITIZED = "deprioritized"
    UNAVAILABLE = "unavailable"


class StrategyMarketFit(StrEnum):
    SUPPORTIVE = "supportive"
    NEUTRAL = "neutral"
    ADVERSE = "adverse"
    UNAVAILABLE = "unavailable"


class StrategyEvidenceAvailability(StrEnum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"


class StrategyEvidenceKind(StrEnum):
    SUPPORTING = "supporting"
    COUNTEREVIDENCE = "counterevidence"


class StrategyEvidenceRole(StrEnum):
    PRIMARY = "primary"
    CONTEXT = "context"


class StrategyEvidenceSource(StrEnum):
    PRICE_VOLUME = "price_volume"
    MARKET_REGIME = "market_regime"
    PRICE_DERIVED_RELATIONSHIP_PROXY = "price_derived_relationship_proxy"
    FUNDAMENTALS = "fundamentals"
    VALUATION = "valuation"
    EVENT = "event"
    DATA_QUALITY = "data_quality"


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class StrategyChannelEvidenceV1(FrozenModel):
    evidence_id: str
    evidence_kind: StrategyEvidenceKind
    role: StrategyEvidenceRole
    source_kind: StrategyEvidenceSource
    evidence_type: Literal["fact", "proxy", "statistical_inference", "data_quality"]
    availability: StrategyEvidenceAvailability
    observed_value: str | None
    raw_unit: str
    source_session: date | None
    missing_reason_code: str | None
    reason_codes: tuple[str, ...]

    @model_validator(mode="after")
    def evidence_reconciles(self) -> "StrategyChannelEvidenceV1":
        if self.availability is StrategyEvidenceAvailability.AVAILABLE:
            if self.observed_value is None or self.source_session is None or self.missing_reason_code is not None:
                raise ValueError("available strategy evidence requires a value and source session")
        elif self.observed_value is not None or self.source_session is not None or self.missing_reason_code is None:
            raise ValueError("unavailable strategy evidence must be null with a reason")
        if self.source_kind is StrategyEvidenceSource.EVENT and self.role is not StrategyEvidenceRole.CONTEXT:
            raise ValueError("event evidence is auxiliary context and cannot be primary strategy evidence")
        if (
            self.source_kind is StrategyEvidenceSource.PRICE_DERIVED_RELATIONSHIP_PROXY
            and self.evidence_type != "proxy"
        ):
            raise ValueError("price-derived relationship evidence must remain labelled as a proxy")
        return self


class CandidateStrategyChannelAssessmentV1(FrozenModel):
    schema_version: Literal["1.0"] = "1.0"
    contract_version: Literal[STRATEGY_CHANNEL_CONTRACT_VERSION] = STRATEGY_CHANNEL_CONTRACT_VERSION
    calculation_version: Literal[STRATEGY_CHANNEL_CALCULATION_VERSION] = STRATEGY_CHANNEL_CALCULATION_VERSION
    parameter_set_id: Literal[STRATEGY_CHANNEL_PARAMETER_SET_ID] = STRATEGY_CHANNEL_PARAMETER_SET_ID
    parameter_fingerprint: Literal[STRATEGY_CHANNEL_PARAMETER_FINGERPRINT] = (
        STRATEGY_CHANNEL_PARAMETER_FINGERPRINT
    )
    as_of_session: date
    universe_id: str
    instrument_id: UUID
    ticker: str
    security_type: Literal["CS", "ADRC"]
    channel: StrategyChannel
    status: StrategyChannelStatus
    channel_score: str | None
    within_channel_rank: int | None = Field(default=None, ge=1)
    score_meaning: Literal["within_channel_research_priority_not_return_probability"] = (
        "within_channel_research_priority_not_return_probability"
    )
    market_fit: StrategyMarketFit
    market_fit_reason_codes: tuple[str, ...]
    market_fit_separate_from_channel_score: Literal[True] = True
    first_rejection_is_risk_not_status_reason: Literal[True] = True
    source_candidate_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_entry_geometry_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    evidence: tuple[StrategyChannelEvidenceV1, ...]
    missing_required_evidence_codes: tuple[str, ...]
    why_surfaced_codes: tuple[str, ...]
    first_rejection_code: str | None
    what_would_make_researchable_codes: tuple[str, ...]
    invalidation_codes: tuple[str, ...]
    required_manual_check_codes: tuple[str, ...]
    warning_codes: tuple[str, ...]
    logical_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def assessment_reconciles(self) -> "CandidateStrategyChannelAssessmentV1":
        if any(
            row.source_session is not None and row.source_session > self.as_of_session
            for row in self.evidence
        ):
            raise ValueError("strategy evidence cannot use a future session")
        evidence_ids = tuple(row.evidence_id for row in self.evidence)
        if len(evidence_ids) != len(set(evidence_ids)):
            raise ValueError("strategy evidence IDs must be unique within an assessment")
        available_primary_sources = {
            row.source_kind
            for row in self.evidence
            if row.availability is StrategyEvidenceAvailability.AVAILABLE
            and row.role is StrategyEvidenceRole.PRIMARY
        }
        if self.status is StrategyChannelStatus.UNAVAILABLE:
            if (
                self.channel_score is not None
                or self.within_channel_rank is not None
                or not self.missing_required_evidence_codes
            ):
                raise ValueError("unavailable strategy assessment must be unscored with missing evidence")
        else:
            _score(self.channel_score)
            if self.missing_required_evidence_codes:
                raise ValueError("assessable strategy result cannot carry missing required evidence")
            if self.status in {
                StrategyChannelStatus.ADVANCE_TO_RESEARCH,
                StrategyChannelStatus.WATCH_FOR_TRIGGER,
            }:
                if self.within_channel_rank is None:
                    raise ValueError("research and watch strategy results require a within-channel rank")
            elif self.within_channel_rank is not None:
                raise ValueError("deprioritized strategy results cannot carry a rank")
        if self.status is StrategyChannelStatus.ADVANCE_TO_RESEARCH:
            if (
                not self.why_surfaced_codes
                or not self.invalidation_codes
                or not any(
                    row.evidence_kind is StrategyEvidenceKind.SUPPORTING
                    and row.availability is StrategyEvidenceAvailability.AVAILABLE
                    and row.role is StrategyEvidenceRole.PRIMARY
                    for row in self.evidence
                )
                or not any(
                    row.evidence_kind is StrategyEvidenceKind.COUNTEREVIDENCE
                    and row.availability is StrategyEvidenceAvailability.AVAILABLE
                    for row in self.evidence
                )
            ):
                raise ValueError(
                    "advanced strategy research requires why-now, support, counterevidence, and invalidation"
                )
        elif not self.what_would_make_researchable_codes:
            raise ValueError("non-advanced strategy result requires a reviewability condition")
        if self.first_rejection_code is None:
            raise ValueError("every strategy result requires its first smart rejection risk")

        if self.status is not StrategyChannelStatus.UNAVAILABLE:
            required_sources = {
                StrategyEvidenceSource(value)
                for value in REQUIRED_PRIMARY_EVIDENCE[self.channel]
            }
            if not required_sources.issubset(available_primary_sources):
                raise ValueError("assessable strategy channel lacks its required primary evidence classes")

        if _fingerprint(self, exclude={"logical_fingerprint"}) != self.logical_fingerprint:
            raise ValueError("strategy-channel assessment logical fingerprint mismatch")
        return self


class CandidateStrategyChannelBatchV1(FrozenModel):
    schema_version: Literal["1.0"] = "1.0"
    contract_version: Literal[STRATEGY_CHANNEL_CONTRACT_VERSION] = STRATEGY_CHANNEL_CONTRACT_VERSION
    calculation_version: Literal[STRATEGY_CHANNEL_CALCULATION_VERSION] = STRATEGY_CHANNEL_CALCULATION_VERSION
    parameter_set_id: Literal[STRATEGY_CHANNEL_PARAMETER_SET_ID] = STRATEGY_CHANNEL_PARAMETER_SET_ID
    parameter_fingerprint: Literal[STRATEGY_CHANNEL_PARAMETER_FINGERPRINT] = (
        STRATEGY_CHANNEL_PARAMETER_FINGERPRINT
    )
    as_of_session: date
    universe_id: str
    source_candidate_batch_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_entry_geometry_batch_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    channel_order: tuple[
        StrategyChannel,
        StrategyChannel,
        StrategyChannel,
        StrategyChannel,
        StrategyChannel,
        StrategyChannel,
    ] = tuple(StrategyChannel)
    records: tuple[CandidateStrategyChannelAssessmentV1, ...] = Field(min_length=6)
    status_counts: dict[StrategyChannel, dict[StrategyChannelStatus, int]]
    cross_channel_score_prohibited: Literal[True] = True
    research_priority_only: Literal[True] = True
    event_context_is_auxiliary: Literal[True] = True
    underlying_stock_result_not_option_return: Literal[True] = True
    price_volume_not_fund_flow: Literal[True] = True
    warnings: tuple[str, ...]
    logical_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def batch_reconciles(self) -> "CandidateStrategyChannelBatchV1":
        if tuple(item.value for item in self.channel_order) != STRATEGY_CHANNEL_ORDER:
            raise ValueError("strategy channels must use the fixed product order")
        channel_index = {channel: index for index, channel in enumerate(self.channel_order)}
        keys = tuple((str(row.instrument_id), channel_index[row.channel]) for row in self.records)
        if keys != tuple(sorted(keys)) or len(keys) != len(set(keys)):
            raise ValueError("strategy assessments must be unique and stable-ID/channel ordered")
        grouped: dict[UUID, list[CandidateStrategyChannelAssessmentV1]] = defaultdict(list)
        for row in self.records:
            if row.as_of_session != self.as_of_session or row.universe_id != self.universe_id:
                raise ValueError("strategy assessment identity differs from its batch")
            grouped[row.instrument_id].append(row)
        if any(tuple(row.channel for row in rows) != self.channel_order for rows in grouped.values()):
            raise ValueError("every included security requires an explicit result for every strategy channel")
        if any(
            len({(row.ticker, row.security_type) for row in rows}) != 1
            for rows in grouped.values()
        ):
            raise ValueError("strategy assessment security identity differs across channels")

        actual_counts = {
            channel: dict(Counter(row.status for row in self.records if row.channel is channel))
            for channel in self.channel_order
        }
        normalized_expected = {
            channel: {status: count for status, count in counts.items() if count}
            for channel, counts in self.status_counts.items()
        }
        if actual_counts != normalized_expected:
            raise ValueError("strategy-channel status counts do not reconcile")
        for channel in self.channel_order:
            ranks = sorted(
                row.within_channel_rank
                for row in self.records
                if row.channel is channel and row.within_channel_rank is not None
            )
            if ranks != list(range(1, len(ranks) + 1)):
                raise ValueError("within-channel ranks must be unique and contiguous")
        if _fingerprint(self, exclude={"logical_fingerprint"}) != self.logical_fingerprint:
            raise ValueError("strategy-channel batch logical fingerprint mismatch")
        return self


class CandidateStrategyChannelViewV1(FrozenModel):
    schema_version: Literal["1.0"] = "1.0"
    channel: StrategyChannel
    status_counts: dict[StrategyChannelStatus, int]
    qualifying_count: int = Field(ge=0)
    display_cap: Literal[STRATEGY_CHANNEL_DISPLAY_CAP] = STRATEGY_CHANNEL_DISPLAY_CAP
    displayed_records: tuple[CandidateStrategyChannelAssessmentV1, ...]
    logical_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def view_reconciles(self) -> "CandidateStrategyChannelViewV1":
        if any(count < 0 for count in self.status_counts.values()):
            raise ValueError("strategy-channel status counts cannot be negative")
        expected_qualifying = sum(
            self.status_counts.get(status, 0)
            for status in (
                StrategyChannelStatus.ADVANCE_TO_RESEARCH,
                StrategyChannelStatus.WATCH_FOR_TRIGGER,
            )
        )
        if self.qualifying_count != expected_qualifying:
            raise ValueError("strategy-channel qualifying count does not reconcile")
        if len(self.displayed_records) != min(self.qualifying_count, self.display_cap):
            raise ValueError("strategy-channel display count differs from its cap")
        if any(
            row.channel is not self.channel
            or row.status
            not in {
                StrategyChannelStatus.ADVANCE_TO_RESEARCH,
                StrategyChannelStatus.WATCH_FOR_TRIGGER,
            }
            for row in self.displayed_records
        ):
            raise ValueError("strategy-channel view contains an ineligible record")
        ranks = tuple(row.within_channel_rank for row in self.displayed_records)
        if ranks != tuple(range(1, len(ranks) + 1)):
            raise ValueError("strategy-channel view must contain the leading contiguous ranks")
        if _fingerprint(self, exclude={"logical_fingerprint"}) != self.logical_fingerprint:
            raise ValueError("strategy-channel view logical fingerprint mismatch")
        return self


class CandidateStrategyChannelConsumerV1(FrozenModel):
    schema_version: Literal["1.0"] = "1.0"
    contract_version: Literal[STRATEGY_CHANNEL_CONSUMER_CONTRACT_VERSION] = (
        STRATEGY_CHANNEL_CONSUMER_CONTRACT_VERSION
    )
    as_of_session: date
    universe_id: str
    source_batch_logical_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    channel_order: tuple[
        StrategyChannel,
        StrategyChannel,
        StrategyChannel,
        StrategyChannel,
        StrategyChannel,
        StrategyChannel,
    ] = tuple(StrategyChannel)
    channels: tuple[
        CandidateStrategyChannelViewV1,
        CandidateStrategyChannelViewV1,
        CandidateStrategyChannelViewV1,
        CandidateStrategyChannelViewV1,
        CandidateStrategyChannelViewV1,
        CandidateStrategyChannelViewV1,
    ]
    cross_channel_score_prohibited: Literal[True] = True
    shadow_only: Literal[True] = True
    warnings: tuple[str, ...]
    logical_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def consumer_reconciles(self) -> "CandidateStrategyChannelConsumerV1":
        if tuple(item.value for item in self.channel_order) != STRATEGY_CHANNEL_ORDER:
            raise ValueError("strategy-channel consumer order differs")
        if tuple(item.channel for item in self.channels) != self.channel_order:
            raise ValueError("strategy-channel consumer views differ from product order")
        for view in self.channels:
            if any(
                row.as_of_session != self.as_of_session
                or row.universe_id != self.universe_id
                for row in view.displayed_records
            ):
                raise ValueError("strategy-channel consumer record identity differs")
        if _fingerprint(self, exclude={"logical_fingerprint"}) != self.logical_fingerprint:
            raise ValueError("strategy-channel consumer logical fingerprint mismatch")
        return self


def strategy_channel_logical_fingerprint(
    value: BaseModel | dict[str, object],
    *,
    exclude: set[str] | None = None,
) -> str:
    """Return the canonical logical fingerprint used by the shadow contract."""

    return _fingerprint(value, exclude=exclude or set())


def _fingerprint(value: BaseModel | dict[str, object], *, exclude: set[str]) -> str:
    payload = value.model_dump(mode="json", exclude=exclude) if isinstance(value, BaseModel) else {
        key: item for key, item in value.items() if key not in exclude
    }
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _score(value: str | None) -> Decimal:
    if value is None:
        raise ValueError("assessable strategy result requires a channel score")
    try:
        score = Decimal(value)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("strategy channel score must be a Decimal string") from exc
    if (
        not score.is_finite()
        or value != format(score.quantize(Decimal("0.0001")), "f")
        or not Decimal("0") <= score <= Decimal("100")
    ):
        raise ValueError("strategy channel score must use scale 4 within [0,100]")
    return score
