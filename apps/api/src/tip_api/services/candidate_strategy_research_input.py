"""Pure, fail-closed input construction for Strong-Leader Pullback research."""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from datetime import UTC, date, datetime
from decimal import (
    Context,
    Decimal,
    DivisionByZero,
    InvalidOperation,
    Overflow,
    ROUND_HALF_EVEN,
    localcontext,
)
from enum import Enum
from typing import Any, Mapping
from uuid import UUID

from pydantic import BaseModel

from tip_api.contracts.analytics.v1 import (
    STRONG_LEADER_PULLBACK_INPUT_FEATURE_FINGERPRINT,
    STRONG_STOCK_PULLBACK_RESEARCH_FINGERPRINT,
    MarketRegimeStateRecordV1,
    RegimeState,
    RegimeStateAvailability,
    StrategyMembershipMode,
    StrongLeaderPullbackDatasetBindingV1,
    StrongLeaderPullbackResearchInputBatchV1,
    research_input_fingerprint,
    strong_stock_pullback_research_experiment_v1,
)
from tip_api.contracts.common import QualityStatus
from tip_api.contracts.data_governance.v1 import PointInTimeEligibility
from tip_api.contracts.market_data.v1 import (
    AdjustmentAvailabilityStatus,
    AdjustmentLedgerEntryV1,
    HistoricalCoverageManifestV1,
    HistoricalReadinessStatus,
    InstrumentType,
    UniverseMembershipCanonicalPublicationV1,
    UniverseMembershipDecisionV1,
    UniverseMembershipDisposition,
    UniverseMembershipPartitionManifestV1,
    historical_coverage_manifest_fingerprint,
)
from tip_api.read_models.eod import EodMarketBarReadModel
from tip_api.services.candidate_strategy_research_execution import (
    build_strong_leader_pullback_observation,
)
from tip_api.services.market_calendar import ExchangeCalendar, MarketSessionCalendar
from tip_api.services.strong_leader_pullback_features import (
    StrongLeaderPullbackFeatureBar,
    StrongLeaderPullbackFeatureError,
    calculate_strong_leader_pullback_features,
)
from tip_api.services.strategy_research_readiness import (
    StrategyResearchReadinessAssessment,
    StrategyResearchReadinessStatus,
    validate_strategy_research_readiness_assessment,
)


SOURCE_SESSION_COUNT = 21
ZERO = Decimal("0")
RAW_QUANTUM = Decimal("0.0000000001")


class StrongLeaderPullbackResearchInputError(ValueError):
    """Raised before an incomplete or non-point-in-time cross-section can enter research."""


