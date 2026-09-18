"""Pure outcome-blind listed-security applicability census."""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, datetime
from typing import Literal

import pyarrow as pa

from tip_api.contracts.analytics.v1.quant_research_sec_cash_quality_security_applicability import (
    SecCashQualitySecurityApplicabilityPlanV1,
    SecCashQualitySecurityApplicabilityResultV1,
    SecCashQualitySecurityApplicabilityVerificationV1,
)
from tip_api.contracts.analytics.v1.quant_research_sec_cash_quality_source_readiness_census import census_fingerprint


class SecCashQualitySecurityApplicabilityError(RuntimeError):
    pass


def census_sec_cash_quality_security_applicability(
    *, ttm_rows: pa.Table, lineage_rows: pa.Table,
    link_rows_by_session: dict[date, pa.Table], provider_form_rows: pa.Table,
    session_opens: dict[date, datetime],
    plan: SecCashQualitySecurityApplicabilityPlanV1,
    traversal_order: Literal["forward", "reverse"] = "forward",
) -> SecCashQualitySecurityApplicabilityResultV1:
    if ttm_rows.num_rows != plan.expected_ttm_endpoint_count:
        raise SecCashQualitySecurityApplicabilityError("TTM applicability denominator differs")
    occurrence_sessions: dict[str, date] = {}
    for row in lineage_rows.select(["signal_eligible_session", "source_occurrence_ids"]).to_pylist():
        for occurrence_id in row["source_occurrence_ids"]:
            prior = occurrence_sessions.setdefault(occurrence_id, row["signal_eligible_session"])
            if prior != row["signal_eligible_session"]:
                raise SecCashQualitySecurityApplicabilityError("lineage session conflict")
    links: dict[date, dict[str, list[dict]]] = {}
    for session, table in link_rows_by_session.items():
        by_cik: dict[str, list[dict]] = defaultdict(list)
        for row in table.to_pylist():
            if row["sec_cik"] is not None:
                by_cik[row["sec_cik"]].append(row)
        links[session] = dict(by_cik)
    provider = {
        row["instrument_id"]: row for row in provider_form_rows.to_pylist()
    }
    primary: Counter[str] = Counter()
    gaps: Counter[str] = Counter()
    forms: Counter[str] = Counter()
    sessions: set[date] = set()
    instruments: set[str] = set()
    tickers: dict[str, set[str]] = defaultdict(set)
    counts: Counter[str] = Counter()
    rows = ttm_rows.to_pylist()
    iterable = rows if traversal_order == "forward" else reversed(rows)
    for row in iterable:
        component_sessions = [
            occurrence_sessions.get(item) for item in row["source_occurrence_ids"]
        ]
        if not component_sessions or any(item is None for item in component_sessions):
            primary["financial_lineage_signal_session_missing"] += 1
            continue
        session = max(component_sessions)
        counts["lineage"] += 1
        sessions.add(session)
        if session not in links or session not in session_opens:
            primary["identity_link_session_unavailable"] += 1
            continue
        counts["link_session"] += 1
        admitted = [
            item for item in links[session].get(row["companyfacts_cik"], ())
            if item["decision_status"] == "admitted_unique_cik"
        ]
        if not admitted:
            primary["stable_security_cik_link_missing_or_quarantined"] += 1
            continue
        counts["cik_linked"] += 1
        if len(admitted) > 1:
            counts["multi_security"] += 1
        common = [item for item in admitted if item["instrument_type"] == "common_stock"]
        if not common:
            primary["no_common_security_at_signal_session"] += 1
            continue
        if len(common) > 1:
            counts["multi_common"] += 1
            primary["multiple_common_securities_for_cik"] += 1
            continue
        counts["unique_common"] += 1
        selected = common[0]
        instrument_id = selected["instrument_id"]
        instruments.add(instrument_id)
        tickers[instrument_id].add(selected["ticker"])
        evidence = provider.get(instrument_id)
        if evidence is None:
            gaps["provider_security_form_missing"] += 1
        else:
            forms[str(evidence["security_form_evidence"])] += 1
            gaps["provider_security_form_not_effective_dated"] += 1
        gaps["authoritative_issuer_structure_missing"] += 1
        gaps["listing_interval_not_proven_beyond_exact_daily_occurrence"] += 1
        if selected["point_in_time_eligibility"] != "eligible_at_source_observed_at":
            primary["identity_evidence_outcome_reconciliation_only"] += 1
            continue
        if (
            selected["source_observed_at"] is None
            or selected["source_observed_at"] > session_opens[session]
        ):
            primary["identity_evidence_not_known_by_signal_open"] += 1
            continue
        counts["identity_known"] += 1
        primary["security_form_not_effective_dated"] += 1
    gaps["sec_filer_identity_not_listed_security_proof"] = ttm_rows.num_rows
    values = {
        "plan_fingerprint": plan.logical_fingerprint,
        "ttm_endpoint_count": ttm_rows.num_rows,
        "lineage_session_recovered_count": counts["lineage"],
        "distinct_signal_session_count": len(sessions),
        "link_session_in_range_count": counts["link_session"],
        "cik_linked_endpoint_count": counts["cik_linked"],
        "unique_common_security_endpoint_count": counts["unique_common"],
        "multiple_security_issuer_endpoint_count": counts["multi_security"],
        "multiple_common_security_endpoint_count": counts["multi_common"],
        "identity_known_by_signal_open_count": counts["identity_known"],
        "observed_provider_form_counts": tuple(sorted(forms.items())),
        "stable_instrument_count": len(instruments),
        "stable_instrument_ticker_change_count": sum(
            len(values) > 1 for values in tickers.values()
        ),
        "primary_blocker_counts": tuple(sorted(primary.items())),
        "evidence_gap_counts": tuple(sorted(gaps.items())),
    }
    provisional = SecCashQualitySecurityApplicabilityResultV1.model_construct(
        **values, logical_fingerprint="0" * 64
    )
    return SecCashQualitySecurityApplicabilityResultV1.model_validate(
        {**values, "logical_fingerprint": census_fingerprint(provisional)}
    )


def independently_verify_sec_cash_quality_security_applicability(
    **kwargs,
) -> tuple[
    SecCashQualitySecurityApplicabilityResultV1,
    SecCashQualitySecurityApplicabilityVerificationV1,
]:
    forward = census_sec_cash_quality_security_applicability(**kwargs)
    reverse = census_sec_cash_quality_security_applicability(
        **kwargs, traversal_order="reverse"
    )
    values = {
        "plan_fingerprint": kwargs["plan"].logical_fingerprint,
        "forward_result_fingerprint": forward.logical_fingerprint,
        "reverse_result_fingerprint": reverse.logical_fingerprint,
    }
    provisional = SecCashQualitySecurityApplicabilityVerificationV1.model_construct(
        **values, logical_fingerprint="0" * 64
    )
    verification = SecCashQualitySecurityApplicabilityVerificationV1.model_validate(
        {**values, "logical_fingerprint": census_fingerprint(provisional)}
    )
    return forward, verification
