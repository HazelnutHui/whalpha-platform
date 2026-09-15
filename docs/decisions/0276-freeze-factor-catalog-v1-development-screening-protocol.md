# ADR 0276: Freeze Factor Catalog V1 Development Screening Protocol

## Status

Accepted

## Date

2026-09-15

## Context

Factor Catalog V1 completed its outcome-blind qualification and exact replay.
That report established calculation, coverage, distribution, concentration,
and redundancy facts but did not establish predictive information. Outcomes
cannot be opened until the cohort, labels, formal trial count, multiplicity,
stability rules, cost treatment, factor cap, and stopping rule are fixed.

The completed Strong-Leader Pullback outcomes are a consumed strategy study.
They cannot be reused to choose factors for a new research lineage. The new
screen therefore binds the Factor Catalog cohort directly and may reuse only
governed source and lifecycle evidence, never the prior strategy results.

## Decision

Freeze one development-only screening campaign for Factor Catalog V1.
The typed protocol logical fingerprint is
`222b14dd358f5d4e6e260c77226b11f3ac2130f8850f96abe5ae5d48a07a8a60`.

### Cohort and isolation

- Bind catalog fingerprint
  `699fff686d2b05c53ba5f586934224794e17cef8d38690ced6a7da2dcd5a9368`
  and qualification fingerprint
  `fb92e95acb146af66fb4d9e286c96852374a51884936f5d69536c4accacdab02`.
- Reuse the frozen 287-session chronological plan, but admit only usable
  Development sessions having a complete 12-factor cross-section: 106 sessions
  from 2025-07-22 through 2026-01-07 and 167,860 expected instrument-session
  paths.
- Exclude an entire session when its complete-vector condition fails. Never
  substitute current Membership, current classification, or a ticker-only
  history.
- Read only Development outcomes. Validation and Holdout remain closed.

### Registered hypotheses and labels

The formal budget is eight factor hypotheses:

- five `candidate_alpha` factors use next-open to horizon-close SPY-relative
  underlying-stock return; and
- three `risk_guard` factors use maximum adverse excursion from the next open.

The primary horizon is three sessions. One- and five-session results are decay
diagnostics and cannot replace the primary result. Alpha factors with finite
terminal intervals must pass under both lower and upper endpoint worlds. Risk
guards use only complete exact excursion paths. Unexecutable or unavailable
labels remain nonnumeric exclusions with reasons.

The four `setup_conditioner` factors consume zero outcome trials in this
campaign. They cannot be promoted by attractive standalone returns. A future
threshold, shape, or interaction test requires a separately registered model-
development trial.

### Frozen statistics and gates

- Orient each factor so a higher same-session average rank means the
  preregistered better state. Rank the role-specific target within the same
  session. No outcome-guided winsorization is allowed.
- Require at least 100 usable instruments in a session, 80 primary sessions,
  and 40 sessions in each chronological half.
- Calculate unweighted daily Spearman rank IC, a deterministic 10,000-replicate
  circular session-block bootstrap with five-session blocks, 90% confidence
  bounds, positive-session share, absolute session contribution, chronological
  halves, five bucket means, bucket monotonicity, and top-minus-bottom spread.
- The 20-session SPY-relative return is the transparent baseline. Every other
  formal factor also requires same-session partial Spearman evidence after
  linear rank residualization against that baseline.
- A factor gate requires primary mean rank IC at least 0.015, incremental mean
  partial rank IC at least 0.005 when applicable, lower one-sided 90% bounds
  above zero, at least 55% positive sessions, both chronological halves
  positive, absolute single-session contribution no greater than 15%, bucket
  Spearman at least 0.80, positive top-minus-bottom target spread, and no 1- or
  5-session mean rank IC below -0.01.
- Apply Holm family-wise adjustment at 0.05 separately across the five Alpha
  hypotheses and three risk-guard hypotheses. For interval Alpha outcomes the
  least favorable endpoint statistic controls every gate and adjusted
  probability.

Historical point-in-time industry classification and diverse Regime coverage
are unavailable. They remain explicit limitations, not inferred controls.
Regime summaries are descriptive only if a trustworthy source is present.

### Cost, selection, and stopping

For Alpha factors, report long-top-quintile minus short-bottom-quintile gross
spread and fixed 0/10/25/50 basis-point-per-side sensitivities. Four sides are
charged for the long-short round trip. Cost is diagnostic, not an admission
gate, because this stage has not defined a portfolio or strategy expression.

At most three screened factors may enter the first model candidate set: no
more than two candidate-Alpha factors, one risk guard, and one factor per
related-factor group. Passing factors are ordered by the least favorable
registered effect, then its lower bound, then stable factor ID. At least one
candidate-Alpha factor must survive before Model Construction can be proposed.

The campaign permits one immutable report and one exact independent replay.
No formula, threshold, role, label, endpoint, or selection-rule revision is
allowed after outcome access. Failure ends this catalog version; a changed
question requires a new registered version and counted trials.

## Consequences

- Factor screening is statistically finite and independent of the rejected
  Pullback strategy results.
- A factor may be rejected despite an attractive chart or pooled return.
- A surviving factor is only a reconstructed-development model input candidate,
  not validated Alpha, a strategy, a Candidate ranking, or a Production claim.
- Model Construction, Strategy Expression, Validation, Holdout, Candidate,
  deployment, broker, and order-execution authority remain closed.

## Alternatives considered

### Reuse the Strong-Leader Pullback development result

Rejected because that outcome was consumed under another registered strategy
question and cannot provide independent factor selection.

### Screen all 12 factors for standalone returns

Rejected because the four conditioners have no standalone monotonic Alpha
claim and would invite post-hoc threshold selection.

### Use pooled instrument rows as independent observations

Rejected because 167,860 cross-sectional rows do not create that many
independent time observations. Inference is session-balanced and block-aware.

### Require sector-neutral evidence now

Rejected because point-in-time historical classification is not available.
The limitation is disclosed and carried forward rather than filled with
today's labels.
