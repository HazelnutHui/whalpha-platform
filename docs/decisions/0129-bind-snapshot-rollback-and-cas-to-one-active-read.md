# ADR 0129: Bind Snapshot rollback and CAS to one active read

## Status

Accepted.

## Date

2026-09-04.

## Context

Dashboard Snapshot approval-plan construction formally read and validated the
active Snapshot once to capture its rollback reference, then called the public
current-state fingerprint reader. That second call formally read and validated
the same active Snapshot again. On the unchanged 2026-09-03 Dell state, one
active Snapshot read took approximately 12.3 seconds.

The duplicate was not needed for independent validation: both values belong to
one approval-plan observation and must describe the same current state. Reading
them separately also allowed an active-state change between the rollback read
and the expected-state read to produce an internally mixed plan. Apply already
performs a fresh current-state read under its compare-and-swap boundary.

## Decision

- Derive both the rollback reference and
  `expected_current_state_fingerprint` from the same fully validated
  `ActiveDashboardSnapshot` object while building one approval plan.
- Centralize the object-to-state-fingerprint projection. A pointer-backed
  active state uses its already verified pointer-content fingerprint; the
  legacy fallback uses the unchanged canonical reference projection.
- Keep the standalone current-state fingerprint reader as a fresh formal read.
  Apply, verify-then-link, rollback, and recovery paths therefore retain their
  independent current-state checks.
- Do not cache an active object across processes, plans, or Apply. A plan is
  still bound to the exact observed state, and any later state change must fail
  compare-and-swap validation.

## Consequences

- One approval plan cannot mix a rollback reference from one active state with
  a CAS fingerprint from another.
- Plan construction removes one complete duplicate active Snapshot validation
  without changing candidate, Snapshot, Dashboard, approval-plan, pointer, or
  publication contracts.
- On unchanged 2026-09-03 inputs, candidate-plus-plan wall time fell from
  135.00 to 121.57 seconds and peak RSS remained effectively unchanged at
  994,052 KiB. All 42 generated Snapshot files were byte-identical. The two
  plans differed only in their required temporary `candidate_path` and the
  derived plan-content fingerprint; rollback, expected current state, target
  pointer, aggregate, and manifest bindings were exact.
- A focused regression test requires exactly one active read during plan
  construction and checks that both bindings derive from that observation.
- No `/data`, Production, scheduler, publication, deployment, formula,
  parameter, Universe, or network boundary changes.

## Alternatives Considered

### Keep two formal reads

Rejected. The two observations are not independent gates and can describe
different active states. Apply already provides the necessary later fresh
comparison.

### Reuse the planning read during Apply

Rejected. That would weaken the compare-and-swap boundary across processes or
elapsed time.

### Cache active Snapshot validation globally

Rejected. Global or cross-operation reuse would make state freshness and
invalidation ambiguous.
