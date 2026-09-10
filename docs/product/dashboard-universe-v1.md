# Dashboard Universe

## Current product boundary

Production uses an immutable Dashboard Universe Activation and a separately
stored active pointer. The first/default view is `Common Shares`; the
secondary view is `Common Shares + ADRs`. Exact active counts, session,
revision, and fingerprints belong in
[Current Context](../project/current-context.md).

The active provider-form classification is provisional:

- stable `instrument_id`, not ticker, is the identity key;
- security form, issuer structure, listing scope, evidence, and eligibility
  remain separate;
- provider security form does not prove issuer domicile or operating-company
  structure;
- Common Shares never silently include ADRCs;
- Legacy remains hidden compatibility/rollback state; and
- future Core/Broad issuer-structure activation remains deferred.

The active Snapshot carries the two-row catalog and the
[source-backed Universe Funnel](dashboard-universe-funnel.md). A new
Activation requires its own reviewed publication and pointer update. A
Snapshot, model, or browser view cannot modify membership.

## Purpose

The Universe selector defines which eligible instruments feed each Dashboard
calculation. It is a product input, not a claim that excluded securities are
uninvestable or included securities are recommendations.

Both guest and authenticated sessions receive the same Universe choices,
counts, data, and analysis. The selection is URL-addressable and must remain
stable across refresh and browser history.

## Eligibility and evidence rules

An activated member must retain:

1. a stable canonical `instrument_id`;
2. recognized security-form evidence;
3. supported listing/exchange evidence;
4. the exact effective session and source lineage;
5. the accepted trailing-liquidity decision; and
6. an explicit Universe disposition.

Unknown, ambiguous, malformed, heuristic-only, or insufficient-evidence
records remain quarantined. Names and ticker patterns may create review flags
but may not establish positive eligibility.

The trailing-liquidity policy uses only the 20 XNYS sessions before analysis
date `D`; `D` never selects itself. It is
`current_as_of_constituent_liquidity`, not a survivorship-free historical
panel. See [20-Session Trailing Liquidity](20-session-trailing-liquidity.md).

## Market overview boundary

Stock breadth, movers, Candidate views, and the Trading Activity Map use the
selected activated equity Universe. Fixed benchmark ETFs are context and do
not enter stock membership.

The benchmark strip may show SPY, QQQ, IWM, DIA, and a selected-Universe
equal-weight return. Sector benchmark ETFs are:

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

ETF relative performance remains:

```text
relative_to_spy_return = sector_etf_1d_return - SPY_1d_return
```

This is a price-return difference, not alpha, causal sector leadership, fund
flow, or money flow.

## Trading Activity Map

The current map uses:

- size: latest close × latest volume;
- color: close-to-close return;
- default population: top 50 by the activity proxy; and
- optional population sizes: 75 or 100.

It is not market-cap weighted. The size measure is a close-times-volume proxy,
not traded notional, capital flow, ownership change, or market capitalization.
Sector grouping, when shown elsewhere, must come from its separately governed
taxonomy and cannot be inferred from this proxy.

Records with `current_close / previous_close >= 2` or `<= 0.5` are flagged
as `unverified_price_discontinuity`. They remain auditable but are excluded
from default movers and the activity map until adjustment evidence resolves the
discontinuity.

## Historical V1 compatibility

The original Dashboard Universe V1 dynamically derived a provisional
`Tradable U.S. Equities` view from common-equity/exchange recognition,
previous close of at least USD 5, and previous close × volume of at least USD
20 million. It also exposed broader diagnostic views.

That path is retained only as historical and compatibility context. It was
superseded by immutable Activation publications and must not be read as the
current member count or current eligibility authority. Dated counts, HSAI/SNDK
reviews, Activation V1, and full-base correction evidence remain in the
relevant audits, ADRs, changelog, and Git history.

## Deferred work

- issuer-structure-aware Core/Broad activation;
- complete point-in-time sector/industry taxonomy;
- governed market-capitalization data;
- survivorship-safe research membership history; and
- a traditional market-cap sector heatmap if its data and display rights are
  accepted.

None of these items may be approximated by ticker, company name, current
membership, or price/volume proxies.
