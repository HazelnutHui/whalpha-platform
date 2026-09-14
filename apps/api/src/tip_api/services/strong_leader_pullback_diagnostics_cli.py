"""Read-only Dell runner for Strong-Leader Pullback method diagnostics."""

from __future__ import annotations

import argparse
import hashlib
import json
import socket
import sys
from collections import deque
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Iterator, Mapping
from uuid import UUID

from pydantic import BaseModel

from tip_api.contracts.analytics.v1 import (
    RegimeState,
    RegimeStateAvailability,
    StrategyMembershipMode,
    StrongLeaderPullbackDiagnosticExcludedPathV1,
    StrongLeaderPullbackDiagnosticUnavailableFeatureV1,
    StrongLeaderPullbackMethodDiagnosticsV1,
)
from tip_api.contracts.analytics.v1.candidate_strategy_development_coverage import (
    STRONG_LEADER_PULLBACK_CENSUS_FIRST_SESSION,
    STRONG_LEADER_PULLBACK_CENSUS_LAST_SESSION,
    STRONG_LEADER_PULLBACK_CENSUS_MEMBERSHIP_METHODOLOGY,
    STRONG_LEADER_PULLBACK_CENSUS_PRIMARY_UNIVERSE,
)
from tip_api.contracts.common import QualityStatus
from tip_api.contracts.market_data.v1 import (
    AdjustmentAvailabilityStatus,
    AdjustmentLedgerEntryV1,
    CorporateActionRecordStatus,
    UniverseMembershipDecisionV1,
    UniverseMembershipDisposition,
    UniverseMembershipOrigin,
    UniverseMembershipPartitionManifestV1,
)
from tip_api.parameters.market_regime.v1_0_0 import BROAD_BENCHMARK_TICKERS
from tip_api.persistence.development_coverage_census import (
    read_development_coverage_census,
)
from tip_api.persistence.eod_read import EodHistorySessionRead
from tip_api.persistence.parquet.canonical_corporate_action import (
    read_canonical_split_action_publication,
)
from tip_api.persistence.parquet.canonical_split_adjustment import (
    read_canonical_split_adjustment_publication,
)
from tip_api.persistence.parquet.eod_read import CanonicalEodReadRepository
from tip_api.persistence.parquet.historical_research import (
    ParquetHistoricalResearchRepository,
)
from tip_api.persistence.strong_leader_pullback_diagnostics import (
    write_strong_leader_pullback_diagnostics,
)
from tip_api.read_models.eod import EodMarketBarReadModel
from tip_api.services.candidate_strategy_development_coverage_cli import (
    _batch_root,
    _discover_membership_partitions,
    _validated_data_root,
    _validated_shadow_root,
)
from tip_api.services.candidate_strategy_research_execution import (
    build_candidate_strategy_chronological_plan,
    build_strong_leader_pullback_observation,
)
from tip_api.services.market_calendar import ExchangeCalendar
from tip_api.services.market_regime import calculate_market_regime
from tip_api.services.market_regime_sources import (
    MarketRegimeBar,
    MarketRegimeInputPanel,
    MarketRegimeSourceSession,
    MarketRegimeUniverseSource,
)
from tip_api.services.market_regime_state import (
    replay_regime_state_history,
    state_history_fingerprint,
)
from tip_api.services.strong_leader_pullback_diagnostics import (
    build_strong_leader_pullback_method_diagnostics,
)
from tip_api.services.strong_leader_pullback_features import (
    StrongLeaderPullbackComputedFeatures,
    StrongLeaderPullbackFeatureBar,
    StrongLeaderPullbackFeatureError,
    calculate_strong_leader_pullback_features,
)
from tip_api.services.strong_leader_pullback_method_engineering_launch_review import (
    read_strong_leader_pullback_method_engineering_launch_review,
)


PRICE_FEATURE_IDS = (
    "adjusted_ohlcv_panel",
    "atr_pullback_depth",
    "recovery_trigger",
    "relative_leadership_20s",
    "trend_quality",
    "volume_contraction",
)


class StrongLeaderPullbackDiagnosticsCliError(RuntimeError):
    """Raised when private diagnostic evidence is incomplete or unsafe."""