def build_strong_leader_pullback_research_input(
    *,
    as_of_session: date,
    benchmark_instrument_id: UUID,
    readiness: StrategyResearchReadinessAssessment,
    coverage: HistoricalCoverageManifestV1,
    membership_publication: UniverseMembershipCanonicalPublicationV1,
    membership_manifest: UniverseMembershipPartitionManifestV1,
    membership_records: tuple[UniverseMembershipDecisionV1, ...],
    market_regime: MarketRegimeStateRecordV1,
    bars: tuple[EodMarketBarReadModel, ...],
    adjustments: tuple[AdjustmentLedgerEntryV1, ...],
    calendar: MarketSessionCalendar | None = None,
) -> StrongLeaderPullbackResearchInputBatchV1:
    """Build one complete outcome-free Primary batch from already-read canonical evidence.

    The function performs no I/O. Any missing member/session/adjustment evidence rejects
    the whole signal-session cross-section so ranks cannot improve through survivorship.
    """

    experiment = strong_stock_pullback_research_experiment_v1()
    if experiment.logical_fingerprint != STRONG_STOCK_PULLBACK_RESEARCH_FINGERPRINT:
        raise StrongLeaderPullbackResearchInputError("frozen experiment fingerprint differs")
    _validate_readiness(readiness, coverage, as_of_session)
    source_sessions = _source_sessions(coverage, as_of_session, calendar or ExchangeCalendar())
    member_rows = _validate_membership(
        as_of_session=as_of_session,
        publication=membership_publication,
        manifest=membership_manifest,
        records=membership_records,
    )
    regime_label = _validate_regime(market_regime, as_of_session)
    member_ids = frozenset(item.instrument_id for item in member_rows)
    if benchmark_instrument_id in member_ids:
        raise StrongLeaderPullbackResearchInputError(
            "stable-ID SPY benchmark cannot be a Primary common-stock member"
        )
    required_ids = member_ids | {benchmark_instrument_id}
    bars_by_id = _validate_bars(
        bars=bars,
        required_ids=required_ids,
        member_ids=member_ids,
        benchmark_id=benchmark_instrument_id,
        sessions=source_sessions,
    )
    adjustments_by_id = _validate_adjustments(
        adjustments=adjustments,
        required_ids=required_ids,
        sessions=source_sessions,
        basis_session=as_of_session,
        next_session_open_at=(
            membership_publication.knowledge_time_assessment.next_session_open_at
        ),
    )
    adjusted = {
        instrument_id: _adjusted_series(
            bars_by_id[instrument_id], adjustments_by_id[instrument_id]
        )
        for instrument_id in required_ids
    }
    cross_section_source_fingerprint = _fingerprint(
        {
            "required_instrument_ids": [
                str(item) for item in sorted(required_ids, key=str)
            ],
            "sessions": [item.isoformat() for item in source_sessions],
            "bars": [
                _canonical(item)
                for instrument_id in sorted(required_ids, key=str)
                for item in bars_by_id[instrument_id]
            ],
            "adjustments": [
                _canonical(item)
                for instrument_id in sorted(required_ids, key=str)
                for item in adjustments_by_id[instrument_id]
            ],
        }
    )
    try:
        feature_panel = calculate_strong_leader_pullback_features(
            member_ids=member_ids,
            benchmark_instrument_id=benchmark_instrument_id,
            series_by_instrument=adjusted,
        )
    except StrongLeaderPullbackFeatureError as exc:
        raise StrongLeaderPullbackResearchInputError(
            "registered feature panel is incomplete or invalid"
        ) from exc
    features_by_id = {
        item.instrument_id: item for item in feature_panel.features
    }
    observations = []
    dataset_bindings = tuple(
        StrongLeaderPullbackDatasetBindingV1(
            family=item.family.value,
            logical_fingerprint=item.logical_fingerprint,
            physical_sha256=item.physical_sha256,
        )
        for item in sorted(coverage.datasets, key=lambda row: row.family.value)
    )
    for membership in sorted(member_rows, key=lambda row: str(row.instrument_id)):
        features = features_by_id[membership.instrument_id]
        values = {
            "as_of_session": as_of_session,
            "universe_id": "primary",
            "instrument_id": membership.instrument_id,
            "ticker": bars_by_id[membership.instrument_id][-1].ticker,
            "membership_mode": StrategyMembershipMode.POINT_IN_TIME,
            "membership_session": as_of_session,
            "membership_included": True,
            "relative_strength_20s_percentile": (
                features.relative_strength_20s_percentile
            ),
            "trend_quality_score": features.trend_quality_score,
            "pullback_depth_atr": features.pullback_depth_atr,
            "close_above_prior_close": features.close_above_prior_close,
            "close_above_prior_high": features.close_above_prior_high,
            "pullback_volume_ratio": features.pullback_volume_ratio,
            "market_regime": regime_label,
            "source_max_session": as_of_session,
            "source_fingerprint": _fingerprint(
                {
                    "feature_fingerprint": STRONG_LEADER_PULLBACK_INPUT_FEATURE_FINGERPRINT,
                    "coverage_fingerprint": coverage.logical_fingerprint,
                    "membership_publication_fingerprint": (
                        membership_publication.logical_fingerprint
                    ),
                    "market_regime_fingerprint": market_regime.logical_fingerprint,
                    "instrument_id": str(membership.instrument_id),
                    "benchmark_instrument_id": str(benchmark_instrument_id),
                    "cross_section_source_fingerprint": (
                        cross_section_source_fingerprint
                    ),
                    "sessions": [item.isoformat() for item in source_sessions],
                }
            ),
        }
        try:
            observations.append(build_strong_leader_pullback_observation(**values))
        except Exception as exc:
            raise StrongLeaderPullbackResearchInputError(
                f"research feature output is invalid for {membership.instrument_id}"
            ) from exc

    payload: dict[str, object] = {
        "as_of_session": as_of_session,
        "entry_session_date": (
            membership_publication.knowledge_time_assessment.entry_session_date
        ),
        "next_session_open_at": (
            membership_publication.knowledge_time_assessment.next_session_open_at
        ),
        "universe_id": "primary",
        "membership_mode": StrategyMembershipMode.POINT_IN_TIME,
        "source_sessions": source_sessions,
        "benchmark_instrument_id": benchmark_instrument_id,
        "benchmark_ticker": "SPY",
        "benchmark_20_session_return": _raw(
            feature_panel.benchmark_20_session_return
        ),
        "readiness_fingerprint": readiness.logical_content_fingerprint,
        "coverage_fingerprint": coverage.logical_fingerprint,
        "membership_publication_fingerprint": membership_publication.logical_fingerprint,
        "membership_partition_fingerprint": membership_manifest.logical_fingerprint,
        "membership_knowledge_time_fingerprint": (
            membership_publication.knowledge_time_assessment.logical_fingerprint
        ),
        "market_regime_fingerprint": market_regime.logical_fingerprint,
        "cross_section_source_fingerprint": cross_section_source_fingerprint,
        "dataset_bindings": dataset_bindings,
        "expected_member_count": len(member_rows),
        "observation_count": len(observations),
        "observations": tuple(observations),
        "contains_forward_outcomes": False,
        "development_authorized": False,
        "performance_claims_authorized": False,
        "external_request_count": 0,
        "production_write_count": 0,
    }
    provisional = StrongLeaderPullbackResearchInputBatchV1.model_construct(
        **payload, logical_fingerprint="0" * 64
    )
    return StrongLeaderPullbackResearchInputBatchV1.model_validate(
        {**payload, "logical_fingerprint": research_input_fingerprint(provisional)}
    )


