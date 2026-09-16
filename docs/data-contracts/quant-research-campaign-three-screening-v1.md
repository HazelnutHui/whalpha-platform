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

ADR 0292 fixes the implementation choices that ADR 0291 intentionally leaves
implicit:

- unweighted OLS with intercept over ordered session pairs;
- the original calendar halves, not a midpoint split of surviving evidence;
- paired circular-block resampling with deterministic content-bound seeds;
- the linearly interpolated tenth percentile as the one-sided 90% lower bound;
- a centered-bootstrap one-sided probability with finite-sample `+1`
  correction;
- maximum probability and minimum slope/lower bound across registered primary
  endpoint and block worlds;
- probability one for an unavailable registered trial, which remains in Holm;
- exact complete-path evidence for the risk guard; and
- nonnumeric, non-gating cost declarations until Strategy Expression exists.

Exact gates and rationale are frozen in [ADR 0291](../decisions/0291-freeze-campaign-three-screening-protocol-and-ledger-v4.md),
with evaluator and custody mechanics in [ADR 0292](../decisions/0292-freeze-campaign-three-evaluator-and-execution-custody.md).

## Result and execution contracts

The typed report contains all ordered session evidence, 15 summaries, three
decisions, role-specific Holm results, conservative primary statistics,
source lineage, limitations, and zero downstream authority. It binds the
exact V1 diagnostics, V2 qualification, Campaign Three input qualification,
qualified Market-State artifact, canonical labels, request, grant, clean
implementation revision, and evaluator code hash.

The access workflow persists four immutable record types under owner-only
custody:

1. a closed request bound to the clean revision, protocol, and Ledger V4;
2. an exact user grant bound to that request;
3. one formal reservation and completion; and
4. one exact-replay reservation and completion.

Reservation occurs only after all outcome-blind reconstruction and preflight
checks pass, but before terminal evidence or future EOD labels are read. A
reservation consumes its slot even if the subsequent run fails. Replay
requires a completed formal report, the same request/grant/revision/
`created_at`/sources, a distinct output root, and byte-identical report SHA-256
and logical fingerprint. A third run is rejected.

## Authority boundary

The contract leaves Development outcome authorization false. It requires a
separate typed grant bound to the protocol, Ledger V4, and a clean committed
implementation revision. Validation, Holdout, Model Construction, Strategy
Expression, Candidate activation, publication, options, broker access, and
trading remain closed.

The evaluator, immutable report custody, typed access workflow, and two-slot
execution boundary are implemented and tested. No request, grant, formal run,
replay, or Campaign Three result exists yet.