@dataclass(frozen=True, slots=True)
class _SessionFeatureBatch:
    session: date
    member_ids: frozenset[UUID]
    tickers: Mapping[UUID, str]
    features: tuple[StrongLeaderPullbackComputedFeatures, ...]
    feature_source_fingerprint: str
    known_split_adjustment_ids: frozenset[UUID]
    unavailable_feature_ids: tuple[str, ...] = ()
    unavailable_reason_codes: tuple[str, ...] = ()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build one private outcome-blind method diagnostic from formally "
            "reread Dell evidence."
        )
    )
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--membership-shadow-root", type=Path, required=True)
    parser.add_argument("--development-census-root", type=Path, required=True)
    parser.add_argument("--split-action-publication-root", type=Path, required=True)
    parser.add_argument(
        "--split-adjustment-publication-root", type=Path, required=True
    )
    parser.add_argument("--method-launch-root", type=Path, required=True)
    parser.add_argument("--method-launch-custody-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--output-custody-root", type=Path, required=True)
    args = parser.parse_args(argv)

    try:
        report_path, report = run_strong_leader_pullback_diagnostics(
            data_root=args.data_root,
            membership_shadow_root=args.membership_shadow_root,
            development_census_root=args.development_census_root,
            split_action_publication_root=args.split_action_publication_root,
            split_adjustment_publication_root=(
                args.split_adjustment_publication_root
            ),
            method_launch_root=args.method_launch_root,
            method_launch_custody_root=args.method_launch_custody_root,
            output_root=args.output_root,
            output_custody_root=args.output_custody_root,
        )
    except Exception as exc:
        print(
            json.dumps(
                {
                    "status": "rejected",
                    "reason_code": "strong_leader_pullback_method_diagnostics_rejected",
                    "error_type": type(exc).__name__,
                    "error_detail": _safe_error_detail(exc),
                    "external_request_count": 0,
                    "canonical_data_write_count": 0,
                    "production_write_count": 0,
                },
                sort_keys=True,
                separators=(",", ":"),
            )
        )
        return 1

    print(
        json.dumps(
            {
                "status": "completed",
                "report_path": str(report_path),
                "logical_fingerprint": report.logical_fingerprint,
                "session_count": report.session_count,
                "expected_path_count": report.expected_path_count,
                "complete_observation_count": report.complete_observation_count,
                "excluded_path_count": report.excluded_path_count,
                "known_split_adjustment_applied_path_count": (
                    report.known_split_adjustment_applied_path_count
                ),
                "external_request_count": 0,
                "canonical_data_write_count": 0,
                "production_write_count": 0,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 0


def run_strong_leader_pullback_diagnostics(
    *,
    data_root: Path,
    membership_shadow_root: Path,
    development_census_root: Path,
    split_action_publication_root: Path,
    split_adjustment_publication_root: Path,
    method_launch_root: Path,
    method_launch_custody_root: Path,
    output_root: Path,
    output_custody_root: Path,
) -> tuple[Path, StrongLeaderPullbackMethodDiagnosticsV1]:
    with _network_disabled():
        return _run_strong_leader_pullback_diagnostics(
            data_root=data_root,
            membership_shadow_root=membership_shadow_root,
            development_census_root=development_census_root,
            split_action_publication_root=split_action_publication_root,
            split_adjustment_publication_root=(
                split_adjustment_publication_root
            ),
            method_launch_root=method_launch_root,
            method_launch_custody_root=method_launch_custody_root,
            output_root=output_root,
            output_custody_root=output_custody_root,
        )


def _run_strong_leader_pullback_diagnostics(
    *,
    data_root: Path,
    membership_shadow_root: Path,
    development_census_root: Path,
    split_action_publication_root: Path,
    split_adjustment_publication_root: Path,
    method_launch_root: Path,
    method_launch_custody_root: Path,
    output_root: Path,
    output_custody_root: Path,
) -> tuple[Path, StrongLeaderPullbackMethodDiagnosticsV1]:
    canonical_root = _validated_data_root(data_root)
    shadow_root = _validated_shadow_root(membership_shadow_root)
    launch = read_strong_leader_pullback_method_engineering_launch_review(
        output_root=method_launch_root,
        output_custody_root=method_launch_custody_root,
    ).report
    census = read_development_coverage_census(
        output_root=development_census_root
    )
    _validate_launch_and_census(launch=launch, census=census)
    action_source = read_canonical_split_action_publication(
        data_root=canonical_root,
        publication_root=split_action_publication_root,
    )
    adjustment_source = read_canonical_split_adjustment_publication(
        data_root=canonical_root,
        publication_root=split_adjustment_publication_root,
    )
    _validate_census_sources(
        census=census,
        action_fingerprint=action_source.publication.logical_fingerprint,
        adjustment_fingerprint=adjustment_source.publication.logical_fingerprint,
    )

    calendar = ExchangeCalendar()
    plan = build_candidate_strategy_chronological_plan(
        ordered_sessions=tuple(item.session_date for item in census.sessions),
        calendar=calendar,
    )
    partitions = _discover_membership_partitions(shadow_root)
    expected_sessions = plan.ordered_sessions
    if tuple(sorted(partitions)) != expected_sessions:
        raise StrongLeaderPullbackDiagnosticsCliError(
            "Membership partitions do not exactly cover the diagnostic plan"
        )

    active_action_keys = {
        (item.instrument_id, item.effective_date)
        for item in action_source.actions
        if item.record_status is CorporateActionRecordStatus.ACTIVE
    }
    quarantined_action_keys = {
        (item.instrument_id, item.effective_date)
        for item in action_source.actions
        if item.record_status is not CorporateActionRecordStatus.ACTIVE
    }
    unresolved_impact_keys = {
        (item.instrument_id, effective_date)
        for item in action_source.publication.possible_unresolved_impacts
        for effective_date in item.effective_dates
    }
    clear_adjustments = {
        (item.instrument_id, item.source_session): item
        for item in adjustment_source.records
        if item.split_adjustment_status is AdjustmentAvailabilityStatus.CLEAR
    }
    quarantined_adjustment_keys = {
        (item.instrument_id, item.source_session)
        for item in adjustment_source.records
        if item.split_adjustment_status is not AdjustmentAvailabilityStatus.CLEAR
    }

    repository = CanonicalEodReadRepository(canonical_root)
    session_index = repository.list_session_index()
    if not set(expected_sessions).issubset(session_index):
        raise StrongLeaderPullbackDiagnosticsCliError(
            "canonical EOD does not cover the diagnostic sessions"
        )
    census_by_session = {item.session_date: item for item in census.sessions}
    window: deque[object] = deque(maxlen=21)
    batches: list[_SessionFeatureBatch] = []
    composites = []
    for session_index_value, session in enumerate(expected_sessions, start=1):
        read = repository.read_history_sessions((session,))[0]
        window.append(read)
        membership, membership_fingerprint = _read_membership(
            shadow_root=shadow_root,
            partition=partitions[session],
            census_session=census_by_session[session],
        )
        member_ids = frozenset(item.instrument_id for item in membership)
        if not member_ids:
            batches.append(
                _SessionFeatureBatch(
                    session=session,
                    member_ids=member_ids,
                    tickers={},
                    features=(),
                    feature_source_fingerprint=_fingerprint(
                        {
                            "session": session.isoformat(),
                            "membership": membership_fingerprint,
                            "member_ids": [],
                        }
                    ),
                    known_split_adjustment_ids=frozenset(),
                )
            )
            continue
        if len(window) != 21:
            raise StrongLeaderPullbackDiagnosticsCliError(
                "included Membership appears before the complete feature window"
            )
        batch, composite = _build_session_batch(
            session=session,
            session_reads=tuple(window),
            member_ids=member_ids,
            membership_fingerprint=membership_fingerprint,
            active_action_keys=active_action_keys,
            quarantined_action_keys=quarantined_action_keys,
            unresolved_impact_keys=unresolved_impact_keys,
            clear_adjustments=clear_adjustments,
            quarantined_adjustment_keys=quarantined_adjustment_keys,
            action_start=action_source.publication.start_date,
            adjustment_start=adjustment_source.publication.first_source_session,
            action_fingerprint=action_source.publication.logical_fingerprint,
            adjustment_fingerprint=(
                adjustment_source.publication.logical_fingerprint
            ),
            calendar=calendar,
        )
        batches.append(batch)
        if composite is not None:
            composites.append(composite)
        if session_index_value % 25 == 0 or session_index_value == len(
            expected_sessions
        ):
            print(
                json.dumps(
                    {
                        "status": "running",
                        "completed_sessions": session_index_value,
                        "total_sessions": len(expected_sessions),
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                ),
                file=sys.stderr,
                flush=True,
            )

    states, _ = replay_regime_state_history(
        composites=tuple(composites),
        expected_sessions=expected_sessions,
        universe_id="primary",
        calendar=calendar,
    )
    state_fingerprint = state_history_fingerprint(states)
    observations = []
    excluded_paths = []
    known_split_count = 0
    for batch, state in zip(batches, states, strict=True):
        if not batch.member_ids:
            continue
        unavailable = [
            StrongLeaderPullbackDiagnosticUnavailableFeatureV1(
                feature_id=feature_id,
                reason_codes=batch.unavailable_reason_codes,
            )
            for feature_id in batch.unavailable_feature_ids
        ]
        regime = None
        if (
            state.state_availability is RegimeStateAvailability.AVAILABLE
            and not state.stale_state
            and state.confirmed_state is not None
        ):
            regime = _regime_label(state.confirmed_state)
        else:
            unavailable.append(
                StrongLeaderPullbackDiagnosticUnavailableFeatureV1(
                    feature_id="market_regime_state",
                    reason_codes=(
                        "confirmed_market_regime_proxy_unavailable",
                    ),
                )
            )
        if unavailable:
            unavailable_features = tuple(
                sorted(unavailable, key=lambda item: item.feature_id)
            )
            for instrument_id in sorted(batch.member_ids, key=str):
                excluded_paths.append(
                    StrongLeaderPullbackDiagnosticExcludedPathV1(
                        as_of_session=batch.session,
                        instrument_id=instrument_id,
                        unavailable_features=unavailable_features,
                        source_max_session=batch.session,
                        source_fingerprint=_fingerprint(
                            {
                                "feature_source_fingerprint": (
                                    batch.feature_source_fingerprint
                                ),
                                "regime_state_fingerprint": (
                                    state.logical_fingerprint
                                ),
                                "unavailable_features": [
                                    item.model_dump(mode="json")
                                    for item in unavailable_features
                                ],
                            }
                        ),
                    )
                )
            continue
        assert regime is not None
        for feature in batch.features:
            source_fingerprint = _fingerprint(
                {
                    "feature_source_fingerprint": (
                        batch.feature_source_fingerprint
                    ),
                    "instrument_id": str(feature.instrument_id),
                    "regime_state_fingerprint": state.logical_fingerprint,
                    "state_history_fingerprint": state_fingerprint,
                }
            )
            observations.append(
                build_strong_leader_pullback_observation(
                    as_of_session=batch.session,
                    universe_id="primary",
                    instrument_id=feature.instrument_id,
                    ticker=batch.tickers[feature.instrument_id],
                    membership_mode=StrategyMembershipMode.POINT_IN_TIME,
                    membership_session=batch.session,
                    membership_included=True,
                    relative_strength_20s_percentile=(
                        feature.relative_strength_20s_percentile
                    ),
                    trend_quality_score=feature.trend_quality_score,
                    pullback_depth_atr=feature.pullback_depth_atr,
                    close_above_prior_close=feature.close_above_prior_close,
                    close_above_prior_high=feature.close_above_prior_high,
                    pullback_volume_ratio=feature.pullback_volume_ratio,
                    market_regime=regime,
                    source_max_session=batch.session,
                    source_fingerprint=source_fingerprint,
                )
            )
            if feature.instrument_id in batch.known_split_adjustment_ids:
                known_split_count += 1

    ordered_observations = tuple(
        sorted(observations, key=lambda item: (item.as_of_session, str(item.instrument_id)))
    )
    ordered_exclusions = tuple(
        sorted(excluded_paths, key=lambda item: (item.as_of_session, str(item.instrument_id)))
    )
    if len(ordered_observations) + len(ordered_exclusions) != launch.included_path_count:
        raise StrongLeaderPullbackDiagnosticsCliError(
            "diagnostic paths do not reconcile to the authorized population"
        )
    report = build_strong_leader_pullback_method_diagnostics(
        plan=plan,
        observations=ordered_observations,
        excluded_paths=ordered_exclusions,
        known_split_adjustment_applied_path_count=known_split_count,
    )
    report_path = write_strong_leader_pullback_diagnostics(
        output_root=output_root,
        output_custody_root=output_custody_root,
        report=report,
    )
    return report_path, report


def _build_session_batch(
    *,
    session: date,
    session_reads: tuple[EodHistorySessionRead, ...],
    member_ids: frozenset[UUID],
    membership_fingerprint: str,
    active_action_keys: set[tuple[UUID, date]],
    quarantined_action_keys: set[tuple[UUID, date]],
    unresolved_impact_keys: set[tuple[UUID, date]],
    clear_adjustments: Mapping[tuple[UUID, date], AdjustmentLedgerEntryV1],
    quarantined_adjustment_keys: set[tuple[UUID, date]],
    action_start: date,
    adjustment_start: date,
    action_fingerprint: str,
    adjustment_fingerprint: str,
    calendar: ExchangeCalendar,
):
    sessions = tuple(item.integrity.session_date for item in session_reads)
    if sessions[-1] != session or sessions != tuple(
        (*calendar.sessions_before(session, 20), session)
    ):
        raise StrongLeaderPullbackDiagnosticsCliError(
            "EOD feature window is not the exact 21-session interval"
        )
    by_session = {
        item.integrity.session_date: {
            bar.instrument_id: bar for bar in item.bars
        }
        for item in session_reads
    }
    current = by_session[session]
    benchmark_ids = _benchmark_ids(current)
    required_ids = member_ids | frozenset(benchmark_ids.values())
    source_fingerprint = _fingerprint(
        {
            "session": session.isoformat(),
            "membership_fingerprint": membership_fingerprint,
            "member_ids": [str(item) for item in sorted(member_ids, key=str)],
            "eod": [
                item.integrity.model_dump(mode="json") for item in session_reads
            ],
            "action_fingerprint": action_fingerprint,
            "adjustment_fingerprint": adjustment_fingerprint,
        }
    )
    missing_or_invalid = {
        instrument_id
        for instrument_id in required_ids
        if any(
            instrument_id not in by_session[source_session]
            or not _valid_bar(by_session[source_session].get(instrument_id))
            for source_session in sessions
        )
    }
    hazard_ids, clear_exposure_ids = _split_path_status(
        required_ids=required_ids,
        sessions=sessions,
        active_action_keys=active_action_keys,
        quarantined_action_keys=quarantined_action_keys,
        unresolved_impact_keys=unresolved_impact_keys,
        clear_adjustments=clear_adjustments,
        quarantined_adjustment_keys=quarantined_adjustment_keys,
        action_start=action_start,
        adjustment_start=adjustment_start,
    )
    reasons = set()
    if missing_or_invalid:
        reasons.add("complete_cross_section_eod_unavailable")
    if hazard_ids:
        reasons.add("complete_cross_section_split_evidence_quarantined")
    if reasons:
        return (
            _SessionFeatureBatch(
                session=session,
                member_ids=member_ids,
                tickers={
                    item: current[item].ticker
                    for item in member_ids
                    if item in current
                },
                features=(),
                feature_source_fingerprint=source_fingerprint,
                known_split_adjustment_ids=frozenset(),
                unavailable_feature_ids=PRICE_FEATURE_IDS,
                unavailable_reason_codes=tuple(sorted(reasons)),
            ),
            None,
        )

    adjusted = {
        instrument_id: tuple(
            _adjusted_bar(
                by_session[source_session][instrument_id],
                clear_adjustments.get((instrument_id, source_session)),
            )
            for source_session in sessions
        )
        for instrument_id in required_ids
    }
    try:
        feature_panel = calculate_strong_leader_pullback_features(
            member_ids=member_ids,
            benchmark_instrument_id=benchmark_ids["SPY"],
            series_by_instrument={
                instrument_id: adjusted[instrument_id]
                for instrument_id in member_ids | {benchmark_ids["SPY"]}
            },
        )
    except StrongLeaderPullbackFeatureError:
        return (
            _SessionFeatureBatch(
                session=session,
                member_ids=member_ids,
                tickers={item: current[item].ticker for item in member_ids},
                features=(),
                feature_source_fingerprint=source_fingerprint,
                known_split_adjustment_ids=frozenset(),
                unavailable_feature_ids=PRICE_FEATURE_IDS,
                unavailable_reason_codes=(
                    "complete_cross_section_feature_calculation_rejected",
                ),
            ),
            None,
        )
    if any(not _feature_contract_compatible(item) for item in feature_panel.features):
        return (
            _SessionFeatureBatch(
                session=session,
                member_ids=member_ids,
                tickers={item: current[item].ticker for item in member_ids},
                features=(),
                feature_source_fingerprint=source_fingerprint,
                known_split_adjustment_ids=frozenset(),
                unavailable_feature_ids=PRICE_FEATURE_IDS,
                unavailable_reason_codes=(
                    "complete_cross_section_feature_contract_rejected",
                ),
            ),
            None,
        )

    market_bars = tuple(
        MarketRegimeBar(
            instrument_id=instrument_id,
            ticker=by_session[source_session][instrument_id].ticker,
            instrument_type=(
                by_session[source_session][instrument_id].instrument_type.value
            ),
            primary_exchange=(
                by_session[source_session][instrument_id].primary_exchange
            ),
            session_date=source_session,
            open=adjusted[instrument_id][index].open,
            high=adjusted[instrument_id][index].high,
            low=adjusted[instrument_id][index].low,
            close=adjusted[instrument_id][index].close,
            volume=adjusted[instrument_id][index].volume,
        )
        for index, source_session in enumerate(sessions)
        for instrument_id in sorted(required_ids, key=str)
    )
    source_sessions = tuple(
        MarketRegimeSourceSession(
            session_date=item.integrity.session_date,
            dataset_path=(
                "market-data/eod-price-bars/schema_version=1/"
                f"session_date={item.integrity.session_date.isoformat()}"
            ),
            record_count=item.integrity.record_count,
            content_fingerprint=item.integrity.content_fingerprint,
            parquet_sha256=item.integrity.parquet_sha256,
            identity_snapshot_date=item.integrity.identity_snapshot_date,
            identity_snapshot_fingerprint=(
                item.integrity.identity_snapshot_fingerprint
            ),
        )
        for item in session_reads
    )
    panel = MarketRegimeInputPanel(
        as_of_session=session,
        calendar_id=calendar.calendar_id,
        calendar_version=calendar.calendar_version,
        sessions=sessions,
        source_sessions=source_sessions,
        bars=market_bars,
        universes=(
            MarketRegimeUniverseSource(
                universe_id="primary",
                display_name="Reconstructed Primary proxy",
                is_default=True,
                catalog_order=0,
                member_ids=member_ids,
                membership_fingerprint=membership_fingerprint,
            ),
        ),
        activation_pointer_fingerprint=_fingerprint(
            {
                "basis": "reconstructed_same_session_membership_proxy",
                "membership_fingerprint": membership_fingerprint,
            }
        ),
        identity_logical_fingerprint=(
            source_sessions[-1].identity_snapshot_fingerprint
        ),
        eod_content_fingerprint=source_sessions[-1].content_fingerprint,
        eod_business_key_fingerprint=_fingerprint(
            {
                "session": session.isoformat(),
                "instrument_ids": [
                    str(item) for item in sorted(current, key=str)
                ],
            }
        ),
        history_source_fingerprint=_fingerprint(
            [
                {
                    "session_date": item.session_date.isoformat(),
                    "record_count": item.record_count,
                    "content_fingerprint": item.content_fingerprint,
                    "parquet_sha256": item.parquet_sha256,
                    "identity_snapshot_date": (
                        item.identity_snapshot_date.isoformat()
                    ),
                    "identity_snapshot_fingerprint": (
                        item.identity_snapshot_fingerprint
                    ),
                }
                for item in source_sessions
            ]
        ),
    )
    composite, _ = calculate_market_regime(panel=panel, universe_id="primary")
    return (
        _SessionFeatureBatch(
            session=session,
            member_ids=member_ids,
            tickers={item: current[item].ticker for item in member_ids},
            features=feature_panel.features,
            feature_source_fingerprint=source_fingerprint,
            known_split_adjustment_ids=frozenset(
                member_ids & clear_exposure_ids
            ),
        ),
        composite,
    )


def _read_membership(*, shadow_root, partition, census_session):
    repository = ParquetHistoricalResearchRepository(
        _batch_root(shadow_root, partition)
    )
    records = repository.read_universe_membership(partition)
    manifest_raw = (partition / "manifest.json").read_bytes()
    manifest = UniverseMembershipPartitionManifestV1.model_validate_json(
        manifest_raw
    )
    manifest_sha256 = hashlib.sha256(manifest_raw).hexdigest()
    if (
        manifest.session_date != census_session.session_date
        or manifest.methodology_version
        != STRONG_LEADER_PULLBACK_CENSUS_MEMBERSHIP_METHODOLOGY
        or manifest.origin is not UniverseMembershipOrigin.RECONSTRUCTED_POINT_IN_TIME
        or manifest.record_count != len(records)
        or manifest.logical_fingerprint
        != census_session.membership_logical_fingerprint
        or manifest.physical_sha256
        != census_session.membership_physical_sha256
        or manifest_sha256 != census_session.membership_manifest_sha256
        or STRONG_LEADER_PULLBACK_CENSUS_PRIMARY_UNIVERSE
        not in manifest.universe_ids
    ):
        raise StrongLeaderPullbackDiagnosticsCliError(
            "Membership partition differs from the bound census"
        )
    seen = set()
    included = []
    for item in records:
        key = (item.universe_id, item.instrument_id)
        if (
            key in seen
            or item.session_date != manifest.session_date
            or item.methodology_version != manifest.methodology_version
            or item.origin is not manifest.origin
            or item.evaluated_base_fingerprint
            != manifest.evaluated_base_fingerprint
            or item.source_fingerprints != manifest.source_fingerprints
            or item.source_data_cutoff != manifest.source_data_cutoff
            or item.evaluated_at != manifest.evaluated_at
        ):
            raise StrongLeaderPullbackDiagnosticsCliError(
                "Membership row binding differs"
            )
        seen.add(key)
        if (
            item.universe_id == STRONG_LEADER_PULLBACK_CENSUS_PRIMARY_UNIVERSE
            and item.disposition is UniverseMembershipDisposition.INCLUDED
        ):
            included.append(item)
    if len(included) != census_session.primary_included_count:
        raise StrongLeaderPullbackDiagnosticsCliError(
            "Membership included count differs from the bound census"
        )
    return tuple(sorted(included, key=lambda item: str(item.instrument_id))), (
        manifest.logical_fingerprint
    )


def _benchmark_ids(current: Mapping[UUID, EodMarketBarReadModel]) -> dict[str, UUID]:
    output = {}
    for ticker in BROAD_BENCHMARK_TICKERS:
        matches = tuple(
            item.instrument_id
            for item in current.values()
            if item.ticker == ticker and item.instrument_type.value == "etf"
        )
        if len(matches) != 1:
            raise StrongLeaderPullbackDiagnosticsCliError(
                f"broad benchmark {ticker} is not uniquely available"
            )
        output[ticker] = matches[0]
    return output


def _split_path_status(
    *,
    required_ids: frozenset[UUID],
    sessions: tuple[date, ...],
    active_action_keys: set[tuple[UUID, date]],
    quarantined_action_keys: set[tuple[UUID, date]],
    unresolved_impact_keys: set[tuple[UUID, date]],
    clear_adjustments: Mapping[tuple[UUID, date], AdjustmentLedgerEntryV1],
    quarantined_adjustment_keys: set[tuple[UUID, date]],
    action_start: date,
    adjustment_start: date,
) -> tuple[frozenset[UUID], frozenset[UUID]]:
    if sessions[0] < action_start or sessions[0] < adjustment_start:
        return required_ids, frozenset()
    hazard = set()
    clear_exposure = set()
    source_dates = frozenset(sessions)
    event_dates = frozenset(sessions[1:])
    for instrument_id in required_ids:
        source_keys = {(instrument_id, item) for item in source_dates}
        event_keys = {(instrument_id, item) for item in event_dates}
        active = bool(event_keys & active_action_keys)
        clear = any(key in clear_adjustments for key in source_keys)
        if active and clear:
            clear_exposure.add(instrument_id)
        if bool(
            event_keys & (quarantined_action_keys | unresolved_impact_keys)
        ) or (
            active
            and (
                not clear
                or bool(source_keys & quarantined_adjustment_keys)
            )
        ):
            hazard.add(instrument_id)
    return frozenset(hazard), frozenset(clear_exposure)


def _adjusted_bar(
    bar: EodMarketBarReadModel, adjustment: AdjustmentLedgerEntryV1 | None
) -> StrongLeaderPullbackFeatureBar:
    price = Decimal("1")
    volume = Decimal("1")
    if adjustment is not None:
        price = adjustment.split_price_multiplier_to_basis
        volume = adjustment.split_volume_multiplier_to_basis
        if price is None or volume is None:
            raise StrongLeaderPullbackDiagnosticsCliError(
                "clear split adjustment lacks factors"
            )
    return StrongLeaderPullbackFeatureBar(
        session=bar.session_date,
        open=bar.open * price,
        high=bar.high * price,
        low=bar.low * price,
        close=bar.close * price,
        volume=bar.volume * volume,
    )


def _valid_bar(bar: EodMarketBarReadModel | None) -> bool:
    return bool(
        bar is not None
        and bar.quality_status is QualityStatus.VALID
        and bar.currency == "USD"
        and all(
            isinstance(value, Decimal) and value.is_finite()
            for value in (bar.open, bar.high, bar.low, bar.close, bar.volume)
        )
        and min(bar.open, bar.high, bar.low, bar.close) > 0
        and bar.volume >= 0
    )


def _feature_contract_compatible(
    feature: StrongLeaderPullbackComputedFeatures,
) -> bool:
    values = (
        (
            Decimal(feature.relative_strength_20s_percentile),
            Decimal("0"),
            Decimal("1"),
        ),
        (Decimal(feature.trend_quality_score), Decimal("0"), Decimal("100")),
    )
    return (
        all(
            value.is_finite() and low <= value <= high
            for value, low, high in values
        )
        and Decimal(feature.pullback_depth_atr).is_finite()
        and Decimal(feature.pullback_volume_ratio).is_finite()
        and Decimal(feature.pullback_volume_ratio) >= 0
    )


def _validate_launch_and_census(*, launch, census) -> None:
    sessions = tuple(item.session_date for item in census.sessions)
    if (
        not launch.method_engineering_authorized
        or not launch.private_outcome_blind_feature_diagnostics_authorized
        or launch.true_return_labels_authorized
        or launch.parameter_selection_authorized
        or launch.formal_development_stage_authorized
        or launch.validation_authorized
        or launch.holdout_access_authorized
        or launch.candidate_activation_authorized
        or census.first_session != STRONG_LEADER_PULLBACK_CENSUS_FIRST_SESSION
        or census.last_session != STRONG_LEADER_PULLBACK_CENSUS_LAST_SESSION
        or len(sessions) != launch.signal_session_count
        or census.primary_included_count != launch.included_path_count
        or sessions != tuple(sorted(set(sessions)))
    ):
        raise StrongLeaderPullbackDiagnosticsCliError(
            "method launch or development census boundary differs"
        )


def _validate_census_sources(
    *, census, action_fingerprint: str, adjustment_fingerprint: str
) -> None:
    by_family = {item.family: item for item in census.dataset_evidence}
    if (
        by_family["corporate_action"].logical_fingerprint != action_fingerprint
        or by_family["adjustment_ledger"].logical_fingerprint
        != adjustment_fingerprint
    ):
        raise StrongLeaderPullbackDiagnosticsCliError(
            "split evidence differs from the bound development census"
        )


def _regime_label(value: RegimeState) -> str:
    return {
        RegimeState.RISK_ON: "Risk-on",
        RegimeState.BALANCED: "Balanced",
        RegimeState.DEFENSIVE: "Defensive",
        RegimeState.STRESS: "Stress",
    }[value]


def _fingerprint(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            _canonical(value),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _canonical(value: object):
    if isinstance(value, BaseModel):
        return _canonical(value.model_dump(mode="json"))
    if isinstance(value, Mapping):
        return {str(key): _canonical(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_canonical(item) for item in value]
    if isinstance(value, (date, UUID, Decimal)):
        return str(value)
    return value


def _safe_error_detail(exc: Exception) -> object:
    if hasattr(exc, "errors"):
        return tuple(
            {
                "location": ".".join(str(item) for item in error.get("loc", ())),
                "type": str(error.get("type", "unknown")),
                "message": str(error.get("msg", "validation failed")),
            }
            for error in exc.errors(include_url=False, include_input=False)[:10]
        )
    return str(exc)[:500]


@contextmanager
def _network_disabled() -> Iterator[None]:
    original_socket = socket.socket

    def blocked_socket(*_args: object, **_kwargs: object):
        raise RuntimeError("network access is disabled for method diagnostics")

    socket.socket = blocked_socket  # type: ignore[assignment]
    try:
        yield
    finally:
        socket.socket = original_socket  # type: ignore[assignment]


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
