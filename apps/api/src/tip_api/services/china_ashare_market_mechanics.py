"""Reconcile pilot A-share trading rules and explicit execution costs."""

from __future__ import annotations

from datetime import UTC, date, datetime, time
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

from tip_api.contracts.china_ashare.v1 import (
    ChinaAshareAccountCostScenarioV1,
    ChinaAshareBoard,
    ChinaAshareCommissionBasis,
    ChinaAshareExchange,
    ChinaAshareExecutionCostBreakdownV1,
    ChinaAshareFeeKind,
    ChinaAshareFeeRuleV1,
    ChinaAshareMarketMechanicsReportV1,
    ChinaAshareOfficialSourceReferenceV1,
    ChinaAsharePilotPriceLimitDecisionV1,
    ChinaAsharePriceLimitRegime,
    ChinaAshareRiskWarningStatus,
    ChinaAshareTradeSide,
    ChinaAshareTradingRuleV1,
    build_account_cost_scenario,
    build_market_mechanics_report,
)
from tip_api.contracts.common import QualityStatus
from tip_api.persistence.china_ashare_pilot_package import (
    ChinaAsharePilotDailyPackageResultV1,
    read_china_ashare_pilot_daily_package,
)
from tip_api.persistence.china_ashare_calendar_evidence_package import (
    read_china_ashare_calendar_evidence_package,
)
from tip_api.persistence.china_ashare_market_mechanics_package import (
    ChinaAshareMarketMechanicsPackageResultV1,
    publish_china_ashare_market_mechanics_package,
)
from tip_api.providers.china_ashare.official_market_mechanics_adapter import (
    OfficialMarketMechanicsHttpFetcher,
    UrllibOfficialMarketMechanicsHttpFetcher,
    capture_official_market_mechanics_source,
)

_CENT = Decimal("0.01")
_ZERO = Decimal("0")
_SUPPORTED_EXCHANGES = (ChinaAshareExchange.SSE, ChinaAshareExchange.SZSE)


def capture_and_publish_pilot_market_mechanics(
    *,
    daily_package_path: Path,
    calendar_package_path: Path,
    custody_root: Path,
    captured_at: datetime,
    fetcher: OfficialMarketMechanicsHttpFetcher | None = None,
) -> ChinaAshareMarketMechanicsPackageResultV1:
    """Capture official mechanics evidence and bind it to the pilot packages."""

    daily_package = read_china_ashare_pilot_daily_package(
        package_path=daily_package_path
    )
    calendar_package = read_china_ashare_calendar_evidence_package(
        package_path=calendar_package_path
    )
    if calendar_package.report.daily_package_fingerprint != (
        daily_package.manifest.logical_fingerprint
    ):
        raise ValueError("calendar evidence is not bound to the selected daily package")
    if not calendar_package.report.calendar_reconciled:
        raise ValueError("calendar evidence has not passed reconciliation")
    source_references = build_official_market_mechanics_sources(
        retrieved_at=captured_at
    )
    active_fetcher = fetcher or UrllibOfficialMarketMechanicsHttpFetcher()
    captured_sources = tuple(
        capture_official_market_mechanics_source(
            reference=reference,
            fetcher=active_fetcher,
        )
        for reference in source_references
    )
    captured_references = tuple(item.reference for item in captured_sources)
    trading_rules = build_pilot_trading_rules(
        source_references=captured_references
    )
    fee_rules = build_pilot_fee_rules(source_references=captured_references)
    account_cost_scenario = build_ping_an_account_cost_scenario(
        first_target_session=daily_package.plan.history_start_date,
        confirmed_at=captured_at,
    )
    decisions = reconcile_pilot_price_limits(
        daily_package=daily_package,
        trading_rules=trading_rules,
    )
    report = build_pilot_market_mechanics_report(
        daily_package=daily_package,
        calendar_package_fingerprint=calendar_package.manifest.logical_fingerprint,
        source_references=captured_references,
        trading_rules=trading_rules,
        fee_rules=fee_rules,
        decisions=decisions,
        account_cost_scenario=account_cost_scenario,
        evaluated_at=captured_at,
    )
    return publish_china_ashare_market_mechanics_package(
        custody_root=custody_root,
        captured_sources=captured_sources,
        trading_rules=trading_rules,
        fee_rules=fee_rules,
        account_cost_scenario=account_cost_scenario,
        price_limit_decisions=decisions,
        report=report,
    )


