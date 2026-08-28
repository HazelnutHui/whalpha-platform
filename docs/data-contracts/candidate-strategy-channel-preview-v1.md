# Candidate Strategy Channel Preview V1

## Status

Implemented in repository source as a pure Dell/offline shadow calculation,
bounded consumer, independent Oracle, and immutable temporary-root audit. It is
fixed but not chronologically validated, published, or deployed. An additive
repository-only product projection and bilingual UI now consume its formal
audit without changing this shadow calculation.

## Inputs and custody

The calculator accepts one formally typed `OpportunityCandidateBatchV1` and
its exact `CandidateEntryGeometryBatchV1`. Session, Universe, full stable-ID
population, Candidate batch fingerprint, per-security Candidate fingerprint,
Ticker display metadata, security form, and base score must match. Input order
does not affect output.

It produces six explicit results per included security. No browser logic,
network request, `/data` write, forward outcome, option chain, or market-fit
adjustment is involved.

## Fixed technical scores

All source component and geometry terms are 0–100. The final value is rounded
half-even to four decimals.

| Channel | Formula |
| --- | --- |
| Momentum breakout | 35% stock relative strength + 25% trend quality + 15% volume participation + 25% breakout geometry |
| Strong-stock pullback | 30% stock relative strength + 25% trend quality + 15% volatility/risk + 10% liquidity suitability + 20% pullback geometry |
| Trend continuation | 35% stock relative strength + 35% trend quality + 15% volume participation + 10% volatility/risk + 5% continuation geometry |

The geometry lookup is fixed:

| Existing Entry Geometry setup | Breakout | Pullback | Continuation |
| --- | ---: | ---: | ---: |
| Breakout confirmed | 100 | 25 | 85 |
| Breakout watch | 70 | 35 | 70 |
| Pullback | 25 | 100 | 85 |
| Strong but extended | 15 | 55 | 35 |
| No viable setup | 20 | 20 | 50 |

These are transparent provisional research weights, not fitted coefficients.
Scores are incomparable across channels and are not probability, confidence,
expected return, or trade instructions.

## Status routing

- Momentum breakout advances only an existing `breakout_confirmed` structure;
  breakout watch and strong-but-extended wait for a trigger or reset.
- Strong-stock pullback advances only an existing `pullback` structure;
  strong-but-extended waits for an orderly reset.
- Trend continuation advances only when Candidate state is Prepare/Enter,
  relative-strength and trend components are each at least 65, and extension
  is low or moderate. A base score of at least 65 with both components at least
  55 remains watch-only.
- Invalidated Candidate state is deprioritized. Failed/quarantined source
  quality, missing required score components, or unavailable Entry Geometry is
  unavailable rather than scored.

Every assessable result contains the input components used, technical setup,
extension/chase-risk counterevidence, why it surfaced, first rejection risk,
reviewability condition, invalidation, and manual event/options/execution
checks. Market fit remains `unavailable` with an explicit unvalidated reason.

## Explicit unavailable channels

- Technical reversal requires stabilization and reclaim facts.
- Fundamental value reversal requires governed fundamentals, valuation, and
  price stabilization.
- Defensive rotation requires point-in-time defensive taxonomy, a bound Market
  Regime state, and a labelled relationship proxy.

No technical proxy fills these gaps.

## Bounded consumer

`candidate-strategy-channel-consumer/1.0` retains complete status counts and
shows only the leading contiguous ranks among Advance and Watch results, capped
at eight per channel. Deprioritized and unavailable rows are not displayed but
remain in the full shadow batch for audit.

## Independent Oracle and audit

The Oracle independently repeats the fixed formulas, technical status gates,
and within-channel ranking without importing the Production strategy
calculator. It also reverses both typed source sequences and requires identical
expected output. The audit writer refuses any Oracle mismatch.

The operational entry point formally rereads the Candidate and Entry Geometry
audits, requires exact current-session Universe order and source fingerprints,
and runs with outbound sockets disabled. It atomically writes a direct child of
`/tmp`, binds both source manifest hashes, records zero external requests and
zero Production writes, makes artifacts read-only, and formally rereads typed
batches and consumers before success. The audit remains disposable shadow
evidence, not a publication input.

## Remaining activation gates

1. Chronological 1/3/5-session evaluation using point-in-time membership and
   corporate-action/lifecycle-safe outcomes.
2. Review by Regime, industry, liquidity, volatility, turnover, chase, false
   positives, and missed opportunities.
3. Additive product payload and bilingual UI review. **Completed mechanically;
   not published or deployed.**
4. Separate publication and deployment authorization.