def _validate_readiness(
    readiness: StrategyResearchReadinessAssessment,
    coverage: HistoricalCoverageManifestV1,
    as_of_session: date,
) -> None:
    try:
        HistoricalCoverageManifestV1.model_validate(coverage.model_dump(mode="python"))
        validate_strategy_research_readiness_assessment(readiness)
        assessed_through = (
            None
            if readiness.assessed_through_session is None
            else date.fromisoformat(readiness.assessed_through_session)
        )
    except Exception as exc:
        raise StrongLeaderPullbackResearchInputError(
            "research readiness evidence does not reconcile"
        ) from exc
    if (
        readiness.status is not StrategyResearchReadinessStatus.READY_FOR_DEVELOPMENT_REVIEW
        or readiness.experiment_fingerprint != STRONG_STOCK_PULLBACK_RESEARCH_FINGERPRINT
        or readiness.historical_coverage_manifest_fingerprint != coverage.logical_fingerprint
        or coverage.readiness_status is not HistoricalReadinessStatus.RESEARCH_READY
        or historical_coverage_manifest_fingerprint(coverage) != coverage.logical_fingerprint
        or assessed_through is None
        or assessed_through < as_of_session
    ):
        raise StrongLeaderPullbackResearchInputError(
            "research input requires matching research-ready historical evidence"
        )


def _source_sessions(
    coverage: HistoricalCoverageManifestV1,
    as_of_session: date,
    calendar: MarketSessionCalendar,
) -> tuple[date, ...]:
    try:
        index = coverage.sessions.index(as_of_session)
    except ValueError as exc:
        raise StrongLeaderPullbackResearchInputError(
            "signal session is outside historical coverage"
        ) from exc
    if index < SOURCE_SESSION_COUNT - 1:
        raise StrongLeaderPullbackResearchInputError("signal session lacks 20-session warmup")
    sessions = coverage.sessions[index - SOURCE_SESSION_COUNT + 1 : index + 1]
    if any(not calendar.is_session(item) for item in sessions) or any(
        calendar.next_session(left) != right
        for left, right in zip(sessions, sessions[1:])
    ):
        raise StrongLeaderPullbackResearchInputError(
            "research feature window is not contiguous XNYS time"
        )
    return sessions


