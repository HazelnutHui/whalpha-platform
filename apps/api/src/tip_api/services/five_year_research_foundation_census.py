"""Network-free census of the ADR 0196 five-year research foundation."""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Any

from tip_api.contracts.market_data.v1 import (
    FIVE_YEAR_FOUNDATION_FAMILY_ORDER,
    FIVE_YEAR_PRICE_STRATEGY_REQUIRED_FAMILIES,
    FIVE_YEAR_PROGRAM_REQUIRED_FAMILIES,
    FiveYearFoundationCoverageStatus,
    FiveYearFoundationEvidenceTier,
    FiveYearFoundationFamily,
    FiveYearFoundationFamilyCensusV1,
    FiveYearResearchFoundationCensusV1,
    build_five_year_research_foundation_census,
)
from tip_api.persistence.parquet.eod_read import CanonicalEodReadRepository
from tip_api.services.current_context_report import _historical_research_readiness
from tip_api.services.market_calendar import ExchangeCalendar, MarketSessionCalendar


class FiveYearResearchFoundationCensusError(RuntimeError):
    """Raised when the five-year target or current evidence cannot be reconciled."""


def assess_five_year_research_foundation(
    data_root: Path,
    *,
    calendar: MarketSessionCalendar | None = None,
) -> FiveYearResearchFoundationCensusV1:
    """Formally reread current families and compare them with a five-year target."""

    session_calendar = calendar or ExchangeCalendar()
    if session_calendar.calendar_id != "XNYS":
        raise FiveYearResearchFoundationCensusError(
            "five-year research foundation requires XNYS"
        )
    eod_sessions = CanonicalEodReadRepository(data_root).list_session_index()
    if not eod_sessions or eod_sessions != tuple(sorted(set(eod_sessions))):
        raise FiveYearResearchFoundationCensusError(
            "canonical EOD sessions are absent, duplicated, or unordered"
        )
    target_end = eod_sessions[-1]
    target_anchor = _subtract_calendar_years(target_end, 5)
    target_sessions = session_calendar.sessions_in_range(target_anchor, target_end)
    if target_sessions[-1] != target_end:
        raise FiveYearResearchFoundationCensusError(
            "five-year target does not end at latest canonical EOD"
        )

    readiness = _historical_research_readiness(
        data_root,
        session_dates=eod_sessions,
        history_validation_scope="completion_index_plus_family_formal_reads",
    )
    inventories = {item["family"]: item for item in readiness["families"]}
    families = _build_family_census(
        target_sessions=target_sessions,
        eod_sessions=eod_sessions,
        membership_session_dates=_membership_publication_dates(data_root),
        inventories=inventories,
    )
    return build_five_year_research_foundation_census(
        calendar_version=session_calendar.calendar_version,
        target_anchor_date=target_anchor,
        target_sessions=target_sessions,
        families=families,
    )


