"""Pure outcome-blind resolution of effective-dated A-share price-limit rules."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

from tip_api.contracts.china_ashare.v1.foundation import (
    ChinaAshareBoard,
    ChinaAshareExchange,
    ChinaAsharePriceLimitRegime,
    ChinaAshareRiskWarningStatus,
    ChinaAshareTradingRuleV1,
)
from tip_api.contracts.china_ashare.v1.price_limit_resolver import (
    ChinaAshareListingStage,
    ChinaAsharePriceLimitResolutionStatus,
    ChinaAsharePriceLimitResolutionV1,
    ChinaAsharePriceLimitResolverPlanV1,
    build_price_limit_partition_aggregate,
    build_price_limit_resolution,
    build_price_limit_resolver_plan,
    price_limit_resolution_set_fingerprint,
    trading_rule_set_fingerprint,
)
from tip_api.persistence.china_ashare_market_mechanics_package import (
    ChinaAshareMarketMechanicsPackageResultV1,
)


class ChinaAsharePriceLimitResolverError(RuntimeError):
    pass


_SUPPORTED_BOARDS = {
    (ChinaAshareExchange.SSE, ChinaAshareBoard.SSE_MAIN),
    (ChinaAshareExchange.SSE, ChinaAshareBoard.STAR),
    (ChinaAshareExchange.SZSE, ChinaAshareBoard.SZSE_MAIN),
    (ChinaAshareExchange.SZSE, ChinaAshareBoard.CHINEXT),
}
_RATIO_REGIMES = {
    Decimal("0.05"): ChinaAsharePriceLimitRegime.PERCENT_5,
    Decimal("0.10"): ChinaAsharePriceLimitRegime.PERCENT_10,
    Decimal("0.20"): ChinaAsharePriceLimitRegime.PERCENT_20,
}


def plan_china_ashare_price_limit_resolver(
    *, mechanics: ChinaAshareMarketMechanicsPackageResultV1
) -> ChinaAsharePriceLimitResolverPlanV1:
    """Bind a resolver plan to one exact-reread official mechanics package."""

    rules = tuple(sorted(mechanics.trading_rules, key=lambda item: item.rule_id))
    if not rules:
        raise ChinaAsharePriceLimitResolverError("price-limit rule set is empty")
    _validate_rule_intervals(rules)
    return build_price_limit_resolver_plan(
        market_mechanics_package_fingerprint=mechanics.manifest.logical_fingerprint,
        trading_rule_set_fingerprint=trading_rule_set_fingerprint(rules),
        trading_rule_ids=tuple(item.rule_id for item in rules),
        official_source_urls=tuple(sorted({item.official_source_url for item in rules})),
        warning_subtype_fail_closed=True,
        ipo_stage_fail_closed=True,
        relisting_fail_closed=True,
        terminal_boundary_fail_closed=True,
        outcome_read_count=0,
        as_operated_claim_authorized=False,
        historical_coverage_authorized=False,
        research_backtest_authorized=False,
        product_publication_authorized=False,
    )


def resolve_china_ashare_price_limit(
    *,
    plan: ChinaAsharePriceLimitResolverPlanV1,
    trading_rules: tuple[ChinaAshareTradingRuleV1, ...],
    instrument_id: UUID,
    session_date: date,
    exchange: ChinaAshareExchange,
    board: ChinaAshareBoard,
    risk_warning_status: ChinaAshareRiskWarningStatus,
    listing_date: date,
    listing_stage: ChinaAshareListingStage,
    listing_session_ordinal: int | None,
    original_listing_evidence_complete: bool,
    risk_warning_evidence_complete: bool,
    relisting_absence_evidence_complete: bool,
    terminal_boundary_absence_evidence_complete: bool,
    input_partition_manifest_fingerprint: str | None = None,
) -> ChinaAsharePriceLimitResolutionV1:
    """Resolve from rules and declared evidence only; price/return values are absent."""

    rules = tuple(sorted(trading_rules, key=lambda item: item.rule_id))
    if trading_rule_set_fingerprint(rules) != plan.trading_rule_set_fingerprint:
        raise ChinaAsharePriceLimitResolverError("price-limit rule-set binding differs")
    reasons: set[str] = {"outcome_blind_effective_dated_resolution"}
    if session_date < listing_date:
        reasons.add("session_precedes_listing_date")
    if (exchange, board) not in _SUPPORTED_BOARDS:
        reasons.add("exchange_board_rule_scope_unsupported")
    if not original_listing_evidence_complete:
        reasons.add("original_listing_evidence_incomplete")
    if not relisting_absence_evidence_complete:
        reasons.add("relisting_absence_evidence_incomplete")
    if not terminal_boundary_absence_evidence_complete:
        reasons.add("terminal_boundary_evidence_incomplete")
    if not risk_warning_evidence_complete:
        reasons.add("risk_warning_evidence_incomplete")
    if risk_warning_status is ChinaAshareRiskWarningStatus.UNKNOWN:
        reasons.add("risk_warning_status_unknown")
    elif risk_warning_status is not ChinaAshareRiskWarningStatus.NONE:
        reasons.add("risk_warning_subtype_or_transition_not_adjudicated")
    if listing_stage is ChinaAshareListingStage.UNKNOWN:
        reasons.add("listing_stage_unknown")
    elif listing_stage is ChinaAshareListingStage.RELISTING_OR_RESUMPTION:
        reasons.add("relisting_or_resumption_stage_not_adjudicated")
    elif listing_stage is ChinaAshareListingStage.TERMINAL_BOUNDARY:
        reasons.add("terminal_boundary_stage_not_adjudicated")
    elif (
        listing_stage is ChinaAshareListingStage.ORIGINAL_IPO
        and listing_session_ordinal is None
    ):
        reasons.add("listing_session_ordinal_unproven")

    hard_gap = any(
        item in reasons
        for item in (
            "session_precedes_listing_date",
            "exchange_board_rule_scope_unsupported",
            "original_listing_evidence_incomplete",
            "relisting_absence_evidence_incomplete",
            "terminal_boundary_evidence_incomplete",
            "risk_warning_evidence_incomplete",
            "risk_warning_status_unknown",
            "risk_warning_subtype_or_transition_not_adjudicated",
            "listing_stage_unknown",
            "relisting_or_resumption_stage_not_adjudicated",
            "terminal_boundary_stage_not_adjudicated",
            "listing_session_ordinal_unproven",
        )
    )
    matching = ()
    if not hard_gap:
        matching = tuple(
            item
            for item in rules
            if item.exchange is exchange
            and item.board is board
            and item.risk_warning_status is ChinaAshareRiskWarningStatus.NONE
            and item.effective_from <= session_date
            and (item.effective_to is None or session_date <= item.effective_to)
        )
        if not matching:
            reasons.add("effective_dated_rule_missing")
        elif len(matching) > 1:
            reasons.add("effective_dated_rule_ambiguous")

    if hard_gap or len(matching) != 1:
        return _quarantined(
            plan=plan,
            instrument_id=instrument_id,
            session_date=session_date,
            exchange=exchange,
            board=board,
            risk_warning_status=risk_warning_status,
            listing_date=listing_date,
            listing_stage=listing_stage,
            listing_session_ordinal=listing_session_ordinal,
            original_listing_evidence_complete=original_listing_evidence_complete,
            risk_warning_evidence_complete=risk_warning_evidence_complete,
            relisting_absence_evidence_complete=relisting_absence_evidence_complete,
            terminal_boundary_absence_evidence_complete=(
                terminal_boundary_absence_evidence_complete
            ),
            reasons=reasons,
            input_partition_manifest_fingerprint=input_partition_manifest_fingerprint,
        )

    rule = matching[0]
    if (
        listing_stage is ChinaAshareListingStage.ORIGINAL_IPO
        and rule.ipo_no_limit_session_count == 0
    ):
        reasons.add("legacy_ipo_stage_transition_rule_missing")
        return _quarantined(
            plan=plan,
            instrument_id=instrument_id,
            session_date=session_date,
            exchange=exchange,
            board=board,
            risk_warning_status=risk_warning_status,
            listing_date=listing_date,
            listing_stage=listing_stage,
            listing_session_ordinal=listing_session_ordinal,
            original_listing_evidence_complete=original_listing_evidence_complete,
            risk_warning_evidence_complete=risk_warning_evidence_complete,
            relisting_absence_evidence_complete=relisting_absence_evidence_complete,
            terminal_boundary_absence_evidence_complete=(
                terminal_boundary_absence_evidence_complete
            ),
            reasons=reasons,
            input_partition_manifest_fingerprint=input_partition_manifest_fingerprint,
        )
    if (
        listing_stage is ChinaAshareListingStage.ORIGINAL_IPO
        and listing_session_ordinal is not None
        and listing_session_ordinal <= rule.ipo_no_limit_session_count
    ):
        regime = ChinaAsharePriceLimitRegime.NO_DAILY_LIMIT
        ratio = None
        reasons.add("original_ipo_no_limit_session_proven")
    else:
        ratio = rule.daily_price_limit_ratio
        regime = _RATIO_REGIMES.get(ratio) if ratio is not None else None
        if regime is None:
            reasons.add("daily_price_limit_ratio_unsupported")
            return _quarantined(
                plan=plan,
                instrument_id=instrument_id,
                session_date=session_date,
                exchange=exchange,
                board=board,
                risk_warning_status=risk_warning_status,
                listing_date=listing_date,
                listing_stage=listing_stage,
                listing_session_ordinal=listing_session_ordinal,
                original_listing_evidence_complete=original_listing_evidence_complete,
                risk_warning_evidence_complete=risk_warning_evidence_complete,
                relisting_absence_evidence_complete=relisting_absence_evidence_complete,
                terminal_boundary_absence_evidence_complete=(
                    terminal_boundary_absence_evidence_complete
                ),
                reasons=reasons,
                input_partition_manifest_fingerprint=(
                    input_partition_manifest_fingerprint
                ),
            )
        reasons.add("bounded_daily_ratio_rule_selected")
    return build_price_limit_resolution(
        instrument_id=instrument_id,
        session_date=session_date,
        exchange=exchange,
        board=board,
        risk_warning_status=risk_warning_status,
        listing_date=listing_date,
        listing_stage=listing_stage,
        listing_session_ordinal=listing_session_ordinal,
        original_listing_evidence_complete=original_listing_evidence_complete,
        risk_warning_evidence_complete=risk_warning_evidence_complete,
        relisting_absence_evidence_complete=relisting_absence_evidence_complete,
        terminal_boundary_absence_evidence_complete=(
            terminal_boundary_absence_evidence_complete
        ),
        status=ChinaAsharePriceLimitResolutionStatus.RESOLVED,
        price_limit_regime=regime,
        daily_price_limit_ratio=ratio,
        selected_rule_id=rule.rule_id,
        reason_codes=tuple(sorted(reasons)),
        resolver_plan_fingerprint=plan.logical_fingerprint,
        input_partition_manifest_fingerprint=input_partition_manifest_fingerprint,
        outcome_read_count=0,
        as_operated=False,
        research_eligible=False,
    )


def build_price_limit_partition_aggregate_from_resolutions(
    *,
    plan: ChinaAsharePriceLimitResolverPlanV1,
    partition_index: int,
    input_partition_manifest_fingerprint: str,
    resolutions: tuple[ChinaAsharePriceLimitResolutionV1, ...],
):
    if not resolutions:
        raise ChinaAsharePriceLimitResolverError("price-limit partition is empty")
    if any(
        item.resolver_plan_fingerprint != plan.logical_fingerprint
        or item.input_partition_manifest_fingerprint
        != input_partition_manifest_fingerprint
        for item in resolutions
    ):
        raise ChinaAsharePriceLimitResolverError("price-limit partition binding differs")
    regimes = tuple(item.price_limit_regime for item in resolutions)
    reason_sets = tuple(set(item.reason_codes) for item in resolutions)
    return build_price_limit_partition_aggregate(
        resolver_plan_fingerprint=plan.logical_fingerprint,
        partition_index=partition_index,
        input_partition_manifest_fingerprint=input_partition_manifest_fingerprint,
        state_count=len(resolutions),
        resolved_count=sum(
            item.status is ChinaAsharePriceLimitResolutionStatus.RESOLVED
            for item in resolutions
        ),
        quarantined_count=sum(
            item.status is ChinaAsharePriceLimitResolutionStatus.QUARANTINED
            for item in resolutions
        ),
        no_daily_limit_count=regimes.count(ChinaAsharePriceLimitRegime.NO_DAILY_LIMIT),
        percent_5_count=regimes.count(ChinaAsharePriceLimitRegime.PERCENT_5),
        percent_10_count=regimes.count(ChinaAsharePriceLimitRegime.PERCENT_10),
        percent_20_count=regimes.count(ChinaAsharePriceLimitRegime.PERCENT_20),
        warning_evidence_gap_count=sum(
            bool(
                reasons
                & {
                    "risk_warning_evidence_incomplete",
                    "risk_warning_status_unknown",
                    "risk_warning_subtype_or_transition_not_adjudicated",
                }
            )
            for reasons in reason_sets
        ),
        lifecycle_evidence_gap_count=sum(
            bool(
                reasons
                & {
                    "original_listing_evidence_incomplete",
                    "relisting_absence_evidence_incomplete",
                    "terminal_boundary_evidence_incomplete",
                    "listing_stage_unknown",
                    "relisting_or_resumption_stage_not_adjudicated",
                    "terminal_boundary_stage_not_adjudicated",
                    "listing_session_ordinal_unproven",
                    "legacy_ipo_stage_transition_rule_missing",
                }
            )
            for reasons in reason_sets
        ),
        rule_gap_count=sum(
            bool(
                reasons
                & {
                    "exchange_board_rule_scope_unsupported",
                    "effective_dated_rule_missing",
                    "effective_dated_rule_ambiguous",
                    "daily_price_limit_ratio_unsupported",
                }
            )
            for reasons in reason_sets
        ),
        resolution_set_fingerprint=price_limit_resolution_set_fingerprint(resolutions),
        outcome_read_count=0,
        as_operated_claim_authorized=False,
        research_backtest_authorized=False,
    )


def _quarantined(
    *,
    plan: ChinaAsharePriceLimitResolverPlanV1,
    instrument_id: UUID,
    session_date: date,
    exchange: ChinaAshareExchange,
    board: ChinaAshareBoard,
    risk_warning_status: ChinaAshareRiskWarningStatus,
    listing_date: date,
    listing_stage: ChinaAshareListingStage,
    listing_session_ordinal: int | None,
    original_listing_evidence_complete: bool,
    risk_warning_evidence_complete: bool,
    relisting_absence_evidence_complete: bool,
    terminal_boundary_absence_evidence_complete: bool,
    reasons: set[str],
    input_partition_manifest_fingerprint: str | None,
) -> ChinaAsharePriceLimitResolutionV1:
    return build_price_limit_resolution(
        instrument_id=instrument_id,
        session_date=session_date,
        exchange=exchange,
        board=board,
        risk_warning_status=risk_warning_status,
        listing_date=listing_date,
        listing_stage=listing_stage,
        listing_session_ordinal=listing_session_ordinal,
        original_listing_evidence_complete=original_listing_evidence_complete,
        risk_warning_evidence_complete=risk_warning_evidence_complete,
        relisting_absence_evidence_complete=relisting_absence_evidence_complete,
        terminal_boundary_absence_evidence_complete=(
            terminal_boundary_absence_evidence_complete
        ),
        status=ChinaAsharePriceLimitResolutionStatus.QUARANTINED,
        price_limit_regime=ChinaAsharePriceLimitRegime.UNKNOWN,
        daily_price_limit_ratio=None,
        selected_rule_id=None,
        reason_codes=tuple(sorted(reasons)),
        resolver_plan_fingerprint=plan.logical_fingerprint,
        input_partition_manifest_fingerprint=input_partition_manifest_fingerprint,
        outcome_read_count=0,
        as_operated=False,
        research_eligible=False,
    )


def _validate_rule_intervals(rules: tuple[ChinaAshareTradingRuleV1, ...]) -> None:
    for index, left in enumerate(rules):
        for right in rules[index + 1 :]:
            if (
                left.exchange is not right.exchange
                or left.board is not right.board
                or left.risk_warning_status is not right.risk_warning_status
            ):
                continue
            left_end = left.effective_to or date.max
            right_end = right.effective_to or date.max
            if left.effective_from <= right_end and right.effective_from <= left_end:
                raise ChinaAsharePriceLimitResolverError(
                    "price-limit effective intervals overlap"
                )
