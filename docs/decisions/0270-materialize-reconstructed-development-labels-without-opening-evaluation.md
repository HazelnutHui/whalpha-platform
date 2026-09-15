# ADR 0270: Materialize Reconstructed Development Labels Without Opening Evaluation

- Status: Accepted
- Date: 2026-09-15

## Context

The source-driven V2 admission permits reconstructed development-label
construction and development-only parameter selection. Validation and holdout
remain closed. The existing outcome contract assumes a fully observed future
bar path and cannot represent the finite terminal-reference intervals admitted
by ADR 0268 and ADR 0269.

Terminal evidence also does not create an executable entry. If a security
stops trading before the registered next-session open, a gross merger or
delisting reference can describe an existing holder's terminal entitlement but
cannot supply the strategy's missing entry price. Replacing that entry with the
signal close would change the preregistered experiment.

## Decision

Create one immutable, owner-only reconstructed development dataset on Dell.
It contains the complete outcome-free observations for usable development
sessions and one independent 1/3/5-session label row per observation.

1. The builder must formally reproduce the frozen method diagnostic before it
   may retain any observation row. It then selects only chronological
   `development` assignments that are usable under the fixed purge, embargo,
   warm-up, and maturity rules.
2. Validation and holdout observations may be recomputed only for the
   outcome-blind diagnostic reconciliation already admitted. Their forward
   labels, cohort outcomes, statistics, and parameter comparisons remain
   unread and unwritten.
3. Entry remains the next-session open and exit remains the registered
   horizon-session close. Raw bars are multiplied by the frozen split factors
   to the common basis. Sparse omitted adjustment rows are neutral only under
   the exact ADR 0268 source reconciliation.
4. A fully observed exit produces an exact EOD label. A path that has an
   executable entry but crosses a proven terminal boundary uses the retained
   exact reference or finite interval. Interval endpoints remain separate;
   point imputation and complete-case headlines are prohibited.
5. A path with no next-session opening trade is retained as
   `unexecutable_no_next_open`. It has no price, return, excursion, or
   performance value and must be counted in later coverage reports. Signal-day
   close substitution is prohibited.
6. MFE and MAE are populated only when every trading bar in the registered path
   is observed. A terminal reference does not invent the missing intraperiod
   path.
7. The immutable raw label ledger does not apply transaction costs. The fixed
   0/10/25/50 basis-point-per-side scenarios remain derived evaluation layers,
   so the same source label is never duplicated or silently altered.
8. These are underlying-stock price outcomes. They are not total returns,
   alpha, option returns, recommendations, or Production signals.

The dataset may not select parameters, run validation, expose holdout data,
activate Candidate, publish a performance claim, write canonical `/data`, or
deploy Production.

## Consequences

The first real research dataset has an auditable split boundary and can support
the registered development comparison without contaminating later evaluation.
Terminal uncertainty and entry infeasibility remain visible instead of being
hidden inside one numeric return. Development selection will require a later
real-statistics contract that evaluates both adverse interval assignments and
reports unavailable-entry coverage before it can lock a specification.

