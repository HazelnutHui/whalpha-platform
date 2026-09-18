"""Streaming candidate census for conservative reconstructed A-share research."""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict

from tip_api.contracts.china_ashare.v1.cninfo_event_evidence import (
    ChinaAshareCninfoParseStatus,
    ChinaAshareCninfoRequestKind,
)
from tip_api.contracts.china_ashare.v1.conservative_reconstruction_census import (
    ChinaAshareConservativeEvidenceCandidateV1,
    ChinaAshareOfficialEvidenceBudgetTierV1,
    ChinaAshareOfficialEvidenceBudgetFamily,
    build_conservative_partition_census,
    build_conservative_reconstruction_census,
    build_conservative_reconstruction_plan,
    build_price_limit_smoke,
    candidate_set_fingerprint,
)
from tip_api.contracts.china_ashare.v1.foundation import (
    ChinaAshareBoard,
    ChinaAshareRiskWarningStatus,
    ChinaAshareTradingStatus,
)
from tip_api.contracts.china_ashare.v1.conservative_reconstructed_universe import (
    ChinaAshareConservativeUniverseDisposition,
    ChinaAshareConservativeUniverseRowV1,
)
from tip_api.contracts.china_ashare.v1.population import (
    ChinaAsharePopulationDisposition,
)
from tip_api.contracts.china_ashare.v1.price_limit_resolver import (
    ChinaAshareListingStage,
)
from tip_api.services.china_ashare_price_limit_resolver import (
    resolve_china_ashare_price_limit,
)


_SUPPORTED_BOARDS = {
    ChinaAshareBoard.SSE_MAIN,
    ChinaAshareBoard.STAR,
    ChinaAshareBoard.SZSE_MAIN,
    ChinaAshareBoard.CHINEXT,
}
_REQUEST_COUNTS = {
    ChinaAshareOfficialEvidenceBudgetFamily.RISK_WARNING: 1,
    ChinaAshareOfficialEvidenceBudgetFamily.LIFECYCLE: 4,
    ChinaAshareOfficialEvidenceBudgetFamily.LISTING_STAGE: 1,
    ChinaAshareOfficialEvidenceBudgetFamily.CORPORATE_ACTION: 0,
}


def cninfo_replay_set_fingerprint(*, plan, replay_captures) -> str:
    by_id = {item.query_id: item for item in replay_captures}
    if set(by_id) != {item.query_id for item in plan.queries}:
        raise ValueError("CNINFO replay capture set differs")
    payload = [
        (query.query_id, by_id[query.query_id].logical_fingerprint)
        for query in plan.queries
    ]
    return _fingerprint(payload)


def plan_conservative_reconstruction_census(
    *,
    source_plan,
    population,
    diagnostic_plan,
    mechanics,
    price_limit_resolver_plan,
    cninfo_plan,
    cninfo_replay_captures,
    target_sessions,
):
    replay_fingerprint = cninfo_replay_set_fingerprint(
        plan=cninfo_plan, replay_captures=cninfo_replay_captures
    )
    return build_conservative_reconstruction_plan(
        source_expansion_plan_fingerprint=source_plan.plan.logical_fingerprint,
        population_package_fingerprint=population.manifest.logical_fingerprint,
        normalized_run_fingerprint=diagnostic_plan.plan.normalized_run_fingerprint,
        normalized_partition_manifest_fingerprints=(
            diagnostic_plan.plan.normalized_partition_manifest_fingerprints
        ),
        market_mechanics_package_fingerprint=mechanics.manifest.logical_fingerprint,
        price_limit_resolver_plan_fingerprint=(
            price_limit_resolver_plan.logical_fingerprint
        ),
        cninfo_sample_plan_fingerprint=cninfo_plan.logical_fingerprint,
        cninfo_sample_replay_set_fingerprint=replay_fingerprint,
        interval_start=source_plan.plan.interval_start,
        interval_end=source_plan.plan.interval_end,
        target_sessions=tuple(target_sessions),
        official_evidence_priority=(
            ChinaAshareOfficialEvidenceBudgetFamily.RISK_WARNING,
            ChinaAshareOfficialEvidenceBudgetFamily.LIFECYCLE,
            ChinaAshareOfficialEvidenceBudgetFamily.LISTING_STAGE,
        ),
        official_confirmed_requires_all_families=True,
        provider_provisional_as_operated=False,
        provider_provisional_excludes_warning_windows=True,
        provider_provisional_quarantines_action_windows=True,
        provider_provisional_quarantines_terminal_boundaries=True,
        provider_provisional_quarantines_unknown_states=True,
        provider_provisional_reconstructs_normal_limits_from_official_mechanics=True,
        provider_provisional_personal_research_candidate_only=True,
        maximum_requests_per_warning_candidate=1,
        maximum_requests_per_lifecycle_candidate=4,
        maximum_requests_per_listing_candidate=1,
        maximum_requests_per_action_candidate=0,
        action_candidates_remain_isolated_without_official_requests=True,
        outcome_read_count=0,
        return_construction_authorized=False,
        historical_coverage_authorized=False,
        research_backtest_authorized=False,
        factor_discovery_authorized=False,
        product_publication_authorized=False,
    )


