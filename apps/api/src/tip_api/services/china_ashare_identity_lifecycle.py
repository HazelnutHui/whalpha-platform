"""Build stable research identities and lifecycle intervals for the A-share pilot."""

from __future__ import annotations

import json
from io import BytesIO
from datetime import date, datetime

from tip_api.contracts.china_ashare.v1.foundation import (
    ChinaAshareLifecycleSubjectKind,
    ChinaAshareSecurityForm,
    ChinaAshareTradingStatus,
)
from tip_api.contracts.china_ashare.v1.identity_lifecycle import (
    ChinaAshareIdentityLifecycleReportV1,
    ChinaAshareListedLifecycleDecisionV1,
    build_identity_lifecycle_report,
    build_research_instrument_identity,
)
from tip_api.contracts.china_ashare.v1.pilot import (
    ChinaAsharePilotIdentityDisposition,
    china_ashare_pilot_source_observation_fingerprint,
)
from tip_api.contracts.common import QualityStatus
from tip_api.persistence.china_ashare_pilot_package import (
    ChinaAsharePilotDailyPackageResultV1,
    ChinaAsharePilotPackageResultV1,
)
from tip_api.providers.china_ashare.official_identity_evidence_adapter import (
    CapturedOfficialIdentityArtifactV1,
    OfficialIdentityArtifactKind,
)


def validate_official_identity_artifacts_for_pilot(
    *,
    reference_package: ChinaAsharePilotPackageResultV1,
    captured_sources: tuple[CapturedOfficialIdentityArtifactV1, ...],
) -> bool:
    """Bind exact official bytes to every normalized pilot identity observation."""

    by_kind = {item.artifact_kind: item for item in captured_sources}
    if set(by_kind) != set(OfficialIdentityArtifactKind):
        raise ValueError("official identity artifacts do not cover all source kinds")
    current_rows: dict[str, tuple[str, str, str]] = {}
    for kind, expected_board in (
        (OfficialIdentityArtifactKind.SSE_MAIN_CURRENT, "sse_main"),
        (OfficialIdentityArtifactKind.SSE_STAR_CURRENT, "star"),
    ):
        document = json.loads(by_kind[kind].raw_bytes)
        if not isinstance(document, dict) or not isinstance(document.get("result"), list):
            raise ValueError("official SSE current-list schema differs")
        for row in document["result"]:
            if not isinstance(row, dict):
                raise ValueError("official SSE current-list row is malformed")
            code = _source_code(row.get("A_STOCK_CODE"))
            if not code:
                continue
            current_rows[f"sh.{code}"] = (
                str(row.get("SEC_NAME_CN") or "").strip(),
                _frame_date_text(row.get("LIST_DATE")),
                expected_board,
            )
    try:
        import pandas as pd
    except ImportError as exc:  # pragma: no cover - environment boundary
        raise RuntimeError("pandas is required to parse official SZSE evidence") from exc
    szse_current = pd.read_excel(
        BytesIO(by_kind[OfficialIdentityArtifactKind.SZSE_A_CURRENT].raw_bytes)
    )
    required_current = {"板块", "A股代码", "A股简称", "A股上市日期"}
    if not required_current.issubset(set(szse_current.columns)):
        raise ValueError("official SZSE current-list schema differs")
    for row in szse_current.to_dict(orient="records"):
        code = _source_code(row.get("A股代码"))
        if not code:
            continue
        board = {"主板": "szse_main", "创业板": "chinext"}.get(
            str(row.get("板块") or "").strip()
        )
        if board is None:
            continue
        current_rows[f"sz.{code}"] = (
            str(row.get("A股简称") or "").strip(),
            _frame_date_text(row.get("A股上市日期")),
            board,
        )
    targets = {
        item.source_security_id: item
        for item in reference_package.captured.official_current_instruments
        if item.source_security_id.startswith(("sh.", "sz."))
    }
    if not targets:
        raise ValueError("reference package has no SSE/SZSE identity targets")
    for source_id, normalized in targets.items():
        exact = current_rows.get(source_id)
        if exact is None:
            raise ValueError("official raw current list lacks a pilot identity")
        expected = (
            normalized.name,
            normalized.list_date.isoformat() if normalized.list_date else "",
            normalized.board.value,
        )
        if exact != expected:
            raise ValueError(
                "official raw current-list identity differs from package: "
                f"source_security_id={source_id}, exact={exact!r}, "
                f"normalized={expected!r}"
            )

    sse_delist_document = json.loads(
        by_kind[OfficialIdentityArtifactKind.SSE_DELIST].raw_bytes
    )
    if not isinstance(sse_delist_document, dict) or not isinstance(
        sse_delist_document.get("result"), list
    ):
        raise ValueError("official SSE delist schema differs")
    sse_delist_codes = {
        _source_code(row.get("COMPANY_CODE"))
        for row in sse_delist_document["result"]
        if isinstance(row, dict)
    }
    szse_delist = pd.read_excel(
        BytesIO(by_kind[OfficialIdentityArtifactKind.SZSE_DELIST].raw_bytes)
    )
    if "证券代码" not in szse_delist.columns:
        raise ValueError("official SZSE delist schema differs")
    szse_delist_codes = {
        _source_code(value) for value in szse_delist["证券代码"].tolist()
    }
    for source_id in targets:
        prefix, code = source_id.split(".", 1)
        if prefix == "sh" and code in sse_delist_codes:
            raise ValueError("pilot identity appears in issuer-level SSE delist source")
        if prefix == "sz" and code in szse_delist_codes:
            raise ValueError("pilot identity appears in SZSE delist source")
    return True


