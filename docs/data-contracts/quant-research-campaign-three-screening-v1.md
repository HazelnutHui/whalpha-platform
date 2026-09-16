# Campaign Three Screening Protocol V1

## Purpose

`quant-research-campaign-three-screening-protocol/1.0` is the immutable
before-outcomes contract for Campaign Three. It binds the exact outcome-blind
input qualification, three formal interaction trials, Development chronology,
labels, inference, multiplicity, costs, selection cap, and stopping rule.

## Registered trials

| Trial | Role | State interaction | Primary target |
| --- | --- | --- | --- |
| Breakout breadth | Candidate Alpha | Breakout-position rank IC by reconstructed member breadth | 3-session SPY-relative stock return |
| Volume participation | Candidate Alpha | Dollar-volume-surprise rank IC by positive-return participation | 3-session SPY-relative stock return |
| Residual-risk volatility | Risk guard | Safer residual-volatility rank IC by broad realized volatility | Exact 3-session maximum adverse excursion |

The intake near-duplicate and defensive-resilience input rejection remain
retained before-outcomes failures and are not registered trials.

## Evaluation

- exact 106-session Development cohort, 53 / 53 chronological halves;
- same-session average ranks and one session-level Spearman `q(t)`;
- fixed regression `q(t) = alpha + beta * S(t) + error`;
- third-session primary endpoint with one- and five-session diagnostics;
- 10,000 deterministic circular block-bootstrap replicates using 10 sessions
  as primary and 20 sessions as sensitivity;
- positive beta, positive one-sided 90% lower bounds under both block lengths, positive beta in both
  halves, Alpha favorable-state support, and Holm correction at 0.05 within
  the two-Alpha and one-risk families;
- 0/10/25/50 basis-point-per-side non-gating cost diagnostics; and
- at most one selected Alpha plus one selected risk guard, with Alpha required
  before Model Construction can be proposed.

Exact gates and rationale are frozen in [ADR 0291](../decisions/0291-freeze-campaign-three-screening-protocol-and-ledger-v4.md).

## Authority boundary

The contract leaves Development outcome authorization false. It requires a
separate typed grant bound to the protocol, Ledger V4, and a clean committed
implementation revision. Validation, Holdout, Model Construction, Strategy
Expression, Candidate activation, publication, options, broker access, and
trading remain closed.