def build_official_market_mechanics_sources(
    *, retrieved_at: datetime
) -> tuple[ChinaAshareOfficialSourceReferenceV1, ...]:
    """Return the bounded official source registry for the pilot mechanics gate."""

    rows = (
        (
            "sse-trading-rule-2026",
            "https://www.sse.com.cn/lawandrules/sselawsrules2025/stocks/exchange/c/c_20260424_10816482.shtml",
            "上海证券交易所",
            date(2026, 4, 24),
            "A股交收前不得卖出、主板及科创板涨跌幅和申报数量规则",
        ),
        (
            "sse-star-trading",
            "https://star.sse.com.cn/star/media/news/c/c_20190719_4866789.shtml",
            "上海证券交易所",
            date(2019, 7, 19),
            "科创板20%涨跌幅、首五日无涨跌幅及200股最低申报",
        ),
        (
            "szse-chinext-trading",
            "https://www.szse.cn/www/investor/knowledge/t20200729_580056.html",
            "深圳证券交易所",
            date(2020, 7, 29),
            "创业板20%涨跌幅及首五日无涨跌幅",
        ),
        (
            "szse-main-2023",
            "https://investor.szse.cn/institute/rules/t20230629_601434.html",
            "深圳证券交易所",
            date(2023, 6, 29),
            "主板10%、风险警示5%、创业板20%及首五日无涨跌幅",
        ),
        (
            "sse-risk-warning-2026",
            "https://www.sse.com.cn/aboutus/mediacenter/hotandd/c/c_20260424_10816474.shtml",
            "上海证券交易所",
            date(2026, 4, 24),
            "主板风险警示股票自2026-07-06由5%调整为10%",
        ),
        (
            "szse-risk-warning-2026",
            "https://www.szse.cn/lawrules/service/member/t20260630_621404.html",
            "深圳证券交易所",
            date(2026, 6, 30),
            "深市主板风险警示股票2026-07-06规则变更",
        ),
        (
            "stamp-duty-law-2022",
            "https://guangdong.chinatax.gov.cn/gdsw/fssw_gkwj/2023-03/07/content_ca650c65a7ca4d95b4d0b3097fb44f51.shtml",
            "国家税务总局",
            date(2023, 3, 7),
            "证券交易印花税出让方单边征收及法定税率",
        ),
        (
            "stamp-duty-half-2023",
            "https://shanxi.chinatax.gov.cn/web/detail/sx-11400-545-1780448",
            "财政部、国家税务总局",
            date(2023, 8, 27),
            "自2023-08-28证券交易印花税减半",
        ),
        (
            "sse-handling-fee-2023",
            "https://www.sse.com.cn/aboutus/mediacenter/hotandd/c/c_20230818_5725378.shtml",
            "上海证券交易所",
            date(2023, 8, 18),
            "沪市A股经手费由0.00487%降至0.00341%",
        ),
        (
            "szse-handling-fee-2023",
            "https://www.szse.cn/disclosure/notice/t20230818_602805.html",
            "深圳证券交易所",
            date(2023, 8, 18),
            "深市A股经手费由0.00487%降至0.00341%",
        ),
        (
            "transfer-fee-cut-2022",
            "https://jrj.sh.gov.cn/SCDT197/20220429/f715759a877b4158812eb6df70ccb49e.html",
            "中共上海市委金融委员会办公室",
            date(2022, 4, 29),
            "中国结算公告所载A股过户费由0.02‰降至0.01‰并双向收取",
        ),
        (
            "regulatory-fee-2012",
            "https://www.csrc.gov.cn/csrc/c100028/c1002446/content.shtml",
            "中国证券监督管理委员会",
            date(2012, 7, 13),
            "股票证券交易监管费0.02‰",
        ),
        (
            "commission-standard-2002",
            "https://www.chinatax.gov.cn/chinatax/n810341/n810765/n812203/200202/c1209808/content.html",
            "国家计委、中国证监会、国家税务总局",
            date(2002, 5, 1),
            "A股佣金包含监管费和交易所手续费且不足5元按5元收取",
        ),
    )
    return tuple(
        ChinaAshareOfficialSourceReferenceV1(
            source_id=source_id,
            source_url=source_url,
            publisher=publisher,
            published_date=published_date,
            evidence_purpose=evidence_purpose,
            retrieved_at=retrieved_at,
        )
        for source_id, source_url, publisher, published_date, evidence_purpose in rows
    )


