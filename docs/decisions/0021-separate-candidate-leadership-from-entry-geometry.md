# ADR 0021: Separate Candidate Leadership from Entry Geometry

## Status

Accepted

## Date

2026-08-26

## Context

The deployed Candidate base score is intentionally effective at finding
relative-strength and trend leadership. It is not an entry-location model.
Market, ETF direction, stock relative strength, trend, and volume participation
all tend to reward continuation, while existing risk modes gate liquidity,
volatility, gaps, price, confidence, ADR policy, and concentration. They do not
measure how far price has already moved from a nearby technical structure.

The formal 2026-08-24 shadow review made the distinction material. In the
Primary Balanced top 50, 41 candidates had high or extreme extension under the
pre-registered entry-geometry rules; only two met a bounded breakout or
pullback technical-review setup and four were near a breakout trigger. Treating
the original rank as entry timing would therefore create a structural chase
risk.

## Decision

Keep the existing Candidate score, state, and risk rank unchanged as the
leadership and research-priority axis. Add a separate, fixed, source-bound
entry-geometry layer that answers a narrower question: whether current EOD
price location is suitable for technical review, should be monitored for a
trigger, or is too extended and should wait for a reset.

The additive layer uses only contemporaneously available 26-session EOD facts:
SMA10, SMA20, simple ATR14, three- and five-session return, volatility-scaled
five-session move, consecutive up sessions, current gap/range/close location,
volume ratio, prior-five-session close high/low, and a labelled reference
support distance. It emits one of five technical structures:

- bounded breakout confirmed;
- breakout watch;
- orderly pullback;
- strong but extended;
- no viable setup.

It separately emits low/moderate/high/extreme extension risk and one review
posture: technical review ready, monitor for trigger, wait for reset,
deprioritized, or not assessable. High or extreme extension can never be called
technical-review ready.

The first version is an offline shadow contract with a second independent
raw-panel Oracle and canonical `/tmp` audit. It does not feed Candidate score,
state, risk rank, Market Intelligence, Snapshot, frontend, or Production.
Parameters were frozen before the real-data distribution was reviewed and were
not fitted to forward outcomes.

## Consequences

- A strong stock can correctly remain high in research priority while being
  labelled unsuitable for immediate technical review.
- Product presentation can become a two-axis decision surface—leadership
  quality by entry location—instead of one misleading sorted list.
- A later consumer should use separate lanes for review now, wait for trigger,
  wait for reset, and other research candidates. It must not silently reorder
  or overwrite the original formal rank.
- Reference support is descriptive context, not a stop price. A technical
  review posture is not a recommendation or order instruction.
- Twenty-six sessions can verify deterministic mechanics and current
  distribution only. It cannot validate predictive value or justify tuning.
- Publication, Snapshot, frontend integration, and deployment require a new
  additive consumer contract and separate approvals.

## Alternatives Considered

### Reduce momentum weights in the original score

Rejected because this would weaken discovery of genuine leadership without
answering whether price is currently extended. It also mixes two different
decisions into one less interpretable number.

### Apply an opaque chase penalty to the base score

Rejected because the user could no longer distinguish a weak candidate from a
strong candidate at a poor location, and risk modes would cease to be cleanly
separate from source facts.

### Select only pullbacks

Rejected because a valid bounded breakout and an orderly pullback are distinct
trade archetypes. One should not be treated as universally superior.

### Tune thresholds until a preferred number of top-ranked names passes

Rejected as outcome-free distribution fitting. Threshold changes require a
new documented parameter set and, once enough history exists, chronological
evaluation rather than visual preference.
