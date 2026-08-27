# ADR 0050: Seal Strategy Signals Before Forward Outcomes

## Status

Accepted

## Date

2026-08-27

## Context

Independent strategy channels are not useful if their historical evaluation
can see future prices, use current constituents as historical membership,
randomly mix overlapping daily labels, or silently exclude delisted and
corporate-action-affected securities. The current 29-session history and
current-as-of membership replay are enough for deterministic implementation
checks but not for performance claims.

The user's intended holding window is commonly one to five sessions. This
creates overlapping outcome windows and makes leakage possible even when the
feature code itself uses only trailing data.

## Decision

Add two separate repository-only contracts under the fixed evaluation policy
documented in
[Candidate Strategy Evaluation V1](../data-contracts/candidate-strategy-evaluation-v1.md).

A signal record is created from source sessions no later than its as-of
session, binds point-in-time membership and exact source/model fingerprints,
contains no outcome fields, and receives a deterministic business ID and
logical fingerprint. A later outcome record binds that sealed signal and one
predeclared 1-, 3-, or 5-session path. Pending outcomes cannot carry future
labels.

Only point-in-time membership may feed performance evaluation. Current-
constituent replay remains research-only. Random split is prohibited; the
policy uses chronological 50/25/25 development/validation/holdout boundaries,
five-session overlap purging/embargo, and later walk-forward evaluation.

Available outcomes are next-session-open to horizon-session-close underlying-
stock price returns with benchmark arithmetic difference, MFE, and MAE.
Corporate-action/source uncertainty produces quarantine instead of a usable
number. Transaction-cost scenarios remain derived report layers, and option
performance remains a separate future dataset/model.

No physical writer, `/data` dataset, formula, backfill, provider request,
Market Intelligence/Snapshot field, frontend feature, publication, or
deployment is authorized by this decision.

## Consequences

- Features and labels have different immutable identities and maturity times.
- The evaluator can audit exactly which facts, membership, and parameters were
  knowable for each signal.
- The current history is formally labelled insufficient instead of becoming a
  small-sample backtest.
- Point-in-time membership and corporate-action data become explicit blockers,
  not optional cleanup.
- Future option evaluation cannot inherit stock-return results or terminology.

## Alternatives Considered

### Calculate signals and outcomes in one table-building pass

Rejected because code or review can accidentally expose forward columns to
feature selection and threshold tuning.

### Randomly split security-session rows

Rejected because adjacent signals share observations and overlapping forward
paths; random rows leak time and regime information across splits.

### Backtest current Production constituents over all history

Rejected for survivorship and membership look-ahead. Such replay may remain a
clearly labelled implementation comparison but cannot support performance
claims.

### Treat provider-adjusted bars as complete corporate-action governance

Rejected because price adjustment, dividends, listing transitions, identity,
and total return are distinct facts and the canonical corporate-action layer
is not implemented.