def build_pilot_trading_rules(
    *, source_references: tuple[ChinaAshareOfficialSourceReferenceV1, ...]
) -> tuple[ChinaAshareTradingRuleV1, ...]:
    sources = {item.source_id: item for item in source_references}
    required = {
        "sse-trading-rule-2026",
        "sse-star-trading",
        "szse-chinext-trading",
        "szse-main-2023",
        "sse-risk-warning-2026",
        "szse-risk-warning-2026",
    }
    if not required.issubset(sources):
        raise ValueError("official trading-rule source registry is incomplete")

    def row(
        *,
        rule_id: str,
        exchange: ChinaAshareExchange,
        board: ChinaAshareBoard,
        risk: ChinaAshareRiskWarningStatus,
        start: date,
        end: date | None,
        ratio: str,
        ipo_no_limit: int,
        minimum: int,
        increment: int,
        source_id: str,
    ) -> ChinaAshareTradingRuleV1:
        source = sources[source_id]
        return ChinaAshareTradingRuleV1(
            rule_id=rule_id,
            exchange=exchange,
            board=board,
            risk_warning_status=risk,
            effective_from=start,
            effective_to=end,
            settlement_rule="t_plus_one",
            daily_price_limit_ratio=Decimal(ratio),
            ipo_no_limit_session_count=ipo_no_limit,
            minimum_buy_order_shares=minimum,
            order_increment_shares=increment,
            official_source_url=source.source_url,
            source_available_at=_conservative_day_availability(source.published_date),
            ingested_at=source.retrieved_at,
            quality_status=QualityStatus.VALID,
        )

    target_start = date(2021, 9, 16)
    registration_start = date(2023, 4, 10)
    risk_change = date(2026, 7, 6)
    return tuple(
        sorted(
            (
                row(
                    rule_id="sse-main-normal-pre-registration-v1",
                    exchange=ChinaAshareExchange.SSE,
                    board=ChinaAshareBoard.SSE_MAIN,
                    risk=ChinaAshareRiskWarningStatus.NONE,
                    start=target_start,
                    end=registration_start.fromordinal(registration_start.toordinal() - 1),
                    ratio="0.10",
                    ipo_no_limit=0,
                    minimum=100,
                    increment=100,
                    source_id="sse-trading-rule-2026",
                ),
                row(
                    rule_id="sse-main-normal-registration-v1",
                    exchange=ChinaAshareExchange.SSE,
                    board=ChinaAshareBoard.SSE_MAIN,
                    risk=ChinaAshareRiskWarningStatus.NONE,
                    start=registration_start,
                    end=None,
                    ratio="0.10",
                    ipo_no_limit=5,
                    minimum=100,
                    increment=100,
                    source_id="sse-trading-rule-2026",
                ),
                row(
                    rule_id="sse-main-risk-warning-5-v1",
                    exchange=ChinaAshareExchange.SSE,
                    board=ChinaAshareBoard.SSE_MAIN,
                    risk=ChinaAshareRiskWarningStatus.PRESENT_UNSPECIFIED,
                    start=target_start,
                    end=risk_change.fromordinal(risk_change.toordinal() - 1),
                    ratio="0.05",
                    ipo_no_limit=0,
                    minimum=100,
                    increment=100,
                    source_id="sse-risk-warning-2026",
                ),
                row(
                    rule_id="sse-main-risk-warning-10-v1",
                    exchange=ChinaAshareExchange.SSE,
                    board=ChinaAshareBoard.SSE_MAIN,
                    risk=ChinaAshareRiskWarningStatus.PRESENT_UNSPECIFIED,
                    start=risk_change,
                    end=None,
                    ratio="0.10",
                    ipo_no_limit=0,
                    minimum=100,
                    increment=100,
                    source_id="sse-risk-warning-2026",
                ),
                row(
                    rule_id="sse-star-normal-v1",
                    exchange=ChinaAshareExchange.SSE,
                    board=ChinaAshareBoard.STAR,
                    risk=ChinaAshareRiskWarningStatus.NONE,
                    start=target_start,
                    end=None,
                    ratio="0.20",
                    ipo_no_limit=5,
                    minimum=200,
                    increment=1,
                    source_id="sse-star-trading",
                ),
                row(
                    rule_id="szse-main-normal-pre-registration-v1",
                    exchange=ChinaAshareExchange.SZSE,
                    board=ChinaAshareBoard.SZSE_MAIN,
                    risk=ChinaAshareRiskWarningStatus.NONE,
                    start=target_start,
                    end=registration_start.fromordinal(registration_start.toordinal() - 1),
                    ratio="0.10",
                    ipo_no_limit=0,
                    minimum=100,
                    increment=100,
                    source_id="szse-main-2023",
                ),
                row(
                    rule_id="szse-main-normal-registration-v1",
                    exchange=ChinaAshareExchange.SZSE,
                    board=ChinaAshareBoard.SZSE_MAIN,
                    risk=ChinaAshareRiskWarningStatus.NONE,
                    start=registration_start,
                    end=None,
                    ratio="0.10",
                    ipo_no_limit=5,
                    minimum=100,
                    increment=100,
                    source_id="szse-main-2023",
                ),
                row(
                    rule_id="szse-main-risk-warning-5-v1",
                    exchange=ChinaAshareExchange.SZSE,
                    board=ChinaAshareBoard.SZSE_MAIN,
                    risk=ChinaAshareRiskWarningStatus.PRESENT_UNSPECIFIED,
                    start=target_start,
                    end=risk_change.fromordinal(risk_change.toordinal() - 1),
                    ratio="0.05",
                    ipo_no_limit=0,
                    minimum=100,
                    increment=100,
                    source_id="szse-main-2023",
                ),
                row(
                    rule_id="szse-main-risk-warning-10-v1",
                    exchange=ChinaAshareExchange.SZSE,
                    board=ChinaAshareBoard.SZSE_MAIN,
                    risk=ChinaAshareRiskWarningStatus.PRESENT_UNSPECIFIED,
                    start=risk_change,
                    end=None,
                    ratio="0.10",
                    ipo_no_limit=0,
                    minimum=100,
                    increment=100,
                    source_id="szse-risk-warning-2026",
                ),
                row(
                    rule_id="szse-chinext-normal-v1",
                    exchange=ChinaAshareExchange.SZSE,
                    board=ChinaAshareBoard.CHINEXT,
                    risk=ChinaAshareRiskWarningStatus.NONE,
                    start=target_start,
                    end=None,
                    ratio="0.20",
                    ipo_no_limit=5,
                    minimum=100,
                    increment=100,
                    source_id="szse-chinext-trading",
                ),
            ),
            key=lambda item: item.rule_id,
        )
    )


