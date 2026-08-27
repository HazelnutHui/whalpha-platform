# Opportunity Strategy Channels V1

## Purpose

The Candidate workspace must compare like with like. Momentum breakout,
pullback, continuation, reversal, value, and defensive rotation answer
different research questions and must not be collapsed into one score.

This document defines the product taxonomy and evidence boundary before any
channel formula or threshold is selected. It does not authorize Production
publication, deployment, or a trading recommendation.

## Fixed channel order

| Channel | Research question | Minimum primary evidence | Current readiness |
| --- | --- | --- | --- |
| Momentum breakout | Is established relative leadership crossing a bounded resistance structure with credible participation and acceptable extension? | Price/volume, Candidate leadership, entry geometry | Formula research can begin from existing governed inputs |
| Strong-stock pullback | Is a proven leader retracing in an orderly way toward labelled support without breaking its trend? | Price/volume, Candidate leadership, entry geometry | Formula research can begin from existing governed inputs |
| Trend continuation | Is an established trend persisting with healthy breadth/participation and without requiring a fresh breakout or pullback? | Price/volume, relative strength, trend quality | Formula research can begin from existing governed inputs |
| Technical reversal | Is an oversold or damaged stock showing observable stabilization/reclaim evidence rather than only a large decline? | Price/volume, downside stretch, stabilization and reclaim facts | Requires additional reversal-specific facts and chronological evaluation |
| Fundamental value reversal | Is valuation dislocated while business/earnings quality is adequate or improving and price has begun to stabilize? | Fundamentals, valuation, and price/volume | Must remain unavailable until governed fundamental and valuation inputs exist |
| Defensive rotation | When broad or high-beta leadership weakens, is a defensive industry/security showing independently supported relative strength? | Market Regime, price-derived relationship proxy, and stock price/volume | Partially supported; security taxonomy and channel formula remain to be defined |

The order is a stable product catalog, not a preference rank. A security must
receive an explicit result for every channel. Missing data becomes
`unavailable`; it must not silently remove the channel or become a neutral
score.

## Result states

- `advance_to_research`: high-priority diligence candidate, not a buy signal.
- `watch_for_trigger`: interesting but missing an observable price, evidence,
  valuation, or catalyst condition.
- `deprioritized`: assessable but currently fails its first material test.
- `unavailable`: required evidence is absent or not governed.

Every result carries the first smart reason a skeptical reviewer might reject
it; this is a visible risk, not the status decision by itself. Every advanced
result also carries why it surfaced, primary supporting evidence, explicit
counterevidence, and observable invalidation. Non-advanced results state what
would make them researchable. All states may carry manual checks.

## Scoring and ranking boundary

- A channel score, once implemented, is a 0–100 research-priority score only
  inside that channel. It is not a success probability, expected return, or
  confidence level.
- Cross-channel score comparison and a replacement all-strategy total score
  are prohibited.
- Only `advance_to_research` and `watch_for_trigger` rows receive a contiguous
  within-channel rank. Deprioritized and unavailable rows remain unranked.
- Market fit is a separate `supportive`, `neutral`, `adverse`, or `unavailable`
  assessment. V1 does not hide it inside the channel score.
- Existing Candidate leadership and entry geometry remain distinct source
  axes. A high leadership score cannot by itself produce a favorable entry or
  channel result.

## Evidence boundary

Evidence is source-dated and typed as price/volume, Market Regime,
price-derived relationship proxy, fundamentals, valuation, event, or data
quality. No evidence session may be later than the assessment session.

ETF and sector relationships remain price-derived proxies and must not be
described as fund flow or causality. Event and earnings evidence is auxiliary
context: it may increase caution, require a manual check, or define a watch
trigger, but it cannot be the sole primary evidence for a strategy channel.

A fundamental value reversal cannot become assessable from price weakness
alone. It requires governed fundamental facts, valuation facts, and price
stabilization evidence. A defensive rotation result requires all three of
Market Regime, a labelled price-derived relationship proxy, and security-level
price/volume evidence.

## Options boundary

These channels assess the underlying stock research setup. They do not claim
option returns or choose Call/Put, debit spread, covered call, strike, or DTE.
A later option-expression layer may consume a channel result only after it has
option-chain liquidity, spread, open interest, implied-volatility, event, and
payoff evidence. Naked short-option recommendations remain out of scope.

## Evaluation before activation

No threshold may be selected from the 2026-08-26 cross-section or tuned until
a preferred number of names appears. Each future formula requires:

1. a frozen, versioned parameter set and full component ledger;
2. chronological training/validation/test boundaries using only information
   available at each session;
3. walk-forward or expanding-window evaluation with overlap-aware purging for
   the intended 1–5-session holding window;
4. results by channel, Regime, sector, liquidity, volatility, and signal age;
5. turnover, drawdown, false-positive, chase, and missed-opportunity review;
6. an untouched holdout before any Production activation decision.

Forward labels from stock bars must be called underlying-stock forward returns.
Option performance requires a separate historical option dataset and payoff
model.

## Current implementation state

Repository source contains only the typed shadow contract
`candidate-strategy-channel-shadow/1.0` and its invariants. It is not connected
to Candidate calculation, Market Intelligence, Snapshot, frontend, or
Production. Dell remains the only approved compute, history, and governance
boundary for later formula research.

## Planned implementation sequence

1. Define a point-in-time chronological evaluation panel and channel outcome
   ledger without adding new Production fields.
2. Freeze and evaluate momentum breakout, strong-stock pullback, and trend
   continuation formulas separately.
3. Add reversal-specific stabilization facts and evaluate technical reversal.
4. Complete security taxonomy/defensive mapping and evaluate defensive
   rotation across Regimes.
5. Ingest governed fundamentals and valuation data before implementing
   fundamental value reversal.
6. Publish only channels that pass audit, temporal validation, and separate
   activation review.