def _validate_membership(
    *,
    as_of_session: date,
    publication: UniverseMembershipCanonicalPublicationV1,
    manifest: UniverseMembershipPartitionManifestV1,
    records: tuple[UniverseMembershipDecisionV1, ...],
) -> tuple[UniverseMembershipDecisionV1, ...]:
    try:
        publication = UniverseMembershipCanonicalPublicationV1.model_validate(
            publication.model_dump(mode="python")
        )
        manifest = UniverseMembershipPartitionManifestV1.model_validate(
            manifest.model_dump(mode="python")
        )
        records = tuple(
            UniverseMembershipDecisionV1.model_validate(item.model_dump(mode="python"))
            for item in records
        )
    except Exception as exc:
        raise StrongLeaderPullbackResearchInputError(
            "canonical Membership evidence is invalid"
        ) from exc
    assessment = publication.knowledge_time_assessment
    if (
        publication.session_date != as_of_session
        or manifest.session_date != as_of_session
        or publication.point_in_time_eligibility is not PointInTimeEligibility.SIGNAL_ELIGIBLE
        or assessment.point_in_time_eligibility is not PointInTimeEligibility.SIGNAL_ELIGIBLE
        or publication.membership_logical_fingerprint != manifest.logical_fingerprint
        or publication.membership_parquet_sha256 != manifest.physical_sha256
        or publication.record_count != manifest.record_count
        or publication.record_count != len(records)
        or publication.methodology_version != manifest.methodology_version
    ):
        raise StrongLeaderPullbackResearchInputError(
            "Membership publication, manifest, and rows do not reconcile"
        )
    keys = tuple((item.universe_id, str(item.instrument_id)) for item in records)
    if keys != tuple(sorted(set(keys))):
        raise StrongLeaderPullbackResearchInputError(
            "Membership rows must be unique and deterministically ordered"
        )
    if (
        _fingerprint([item.model_dump(mode="python") for item in records])
        != manifest.logical_fingerprint
    ):
        raise StrongLeaderPullbackResearchInputError(
            "Membership row logical fingerprint differs from manifest"
        )
    common = {
        (
            item.session_date,
            item.methodology_version,
            item.origin,
            item.evaluated_base_fingerprint,
            item.source_fingerprints,
            item.source_data_cutoff,
            item.evaluated_at,
        )
        for item in records
    }
    if len(common) != 1:
        raise StrongLeaderPullbackResearchInputError("Membership row provenance is not uniform")
    base_by_universe = {
        universe_id: frozenset(
            item.instrument_id for item in records if item.universe_id == universe_id
        )
        for universe_id in manifest.universe_ids
    }
    if (
        set(item.universe_id for item in records) != set(manifest.universe_ids)
        or any(len(ids) != manifest.evaluated_base_count for ids in base_by_universe.values())
        or len(set(base_by_universe.values())) != 1
        or _fingerprint(
            [str(item) for item in sorted(next(iter(base_by_universe.values())), key=str)]
        )
        != manifest.evaluated_base_fingerprint
    ):
        raise StrongLeaderPullbackResearchInputError(
            "Membership evaluated-base coverage differs from manifest"
        )
    observed_summaries = {
        universe_id: (
            sum(
                item.universe_id == universe_id
                and item.disposition is UniverseMembershipDisposition.INCLUDED
                for item in records
            ),
            sum(
                item.universe_id == universe_id
                and item.disposition is UniverseMembershipDisposition.EXCLUDED
                for item in records
            ),
            sum(
                item.universe_id == universe_id
                and item.disposition is UniverseMembershipDisposition.QUARANTINED
                for item in records
            ),
        )
        for universe_id in manifest.universe_ids
    }
    if any(
        observed_summaries[item.universe_id]
        != (item.included_count, item.excluded_count, item.quarantined_count)
        for item in manifest.disposition_summaries
    ):
        raise StrongLeaderPullbackResearchInputError(
            "Membership disposition totals differ from manifest"
        )
    first = records[0]
    if (
        first.session_date != as_of_session
        or first.methodology_version != manifest.methodology_version
        or first.origin != manifest.origin
        or first.evaluated_base_fingerprint != manifest.evaluated_base_fingerprint
        or first.source_fingerprints != manifest.source_fingerprints
        or first.source_data_cutoff != manifest.source_data_cutoff
        or first.evaluated_at != manifest.evaluated_at
    ):
        raise StrongLeaderPullbackResearchInputError("Membership rows differ from manifest")
    summary = next(
        (item for item in manifest.disposition_summaries if item.universe_id == "primary"),
        None,
    )
    members = tuple(
        item
        for item in records
        if item.universe_id == "primary"
        and item.disposition is UniverseMembershipDisposition.INCLUDED
        and item.is_member
    )
    if (
        summary is None
        or not members
        or len(members) != summary.included_count
        or any(item.quality_status is not QualityStatus.VALID for item in members)
    ):
        raise StrongLeaderPullbackResearchInputError(
            "complete quality-valid Primary Membership is unavailable"
        )
    return members


