# Strong-Leader Pullback Method Diagnostics V1

## Purpose

`strong-leader-pullback-method-diagnostics/1.0` defines the private,
outcome-blind engineering report for the first canonical method. It asks
whether the reconstructed feature population is computable, sufficiently
varied, and mechanically sensible before any real forward return is opened.

The evidence tier is fixed to
`reconstructed_latest_vintage_method_engineering_only`. It is not an
as-operated research sample, a backtest, parameter-selection evidence, or a
performance result.

## Inputs

The pure builder accepts:

- the registered chronological plan;
- complete, source-dated `StrongLeaderPullbackObservationV1` rows; and
- explicit excluded paths whose unavailable features each carry their own
  reason codes and source fingerprint.

Complete and excluded paths must be unique, sorted, disjoint, and inside the
chronological plan. A complete observation must retain eligible same-session
Membership and cannot contain a source date later than its signal session.
Missing paths are represented explicitly; they are never converted to a
neutral feature value or silently dropped.

## Output

The self-fingerprinted report binds the exact method, experiment, input-feature
calculation, chronological plan, and source population. It contains:

- per-feature available, unavailable, and complete-distribution counts;
- minimum, nearest-rank quantiles, maximum, distinct-value count, and duplicate
  excess for the four numeric decision features;
- true/false balance for both close-recovery facts;
- Regime category counts;
- fixed local threshold-proximity diagnostics for leadership, trend, ATR
  depth, and volume-contraction boundaries;
- session and stable-instrument concentration, including maximum share,
  top-ten share, and Herfindahl index; and
- signal, same-session eligible-leader control, chronological exclusion,
  Membership exclusion, non-leader exclusion, and unavailable-input counts
  for each of the 24 preregistered parameter combinations.

The proximity tolerances are engineering diagnostics, not extra parameter
choices: 0.01 leadership-percentile units, one trend-quality point, 0.10 ATR,
and 0.05 volume-ratio units. They measure boundary crowding only and cannot be
used to choose a winning combination.

## Zero-authority invariants

The contract has no outcome or return field. It fixes all of the following:

- `contains_forward_outcomes=false`;
- `contains_performance_metrics=false`;
- trigger counts are not reusable for parameter selection;
- formal development, validation, holdout, and Candidate activation remain
  unauthorized; and
- external requests, canonical data writes, and Production writes remain
  zero.

Every parameter combination must account for the full declared path
population. Feature and concentration aggregates reconcile to their declared
denominators, stable order is enforced, and the complete report carries a
deterministic logical fingerprint.

## Interpretation boundary

The diagnostic may reveal missing inputs, degenerate ranks, boundary ties,
excess concentration, or a formula that rarely produces a trigger. It may not
show expectancy, return, win rate, Sharpe, drawdown, Alpha, a preferred
parameter set, or evidence that the strategy works.

The reconstructed Membership was not recorded as operated. Point-in-time
historical sector concentration is unavailable. Incomplete paths are excluded
from feature distributions but remain in feature-coverage and combination
denominators. Any diagnostic-motivated change to formula or grid requires a
new preregistered method version before outcomes are opened.

## Current implementation boundary

Python/Pydantic contracts, a pure deterministic aggregation service, and
synthetic boundary tests are implemented. No private Dell population reader,
saved real report, canonical persistence, public API, Lab publication,
Candidate change, or deployment is part of this implementation boundary.