def build_pilot_fee_rules(
    *, source_references: tuple[ChinaAshareOfficialSourceReferenceV1, ...]
) -> tuple[ChinaAshareFeeRuleV1, ...]:
    sources = {item.source_id: item for item in source_references}
    required = {
        "stamp-duty-law-2022",
        "stamp-duty-half-2023",
        "sse-handling-fee-2023",
        "szse-handling-fee-2023",
        "transfer-fee-cut-2022",
        "regulatory-fee-2012",
    }
    if not required.issubset(sources):
        raise ValueError("official fee source registry is incomplete")
    target_start = date(2021, 9, 16)
    transfer_change = date(2022, 4, 29)
    fee_change = date(2023, 8, 28)
    rows: list[ChinaAshareFeeRuleV1] = []
    for exchange in _SUPPORTED_EXCHANGES:
        suffix = exchange.value.lower()
        handling_source = f"{suffix}-handling-fee-2023"
        rows.extend(
            (
                _fee_rule(
                    fee_rule_id=f"{suffix}-stamp-duty-0.1pct-v1",
                    fee_kind=ChinaAshareFeeKind.STAMP_DUTY,
                    exchange=exchange,
                    start=target_start,
                    end=date(2023, 8, 27),
                    buy_rate="0",
                    sell_rate="0.001",
                    source_id="stamp-duty-law-2022",
                ),
                _fee_rule(
                    fee_rule_id=f"{suffix}-stamp-duty-0.05pct-v1",
                    fee_kind=ChinaAshareFeeKind.STAMP_DUTY,
                    exchange=exchange,
                    start=fee_change,
                    end=None,
                    buy_rate="0",
                    sell_rate="0.0005",
                    source_id="stamp-duty-half-2023",
                ),
                _fee_rule(
                    fee_rule_id=f"{suffix}-regulatory-fee-0.002pct-v1",
                    fee_kind=ChinaAshareFeeKind.SECURITIES_REGULATORY_FEE,
                    exchange=exchange,
                    start=target_start,
                    end=None,
                    buy_rate="0.00002",
                    sell_rate="0.00002",
                    source_id="regulatory-fee-2012",
                ),
                _fee_rule(
                    fee_rule_id=f"{suffix}-handling-fee-0.00487pct-v1",
                    fee_kind=ChinaAshareFeeKind.EXCHANGE_HANDLING_FEE,
                    exchange=exchange,
                    start=target_start,
                    end=date(2023, 8, 27),
                    buy_rate="0.0000487",
                    sell_rate="0.0000487",
                    source_id=handling_source,
                ),
                _fee_rule(
                    fee_rule_id=f"{suffix}-handling-fee-0.00341pct-v1",
                    fee_kind=ChinaAshareFeeKind.EXCHANGE_HANDLING_FEE,
                    exchange=exchange,
                    start=fee_change,
                    end=None,
                    buy_rate="0.0000341",
                    sell_rate="0.0000341",
                    source_id=handling_source,
                ),
                _fee_rule(
                    fee_rule_id=f"{suffix}-transfer-fee-0.002pct-v1",
                    fee_kind=ChinaAshareFeeKind.TRANSFER_FEE,
                    exchange=exchange,
                    start=target_start,
                    end=date(2022, 4, 28),
                    buy_rate="0.00002",
                    sell_rate="0.00002",
                    source_id="transfer-fee-cut-2022",
                ),
                _fee_rule(
                    fee_rule_id=f"{suffix}-transfer-fee-0.001pct-v1",
                    fee_kind=ChinaAshareFeeKind.TRANSFER_FEE,
                    exchange=exchange,
                    start=transfer_change,
                    end=None,
                    buy_rate="0.00001",
                    sell_rate="0.00001",
                    source_id="transfer-fee-cut-2022",
                ),
            )
        )
    return tuple(sorted(rows, key=lambda item: item.fee_rule_id))


