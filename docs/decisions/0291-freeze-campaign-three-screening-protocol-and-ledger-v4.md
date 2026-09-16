# ADR 0291: Freeze Campaign Three Screening Protocol and Ledger V4

## Status

Accepted

## Date

2026-09-16

## Context

Campaign Three retained five hypothesis cards. One near-duplicate stopped at
intake. ADR 0290 then qualified two candidate-Alpha interactions and one risk
guard over the exact 106-session Development intersection, while defensive
resilience stopped before outcomes because its natural-zero state support was
sparse and concentrated. The report and independent replay are identical.

Opening outcomes before fixing the estimand, inference unit, trial family,
multiplicity, stability, selection, and stop rules would recreate an adaptive
search after two completed campaigns and 14 consumed trials.

## Decision

1. Register exactly three trials: breakout by market breadth, volume activity
   by market participation, and residual risk by broad volatility. The rejected
   defensive-resilience design and intake near-duplicate consume no outcome
   trial and cannot be reintroduced in this campaign.
2. Use the exact 106 Development sessions from 2025-07-22 through 2026-01-07,
   split into two chronological halves of 53 sessions. Membership remains
   reconstructed latest-vintage research evidence, not `as_operated`.
3. For every session, compute same-session Spearman `q(t)` between the oriented
   factor rank and registered target rank. Estimate the fixed interaction
   `q(t) = alpha + beta * S(t) + error` using the preregistered point-in-time
   market-state value.
4. Candidate Alpha uses SPY-relative next-open to third-session-close
   underlying-stock return. The risk guard uses exact three-session maximum
   adverse excursion. One- and five-session horizons are diagnostics and may
   not replace the primary endpoint.
5. Require positive interaction beta, a positive one-sided 90% lower bound,
   positive beta in both chronological halves, at least 80 primary sessions
   and 40 per half, and a positive one-sided 90% lower bound under both
   10-session primary and 20-session sensitivity circular block bootstraps with
   10,000 replicates.
6. Candidate Alpha additionally requires positive mean `q(t)` in the
   preregistered favorable state above natural zero. The continuous volatility
   state for the risk guard is not forced through an economically false zero-
   side gate.
7. Apply Holm family-wise control at 0.05 separately to the two-Alpha family
   and the one-risk family. Costs of 0/10/25/50 basis points per side remain
   non-gating diagnostics because this is not yet a portfolio or strategy.
8. Select at most one Alpha and one risk guard, with no more than one trial per
   related family. A risk guard cannot open Model Construction without a
   surviving Alpha.
9. Append the three unread trials to immutable Ledger V4. It carries all 14
   prior trials unchanged and raises cumulative multiplicity to 17.
10. Protocol and ledger registration do not authorize a Development outcome
    read. A separate typed grant bound to the clean implementation revision is
    required for exactly one formal run and one exact replay.
11. One report and one replay exhaust the protocol. No formula, state,
    threshold, label, family, multiplicity, gate, or selection revision is
    permitted after access.

## Consequences

Campaign Three becomes a registered but unread campaign. Model Construction,
Strategy Expression, Validation, Holdout, Stock Candidates, performance
publication, options, broker access, and trading remain closed. A surviving
Development interaction is still selection evidence, not validated Alpha.

## Rejected alternatives

- include all four input-reviewed designs merely to fill a larger budget;
- rescue defensive resilience with a retrospective quantile threshold;
- treat instrument rows as independent observations;
- pool all 17 historical trials into one nominally fresh campaign;
- select on an attractive backtest chart, win rate, or unadjusted p-value;
- let one qualified risk guard open a model alone; or
- let protocol registration itself grant outcome access.