def _build_family_census(
    *,
    target_sessions: tuple[date, ...],
    eod_sessions: tuple[date, ...],
    membership_session_dates: tuple[date, ...],
    inventories: dict[str, dict[str, Any]],
) -> tuple[FiveYearFoundationFamilyCensusV1, ...]:
    target_set = set(target_sessions)
    eod_in_target = tuple(item for item in eod_sessions if item in target_set)
    eod = inventories[FiveYearFoundationFamily.EOD_PRICE_BAR.value]
    identity = inventories[FiveYearFoundationFamily.POINT_IN_TIME_IDENTITY.value]
    identity_source = inventories[
        FiveYearFoundationFamily.POINT_IN_TIME_IDENTITY_SOURCE.value
    ]
    membership = inventories[FiveYearFoundationFamily.UNIVERSE_MEMBERSHIP.value]
    action_source = inventories[
        FiveYearFoundationFamily.CORPORATE_ACTION_SOURCE.value
    ]
    action = inventories[FiveYearFoundationFamily.CORPORATE_ACTION.value]
    lifecycle = inventories[FiveYearFoundationFamily.INSTRUMENT_LIFECYCLE.value]
    adjustment = inventories[FiveYearFoundationFamily.ADJUSTMENT_LEDGER.value]
    coverage_evidence = inventories[
        FiveYearFoundationFamily.HISTORICAL_COVERAGE_EVIDENCE.value
    ]
    coverage = inventories[FiveYearFoundationFamily.HISTORICAL_COVERAGE.value]

    values = (
        _session_family(
            family=FiveYearFoundationFamily.EOD_PRICE_BAR,
            target_sessions=target_sessions,
            covered_sessions=eod_in_target,
            inventory=eod,
            evidence_tier=FiveYearFoundationEvidenceTier.MIXED,
            source_ids=("massive",),
            partial_reason="five_year_eod_sessions_missing",
        ),
        _session_family(
            family=FiveYearFoundationFamily.POINT_IN_TIME_IDENTITY,
            target_sessions=target_sessions,
            covered_sessions=tuple(
                item
                for item in _covered_sessions_from_missing_inventory(
                    target_sessions=eod_sessions,
                    inventory=identity,
                )
                if item in target_set
            ),
            inventory=identity,
            evidence_tier=FiveYearFoundationEvidenceTier.MIXED,
            source_ids=("massive",),
            partial_reason="five_year_identity_sessions_missing",
        ),
        _session_family(
            family=FiveYearFoundationFamily.POINT_IN_TIME_IDENTITY_SOURCE,
            target_sessions=target_sessions,
            covered_sessions=tuple(
                item
                for item in _covered_sessions_from_missing_inventory(
                    target_sessions=eod_sessions,
                    inventory=identity_source,
                )
                if item in target_set
            ),
            inventory=identity_source,
            evidence_tier=(
                FiveYearFoundationEvidenceTier.RECONSTRUCTED_LATEST_VINTAGE
                if identity_source.get("partition_count", 0)
                else FiveYearFoundationEvidenceTier.MISSING
            ),
            source_ids=("massive",) if identity_source.get("partition_count", 0) else (),
            partial_reason="five_year_identity_source_sessions_missing",
        ),
        _session_family(
            family=FiveYearFoundationFamily.UNIVERSE_MEMBERSHIP,
            target_sessions=target_sessions,
            covered_sessions=tuple(
                item for item in membership_session_dates if item in target_set
            ),
            inventory=membership,
            evidence_tier=(
                FiveYearFoundationEvidenceTier.AS_OPERATED
                if membership.get("partition_count", 0)
                else FiveYearFoundationEvidenceTier.MISSING
            ),
            source_ids=("whalpha",) if membership.get("partition_count", 0) else (),
            partial_reason="five_year_membership_sessions_missing",
        ),
        _sparse_family(
            family=FiveYearFoundationFamily.CORPORATE_ACTION_SOURCE,
            inventory=action_source,
            evidence_tier=(
                FiveYearFoundationEvidenceTier.SOURCE_OBSERVATION
                if action_source.get("partition_count", 0)
                else FiveYearFoundationEvidenceTier.MISSING
            ),
            source_ids=("massive",) if action_source.get("partition_count", 0) else (),
            reason_codes=(
                "bounded_source_query_not_complete_canonical_actions",
                "outcome_reconciliation_only",
            ),
        ),
        _sparse_family(
            family=FiveYearFoundationFamily.CORPORATE_ACTION,
            inventory=action,
            evidence_tier=(
                FiveYearFoundationEvidenceTier.DERIVED_CANONICAL
                if action.get("partition_count", 0)
                else FiveYearFoundationEvidenceTier.MISSING
            ),
            source_ids=("massive", "whalpha") if action.get("partition_count", 0) else (),
            reason_codes=(
                "canonical_scope_is_split_only",
                "complete_action_availability_and_revision_absent",
            ),
        ),
        _sparse_family(
            family=FiveYearFoundationFamily.INSTRUMENT_LIFECYCLE,
            inventory=lifecycle,
            evidence_tier=FiveYearFoundationEvidenceTier.MISSING,
            source_ids=(),
            reason_codes=("canonical_lifecycle_family_absent",),
        ),
        _sparse_family(
            family=FiveYearFoundationFamily.ADJUSTMENT_LEDGER,
            inventory=adjustment,
            evidence_tier=(
                FiveYearFoundationEvidenceTier.DERIVED_CANONICAL
                if adjustment.get("partition_count", 0)
                else FiveYearFoundationEvidenceTier.MISSING
            ),
            source_ids=("massive", "whalpha")
            if adjustment.get("partition_count", 0)
            else (),
            reason_codes=(
                "absent_row_neutrality_unproven",
                "split_only_sparse_outcome_reconciliation",
                "total_return_adjustment_absent",
            ),
        ),
        _absent_program_family(
            FiveYearFoundationFamily.POINT_IN_TIME_CLASSIFICATION,
            "point_in_time_classification_family_absent",
        ),
        _absent_program_family(
            FiveYearFoundationFamily.POINT_IN_TIME_FUNDAMENTALS,
            "point_in_time_fundamentals_family_absent",
        ),
        _sparse_family(
            family=FiveYearFoundationFamily.HISTORICAL_COVERAGE_EVIDENCE,
            inventory=coverage_evidence,
            evidence_tier=(
                FiveYearFoundationEvidenceTier.DERIVED_CANONICAL
                if coverage_evidence.get("partition_count", 0)
                else FiveYearFoundationEvidenceTier.MISSING
            ),
            source_ids=("whalpha",) if coverage_evidence.get("partition_count", 0) else (),
            reason_codes=("all_required_family_evidence_not_published",),
        ),
        _sparse_family(
            family=FiveYearFoundationFamily.HISTORICAL_COVERAGE,
            inventory=coverage,
            evidence_tier=(
                FiveYearFoundationEvidenceTier.DERIVED_CANONICAL
                if coverage.get("partition_count", 0)
                else FiveYearFoundationEvidenceTier.MISSING
            ),
            source_ids=("whalpha",) if coverage.get("partition_count", 0) else (),
            reason_codes=("five_year_historical_coverage_publication_absent",),
        ),
    )
    if tuple(item.family for item in values) != FIVE_YEAR_FOUNDATION_FAMILY_ORDER:
        raise FiveYearResearchFoundationCensusError(
            "five-year family construction order differs"
        )
    return values