def build_ping_an_account_cost_scenario(
    *,
    first_target_session: date,
    confirmed_at: datetime,
    slippage_rate_per_side: Decimal = Decimal("0.0005"),
) -> ChinaAshareAccountCostScenarioV1:
    """Register the user-reported rate as a research assumption, not broker proof."""

    return build_account_cost_scenario(
        commission_basis=ChinaAshareCommissionBasis.ALL_IN,
        commission_rate_per_side=Decimal("0.0001"),
        minimum_commission_cny_per_order=Decimal("5"),
        slippage_rate_per_side=slippage_rate_per_side,
        currency_quantum_cny=_CENT,
        account_observation_status="user_reported",
        effective_from=first_target_session,
        confirmed_at=confirmed_at,
        reason_codes=(
            "all_in_commission_basis_pending_statement_confirmation",
            "current_rate_backcast_as_research_assumption",
            "minimum_five_yuan_applied_conservatively",
            "user_reported_commission_rate",
        ),
    )


def calculate_execution_cost(
    *,
    session_date: date,
    exchange: ChinaAshareExchange,
    side: ChinaAshareTradeSide,
    gross_notional_cny: Decimal,
    fee_rules: tuple[ChinaAshareFeeRuleV1, ...],
    scenario: ChinaAshareAccountCostScenarioV1,
) -> ChinaAshareExecutionCostBreakdownV1:
    if gross_notional_cny <= 0:
        raise ValueError("gross_notional_cny must be positive")
    selected = {
        kind: _fee_for(
            fee_rules=fee_rules,
            exchange=exchange,
            fee_kind=kind,
            session_date=session_date,
        )
        for kind in ChinaAshareFeeKind
    }
    rate_field = "buy_rate" if side is ChinaAshareTradeSide.BUY else "sell_rate"

    def fee(kind: ChinaAshareFeeKind) -> Decimal:
        return _money(gross_notional_cny * getattr(selected[kind], rate_field))

    commission = _money(
        max(
            gross_notional_cny * scenario.commission_rate_per_side,
            scenario.minimum_commission_cny_per_order,
        )
    )
    regulatory = fee(ChinaAshareFeeKind.SECURITIES_REGULATORY_FEE)
    handling = fee(ChinaAshareFeeKind.EXCHANGE_HANDLING_FEE)
    if scenario.commission_basis is ChinaAshareCommissionBasis.ALL_IN:
        regulatory = _ZERO.quantize(_CENT)
        handling = _ZERO.quantize(_CENT)
    transfer = fee(ChinaAshareFeeKind.TRANSFER_FEE)
    stamp = fee(ChinaAshareFeeKind.STAMP_DUTY)
    slippage = _money(gross_notional_cny * scenario.slippage_rate_per_side)
    total = sum(
        (commission, regulatory, handling, transfer, stamp, slippage),
        _ZERO,
    )
    return ChinaAshareExecutionCostBreakdownV1(
        session_date=session_date,
        exchange=exchange,
        side=side,
        gross_notional_cny=gross_notional_cny,
        broker_commission_cny=commission,
        securities_regulatory_fee_cny=regulatory,
        exchange_handling_fee_cny=handling,
        transfer_fee_cny=transfer,
        stamp_duty_cny=stamp,
        slippage_cny=slippage,
        total_cost_cny=total,
        commission_basis=scenario.commission_basis,
        applied_fee_rule_ids=tuple(sorted(item.fee_rule_id for item in selected.values())),
        scenario_fingerprint=scenario.logical_fingerprint,
    )


