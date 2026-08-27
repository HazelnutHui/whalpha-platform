# ADR 0049: Separate Candidate Strategy Channels

## Status

Accepted

## Date

2026-08-27

## Context

The existing Candidate score is a leadership and research-priority measure.
Entry geometry correctly prevents that score from being interpreted as entry
timing, but one Candidate rank still cannot represent momentum breakout,
strong-stock pullback, trend continuation, technical reversal, fundamental
value reversal, and defensive rotation. Their evidence, false positives, and
failure conditions differ.

Combining them would make a strong breakout numerically comparable with an
oversold reversal or undervalued company even though the strategies answer
different questions. It would also encourage hidden regime adjustments and
make formula changes difficult to audit.

## Decision

Adopt the fixed six-channel taxonomy in
[Opportunity Strategy Channels V1](../product/opportunity-strategy-channels-v1.md)
and add a repository-only typed shadow contract. Every included security has
one explicit assessment for every channel. Missing evidence produces
`unavailable`, not omission or a neutral value.

Channel scores and ranks are comparable only within the same channel. Market
fit remains a separate visible assessment. Candidate leadership, entry
geometry, event context, and later option expression remain separate axes.
Cross-channel total scoring is prohibited.

The contract requires source-dated evidence and a first smart rejection risk
for every result; advanced results also require why-now, primary support,
counterevidence, and invalidation. Non-advanced results require a reviewability
condition. Strict evidence classes apply to value reversal and defensive
rotation. Event evidence is auxiliary and price-derived ETF/sector
relationships remain labelled proxies.

No formula, threshold, real assessment, Market Intelligence field, Snapshot
field, frontend view, Production publication, or deployment is authorized by
this decision. Formula parameters must be frozen before chronological
evaluation and cannot be selected from the 2026-08-26 cross-section.

## Consequences

- Users can understand why a name ranks within one strategy without treating
  a total score as a universal answer.
- The current data can support research on three trend-oriented channels, but
  cannot silently stand in for fundamental or valuation evidence.
- Defensive opportunity means relative resilience supported by market,
  relationship-proxy, and security evidence; it is not a fund-flow claim.
- Future event and option layers can add context without redefining the
  underlying-stock channel result.
- Activation requires channel-specific history, temporal validation, audit,
  consumer design, and a separate reviewed decision.

## Alternatives Considered

### Add strategy weights to the existing total score

Rejected because weights would hide conflicting strategy questions inside one
number and make the explanation dependent on the selected style.

### Let the browser classify strategies from existing fields

Rejected because it would duplicate financial logic, weaken source binding,
and make bilingual presentation the accidental owner of model semantics.

### Implement only the currently available technical channels

Rejected because the product taxonomy must make missing fundamental/value
evidence visible. Explicit unavailable results are safer than omitting future
channels or implying they are covered by technical proxies.