def _session_family(
    *,
    family: FiveYearFoundationFamily,
    target_sessions: tuple[date, ...],
    covered_sessions: tuple[date, ...],
    inventory: dict[str, Any],
    evidence_tier: FiveYearFoundationEvidenceTier,
    source_ids: tuple[str, ...],
    partial_reason: str,
) -> FiveYearFoundationFamilyCensusV1:
    covered_count = len(covered_sessions)
    target_count = len(target_sessions)
    status = (
        FiveYearFoundationCoverageStatus.ABSENT
        if covered_count == 0
        else FiveYearFoundationCoverageStatus.COMPLETE
        if covered_count == target_count and inventory.get("research_ready") is True
        else FiveYearFoundationCoverageStatus.COVERAGE_UNPUBLISHED
        if covered_count == target_count
        else FiveYearFoundationCoverageStatus.PARTIAL
    )
    reasons = (
        ("formal_family_coverage_unpublished",)
        if status is FiveYearFoundationCoverageStatus.COVERAGE_UNPUBLISHED
        else (partial_reason,)
        if status is FiveYearFoundationCoverageStatus.PARTIAL
        else (f"{family.value}_absent",)
    )
    return FiveYearFoundationFamilyCensusV1(
        family=family,
        program_required=family in FIVE_YEAR_PROGRAM_REQUIRED_FAMILIES,
        price_strategy_required=(
            family in FIVE_YEAR_PRICE_STRATEGY_REQUIRED_FAMILIES
        ),
        coverage_status=status,
        evidence_tier=evidence_tier,
        custody_state=str(inventory.get("custody_state", "absent")),
        target_session_count=target_count,
        covered_session_count=covered_count,
        missing_session_count=target_count - covered_count,
        first_observed_session=_date_or_none(inventory.get("first_session")),
        last_observed_session=_date_or_none(inventory.get("last_session")),
        record_count=_optional_non_negative_int(inventory.get("record_count")),
        quarantined_record_count=_optional_non_negative_int(
            inventory.get("quarantined_record_count")
        ),
        source_ids=tuple(sorted(source_ids)),
        reason_codes=tuple(sorted(reasons)),
    )


