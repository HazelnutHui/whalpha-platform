# Dashboard Universe V1

## Purpose

Dashboard Universe V1 defines which completed EOD instruments drive the private Market Dashboard V1.1 overview.

## Default Universe

Canonical name: `Tradable U.S.-Listed Equities V1`.

UI label: `Tradable U.S. Equities`.

Rules:

1. Stable canonical `instrument_id` exists.
2. Current and previous completed sessions both have valid canonical EOD bars.
3. Existing Instrument Master type is recognized as operating common equity by V1.
4. Instrument Master primary exchange is one of the supported major U.S. exchange codes.
5. Previous close is at least USD 5.
6. Previous close x previous volume is at least USD 20,000,000.

The price and liquidity gates use previous-session data only. This avoids same-day selection bias. The USD 20M threshold is a provisional one-day close-times-volume gate, not 20-day ADV.

## Auxiliary Universes

- `All Operating Equities`: operating common equity on supported exchanges without the price and liquidity gates.
- `All Eligible Instruments`: broad comparable research/data-quality view; it may include ETFs and other supported products and is not the default trading overview.

## ETF Boundary

ETFs are excluded from the default stock breadth, movers, and Trading Activity Map. They are shown separately as Sector Benchmark ETFs when present in completed canonical EOD data.

The fixed Sector Benchmark ETF list is:

- XLC — Communication Services
- XLY — Consumer Discretionary
- XLP — Consumer Staples
- XLE — Energy
- XLF — Financials
- XLV — Health Care
- XLI — Industrials
- XLB — Materials
- XLRE — Real Estate
- XLK — Information Technology
- XLU — Utilities

These are S&P 500 Select Sector SPDR benchmark returns. They are not sector breadth, fund flow, money flow, or official sector membership.

## Trading Activity Map

Trading Activity Map replaces the UI label Liquidity Map V1 for the Dashboard. It uses:

- size: current close x current volume
- color: close-to-close return
- default display: top 75 by activity proxy
- user choices: top 50, 75, or 100

It is not market-cap weighted and is not sector grouped.

## Price Discontinuity Review

Records with current close / previous close >= 2 or <= 0.5 are flagged as `unverified_price_discontinuity`. They remain counted for audit, but default movers and the Trading Activity Map exclude them until corporate-action reconciliation is implemented.

## Current Production Audit

For current session 2026-08-13 versus previous session 2026-08-12:

- raw comparable instruments: 9,888
- common-stock classified instruments: 4,528
- ADR count: not separately supported by the current Instrument Type contract
- ETF/ETP classified instruments: 5,360
- other instrument types: 0
- major-exchange records: 9,686
- records passing the USD 5 previous-close gate after operating-equity and exchange gates: 3,274
- final Tradable U.S. Equities count after the previous-session USD 20M gate: 1,876

Exclusion counts are overlapping diagnostic counts, not a mutually exclusive sum:

- excluded instrument type: 5,360
- non-major exchange: 202
- previous close below USD 5: 1,223
- previous close x volume below USD 20M: 7,308

## Deferred Improvements

- trailing 20-session median dollar-volume gate
- explicit ADR/common-stock separation if Instrument Master can support it
- point-in-time sector/industry taxonomy
- market capitalization source
- traditional market-cap sector heatmap