def reconcile_pilot_price_limits(
    *,
    daily_package: ChinaAsharePilotDailyPackageResultV1,
    trading_rules: tuple[ChinaAshareTradingRuleV1, ...],
) -> tuple[ChinaAsharePilotPriceLimitDecisionV1, ...]:
    bars = {
        (item.instrument_id, item.session_date): item
        for item in daily_package.captured.daily_batch.bars
    }
    decisions: list[ChinaAsharePilotPriceLimitDecisionV1] = []
    for state in daily_package.captured.daily_batch.trading_states:
        rule = _trading_rule_for(state=state, trading_rules=trading_rules)
        if rule.daily_price_limit_ratio is None or state.pre_close is None:
            raise ValueError("pilot trading state lacks a bounded price-limit rule")
        up = _price(state.pre_close * (Decimal("1") + rule.daily_price_limit_ratio))
        down = _price(state.pre_close * (Decimal("1") - rule.daily_price_limit_ratio))
        bar = bars.get((state.instrument_id, state.session_date))
        if rule.daily_price_limit_ratio == Decimal("0.05"):
            regime = ChinaAsharePriceLimitRegime.PERCENT_5
        elif rule.daily_price_limit_ratio == Decimal("0.10"):
            regime = ChinaAsharePriceLimitRegime.PERCENT_10
        elif rule.daily_price_limit_ratio == Decimal("0.20"):
            regime = ChinaAsharePriceLimitRegime.PERCENT_20
        else:
            regime = ChinaAsharePriceLimitRegime.SOURCE_OBSERVED_OTHER
        within = None if bar is None else bar.high <= up and bar.low >= down
        decisions.append(
            ChinaAsharePilotPriceLimitDecisionV1(
                instrument_id=state.instrument_id,
                session_date=state.session_date,
                exchange=state.exchange,
                board=state.board,
                trading_status=state.trading_status,
                risk_warning_status=state.risk_warning_status,
                price_limit_regime=regime,
                rule_id=rule.rule_id,
                pre_close=state.pre_close,
                theoretical_up_limit=up,
                theoretical_down_limit=down,
                bar_high=None if bar is None else bar.high,
                bar_low=None if bar is None else bar.low,
                observed_bar_within_limits=within,
                price_tick_cny=_CENT,
                exact_limit_prices_source_observed=False,
                quality_status=(QualityStatus.VALID if within is not False else QualityStatus.REJECTED),
                reason_codes=(
                    "official_effective_dated_rule_applied",
                    "theoretical_limit_not_source_observed",
                ),
            )
        )
    return tuple(
        sorted(decisions, key=lambda item: (str(item.instrument_id), item.session_date))
    )