def _validate_regime(record: MarketRegimeStateRecordV1, session: date) -> str:
    try:
        MarketRegimeStateRecordV1.model_validate(record.model_dump(mode="python"))
    except Exception as exc:
        raise StrongLeaderPullbackResearchInputError(
            "same-session confirmed Primary Market Regime is invalid"
        ) from exc
    if (
        record.as_of_session != session
        or record.universe_id != "primary"
        or record.state_availability is not RegimeStateAvailability.AVAILABLE
        or record.stale_state
        or record.confirmed_state is None
        or _model_fingerprint(record) != record.logical_fingerprint
    ):
        raise StrongLeaderPullbackResearchInputError(
            "same-session confirmed Primary Market Regime is unavailable"
        )
    return {
        RegimeState.RISK_ON: "Risk-on",
        RegimeState.BALANCED: "Balanced",
        RegimeState.DEFENSIVE: "Defensive",
        RegimeState.STRESS: "Stress",
    }[record.confirmed_state]


def _validate_bars(
    *,
    bars: tuple[EodMarketBarReadModel, ...],
    required_ids: frozenset[UUID],
    member_ids: frozenset[UUID],
    benchmark_id: UUID,
    sessions: tuple[date, ...],
) -> dict[UUID, tuple[EodMarketBarReadModel, ...]]:
    by_id: dict[UUID, list[EodMarketBarReadModel]] = defaultdict(list)
    keys = set()
    for item in bars:
        key = (item.instrument_id, item.session_date)
        if key in keys:
            raise StrongLeaderPullbackResearchInputError("EOD bars contain duplicate keys")
        keys.add(key)
        by_id[item.instrument_id].append(item)
    expected_keys = {
        (instrument_id, session)
        for instrument_id in required_ids
        for session in sessions
    }
    if keys != expected_keys:
        raise StrongLeaderPullbackResearchInputError(
            "EOD bars do not exactly cover every admitted member and session"
        )
    output: dict[UUID, tuple[EodMarketBarReadModel, ...]] = {}
    for instrument_id in required_ids:
        ordered = tuple(sorted(by_id[instrument_id], key=lambda item: item.session_date))
        if tuple(item.session_date for item in ordered) != sessions:
            raise StrongLeaderPullbackResearchInputError("EOD bar sessions differ")
        if any(
            item.quality_status is not QualityStatus.VALID
            or item.currency != "USD"
            or any(
                not isinstance(value, Decimal) or not value.is_finite()
                for value in (item.open, item.high, item.low, item.close, item.volume)
            )
            or min(item.open, item.high, item.low, item.close) <= ZERO
            or item.volume < ZERO
            or item.low > min(item.open, item.close)
            or item.high < max(item.open, item.close)
            for item in ordered
        ):
            raise StrongLeaderPullbackResearchInputError("EOD bar quality is not research-safe")
        if instrument_id in member_ids and any(
            item.instrument_type is not InstrumentType.COMMON_STOCK for item in ordered
        ):
            raise StrongLeaderPullbackResearchInputError("Primary research member is not CS")
        if instrument_id == benchmark_id and any(
            item.instrument_type is not InstrumentType.ETF or item.ticker != "SPY"
            for item in ordered
        ):
            raise StrongLeaderPullbackResearchInputError("benchmark is not stable-ID SPY ETF")
        output[instrument_id] = ordered
    return output


