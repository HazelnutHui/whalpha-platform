# ADR 0103: Separate Chronological Research Mechanics from Performance

## Status

Accepted

## Date

2026-08-31

## Context

ADR 0097 preregisters the first Strong-Leader Pullback experiment, ADR 0050
separates sealed signals from later outcomes, and ADR 0098 prevents incomplete
historical evidence from authorizing development. Those decisions define the
rules but did not yet provide one executable chronological assignment layer.

Implementing a full evaluator before the required point-in-time history exists
would invite short-sample tuning. Leaving the mechanics only in prose would
also make later implementation vulnerable to random splits, boundary leakage,
current-constituent replay, or outcome-aware signal construction.

## Decision

Implement a pure, fixture-only chronological research mechanics layer for the
exact frozen Strong-Leader Pullback experiment.

The layer:

- requires at least 252 unique, contiguous XNYS sessions;
- assigns fixed 50/25/25 development, validation, and holdout intervals;
- excludes the first 20 sessions for feature warm-up;
- applies a five-session purge before and five-session embargo after both
  chronological boundaries;
- excludes the final five sessions until the maximum registered outcome can
  mature;
- enumerates exactly the 24 preregistered parameter combinations;
- compares triggered setups only with same-session point-in-time eligible
  leaders that did not trigger;
- seals cohort assignments without forward outcomes or performance authority;
- schedules 1/3/5-session outcomes as pending, then attaches next-open to
  horizon-close underlying-stock labels only after the exact future path is
  known; and
- quarantines corporate-action review cases without numeric results.

The implementation has no canonical reader, writer, CLI, provider transport,
real dataset, statistic selector, Production consumer, page, publication, or
deployment path. It cannot bypass Strategy Research Readiness.

## Consequences

- Later real research has one deterministic execution boundary instead of
  reinterpreting the split and leakage rules.
- Signal/control construction can be tested independently from forward labels.
- Current-constituent replay and boundary observations cannot enter a
  performance-eligible cohort.
- Available labels describe the underlying stock only; they cannot be called
  option returns.
- No performance conclusion exists until complete physical history is formally
  read and a separate development activation is approved.

## Alternatives Considered

### Wait to implement any mechanics until real history exists

Rejected because leakage-prevention rules are safer to freeze and independently
test before outcomes can influence implementation choices.

### Build a temporary backtest over the current 31 sessions

Rejected because the sample and point-in-time evidence fail the registered
readiness gate.

### Combine signal assignment and outcome calculation in one pass

Rejected because it weakens the auditable separation between information
available at signal time and labels observed later.