def _sparse_family(
    *,
    family: FiveYearFoundationFamily,
    inventory: dict[str, Any],
    evidence_tier: FiveYearFoundationEvidenceTier,
    source_ids: tuple[str, ...],
    reason_codes: tuple[str, ...],
) -> FiveYearFoundationFamilyCensusV1:
    record_count = _optional_non_negative_int(inventory.get("record_count"))
    partition_count = int(inventory.get("partition_count", 0))
    status = (
        FiveYearFoundationCoverageStatus.ABSENT
        if partition_count == 0
        else FiveYearFoundationCoverageStatus.COMPLETE
        if inventory.get("research_ready") is True
        else FiveYearFoundationCoverageStatus.PARTIAL
    )
    if status is FiveYearFoundationCoverageStatus.ABSENT:
        evidence_tier = FiveYearFoundationEvidenceTier.MISSING
        source_ids = ()
    return FiveYearFoundationFamilyCensusV1(
        family=family,
        program_required=family in FIVE_YEAR_PROGRAM_REQUIRED_FAMILIES,
        price_strategy_required=(
            family in FIVE_YEAR_PRICE_STRATEGY_REQUIRED_FAMILIES
        ),
        coverage_status=status,
        evidence_tier=evidence_tier,
        custody_state=str(inventory.get("custody_state", "absent")),
        first_observed_session=_date_or_none(inventory.get("first_session")),
        last_observed_session=_date_or_none(inventory.get("last_session")),
        record_count=record_count,
        quarantined_record_count=_optional_non_negative_int(
            inventory.get("quarantined_record_count")
        ),
        source_ids=tuple(sorted(source_ids)),
        reason_codes=tuple(sorted(reason_codes)),
    )


def _absent_program_family(
    family: FiveYearFoundationFamily,
    reason_code: str,
) -> FiveYearFoundationFamilyCensusV1:
    return FiveYearFoundationFamilyCensusV1(
        family=family,
        program_required=True,
        price_strategy_required=False,
        coverage_status=FiveYearFoundationCoverageStatus.ABSENT,
        evidence_tier=FiveYearFoundationEvidenceTier.MISSING,
        custody_state="absent",
        record_count=0,
        quarantined_record_count=0,
        source_ids=(),
        reason_codes=(reason_code,),
    )


def _subtract_calendar_years(value: date, years: int) -> date:
    try:
        return value.replace(year=value.year - years)
    except ValueError:
        return value.replace(year=value.year - years, day=28)


def _date_or_none(value: Any) -> date | None:
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError as exc:
            raise FiveYearResearchFoundationCensusError(
                "family inventory contains malformed date"
            ) from exc
    raise FiveYearResearchFoundationCensusError(
        "family inventory date has unsupported type"
    )


def _covered_sessions_from_missing_inventory(
    *,
    target_sessions: tuple[date, ...],
    inventory: dict[str, Any],
) -> tuple[date, ...]:
    missing_raw = inventory.get("missing_eod_session_dates", ())
    if not isinstance(missing_raw, (tuple, list)):
        raise FiveYearResearchFoundationCensusError(
            "family missing-session inventory is malformed"
        )
    missing = {_date_or_none(item) for item in missing_raw}
    if None in missing:
        raise FiveYearResearchFoundationCensusError(
            "family missing-session inventory contains null"
        )
    covered = tuple(item for item in target_sessions if item not in missing)
    declared_count = int(inventory.get("covered_session_count", 0))
    if len(covered) != declared_count:
        raise FiveYearResearchFoundationCensusError(
            "family exact missing sessions do not reconcile with covered count"
        )
    return covered


def _membership_publication_dates(data_root: Path) -> tuple[date, ...]:
    root = (
        data_root
        / "market-data"
        / "universe-membership-publications"
        / "schema_version=1"
        / "policy_id=next-open-v1"
    )
    if not root.exists():
        return ()
    if root.is_symlink() or not root.is_dir() or root.resolve(strict=True) != root:
        raise FiveYearResearchFoundationCensusError(
            "membership publication root is unsafe"
        )
    partitions = tuple(sorted(root.glob("methodology_version=*/session_date=*")))
    dates: list[date] = []
    for partition in partitions:
        if partition.is_symlink() or not partition.is_dir():
            raise FiveYearResearchFoundationCensusError(
                "membership publication partition is unsafe"
            )
        parsed = _date_or_none(partition.name.removeprefix("session_date="))
        if parsed is None:
            raise FiveYearResearchFoundationCensusError(
                "membership publication date is absent"
            )
        dates.append(parsed)
    return tuple(sorted(set(dates)))


def _optional_non_negative_int(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        raise FiveYearResearchFoundationCensusError(
            "family record count cannot be boolean"
        )
    try:
        result = int(value)
    except (TypeError, ValueError) as exc:
        raise FiveYearResearchFoundationCensusError(
            "family record count is malformed"
        ) from exc
    if result < 0:
        raise FiveYearResearchFoundationCensusError(
            "family record count cannot be negative"
        )
    return result