def build_sz000001_price_limit_smoke(
    *,
    plan,
    cninfo_plan,
    cninfo_replay_captures,
    source_partition,
    normalized_partition,
    mechanics,
    price_limit_resolver_plan,
):
    if source_partition.partition.partition_index != 47:
        raise ValueError("CNINFO resolver smoke partition differs")
    by_query = {item.query_id: item for item in cninfo_replay_captures}
    if set(by_query) != {item.query_id for item in cninfo_plan.queries}:
        raise ValueError("CNINFO resolver smoke capture set differs")
    if any(
        item.parse_status is not ChinaAshareCninfoParseStatus.PARSED
        or item.announcements
        for item in by_query.values()
    ):
        raise ValueError("CNINFO resolver smoke requires official zero events")
    target = next(
        item
        for item in source_partition.partition.targets
        if item.source_security_id == "sz.000001"
    )
    instrument_by_source = _instrument_by_source(normalized_partition)
    instrument_id = instrument_by_source["sz.000001"]
    states = tuple(
        item
        for item in normalized_partition.normalized.states
        if item.instrument_id == instrument_id
    )
    if not states or any(
        item.risk_warning_status is not ChinaAshareRiskWarningStatus.NONE
        for item in states
    ):
        raise ValueError("CNINFO resolver smoke provider states differ")
    resolutions = tuple(
        resolve_china_ashare_price_limit(
            plan=price_limit_resolver_plan,
            trading_rules=mechanics.trading_rules,
            instrument_id=state.instrument_id,
            session_date=state.session_date,
            exchange=state.exchange,
            board=state.board,
            risk_warning_status=state.risk_warning_status,
            listing_date=target.listing_date,
            listing_stage=ChinaAshareListingStage.MATURE_LISTING,
            listing_session_ordinal=None,
            original_listing_evidence_complete=True,
            risk_warning_evidence_complete=True,
            relisting_absence_evidence_complete=True,
            terminal_boundary_absence_evidence_complete=True,
            input_partition_manifest_fingerprint=(
                normalized_partition.manifest.logical_fingerprint
            ),
        )
        for state in states
    )
    resolved_count = sum(item.status.value == "resolved" for item in resolutions)
    return build_price_limit_smoke(
        instrument_id=instrument_id,
        cninfo_plan_fingerprint=cninfo_plan.logical_fingerprint,
        cninfo_replay_set_fingerprint=plan.cninfo_sample_replay_set_fingerprint,
        normalized_partition_manifest_fingerprint=(
            normalized_partition.manifest.logical_fingerprint
        ),
        price_limit_resolver_plan_fingerprint=(
            price_limit_resolver_plan.logical_fingerprint
        ),
        state_count=len(resolutions),
        resolved_count=resolved_count,
        quarantined_count=len(resolutions) - resolved_count,
        resolution_set_fingerprint=_fingerprint(
            [item.model_dump(mode="json") for item in resolutions]
        ),
        official_zero_event_evidence=True,
        as_operated=False,
        outcome_read_count=0,
        historical_coverage_authorized=False,
        research_backtest_authorized=False,
    )


