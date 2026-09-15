# Opportunity Strategy Channels V1

> **Lifecycle: deployed legacy baseline; frozen and unvalidated.** This
> document remains authoritative for the mechanics currently served in
> Production. It is not the future Stock Candidate model architecture. Do not
> tune these formulas in place. New strategy research belongs in
> [Quant Research Lab](quant-research-lab-v1.md), and only separately validated
> and activated Lab models may later drive Stock Candidates under
> [ADR 0191](../decisions/0191-promote-validated-research-models-into-stock-candidates.md).
> Under [ADR 0274](../decisions/0274-adopt-factor-model-strategy-three-layer-research-architecture.md),
> these six labels are a Production compatibility taxonomy only. They are not
> the future factor catalog, model queue, or required strategy count.

## Purpose

The Candidate workspace must compare like with like. Momentum breakout,
pullback, continuation, reversal, value, and defensive rotation answer
different research questions and must not be collapsed into one score.

This document preserves the product taxonomy, evidence boundary, and deployed
V1 behavior. It does not authorize a formula change, new model, Production
publication, deployment, or trading recommendation.

## Fixed channel order

| Channel | Research question | Minimum primary evidence | Current readiness |
| --- | --- | --- | --- |
| Momentum breakout | Is established relative leadership crossing a bounded resistance structure with credible participation and acceptable extension? | Price/volume, Candidate leadership, entry geometry | Deployed provisional baseline; future research requires a new Lab version |
| Strong-stock pullback | Is a proven leader retracing in an orderly way toward labelled support without breaking its trend? | Price/volume, Candidate leadership, entry geometry | Deployed provisional baseline; distinct Lab V1 remains data-blocked |
| Trend continuation | Is an established trend persisting with healthy breadth/participation and without requiring a fresh breakout or pullback? | Price/volume, relative strength, trend quality | Deployed broad filter; distinctness is unvalidated |
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

Repository source now contains the typed shadow contract plus ADR 0056's first
fixed, source-bound offline preview for momentum breakout, strong-stock
pullback, and trend continuation. It reuses the exact Candidate and Entry
Geometry batches, emits all six channel results, and bounds the first consumer
to eight ranked explanations per channel. Technical reversal, fundamental
value reversal, and defensive rotation remain explicitly unavailable.
An independent calculator now verifies technical-channel score, status, and
rank without importing the Production implementation. Its immutable 2026-08-26
temporary-root audit passed both Universes with zero mismatch and input-
permutation equivalence.

The fixed weights are transparent provisional mechanics, not chronologically
validated parameters. Market/sector fit remains separate and unvalidated. ADR
0057 now projects the formal audit into one bounded Snapshot 1.9 payload and a
multilingual lazy Strategy Channels workspace. It does not recalculate in the
browser. Candidate view/channel state is URL-addressable and restores on
refresh or browser history navigation. Strategy mode removes the unrelated
risk-mode control, uses Advance + Watch as its headline population, and marks
evidence-incomplete channels unavailable rather than presenting an unexplained
zero. Snapshot 1.9 / Dashboard 2.6 first deployed this strategy product; later
additive Dashboard contracts retain it. Exact active release and analysis
session belong in [current context](../project/current-context.md).

ADR 0061 now binds the UI to the exact parameter fingerprint and exposes the
formula, underlying component definitions, geometry mapping, status gates,
deterministic ranking order, and each displayed security's weighted
contributions. The browser independently
reconstructs the published score and fails closed on drift; it does not
recalculate status or rank. A full-population overlap diagnostic found that
the current trend-continuation qualifying set contains every qualifying
breakout and pullback member in both Universes. The interface therefore labels
channel distinctness as unvalidated and treats continuation as a broad trend
filter pending continuation-specific facts and chronological validation. These
ADR 0061 source changes are deployed in the current OCI release. See
[Candidate Strategy Channel Preview V1](../data-contracts/candidate-strategy-channel-preview-v1.md),
the [Candidate Strategy Channel Product V1](../data-contracts/candidate-strategy-channel-product-v1.md),
the [2026-08-28 offline review](../audits/candidate-strategy-channel-preview-2026-08-28.md),
the [product/Snapshot review](../audits/candidate-strategy-product-snapshot-review-2026-08-28.md),
and the [channel-overlap review](../audits/candidate-strategy-channel-overlap-2026-08-28.md).

The repository UI now adds a decision-integrity presentation over the unchanged
published facts. It keeps channel status, score, and rank intact while showing
a second, explicitly separate trade-review readiness result from the linked
same-Snapshot Candidate record. A security rejected by all three Candidate risk
modes is labelled `risk_gates_reject`; a non-reviewable posture or
`no_viable_setup` is labelled `wait_for_setup`; only a
`technical_review_ready` posture with at least one eligible risk mode is
labelled `technical_review_ready`. These are browser presentation labels, not
a new model, rank, threshold, recommendation, or publication contract.

The same view counts displayed channel slots and unique securities by stable
`instrument_id`, lists cross-channel repeats, and summarizes unavailable setup,
risk-rejected, and elevated-extension facts. It explicitly does not call that
formal sector concentration: the current technical channels reuse overlapping
price/volume, relative-strength, and trend inputs, while point-in-time sector
taxonomy remains a separate future data requirement. Ticker is display
metadata only.

The repository UI also projects each selected channel's displayed records onto
one decision-position chart: vertical position is the already published
within-channel research score, horizontal position is the separately published
extension-risk category, point colour is the linked Candidate trade-review
state, and an outer ring marks stable-ID repetition in another displayed
channel. The chart opens the existing detail review, never calculates a new
score, never compares scores across channels, and makes no expected-return or
probability claim.

## Transition boundary

This V1 implementation receives correctness and compatibility maintenance
only. Future development does not extend its heuristic scoring family in
place. The transition is:

1. preserve V1 as a transparent, reproducible Production baseline;
2. conduct new, versioned strategy research in Quant Research Lab;
3. retain failed, rejected, and retired experiments as evidence;
4. activate only a small reviewed set of eligible strategy expressions, with
   no permanent numeric model cap; and
5. redesign Stock Candidates to identify the exact active model/version and
   present model rank, current-market applicability, entry readiness,
   counterevidence, and invalidation without inventing a cross-model total.
