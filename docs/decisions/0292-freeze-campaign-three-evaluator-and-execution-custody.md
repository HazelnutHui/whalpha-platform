# ADR 0292: Freeze Campaign Three Evaluator and Execution Custody

## Status

Accepted

## Date

2026-09-16

## Context

ADR 0291 freezes Campaign Three's economic hypotheses, Development population,
endpoints, gates, family-wise control, selection caps, and one-run-plus-replay
limit. It intentionally does not leave implementation choices free after
outcomes become visible. The remaining statistical and custody mechanics must
therefore be fixed before any Development label is read by the Campaign Three
evaluator.

## Decision

1. Fit the registered interaction separately for every hypothesis, horizon,
   and endpoint by unweighted ordinary least squares with an intercept over the
   ordered session pairs `(S(t), q(t))`. Instrument rows are used only to form
   each same-session Spearman rank IC and are never treated as independent
   inference observations.
2. Preserve the original calendar split: Development sessions 1--53 and
   54--106. Missing session evidence does not move the surviving rows into two
   newly balanced halves.
3. Resample the ordered paired session series with a circular block bootstrap.
   Use deterministic, content-bound seeds, 10,000 replicates, the registered
   10-session primary block and 20-session sensitivity block, and fail closed
   if any replicate produces a degenerate state sample.
4. Define the one-sided 90% lower bound as the linearly interpolated tenth
   percentile of bootstrap interaction slopes. Define the conservative
   one-sided bootstrap probability with the finite-sample `+1` correction from
   the centered bootstrap null tail: count replicates satisfying
   `beta_star - beta_observed >= beta_observed`, then divide the count plus one
   by the replicate count plus one.
5. For a trial with two registered primary endpoints, use the maximum
   one-sided probability across both endpoints and both block lengths for
   family testing. Use the minimum interaction beta and minimum registered
   lower bound for conservative reporting. An absent, degenerate, or otherwise
   inconclusive primary result receives probability one and remains in its
   preregistered Holm family.
6. Apply Holm adjustment separately to the fixed two-Alpha family and the
   fixed one-risk family. A missing trial is never dropped from multiplicity.
7. Evaluate the risk guard only on its registered exact complete-path outcome.
   One- and five-session results remain diagnostics and cannot rescue or veto
   the primary third-session decision. The declared 0/10/25/50 basis-point
   cost scenarios remain nonnumeric and non-gating because no portfolio or
   Strategy Expression exists.
8. Select at most one passing Alpha and, only if an Alpha survives, at most one
   passing risk guard. Development selection still creates no validated Alpha,
   model, strategy, Candidate, publication, or trading authority.
9. Persist the typed request, grant, execution state, and result in owner-only,
   immutable, canonical JSON custody. The formal run and exact replay must use
   the same committed revision, request, grant, protocol, ledger, `created_at`,
   and source artifacts but distinct output roots.
10. Reserve an execution slot before opening Campaign Three outcomes. A
    reserved or failed slot remains consumed. The formal slot must complete
    before replay, the replay must match the formal report byte-for-byte, and a
    third execution is rejected.
11. All outcome-blind reconstruction, source verification, and exact-replay
    checks must complete before a slot is reserved. Neither this ADR nor the
    implementation authorizes the first outcome read; the exact typed grant
    from ADR 0291 remains mandatory.

## Consequences

Campaign Three now has a single deterministic statistical interpretation and a
fail-closed two-slot execution boundary. Implementation and tests may proceed
without reading results. After a clean committed revision is bound into the
request, the exact user authorization is still required before the formal run
or replay.

## Rejected alternatives

- split the surviving rows at their midpoint;
- use instrument-level standard errors or ordinary iid resampling;
- report the fifth percentile as a one-sided 90% lower bound;
- choose the most favorable endpoint or block length;
- remove missing trials from Holm adjustment;
- numerically subtract hypothetical trading costs before a strategy exists;
- retry a failed execution without consuming its slot; or
- allow a matching report in the same output root to count as an independent
  replay.
