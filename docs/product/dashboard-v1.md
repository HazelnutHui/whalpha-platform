# Dashboard V1

> Historical design record. This document preserves the original dashboard
> proposal and is not the current product roadmap or workspace authority. Read
> [Product Vision](vision.md), [Product Scope](scope.md), and the
> [Roadmap](../project/roadmap.md) for current direction.

## Confirmed Homepage Structure

Implementation note: the first local Market Dashboard V1 implements the EOD-supported subset only: Market Pulse, breadth, up/down share volume, liquidity-screened movers, Liquidity Map V1, and data-quality/session metadata. Traditional market-cap sector heatmap, sector rotation, relationship monitor, and events remain deferred.


1. Market Structure Summary
2. Market Risk Regime
3. Standard Market Heatmap / Treemap
4. Market Breadth
5. Index & Style Strength
6. Sector / Theme Rotation
7. Dynamic Relationship & Rotation Monitor
8. Key Market Developments

## Market Risk Regime

Use these five canonical states:

- Strong Risk-On
- Selective Risk-On
- Neutral / Mixed
- Selective Risk-Off
- Strong Risk-Off

## Standard Market Heatmap / Treemap

Confirmed behavior:

- Hierarchy: sector -> industry -> stock
- Default size: market capitalization
- Optional size: dollar volume
- Default color: 1-day return
- Selectable windows: 1D / 5D / 20D
- Modes: absolute return / relative-to-SPY
- Tile text: ticker and exact return
- Hover detail: price, return, market cap, volume, relative volume, sector, industry, relative strength

## Market Breadth

Universe: broad liquid U.S. equity universe, conceptually similar to a liquidity-filtered Russell 3000 universe.

Tabs:

- Broad Market
- S&P 500
- Nasdaq 100
- Russell 2000

Metrics:

- Advancing percentage
- Percentage above 20-day moving average
- Percentage above 50-day moving average
- 52-week new highs and lows
- Trend visualization

## Index & Style Strength

Relationships:

- QQQ / IWM
- SPY / RSP
- IWF / IWD
- Cyclical / defensive
- SMH / SPY

Views:

- 1D / 5D / 20D
- Absolute and relative modes

## Dynamic Relationship & Rotation Monitor

Use professional concepts:

- rolling correlation
- correlation regime
- relative strength
- beta-adjusted spread
- divergence / convergence
- lead-lag
- regime shift
- spread Z-score

Relationship sets:

- Curated economically meaningful pairs
- Statistically detected relationships with stability, sample-size, and significance controls

Examples:

- Software vs semiconductors
- Magnificent 7 vs semiconductors
- Growth vs value
- Equal-weight vs capitalization-weighted market
- Cyclicals vs defensives

The homepage should show only the most important 3-5 changes.

Relative performance is not the same as actual fund flow. Price/volume-derived estimates must be labeled as estimates. Actual flow claims require an appropriate source and methodology.

## Key Market Developments

Behavior:

- Show a dynamic 3-5 items; do not force a fixed count.
- Detect breadth improvement or deterioration.
- Detect sector/theme relative-strength extremes or reversals.
- Detect material correlation or beta-adjusted spread changes.
- Detect abnormal volume or dollar volume.
- Detect risk-preference regime changes.
- Rank by magnitude, statistical significance, persistence, breadth, and market relevance.
- A rule/statistical engine creates findings.
- A natural-language layer explains evidence.
- No unsupported AI market guesses.

## Update-Frequency Target

When intraday support exists, target:

- Indices and heatmap: 1 minute
- Breadth: 5 minutes
- Relationship monitor: 5 minutes
- Events: trigger-driven
- Full end-of-day recomputation

These are targets, not current implemented capabilities.