def _validate_adjustments(
    *,
    adjustments: tuple[AdjustmentLedgerEntryV1, ...],
    required_ids: frozenset[UUID],
    sessions: tuple[date, ...],
    basis_session: date,
    next_session_open_at: datetime,
) -> dict[UUID, tuple[AdjustmentLedgerEntryV1, ...]]:
    try:
        adjustments = tuple(
            AdjustmentLedgerEntryV1.model_validate(item.model_dump(mode="python"))
            for item in adjustments
        )
    except Exception as exc:
        raise StrongLeaderPullbackResearchInputError(
            "adjustment ledger entries are invalid"
        ) from exc
    by_id: dict[UUID, list[AdjustmentLedgerEntryV1]] = defaultdict(list)
    keys = set()
    for item in adjustments:
        key = (item.instrument_id, item.source_session)
        if key in keys:
            raise StrongLeaderPullbackResearchInputError("adjustments contain duplicate keys")
        keys.add(key)
        by_id[item.instrument_id].append(item)
    expected_keys = {
        (instrument_id, session)
        for instrument_id in required_ids
        for session in sessions
    }
    if keys != expected_keys:
        raise StrongLeaderPullbackResearchInputError(
            "adjustments do not exactly cover every admitted member and session"
        )
    output = {}
    for instrument_id in required_ids:
        ordered = tuple(sorted(by_id[instrument_id], key=lambda item: item.source_session))
        if any(
            item.basis_session != basis_session
            or item.source_data_cutoff >= next_session_open_at
            or item.split_adjustment_status is not AdjustmentAvailabilityStatus.CLEAR
            or item.total_return_adjustment_status is not AdjustmentAvailabilityStatus.CLEAR
            or item.split_price_multiplier_to_basis is None
            or item.split_volume_multiplier_to_basis is None
            or item.total_return_multiplier_to_basis is None
            or item.quality_status is not QualityStatus.VALID
            for item in ordered
        ):
            raise StrongLeaderPullbackResearchInputError(
                "adjustment ledger is not complete and clear"
            )
        output[instrument_id] = ordered
    return output


def _adjusted_series(
    bars: tuple[EodMarketBarReadModel, ...],
    adjustments: tuple[AdjustmentLedgerEntryV1, ...],
) -> tuple[StrongLeaderPullbackFeatureBar, ...]:
    with localcontext(_context()):
        output = []
        for bar, adjustment in zip(bars, adjustments, strict=True):
            if bar.session_date != adjustment.source_session:
                raise StrongLeaderPullbackResearchInputError(
                    "bar and adjustment sessions differ"
                )
            price = adjustment.split_price_multiplier_to_basis
            volume = adjustment.split_volume_multiplier_to_basis
            assert price is not None and volume is not None
            output.append(
                StrongLeaderPullbackFeatureBar(
                    session=bar.session_date,
                    open=bar.open * price,
                    high=bar.high * price,
                    low=bar.low * price,
                    close=bar.close * price,
                    volume=bar.volume * volume,
                )
            )
        return tuple(output)


def _raw(value: Decimal) -> str:
    with localcontext(_context()):
        return format(value.quantize(RAW_QUANTUM), "f")


def _context() -> Context:
    context = Context(prec=50, rounding=ROUND_HALF_EVEN)
    context.traps[InvalidOperation] = True
    context.traps[DivisionByZero] = True
    context.traps[Overflow] = True
    return context


def _model_fingerprint(value: BaseModel) -> str:
    return _fingerprint(value.model_dump(mode="json", exclude={"logical_fingerprint"}))


def _fingerprint(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            _canonical(value),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()


def _canonical(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return _canonical(value.model_dump(mode="python"))
    if hasattr(value, "__dataclass_fields__"):
        return _canonical({name: getattr(value, name) for name in value.__dataclass_fields__})
    if isinstance(value, Mapping):
        return {str(key): _canonical(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_canonical(item) for item in value]
    if isinstance(value, datetime):
        return value.astimezone(UTC).isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, Enum):
        return value.value
    return value
