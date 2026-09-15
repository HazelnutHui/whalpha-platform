# ADR 0281: Freeze Factor Catalog V2 Development Screening Protocol

## Status

Accepted

## Date

2026-09-15

## Context

Factor Catalog V2 and its unchanged outcome-blind qualification are complete.
The repaired report and exact replay pass the frozen data gates at 98.59%
coverage, but they contain no forward outcome and establish no predictive
value. Development outcomes cannot be opened until the cohort, labels, formal
trial budget, cumulative search history, multiplicity, stability, costs,
selection cap, and stopping rule are fixed.

Factor Discovery V1 already consumed eight Development trials. V2 was designed
with knowledge of those failures and is therefore adaptive; it cannot be
presented as a fresh first search.

## Decision

Freeze one finite, Development-only Factor Catalog V2 screen under protocol
`quant-research-factor-screening/2.0.0`, logical fingerprint
`5441468ef8b392f555aac5a4e9cc8c6d50a9fb064349b6da342ccc2540dc193b`.

### Population and missingness

- Bind the V2 catalog and the byte-identical ADR 0280 qualification at logical
  fingerprint
  `f49b17d74b9ec0960278405475ec962361c8169bd071030deda7fa36557aee90`.
- Reuse the frozen chronological plan and its 106 declared Development sessions
  from 2025-07-22 through 2026-01-07, containing 167,860 declared Membership
  paths. This is reconstructed latest-vintage research, not `as_operated`.
- A stock-specific factor defect excludes only that stable-ID/factor trial. A
  benchmark defect excludes the complete session. Missing outcomes remain
  nonnumeric exclusions with explicit reasons; nothing is zero-filled.
- Read only Development outcomes. Validation and Holdout stay closed.

### Registered trials and outcomes

The formal budget is six trials:

- four `candidate_alpha` measurements use next-open to 3-session-close
  SPY-relative underlying-stock return; and
- two `risk_guard` measurements use exact 3-session maximum adverse excursion
  from the next open.

One- and five-session labels are decay diagnostics and cannot replace the
3-session primary endpoint. Alpha trials with finite terminal intervals must
pass in both lower and upper endpoint worlds. Risk guards use exact complete
paths only.

`down_market_relative_resilience_60s` remains a conditioner with zero outcome
trials. `amihud_illiquidity_20s` remains an applicability/capacity input with
zero standalone Alpha trials. Any threshold, interaction, or capacity segment
requires a separate preregistered Model Construction experiment.

### Frozen inference and gates

- Use same-session average ranks oriented so higher means the registered better
  state. Session, not instrument row, is the unit of inference.
- Reuse the V1 gates unchanged before any V2 outcome read: minimum 100
  instruments, 80 primary sessions, 40 sessions in each chronological half,
  mean rank IC at least 0.015, incremental partial rank IC at least 0.005,
  positive one-sided 90% lower bounds, at least 55% positive sessions, positive
  effect in both halves, no session above 15% absolute contribution, bucket
  Spearman at least 0.80, positive top-minus-bottom spread, and no 1- or 5-day
  mean IC below -0.01.
- Use 10,000 deterministic circular five-session block-bootstrap replicates and
  Holm family-wise adjustment at 0.05 separately across the four Alpha and two
  risk-guard trials.
- Require every trial to show incremental rank evidence after controlling for
  V1's consumed `relative_return_spy_20s`. That baseline is a nuisance control,
  not a seventh V2 trial and not revived Alpha.
- Historical sector neutralization and diverse Regime stability remain
  unavailable and explicitly limit interpretation.

### Costs, selection, and stopping

Report Alpha top-minus-bottom quintile spreads under 0/10/25/50 basis points
per side, charging four sides for a long-short round trip. Costs are diagnostic
because no portfolio or strategy expression exists.

At most two candidate Alpha factors and one risk guard may proceed, with no
more than one factor per related group. Gate pass, least-favorable effect,
lower bound, and stable factor ID determine ordering. At least one candidate
Alpha survivor is required before Model Construction can be proposed.

One immutable report and one exact replay exhaust this protocol. No formula,
threshold, role, label, family, or selection-rule revision is allowed after
outcome access. Failure closes V2; a different question requires a new catalog,
new protocol, and counted trials.

Before outcomes, cumulative ledger version
`whalpha.quant-research.discovery-trial-ledger/2.0.0` carries all eight V1
trials and appends the six V2 trials as `registered_pending_development_screen`.
Its logical fingerprint is
`cdc07a2194540b94dbba6bfee673a720ce232dc1d939f8b2c7496dda628946e9`.

## Consequences

The project may implement and execute exactly this Development screen. A
surviving factor is still selection evidence, not validated Alpha. Model
Construction, Strategy Expression, Validation, Holdout, Candidate ranking,
publication, deployment, broker, and order authority remain closed.

## Rejected alternatives

- Tune gates after seeing V1 or V2 outcomes.
- Treat 167,860 instrument rows as independent observations.
- Screen the conditioner or liquidity input for attractive standalone returns.
- Use pooled return, win rate, or a backtest chart as the sole admission test.
- Hide V1 trials and call V2 a statistically independent first search.
- Infer historical sector labels, Regime diversity, missing actions, or option
  performance from the available daily equity data.
