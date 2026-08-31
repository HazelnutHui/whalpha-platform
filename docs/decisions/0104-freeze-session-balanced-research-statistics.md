# ADR 0104: Freeze Session-Balanced Research Statistics Before Real Labels

## Status

Accepted

## Date

2026-08-31

## Context

ADR 0103 makes the first Strong-Leader Pullback experiment's chronology and
signal/control assignment executable without real data. The registered gates
name a block bootstrap, Holm-Bonferroni correction, net-return condition and
Regime observation floor, but the exact aggregation, evidence floor,
development selection rule and stage-access sequence still need to be fixed
before any real forward label can influence them.

Cross-sectional observations are not independent: many securities share the
same market session and overlapping outcomes. A simple row-weighted average or
ordinary independent-observation test would give busy sessions excessive
weight and understate dependence.

## Decision

Add fixture-only `candidate-strategy-research-statistics/1.0` as an analysis-
plan addendum to the unchanged first preregistration.

For each parameter combination and horizon:

- calculate equal-weight signal and control means within each session;
- use the session-level signal-minus-control difference as the primary
  contrast;
- use a deterministic circular moving-block bootstrap with five-session blocks
  and 2,000 replicates;
- report a percentile 90% interval and a one-sided centered-null probability;
- require at least 60 available signal observations, 60 available control
  observations, and 20 comparable sessions before inferential fields are
  available;
- retain coverage, quarantine, unavailable/pending, underlying return,
  SPY-relative return, hit rate, MFE, MAE and 0/10/25/50 basis-point-per-side
  cost views even when inference is inconclusive; and
- keep every result explicitly an underlying-stock research result, never an
  option return or trade instruction.

Development evaluates all 24 combinations and locks at most one. The fixed
objective is the highest three-session 90% contrast lower bound, followed by
the mean contrast, available signal count and stable combination ID. Validation
cannot change the lock and applies Holm-Bonferroni across the full 24-member
family. Holdout exposes only the locked combination and cannot be consumed
unless every validation gate passes. Every observed Regime reported by a stage
must contain at least 60 available signal observations; a smaller cell fails
the registered floor rather than being promoted as evidence.

The contract and service are permanently marked fixture-only and set both
stage-transition and performance-claim authority to false. Real research will
require a separate formally read input adapter and explicit development
activation after the existing readiness gate passes.

The current fixture report marks when holdout data appears in that report but
does not provide durable single-use custody across process invocations. That
operational control remains explicitly false and must exist before a real
holdout can be called untouched.

## Consequences

- The analysis method is fixed before real labels or attractive charts exist.
- Sessions, rather than the number of securities appearing on a session, are
  the independent time unit for the primary contrast.
- Sparse, quarantined and immature evidence remains visible without receiving
  an inferential conclusion.
- Validation failure prevents holdout inspection; holdout cannot search the
  unused 23 combinations.
- The deterministic bootstrap is reproducible but does not prove that market
  dependence is fully modeled. Later sensitivity analysis may require a new
  registered version rather than silently changing this one.

## Alternatives Considered

### Rank combinations by row-weighted mean return

Rejected because dates with more qualifying securities would dominate the
result and cross-sectional dependence would be ignored.

### Choose the highest development point estimate

Rejected because it rewards unstable extremes. A conservative interval lower
bound is harder to pass and better aligned with avoiding overfit.

### Inspect every holdout combination and correct afterward

Rejected because the holdout would become another tuning set.
