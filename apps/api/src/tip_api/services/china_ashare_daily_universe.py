"""Deterministic point-in-time daily Universe builder for the A-share pilot."""

from __future__ import annotations

from datetime import datetime

from tip_api.contracts.china_ashare.v1.daily_universe import (
    DAILY_UNIVERSE_METHOD_VERSION,
    ChinaAshareDailyUniverseReportV1,
    build_daily_universe_report,
    daily_universe_decision_set_fingerprint,
)
from tip_api.contracts.china_ashare.v1.foundation import (
    ChinaAshareRiskWarningStatus,
    ChinaAshareSecurityForm,
    ChinaAshareTradingStatus,
    ChinaAshareUniverseDecisionV1,
    ChinaAshareUniverseDisposition,
)
from tip_api.persistence.china_ashare_identity_lifecycle_package import (
    ChinaAshareIdentityLifecyclePackageResultV1,
)
from tip_api.persistence.china_ashare_pilot_package import (
    ChinaAsharePilotDailyPackageResultV1,
)


def build_daily_universe_for_pilot(
    *,
    daily_package: ChinaAsharePilotDailyPackageResultV1,
    identity_lifecycle_package: ChinaAshareIdentityLifecyclePackageResultV1,
    evaluated_at: datetime,
) -> tuple[
    tuple[ChinaAshareUniverseDecisionV1, ...],
    ChinaAshareDailyUniverseReportV1,
]:
    """Create one decision for every stable pilot instrument and session."""

    identity_report = identity_lifecycle_package.report
    if identity_report.daily_package_fingerprint != daily_package.manifest.logical_fingerprint:
        raise ValueError("identity/lifecycle package does not bind the daily package")
    if not identity_report.stable_identity_family_complete:
        raise ValueError("stable identity family is incomplete")
    if not identity_report.lifecycle_family_complete:
        raise ValueError("lifecycle family is incomplete")
    if evaluated_at < max(
        item.ingested_at for item in daily_package.captured.daily_batch.trading_states
    ):
        raise ValueError("daily Universe evaluation precedes source ingestion")

    identities = {item.instrument_id: item for item in identity_lifecycle_package.identities}
    lifecycle = {
        item.instrument_id: item
        for item in identity_lifecycle_package.lifecycle_decisions
    }
    states = daily_package.captured.daily_batch.trading_states
    state_keys = tuple((item.instrument_id, item.session_date) for item in states)
    if state_keys != tuple(sorted(set(state_keys), key=lambda item: (str(item[0]), item[1]))):
        raise ValueError("daily trading states are not unique and ordered")
    session_dates = tuple(sorted({item.session_date for item in states}))
    expected_keys = {
        (instrument_id, session_date)
        for instrument_id in identities
        for session_date in session_dates
    }
    if set(state_keys) != expected_keys:
        raise ValueError("daily state population is not the identity/session cross product")
    bar_keys = {
        (item.instrument_id, item.session_date)
        for item in daily_package.captured.daily_batch.bars
    }

    decisions = []
    for state in states:
        identity = identities[state.instrument_id]
        interval = lifecycle[state.instrument_id]
        reasons = {"later_retrieved_state_not_as_operated"}
        if not interval.listed_interval_complete:
            disposition = ChinaAshareUniverseDisposition.QUARANTINED
            reasons.add("listed_lifecycle_incomplete")
        elif identity.security_form is not ChinaAshareSecurityForm.COMMON_STOCK:
            disposition = ChinaAshareUniverseDisposition.EXCLUDED
            reasons.add("non_common_stock_excluded")
        elif state.trading_status is ChinaAshareTradingStatus.UNKNOWN:
            disposition = ChinaAshareUniverseDisposition.QUARANTINED
            reasons.add("trading_status_unknown")
        elif state.trading_status is ChinaAshareTradingStatus.NOT_LISTED:
            disposition = ChinaAshareUniverseDisposition.EXCLUDED
            reasons.add("not_listed_on_session")
        elif state.risk_warning_status is ChinaAshareRiskWarningStatus.UNKNOWN:
            disposition = ChinaAshareUniverseDisposition.QUARANTINED
            reasons.add("risk_warning_status_unknown")
        elif state.risk_warning_status is not ChinaAshareRiskWarningStatus.NONE:
            disposition = ChinaAshareUniverseDisposition.EXCLUDED
            reasons.add("risk_warning_security_excluded")
        else:
            disposition = ChinaAshareUniverseDisposition.INCLUDED
            reasons.update(("common_stock_identity_valid", "listed_on_session"))

        performance_eligible = (
            disposition is ChinaAshareUniverseDisposition.INCLUDED
            and state.trading_status
            in {ChinaAshareTradingStatus.TRADING, ChinaAshareTradingStatus.RESUMED}
            and (state.instrument_id, state.session_date) in bar_keys
        )
        if state.trading_status is ChinaAshareTradingStatus.SUSPENDED:
            reasons.add("suspended_on_session")
        if performance_eligible:
            reasons.add("close_observation_available")
        decisions.append(
            ChinaAshareUniverseDecisionV1(
                instrument_id=state.instrument_id,
                session_date=state.session_date,
                methodology_version=DAILY_UNIVERSE_METHOD_VERSION,
                disposition=disposition,
                reason_codes=tuple(sorted(reasons)),
                source_cutoff_at=state.source_available_at or state.ingested_at,
                evaluated_at=evaluated_at,
                input_fingerprints=(
                    daily_package.manifest.logical_fingerprint,
                    identity.logical_fingerprint,
                    identity_lifecycle_package.manifest.logical_fingerprint,
                ),
                performance_eligible=performance_eligible,
            )
        )
    ordered = tuple(
        sorted(decisions, key=lambda item: (str(item.instrument_id), item.session_date))
    )
    included = sum(
        item.disposition is ChinaAshareUniverseDisposition.INCLUDED for item in ordered
    )
    excluded = sum(
        item.disposition is ChinaAshareUniverseDisposition.EXCLUDED for item in ordered
    )
    quarantined = sum(
        item.disposition is ChinaAshareUniverseDisposition.QUARANTINED for item in ordered
    )
    target = len(identities) * len(session_dates)
    report = build_daily_universe_report(
        daily_package_fingerprint=daily_package.manifest.logical_fingerprint,
        identity_lifecycle_package_fingerprint=(
            identity_lifecycle_package.manifest.logical_fingerprint
        ),
        evaluated_at=evaluated_at,
        interval_start=min(session_dates),
        interval_end=max(session_dates),
        instrument_count=len(identities),
        session_count=len(session_dates),
        target_decision_count=target,
        decision_count=len(ordered),
        included_count=included,
        excluded_count=excluded,
        quarantined_count=quarantined,
        performance_eligible_count=sum(item.performance_eligible for item in ordered),
        decision_set_fingerprint=daily_universe_decision_set_fingerprint(ordered),
        exactly_one_decision_per_instrument_session=len(ordered) == target,
        later_retrieved_state_not_as_operated=True,
        daily_universe_family_complete=len(ordered) == target and quarantined == 0,
        reason_codes=(
            "bounded_sse_szse_pilot_only",
            "daily_universe_partition_reconciled",
            "later_retrieved_state_not_as_operated",
            "research_backtest_not_authorized",
            "risk_warning_securities_excluded",
        ),
        canonical_apply_authorized=False,
        research_backtest_authorized=False,
        product_publication_authorized=False,
        deployment_authorized=False,
    )
    return ordered, report
