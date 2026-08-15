# EOD Return Analytics

## Purpose

This document records the first provider-neutral EOD return analytics boundary built on completed canonical EOD sessions.

## Status

Implemented for completed session pairs; the deployed latest pair is 2026-08-13 and 2026-08-14.

## Close-to-Close Returns

Returns are joined by stable canonical `instrument_id`, not ticker. Ticker is display metadata only.

```text
close_to_close_return = (current_close / previous_close) - 1
```

The result is a decimal ratio: `0.05` means 5%. Calculations use `Decimal` and do not use binary float arithmetic. Display rounding is deferred to the frontend.

Records with no previous bar are not included in the comparable denominator and are counted as current-only. Records present only in the previous session are counted as previous-only.

## Market Summary V1

Market Summary V1 includes:

- comparable instrument count
- current-only and previous-only counts
- advancers, decliners, and unchanged counts
- advance/decline ratio and net
- advancer and decliner current volume
- up/down volume ratio
- equal-weight return
- median return
- positive and negative return share
- common-stock and ETF comparable counts
- quality warning count

The equal-weight return is a simple average over comparable instruments. It is not an index return and is not market-cap weighted.

## Movers V1

Movers use a V1 Candidate Default liquidity screen:

```text
current_dollar_volume_proxy >= 5,000,000 USD
```

`current_dollar_volume_proxy = current_close * current_volume`.

This is a close-times-volume liquidity proxy. It is not real notional, market capitalization, money flow, or fund flow.

Top gainers sort by return descending, liquidity proxy descending, then ticker ascending. Top losers sort by return ascending, liquidity proxy descending, then ticker ascending.

## Dashboard V1.1 Universe Overview

Dashboard V1.1 adds a product-facing overview service on top of the canonical return rows. It computes selected-universe Market Summary, movers, and Trading Activity Map views for `Tradable U.S. Equities`, `All Operating Equities`, and `All Eligible Instruments`.

The default `Tradable U.S. Equities` universe uses previous-session close and previous-session close-times-volume gates only. ETFs are excluded from the default equity breadth and movers, and fixed Sector Benchmark ETFs are reported separately.

Dashboard V1.1 also exposes Market Benchmark Strip rows for SPY, QQQ, IWM, DIA, and the selected universe equal-weight return. ETF benchmarks do not enter stock breadth, movers, or the Trading Activity Map.

Sector Benchmark ETF relative performance is:

```text
relative_to_spy_return = sector_etf_close_to_close_return - SPY_close_to_close_return
```

It is an arithmetic return difference only. It is not alpha, risk-adjusted excess return, sector breadth, sector rotation, or fund flow.

Dashboard Overview uses the accepted offline XNYS calendar to compare expected and actual completed sessions. Calendar freshness remains distinct from completed-file validation and return calculation.

## Liquidity Map V1

Liquidity Map V1 is a liquidity-weighted visual payload, not a traditional market-cap sector heatmap.

Metadata states:

- `map_type=liquidity` for the broad legacy response; `map_type=trading_activity` for Dashboard V1.1 universe projections
- `size_metric=close_times_volume_proxy`
- `color_metric=close_to_close_return`
- `is_market_cap_weighted=false`
- `is_sector_grouped=false`

The current implementation does not invent sector, industry, theme, or market-cap fields.

## Traditional Heatmap Blocker

A traditional Market-Cap Sector Heatmap remains blocked pending accepted sources for:

- canonical market capitalization
- sector/industry taxonomy
- point-in-time classification membership
- licensing and public-display boundary

## Non-Goals

- frontend Dashboard implementation
- market-cap weighting
- sector/theme grouping
- fund-flow or money-flow calculations
- prior-period history beyond the completed pair
- database/catalog integration
- Massive API calls
- OCI deployment