def scan_conservative_reconstruction_partition(
    *,
    plan,
    source_partition,
    normalized_partition,
    population_occurrences_by_fingerprint,
):
    index = source_partition.partition.partition_index
    if (
        normalized_partition.manifest.partition_index != index
        or plan.normalized_partition_manifest_fingerprints[index]
        != normalized_partition.manifest.logical_fingerprint
    ):
        raise ValueError("conservative census partition binding differs")
    instrument_by_source = _instrument_by_source(normalized_partition)
    states_by_instrument = defaultdict(list)
    for state in normalized_partition.normalized.states:
        states_by_instrument[state.instrument_id].append(state)
    factor_changes = _factor_change_dates(normalized_partition)
    records = []
    included = excluded = quarantined = 0
    family_security_counts: Counter = Counter()
    for target in source_partition.partition.targets:
        isolated = target.disposition is ChinaAsharePopulationDisposition.QUARANTINED
        occurrence = population_occurrences_by_fingerprint.get(
            target.population_occurrence_fingerprint
        )
        if occurrence is None or occurrence.source_security_id != target.source_security_id:
            raise ValueError("source target population occurrence differs")
        instrument_id = occurrence.instrument_id
        observed_instrument_id = instrument_by_source.get(target.source_security_id)
        if isolated != (instrument_id is None):
            raise ValueError("source target population identity differs")
        if (
            observed_instrument_id is not None
            and observed_instrument_id != instrument_id
        ):
            raise ValueError("normalized source identity differs from population")
        states = [] if instrument_id is None else states_by_instrument[instrument_id]
        warning_present = sum(
            item.risk_warning_status
            not in {ChinaAshareRiskWarningStatus.NONE, ChinaAshareRiskWarningStatus.UNKNOWN}
            for item in states
        )
        warning_unknown = sum(
            item.risk_warning_status is ChinaAshareRiskWarningStatus.UNKNOWN
            for item in states
        )
        trading_unknown = sum(
            item.trading_status is ChinaAshareTradingStatus.UNKNOWN for item in states
        )
        changed_dates = set() if instrument_id is None else factor_changes[instrument_id]
        last_date = max((item.session_date for item in states), default=None)
        terminal = last_date is not None and last_date < plan.interval_end
        listing_uncertain = isolated or target.listing_date >= plan.interval_start
        families = set()
        if warning_present or warning_unknown:
            families.add(ChinaAshareOfficialEvidenceBudgetFamily.RISK_WARNING)
        if isolated or terminal or trading_unknown or not states:
            families.add(ChinaAshareOfficialEvidenceBudgetFamily.LIFECYCLE)
        if listing_uncertain:
            families.add(ChinaAshareOfficialEvidenceBudgetFamily.LISTING_STAGE)
        if changed_dates:
            families.add(ChinaAshareOfficialEvidenceBudgetFamily.CORPORATE_ACTION)
        ordered_families = tuple(sorted(families, key=lambda item: str(item)))
        if ordered_families:
            for family in ordered_families:
                family_security_counts[family] += 1
            records.append(
                ChinaAshareConservativeEvidenceCandidateV1(
                    source_security_id=target.source_security_id,
                    instrument_id=instrument_id,
                    partition_index=index,
                    source_target_quarantined=isolated,
                    observed_state_count=len(states),
                    warning_present_state_count=warning_present,
                    warning_unknown_state_count=warning_unknown,
                    trading_status_unknown_state_count=trading_unknown,
                    factor_change_candidate_count=len(changed_dates),
                    terminal_boundary_candidate=terminal,
                    listing_stage_uncertain=listing_uncertain,
                    requested_families=ordered_families,
                    maximum_official_request_count=sum(
                        _REQUEST_COUNTS[item] for item in ordered_families
                    ),
                )
            )
        for state in states:
            is_quarantined = (
                listing_uncertain
                or state.risk_warning_status is ChinaAshareRiskWarningStatus.UNKNOWN
                or state.trading_status is ChinaAshareTradingStatus.UNKNOWN
                or state.board not in _SUPPORTED_BOARDS
                or state.session_date in changed_dates
                or (terminal and state.session_date == last_date)
                or state.session_date == plan.interval_end
            )
            is_excluded = (
                state.risk_warning_status
                not in {
                    ChinaAshareRiskWarningStatus.NONE,
                    ChinaAshareRiskWarningStatus.UNKNOWN,
                }
            )
            if is_quarantined:
                quarantined += 1
            elif is_excluded:
                excluded += 1
            else:
                included += 1
    ordered_records = tuple(sorted(records, key=lambda item: item.source_security_id))
    return build_conservative_partition_census(
        plan_fingerprint=plan.logical_fingerprint,
        partition_index=index,
        normalized_partition_manifest_fingerprint=(
            normalized_partition.manifest.logical_fingerprint
        ),
        target_count=len(source_partition.partition.targets),
        resolved_target_count=sum(
            item.disposition is ChinaAsharePopulationDisposition.RESOLVED
            for item in source_partition.partition.targets
        ),
        isolated_target_count=sum(
            item.disposition is ChinaAsharePopulationDisposition.QUARANTINED
            for item in source_partition.partition.targets
        ),
        state_count=len(normalized_partition.normalized.states),
        provisional_candidate_included_state_count=included,
        provisional_candidate_excluded_state_count=excluded,
        provisional_quarantined_state_count=quarantined,
        warning_present_state_count=sum(
            item.warning_present_state_count for item in ordered_records
        ),
        warning_unknown_state_count=sum(
            item.warning_unknown_state_count for item in ordered_records
        ),
        trading_status_unknown_state_count=sum(
            item.trading_status_unknown_state_count for item in ordered_records
        ),
        factor_change_candidate_window_count=sum(
            item.factor_change_candidate_count for item in ordered_records
        ),
        terminal_boundary_candidate_security_count=sum(
            item.terminal_boundary_candidate for item in ordered_records
        ),
        resolved_empty_state_target_count=sum(
            not item.source_target_quarantined and item.observed_state_count == 0
            for item in ordered_records
        ),
        warning_candidate_security_count=family_security_counts[
            ChinaAshareOfficialEvidenceBudgetFamily.RISK_WARNING
        ],
        lifecycle_candidate_security_count=family_security_counts[
            ChinaAshareOfficialEvidenceBudgetFamily.LIFECYCLE
        ],
        listing_stage_candidate_security_count=family_security_counts[
            ChinaAshareOfficialEvidenceBudgetFamily.LISTING_STAGE
        ],
        action_candidate_security_count=family_security_counts[
            ChinaAshareOfficialEvidenceBudgetFamily.CORPORATE_ACTION
        ],
        candidate_records=ordered_records,
        candidate_set_fingerprint=candidate_set_fingerprint(ordered_records),
        maximum_official_request_count=sum(
            item.maximum_official_request_count for item in ordered_records
        ),
        outcome_read_count=0,
        research_backtest_authorized=False,
    )


