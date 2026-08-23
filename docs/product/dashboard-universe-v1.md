# Dashboard Universe V1

## Activation V2 and formal Funnel boundary

Production Activation V2 now resolves 1,718 Common Shares and 1,831 Common Shares + ADRs (1,718 CS plus 113 ADRC); Primary remains first/default and Legacy remains hidden with rollback retained. The deployed snapshot still contains the prior 1,641/1,747 payload. Snapshot contract 1.4 / Dashboard contract 2.1 will carry the [formal source-backed Funnel](dashboard-universe-funnel.md), but freshness currently blocks publication.

## Reviewed HSAI correction

The authoritative revision is now the active Universe source: HSAI has been an ADS since its 2023-02-09 Nasdaq listing and is excluded from Common Shares while retained in Common Shares + ADRs after the same quantitative gates. AKR, UNIT, and DFNS manual warnings remain accepted as non-blocking. Snapshot and OCI still show the prior activation until separately refreshed.

## Governance Status

Dashboard Universe Activation V1 makes the 1,641-member Provider-Classified Common Shares (Provisional) set the default and the 1,747-member CS+ADRC set the optional secondary view for analysis session 2026-08-19. Legacy 1,864 remains formally readable for rollback but is absent from the ordinary selector. Provider security form does not prove issuer domicile or operating-company structure.

The authenticated desktop selector was manually verified after deployment: the two options, counts, URL persistence, refresh behavior, browser history, and Universe-dependent module switching worked as expected. Mobile, tablet, and keyboard acceptance remain unverified.

## Phase A Security Classification Audit

Production still uses the legacy binary common-stock/ETF rule. Phase A proved it insufficient: non-ETF records were treated as operating equities, allowing the closed-end fund VCX into the default set. Security Classification V1 separates legal form, issuer structure, listing scope, evidence, and eligibility but is not connected to production analytics. The [2026-08-14 audit](../audits/security-type-classification-2026-08-14.md) documents non-production Core and Broad candidates.

## Accepted Product Policy

`Common Shares` is the default short label for `provider_classified_common_shares_v1`. `Common Shares + ADRs` selects `provider_classified_common_shares_plus_adrs_v1`. The primary has 1,641 CS; the secondary adds 106 qualifying ADRCs. These are activation-session facts, not permanent constants. Legacy is compatibility/rollback only.

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

The Market Benchmark Strip separately shows SPY, QQQ, IWM, DIA, and the selected universe equal-weight return. These benchmarks are market context only and do not change stock-universe membership.

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

Dashboard V1.1 also reports each Sector SPDR return relative to SPY:

```text
relative_to_spy_return = sector_etf_1d_return - SPY_1d_return
```

This is an arithmetic return difference, not alpha, factor attribution, or risk-adjusted excess return. If SPY is unavailable, the relative value is unavailable.

## Trading Activity Map

Trading Activity Map replaces the UI label Liquidity Map V1 for the Dashboard. It uses:

- size: current close x current volume
- color: close-to-close return
- default display: top 50 by activity proxy
- user choices: top 50, 75, or 100

It is not market-cap weighted and is not sector grouped.

The current display intentionally keeps the raw close-times-volume proxy as the size metric. No logarithmic, square-root, or winsorized display transform has been accepted yet.

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

## SNDK Review

SNDK was reviewed because it appears as a large Trading Activity Map node for 2026-08-13. The completed canonical records show a resolved stable identity, common-stock Instrument Master metadata, internally consistent 2026-08-12 and 2026-08-13 OHLC values, and a 2026-08-13 close-to-close return of about +13.67%.

External market-material review subsequently corroborated the displayed 2026-08-13 SNDK close and approximately +13.67% return. No identity, OHLC, Decimal, or provider-mapping defect was found. Current conclusion:

`verified_consistent_with_current_canonical_data`

The canonical Parquet data was not modified and no ticker-specific exception exists. The pipeline still lacks independent corporate-action and adjustment-factor reconciliation; external manual corroboration must not be represented as automated pipeline verification.

## Freshness

Dashboard V1.1 displays the completed current session and a human-readable snapshot generation timestamp. The accepted offline XNYS calendar compares expected and actual completed sessions; the deployed 2026-08-14 snapshot has lag zero and freshness `fresh`. File/schema consistency remains a separate validation state.

## Deferred Improvements

- separately authorized activation of the published 20-session median dollar-volume policy
- explicit ADR/common-stock separation if Instrument Master can support it
- point-in-time sector/industry taxonomy
- market capitalization source
- traditional market-cap sector heatmap

## Provider-Classified Shadow Status

The [offline provider-classified audit](provider-classified-common-shares-v1.md) reports 1,751 CS-only requested members and a 1,864-member CS+ADRC requested comparison for 2026-08-14. Trailing-liquidity and reviewed eligibility reduce the activated views to 1,641 and 1,747 respectively. ADRC is never folded into the CS-only view.

The completed pre-activation review applies the published 20-session decisions and reviewed stable-ID overlay. Its two proposals are now the activated Dashboard catalog, while remaining provisional and not claiming verified U.S. domicile or issuer structure.

## Trailing-Liquidity Readiness

The published shadow method is the [20-Session Median Dollar-Volume Proxy](20-session-trailing-liquidity.md), using only the 20 XNYS sessions before analysis date `D`. `D` never selects itself. This is `current_as_of_constituent_liquidity`, not a survivorship-free historical panel. For 2026-08-19 the 07-22 through 08-18 window is complete. Activation V1 currently serves 1,641/1,747 members.

An offline scope audit proved those counts were conservatively anchored to the old one-session dollar-volume candidate range. The full-base corrected shadow starts from all 4,193 provider-classified CS and all 4,565 CS/ADRC evidence records, and produces 1,719/1,831 shadow members. These corrected results are not activated and are not present in the production Dashboard or snapshot. A separately authorized review/activation/deployment is required.