def build_pilot_market_mechanics_report(
    *,
    daily_package: ChinaAsharePilotDailyPackageResultV1,
    calendar_package_fingerprint: str,
    source_references: tuple[ChinaAshareOfficialSourceReferenceV1, ...],
    trading_rules: tuple[ChinaAshareTradingRuleV1, ...],
    fee_rules: tuple[ChinaAshareFeeRuleV1, ...],
    decisions: tuple[ChinaAsharePilotPriceLimitDecisionV1, ...],
    account_cost_scenario: ChinaAshareAccountCostScenarioV1,
    evaluated_at: datetime,
) -> ChinaAshareMarketMechanicsReportV1:
    del account_cost_scenario
    sessions = {
        item.session_date for item in daily_package.captured.daily_batch.trading_states
    }
    violations = sum(item.observed_bar_within_limits is False for item in decisions)
    unresolved = sum(
        item.price_limit_regime is ChinaAsharePriceLimitRegime.UNKNOWN
        for item in decisions
    )
    fee_complete = _fee_schedule_complete(
        fee_rules=fee_rules,
        first_session=min(sessions),
        last_session=max(sessions),
    )
    return build_market_mechanics_report(
        daily_package_fingerprint=daily_package.manifest.logical_fingerprint,
        calendar_package_fingerprint=calendar_package_fingerprint,
        evaluated_at=evaluated_at,
        target_session_count=len(sessions),
        source_reference_count=len(source_references),
        trading_rule_count=len(trading_rules),
        fee_rule_count=len(fee_rules),
        price_limit_decision_count=len(decisions),
        price_limit_bar_count=sum(item.bar_high is not None for item in decisions),
        suspended_decision_count=sum(
            item.trading_status.value == "suspended" for item in decisions
        ),
        price_limit_violation_count=violations,
        unresolved_rule_count=unresolved,
        effective_dated_rules_reconciled=violations == 0 and unresolved == 0,
        effective_dated_fees_reconciled=fee_complete,
        account_cost_scenario_registered=True,
        research_backtest_authorized=False,
        canonical_apply_authorized=False,
        product_publication_authorized=False,
        deployment_authorized=False,
        reason_codes=(
            "market_mechanics_gate_reconciled",
            "research_authority_requires_remaining_foundation_families",
        ),
    )