def build_identity_lifecycle_report_for_pilot(
    *,
    reference_package: ChinaAsharePilotPackageResultV1,
    daily_package: ChinaAsharePilotDailyPackageResultV1,
    exact_official_source_bytes_retained: bool,
    evaluated_at: datetime,
) -> ChinaAshareIdentityLifecycleReportV1:
    """Promote only fully corroborated SSE/SZSE listed occurrences."""

    if reference_package.plan.logical_fingerprint != daily_package.plan.logical_fingerprint:
        raise ValueError("reference and daily pilot plans differ")
    if (
        daily_package.manifest.reference_package_fingerprint
        != reference_package.manifest.logical_fingerprint
    ):
        raise ValueError("daily package does not bind the reference package")
    official = {
        item.source_security_id: item
        for item in reference_package.captured.official_current_instruments
    }
    baostock = {
        item.source_security_id: item
        for item in reference_package.captured.baostock_instruments
    }
    bound = tuple(
        item
        for item in daily_package.captured.identity_decisions
        if item.disposition is ChinaAsharePilotIdentityDisposition.BOUND_FOR_DAILY_CAPTURE
    )
    expected_sessions = len(
        {item.session_date for item in daily_package.captured.daily_batch.trading_states}
    )
    if expected_sessions < 1:
        raise ValueError("daily package has no source-state sessions")
    identities = []
    lifecycle = []
    for decision in bound:
        if decision.pilot_instrument_id is None:
            raise ValueError("bound pilot identity lacks instrument ID")
        official_row = official.get(decision.source_security_id)
        baostock_row = baostock.get(decision.source_security_id)
        if official_row is None or baostock_row is None:
            raise ValueError("bound pilot identity lacks source observations")
        if official_row.list_date is None:
            raise ValueError("bound pilot identity lacks official listing date")
        official_fp = china_ashare_pilot_source_observation_fingerprint(official_row)
        baostock_fp = china_ashare_pilot_source_observation_fingerprint(baostock_row)
        identity = build_research_instrument_identity(
            source_security_id=decision.source_security_id,
            display_ticker=official_row.display_ticker,
            current_name=official_row.name,
            exchange=official_row.exchange,
            board=official_row.board,
            security_form=ChinaAshareSecurityForm.COMMON_STOCK,
            listing_date=official_row.list_date,
            alias_valid_from=official_row.list_date,
            official_observation_fingerprint=official_fp,
            baostock_observation_fingerprint=baostock_fp,
            pilot_decision_fingerprint=decision.logical_fingerprint,
            append_only=True,
            ticker_is_permanent_key=False,
            quality_status=QualityStatus.VALID,
            reason_codes=(
                "cross_source_name_agreement",
                "listed_occurrence_keyed",
                "ticker_is_alias_not_identity",
            ),
            canonical_apply_authorized=False,
        )
        if identity.instrument_id != decision.pilot_instrument_id:
            raise ValueError("stable research identity differs from pilot join identity")
        states = tuple(
            item
            for item in daily_package.captured.daily_batch.trading_states
            if item.instrument_id == identity.instrument_id
        )
        status_counts = {
            status: sum(item.trading_status is status for item in states)
            for status in ChinaAshareTradingStatus
        }
        security_events = tuple(
            item
            for item in reference_package.captured.official_lifecycle
            if item.subject_kind is ChinaAshareLifecycleSubjectKind.SECURITY_CODE
            and item.source_security_id == identity.source_security_id
        )
        code = identity.source_security_id.split(".", 1)[1]
        issuer_events = tuple(
            item
            for item in reference_package.captured.official_lifecycle
            if item.subject_kind is ChinaAshareLifecycleSubjectKind.ISSUER_CODE
            and item.source_subject_code == code
        )
        active_count = sum(
            status_counts[status]
            for status in (
                ChinaAshareTradingStatus.TRADING,
                ChinaAshareTradingStatus.SUSPENDED,
                ChinaAshareTradingStatus.RESUMED,
            )
        )
        state_dates_complete = (
            len(states) == expected_sessions
            and active_count == expected_sessions
            and status_counts[ChinaAshareTradingStatus.NOT_LISTED] == 0
            and status_counts[ChinaAshareTradingStatus.UNKNOWN] == 0
        )
        listed_complete = (
            state_dates_complete and not security_events and not issuer_events
        )
        reasons = {
            "current_official_listing_observed",
            "listing_date_precedes_interval",
            "source_state_history_continuous",
        }
        if not listed_complete:
            reasons.add("listed_interval_requires_quarantine")
        lifecycle.append(
            ChinaAshareListedLifecycleDecisionV1(
                instrument_id=identity.instrument_id,
                source_security_id=identity.source_security_id,
                interval_start=daily_package.plan.history_start_date,
                interval_end=daily_package.plan.history_end_date,
                listing_date=identity.listing_date,
                current_list_observed_as_of=official_row.as_of_date,
                expected_session_count=expected_sessions,
                observed_state_count=len(states),
                trading_or_suspended_state_count=active_count,
                not_listed_state_count=status_counts[
                    ChinaAshareTradingStatus.NOT_LISTED
                ],
                unknown_state_count=status_counts[ChinaAshareTradingStatus.UNKNOWN],
                security_termination_event_count=len(security_events),
                issuer_only_event_count=len(issuer_events),
                state_dates_complete=state_dates_complete,
                listed_interval_complete=listed_complete,
                quality_status=(
                    QualityStatus.VALID if listed_complete else QualityStatus.REJECTED
                ),
                evidence_fingerprints=(
                    identity.logical_fingerprint,
                    daily_package.manifest.logical_fingerprint,
                    reference_package.manifest.logical_fingerprint,
                ),
                reason_codes=tuple(sorted(reasons)),
            )
        )
        identities.append(identity)
    ordered_identities = tuple(sorted(identities, key=lambda item: str(item.instrument_id)))
    ordered_lifecycle = tuple(sorted(lifecycle, key=lambda item: str(item.instrument_id)))
    quarantined = len(bound) - len(ordered_identities)
    complete_lifecycle = sum(item.listed_interval_complete for item in ordered_lifecycle)
    identity_complete = (
        exact_official_source_bytes_retained
        and bool(ordered_identities)
        and quarantined == 0
    )
    lifecycle_complete = (
        identity_complete
        and complete_lifecycle == len(ordered_identities)
    )
    reasons = {
        "bounded_sse_szse_pilot_only",
        "canonical_apply_not_authorized",
        "research_backtest_not_authorized",
    }
    if identity_complete:
        reasons.add("stable_research_identity_reconciled")
    if lifecycle_complete:
        reasons.add("listed_lifecycle_interval_reconciled")
    return build_identity_lifecycle_report(
        reference_package_fingerprint=reference_package.manifest.logical_fingerprint,
        daily_package_fingerprint=daily_package.manifest.logical_fingerprint,
        evaluated_at=evaluated_at,
        interval_start=daily_package.plan.history_start_date,
        interval_end=daily_package.plan.history_end_date,
        planned_instrument_count=len(bound),
        resolved_identity_count=len(ordered_identities),
        quarantined_identity_count=quarantined,
        complete_lifecycle_count=complete_lifecycle,
        incomplete_lifecycle_count=len(ordered_lifecycle) - complete_lifecycle,
        exact_official_source_bytes_retained=exact_official_source_bytes_retained,
        stable_identity_family_complete=identity_complete,
        lifecycle_family_complete=lifecycle_complete,
        identities=ordered_identities,
        lifecycle_decisions=ordered_lifecycle,
        reason_codes=tuple(sorted(reasons)),
        canonical_apply_authorized=False,
        research_backtest_authorized=False,
        product_publication_authorized=False,
        deployment_authorized=False,
    )


def _source_code(value: object) -> str:
    if value is None:
        return ""
    text = str(value).strip().split(".", 1)[0]
    if not text or text.lower() in {"nan", "none"}:
        return ""
    normalized = text.zfill(6)
    if len(normalized) != 6 or not normalized.isdigit():
        raise ValueError("official identity source code is invalid")
    return normalized


def _frame_date_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    text = str(value).strip()
    if text.lower() in {"", "nat", "nan", "none"}:
        return ""
    compact = text.split(".", 1)[0]
    if len(compact) == 8 and compact.isdigit():
        return datetime.strptime(compact, "%Y%m%d").date().isoformat()
    try:
        return date.fromisoformat(text[:10]).isoformat()
    except ValueError as exc:
        raise ValueError("official identity date is invalid") from exc