def merge_conservative_reconstruction_census(*, plan, partitions):
    ordered = tuple(sorted(partitions, key=lambda item: item.partition_index))
    if tuple(item.partition_index for item in ordered) != tuple(range(109)):
        raise ValueError("conservative census partition set differs")
    records = tuple(
        sorted(
            (record for item in ordered for record in item.candidate_records),
            key=lambda item: item.source_security_id,
        )
    )
    if len({item.source_security_id for item in records}) != len(records):
        raise ValueError("conservative census candidate IDs differ")
    total_budget = sum(item.maximum_official_request_count for item in records)
    target_count = sum(item.target_count for item in ordered)
    blind_baseline = target_count * 5
    return build_conservative_reconstruction_census(
        plan_fingerprint=plan.logical_fingerprint,
        partition_census_fingerprints=tuple(
            item.logical_fingerprint for item in ordered
        ),
        target_count=target_count,
        resolved_target_count=sum(item.resolved_target_count for item in ordered),
        isolated_target_count=sum(item.isolated_target_count for item in ordered),
        state_count=sum(item.state_count for item in ordered),
        provisional_candidate_included_state_count=sum(
            item.provisional_candidate_included_state_count for item in ordered
        ),
        provisional_candidate_excluded_state_count=sum(
            item.provisional_candidate_excluded_state_count for item in ordered
        ),
        provisional_quarantined_state_count=sum(
            item.provisional_quarantined_state_count for item in ordered
        ),
        warning_present_state_count=sum(
            item.warning_present_state_count for item in ordered
        ),
        warning_unknown_state_count=sum(
            item.warning_unknown_state_count for item in ordered
        ),
        trading_status_unknown_state_count=sum(
            item.trading_status_unknown_state_count for item in ordered
        ),
        factor_change_candidate_window_count=sum(
            item.factor_change_candidate_window_count for item in ordered
        ),
        terminal_boundary_candidate_security_count=sum(
            item.terminal_boundary_candidate_security_count for item in ordered
        ),
        resolved_empty_state_target_count=sum(
            item.resolved_empty_state_target_count for item in ordered
        ),
        official_confirmed_full_family_security_count=0,
        warning_candidate_security_count=sum(
            item.warning_candidate_security_count for item in ordered
        ),
        lifecycle_candidate_security_count=sum(
            item.lifecycle_candidate_security_count for item in ordered
        ),
        listing_stage_candidate_security_count=sum(
            item.listing_stage_candidate_security_count for item in ordered
        ),
        action_candidate_security_count=sum(
            item.action_candidate_security_count for item in ordered
        ),
        candidate_security_count=len(records),
        candidate_set_fingerprint=candidate_set_fingerprint(records),
        official_request_budget_by_priority=(
            ChinaAshareOfficialEvidenceBudgetTierV1(
                priority=1,
                family=ChinaAshareOfficialEvidenceBudgetFamily.RISK_WARNING,
                deduplicated_security_count=sum(
                    item.warning_candidate_security_count for item in ordered
                ),
                maximum_requests_per_security=1,
                maximum_request_count=sum(
                    item.warning_candidate_security_count for item in ordered
                ),
            ),
            ChinaAshareOfficialEvidenceBudgetTierV1(
                priority=2,
                family=ChinaAshareOfficialEvidenceBudgetFamily.LIFECYCLE,
                deduplicated_security_count=sum(
                    item.lifecycle_candidate_security_count for item in ordered
                ),
                maximum_requests_per_security=4,
                maximum_request_count=4
                * sum(item.lifecycle_candidate_security_count for item in ordered),
            ),
            ChinaAshareOfficialEvidenceBudgetTierV1(
                priority=3,
                family=ChinaAshareOfficialEvidenceBudgetFamily.LISTING_STAGE,
                deduplicated_security_count=sum(
                    item.listing_stage_candidate_security_count for item in ordered
                ),
                maximum_requests_per_security=1,
                maximum_request_count=sum(
                    item.listing_stage_candidate_security_count for item in ordered
                ),
            ),
        ),
        maximum_official_request_count=total_budget,
        blind_baseline_request_count=blind_baseline,
        avoided_request_count=blind_baseline - total_budget,
        outcome_read_count=0,
        return_construction_authorized=False,
        historical_coverage_authorized=False,
        research_backtest_authorized=False,
        product_publication_authorized=False,
    )