def _fee_rule(
    *,
    fee_rule_id: str,
    fee_kind: ChinaAshareFeeKind,
    exchange: ChinaAshareExchange,
    start: date,
    end: date | None,
    buy_rate: str,
    sell_rate: str,
    source_id: str,
    quality_status: QualityStatus = QualityStatus.VALID,
) -> ChinaAshareFeeRuleV1:
    return ChinaAshareFeeRuleV1(
        fee_rule_id=fee_rule_id,
        fee_kind=fee_kind,
        exchange=exchange,
        effective_from=start,
        effective_to=end,
        buy_rate=Decimal(buy_rate),
        sell_rate=Decimal(sell_rate),
        source_id=source_id,
        quality_status=quality_status,
    )


def _fee_for(
    *,
    fee_rules: tuple[ChinaAshareFeeRuleV1, ...],
    exchange: ChinaAshareExchange,
    fee_kind: ChinaAshareFeeKind,
    session_date: date,
) -> ChinaAshareFeeRuleV1:
    matching = tuple(
        item
        for item in fee_rules
        if item.exchange is exchange
        and item.fee_kind is fee_kind
        and item.effective_from <= session_date
        and (item.effective_to is None or session_date <= item.effective_to)
    )
    if len(matching) != 1:
        raise ValueError("fee schedule does not select exactly one effective rule")
    return matching[0]


def _trading_rule_for(*, state: object, trading_rules: tuple[ChinaAshareTradingRuleV1, ...]) -> ChinaAshareTradingRuleV1:
    exchange = getattr(state, "exchange")
    board = getattr(state, "board")
    risk = getattr(state, "risk_warning_status")
    session_date = getattr(state, "session_date")
    matching = tuple(
        item
        for item in trading_rules
        if item.exchange is exchange
        and item.board is board
        and item.risk_warning_status is risk
        and item.effective_from <= session_date
        and (item.effective_to is None or session_date <= item.effective_to)
    )
    if len(matching) != 1:
        raise ValueError("trading state does not select exactly one effective rule")
    return matching[0]


def _fee_schedule_complete(
    *,
    fee_rules: tuple[ChinaAshareFeeRuleV1, ...],
    first_session: date,
    last_session: date,
) -> bool:
    checkpoints = {first_session, last_session, date(2022, 4, 28), date(2022, 4, 29), date(2023, 8, 27), date(2023, 8, 28)}
    return all(
        len(
            tuple(
                item
                for item in fee_rules
                if item.exchange is exchange
                and item.fee_kind is kind
                and item.effective_from <= checkpoint
                and (item.effective_to is None or checkpoint <= item.effective_to)
            )
        )
        == 1
        for exchange in _SUPPORTED_EXCHANGES
        for kind in ChinaAshareFeeKind
        for checkpoint in checkpoints
        if first_session <= checkpoint <= last_session
    )


def _conservative_day_availability(value: date) -> datetime:
    return datetime.combine(value, time(15, 59, 59), tzinfo=UTC)


def _money(value: Decimal) -> Decimal:
    return value.quantize(_CENT, rounding=ROUND_HALF_UP)


def _price(value: Decimal) -> Decimal:
    return value.quantize(_CENT, rounding=ROUND_HALF_UP)
