"""Derive only fail-closed gaps from an exact A-share diagnostic package."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from tip_api.contracts.china_ashare.v1.full_population_gaps import (
    ChinaAshareDynamicGapEntryV1,
    ChinaAshareDynamicGapFamily,
    ChinaAshareDynamicGapMeasureV1,
    ChinaAshareFullPopulationGapChecklistV1,
    build_full_population_gap_checklist,
)
from tip_api.persistence.china_ashare_full_population_diagnostic_package import (
    ChinaAshareFullPopulationDiagnosticAggregateResultV1,
    read_china_ashare_full_population_diagnostic_aggregate,
    read_china_ashare_full_population_diagnostic_plan,
)
from tip_api.persistence.china_ashare_full_population_gap_checklist import (
    ChinaAshareFullPopulationGapChecklistResultV1,
    publish_china_ashare_full_population_gap_checklist,
)


class ChinaAshareFullPopulationGapReplayError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class ChinaAshareFullPopulationGapReplayResultV1:
    primary: ChinaAshareFullPopulationGapChecklistResultV1
    replay: ChinaAshareFullPopulationGapChecklistResultV1
    byte_identical: bool
    physical_hash_identical: bool


def build_china_ashare_full_population_gap_checklist(
    *, diagnostic: ChinaAshareFullPopulationDiagnosticAggregateResultV1
) -> ChinaAshareFullPopulationGapChecklistV1:
    partitions = diagnostic.partitions

    def total(field: str) -> int:
        return sum(int(getattr(item, field)) for item in partitions)

    streaming = diagnostic.streaming
    return build_full_population_gap_checklist(
        diagnostic_plan_fingerprint=diagnostic.plan.logical_fingerprint,
        diagnostic_package_fingerprint=diagnostic.manifest.logical_fingerprint,
        streaming_aggregate_fingerprint=streaming.logical_fingerprint,
        partition_aggregate_fingerprints=(
            streaming.partition_aggregate_fingerprints
        ),
        entries=(
            _entry(
                1,
                ChinaAshareDynamicGapFamily.PRICE_LIMIT_RULES,
                measures=(
                    _measure(
                        "price_limit_unknown_state_count",
                        streaming.price_limit_unknown_count,
                        "state",
                    ),
                ),
                blockers=(
                    "effective_dated_official_rule_evidence_missing",
                    "price_limit_regime_unknown",
                ),
            ),
            _entry(
                2,
                ChinaAshareDynamicGapFamily.WARNING_STATE,
                measures=(
                    _measure(
                        "risk_warning_present_unspecified_state_count",
                        streaming.risk_warning_present_unspecified_count,
                        "state",
                    ),
                    _measure(
                        "risk_warning_unknown_state_count",
                        total("risk_warning_unknown_count"),
                        "state",
                    ),
                ),
                blockers=(
                    "effective_dated_official_warning_evidence_missing",
                    "warning_subtype_unspecified",
                ),
            ),
            _entry(
                3,
                ChinaAshareDynamicGapFamily.CORPORATE_ACTION,
                measures=(
                    _measure(
                        "adjustment_change_candidate_count",
                        streaming.adjustment_changed_observation_count,
                        "factor_change_candidate",
                    ),
                    _measure(
                        "adjustment_observation_count",
                        streaming.adjustment_count,
                        "adjustment_observation",
                    ),
                ),
                blockers=(
                    "corporate_action_terms_missing",
                    "factor_movement_is_not_action_proof",
                ),
            ),
            _entry(
                4,
                ChinaAshareDynamicGapFamily.INSTRUMENT_LIFECYCLE,
                measures=(
                    _measure(
                        "quarantined_target_count",
                        streaming.quarantined_target_count,
                        "target",
                    ),
                    _measure(
                        "not_listed_state_count",
                        total("not_listed_state_count"),
                        "state",
                    ),
                    _measure(
                        "unknown_trading_state_count",
                        total("unknown_trading_state_count"),
                        "state",
                    ),
                ),
                blockers=(
                    "listed_security_terminal_evidence_missing",
                    "quarantined_identity_evidence_missing",
                ),
            ),
            _entry(
                5,
                ChinaAshareDynamicGapFamily.HISTORICAL_UNIVERSE,
                measures=(
                    _measure(
                        "unmaterialized_resolved_state_decision_count",
                        streaming.state_count,
                        "instrument_session_state",
                    ),
                    _measure(
                        "source_available_at_null_state_count",
                        streaming.source_available_at_null_state_count,
                        "state",
                    ),
                    _measure(
                        "quarantined_target_count",
                        streaming.quarantined_target_count,
                        "target",
                    ),
                ),
                blockers=(
                    "daily_universe_decisions_absent",
                    "dependency_families_blocked",
                    "point_in_time_source_clock_missing",
                ),
            ),
        ),
        admitted_family_count=0,
        future_return_read_count=0,
        full_universe_rows_materialized=False,
        historical_coverage_authorized=False,
        adjusted_return_authorized=False,
        research_backtest_authorized=False,
        factor_discovery_authorized=False,
        canonical_apply_authorized=False,
        product_publication_authorized=False,
    )


def build_and_replay_china_ashare_full_population_gap_checklist(
    *,
    diagnostic_plan_package: Path,
    diagnostic_aggregate_package: Path,
    output_custody_root: Path,
    replay_custody_root: Path,
) -> ChinaAshareFullPopulationGapReplayResultV1:
    if output_custody_root.expanduser().resolve() == (
        replay_custody_root.expanduser().resolve()
    ):
        raise ChinaAshareFullPopulationGapReplayError(
            "dynamic gap replay custody must be independent"
        )
    primary = _build_and_publish(
        diagnostic_plan_package=diagnostic_plan_package,
        diagnostic_aggregate_package=diagnostic_aggregate_package,
        custody_root=output_custody_root,
    )
    replay = _build_and_publish(
        diagnostic_plan_package=diagnostic_plan_package,
        diagnostic_aggregate_package=diagnostic_aggregate_package,
        custody_root=replay_custody_root,
    )
    primary_bytes = primary.checklist_path.read_bytes()
    replay_bytes = replay.checklist_path.read_bytes()
    return ChinaAshareFullPopulationGapReplayResultV1(
        primary=primary,
        replay=replay,
        byte_identical=primary_bytes == replay_bytes,
        physical_hash_identical=(
            primary.physical_sha256 == replay.physical_sha256
        ),
    )


def _build_and_publish(
    *,
    diagnostic_plan_package: Path,
    diagnostic_aggregate_package: Path,
    custody_root: Path,
) -> ChinaAshareFullPopulationGapChecklistResultV1:
    plan = read_china_ashare_full_population_diagnostic_plan(
        package_path=diagnostic_plan_package
    )
    diagnostic = read_china_ashare_full_population_diagnostic_aggregate(
        plan_result=plan,
        package_path=diagnostic_aggregate_package,
    )
    checklist = build_china_ashare_full_population_gap_checklist(
        diagnostic=diagnostic
    )
    return publish_china_ashare_full_population_gap_checklist(
        custody_root=custody_root,
        checklist=checklist,
    )


def _measure(
    measure_id: str, count: int, unit: str
) -> ChinaAshareDynamicGapMeasureV1:
    return ChinaAshareDynamicGapMeasureV1(
        measure_id=measure_id,
        count=count,
        unit=unit,
    )


def _entry(
    ordinal: int,
    family: ChinaAshareDynamicGapFamily,
    *,
    measures: tuple[ChinaAshareDynamicGapMeasureV1, ...],
    blockers: tuple[str, ...],
) -> ChinaAshareDynamicGapEntryV1:
    return ChinaAshareDynamicGapEntryV1(
        ordinal=ordinal,
        family=family,
        measures=measures,
        blocker_codes=tuple(sorted(blockers)),
        external_official_evidence_required=True,
        admission_authorized=False,
    )