def build_conservative_universe_partition_rows(
    *, plan, partition_census, source_partition, normalized_partition,
    population_occurrences_by_fingerprint,
):
    """Build one bounded partition and prove it reconciles to the prior census."""
    index = source_partition.partition.partition_index
    if (
        partition_census.partition_index != index
        or partition_census.plan_fingerprint != plan.logical_fingerprint
        or partition_census.normalized_partition_manifest_fingerprint
        != normalized_partition.manifest.logical_fingerprint
    ):
        raise ValueError("conservative Universe partition binding differs")
    next_session = {
        session: plan.target_sessions[position + 1]
        for position, session in enumerate(plan.target_sessions[:-1])
    }
    source_by_instrument = {}
    listing_uncertain_by_instrument = {}
    for target in source_partition.partition.targets:
        occurrence = population_occurrences_by_fingerprint.get(
            target.population_occurrence_fingerprint
        )
        if occurrence is None or occurrence.source_security_id != target.source_security_id:
            raise ValueError("source target population occurrence differs")
        if occurrence.instrument_id is not None:
            source_by_instrument[occurrence.instrument_id] = target.source_security_id
            listing_uncertain_by_instrument[occurrence.instrument_id] = (
                target.listing_date >= plan.interval_start
            )
    factor_changes = _factor_change_dates(normalized_partition)
    last_date_by_instrument = {}
    for state in normalized_partition.normalized.states:
        last_date_by_instrument[state.instrument_id] = max(
            state.session_date,
            last_date_by_instrument.get(state.instrument_id, state.session_date),
        )
    rows = []
    for state in normalized_partition.normalized.states:
        source_security_id = source_by_instrument.get(state.instrument_id)
        if source_security_id is None:
            raise ValueError("normalized state lacks population identity")
        terminal = last_date_by_instrument[state.instrument_id] < plan.interval_end
        reasons = {
            "provider_reconstructed_not_as_operated",
            "source_available_at_unobserved",
        }
        knowledge_session_date = next_session.get(state.session_date)
        if knowledge_session_date is None:
            reasons.add("next_session_knowledge_clock_unavailable")
        else:
            reasons.add("next_session_reconstructed_knowledge_clock")
        quarantined = False
        if listing_uncertain_by_instrument[state.instrument_id]:
            reasons.add("listing_stage_not_officially_adjudicated")
            quarantined = True
        if state.risk_warning_status is ChinaAshareRiskWarningStatus.UNKNOWN:
            reasons.add("risk_warning_status_unknown")
            quarantined = True
        if state.trading_status is ChinaAshareTradingStatus.UNKNOWN:
            reasons.add("trading_status_unknown")
            quarantined = True
        if state.board not in _SUPPORTED_BOARDS:
            reasons.add("official_normal_price_limit_rule_unsupported")
            quarantined = True
        if state.session_date in factor_changes[state.instrument_id]:
            reasons.add("factor_change_candidate_window")
            quarantined = True
        if terminal and state.session_date == last_date_by_instrument[state.instrument_id]:
            reasons.add("terminal_boundary_not_officially_adjudicated")
            quarantined = True
        if knowledge_session_date is None:
            quarantined = True
        warning = state.risk_warning_status not in {
            ChinaAshareRiskWarningStatus.NONE,
            ChinaAshareRiskWarningStatus.UNKNOWN,
        }
        if quarantined:
            disposition = ChinaAshareConservativeUniverseDisposition.QUARANTINE
        elif warning:
            disposition = ChinaAshareConservativeUniverseDisposition.WARNING_EXCLUDE
            reasons.add("provider_risk_warning_window_excluded")
        else:
            disposition = ChinaAshareConservativeUniverseDisposition.PROVISIONAL_INCLUDE
            reasons.add("official_normal_price_limit_mechanics_bound")
        rows.append(ChinaAshareConservativeUniverseRowV1(
            partition_index=index,
            instrument_id=state.instrument_id,
            source_security_id=source_security_id,
            session_date=state.session_date,
            knowledge_session_date=knowledge_session_date,
            exchange=state.exchange,
            board=state.board,
            trading_status=state.trading_status,
            risk_warning_status=state.risk_warning_status,
            disposition=disposition,
            reason_codes=tuple(reasons),
            input_partition_manifest_fingerprint=(
                normalized_partition.manifest.logical_fingerprint
            ),
            as_operated=False,
            research_authorized=False,
            return_construction_authorized=False,
            research_backtest_authorized=False,
        ))
    ordered = tuple(
        sorted(rows, key=lambda item: (str(item.instrument_id), item.session_date))
    )
    counts = Counter(item.disposition for item in ordered)
    if (
        len(ordered) != partition_census.state_count
        or counts[ChinaAshareConservativeUniverseDisposition.PROVISIONAL_INCLUDE]
        != partition_census.provisional_candidate_included_state_count
        or counts[ChinaAshareConservativeUniverseDisposition.WARNING_EXCLUDE]
        != partition_census.provisional_candidate_excluded_state_count
        or counts[ChinaAshareConservativeUniverseDisposition.QUARANTINE]
        != partition_census.provisional_quarantined_state_count
    ):
        raise ValueError("conservative Universe rows differ from census")
    return ordered


def _instrument_by_source(normalized_partition):
    result = {}
    for bar in normalized_partition.normalized.bars:
        source_security_id = bar.source_record_id.split(":", 1)[0]
        existing = result.setdefault(source_security_id, bar.instrument_id)
        if existing != bar.instrument_id:
            raise ValueError("source security maps to multiple instruments")
    return result


def _factor_change_dates(normalized_partition):
    by_instrument = defaultdict(list)
    for item in normalized_partition.normalized.adjustments:
        by_instrument[item.instrument_id].append(item)
    changed = defaultdict(set)
    for instrument_id, rows in by_instrument.items():
        previous = None
        for item in sorted(rows, key=lambda value: value.session_date):
            factors = (
                item.provider_factor,
                item.fore_adjust_factor,
                item.back_adjust_factor,
            )
            if previous is not None and factors != previous:
                changed[instrument_id].add(item.session_date)
            previous = factors
    return changed


def _fingerprint(value) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    ).encode()
    return hashlib.sha256(payload).hexdigest()
