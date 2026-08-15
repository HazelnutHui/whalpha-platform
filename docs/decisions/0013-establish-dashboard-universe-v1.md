# ADR 0013: Establish Dashboard Universe V1 for Market Overview

## Status

Accepted

## Date

2026-08-15

## Context

The first private Market Dashboard used the broad completed EOD comparable set. That was useful for pipeline validation, but it mixed common equities, ETFs, and other tradable products in the same breadth, movers, and treemap views. The result was less professional: ETF and stock roles were unclear, low-price and lower-liquidity instruments could dominate movers, and the treemap default contained too many small nodes.

Only two completed EOD sessions are available today: 2026-08-12 and 2026-08-13. The project does not yet have accepted point-in-time sector membership, market capitalization, corporate-action adjudication, or a 20-day liquidity history.

## Decision

Dashboard V1.1 introduces a versioned default analysis universe named `Tradable U.S.-Listed Equities V1`, displayed as `Tradable U.S. Equities`.

Membership requires:

- stable canonical `instrument_id`
- valid canonical EOD bars in both current and previous sessions
- current Instrument Master type recognized as operating common equity by the existing contract
- supported major U.S. exchange code from Instrument Master metadata
- previous-session close at least USD 5
- previous-session close x volume at least USD 20,000,000

The liquidity and price gates use previous-session data only to avoid current-day selection bias. This is a V1 provisional liquidity gate, not 20-day ADV or a long-term liquidity measure.

Auxiliary views remain available:

- `All Operating Equities`: operating common equity on supported exchanges without the V1 price/liquidity gates.
- `All Eligible Instruments`: broad comparable research/data-quality view that may include ETFs and other supported products.

ETF handling is explicit:

- ETFs are excluded from the default stock breadth, movers, and Trading Activity Map.
- The eleven S&P 500 Select Sector SPDR tickers are displayed separately as Sector Benchmark ETFs.
- Sector ETF returns are benchmark/proxy performance, not sector constituent breadth, fund flow, or money flow.

Liquidity Map V1 is renamed in the UI to Trading Activity Map. Node size remains current close x current volume, and color remains close-to-close return. Default display is top 50 nodes, with 50/75/100 controls.

Dashboard V1.1 also shows a compact Market Benchmark Strip for SPY, QQQ, IWM, DIA, and the selected universe equal-weight return. These ETF benchmark returns provide market context only; they do not enter the default stock breadth, movers, or Trading Activity Map.

Sector Benchmark ETFs are displayed as S&P 500 Select Sector SPDR 1D performance, including a `relative_to_spy_return` arithmetic return difference:

```text
relative_to_spy_return = sector_etf_close_to_close_return - SPY_close_to_close_return
```

This is not alpha, risk-adjusted performance, sector breadth, sector rotation, or fund flow.

Freshness status is deliberately conservative. Until the project accepts a reliable market-session calendar, the Dashboard reports the completed dataset session and snapshot generation time while marking freshness as `calendar_not_independently_verified`.

Price discontinuities where current close / previous close is >= 2 or <= 0.5 are flagged as `unverified_price_discontinuity` and excluded from default movers and map until corporate-action reconciliation exists.

## Consequences

- Market Pulse, breadth, up/down volume, movers, and the map now use the selected Dashboard Universe.
- Default home view becomes operating-equity focused and excludes ETFs and other products from equity breadth.
- ADR/common-stock separation is not claimed until Instrument Master supports it explicitly.
- Traditional market-cap sector heatmap remains blocked by missing point-in-time sector taxonomy, market cap, and licensing decisions.
- Once at least 20 completed sessions are available, the liquidity gate should be upgraded to a trailing median dollar-volume rule.
- Dashboard data freshness does not claim the current session is the latest completed U.S. trading day until a reliable calendar boundary is accepted.

## Alternatives Considered

- Keep the broad comparable universe as default. Rejected because it mixes instruments with different market roles.
- Use current-day dollar volume for membership. Rejected because it introduces same-day selection bias.
- Hand-map individual stocks into sectors. Rejected because it would create unsupported taxonomy and point-in-time membership claims.
