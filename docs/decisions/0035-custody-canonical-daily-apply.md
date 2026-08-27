# ADR 0035: Custody Canonical Daily Apply

## Status

Accepted

## Date

2026-08-27

## Context

Identity/EOD fetch attempts and offline analytics already have immutable start
and terminal custody. Canonical apply can publish several immutable Identity
components or one EOD partition under `/data`; a process interruption cannot be
safely represented as an ordinary failed return or automatically retried.

The standing-authorization contract binds an approved plan and expected current
state, but authorization alone does not prove what happened after apply began.

## Decision

Add contract `daily-eod-canonical-apply-custody/1.0` and extend the not-yet-
activated shared journal to `daily-eod-run-journal/1.2` with a third disjoint
start/terminal family.

Before an external apply, custody must hold the global lock and prove:

- no unresolved acquisition, apply, or offline action;
- the latest exact-action acquisition ended in a formally completed package;
- readiness still requests apply review with the exact expected fingerprint;
- the frozen plan formally rereads with the approved whole-file SHA;
- operation, target session, data root, package path and package hashes match
  acquisition custody;
- the plan's expected-current-state fingerprint equals both the reviewed input
  and a fresh canonical inventory fingerprint; and
- every target named by the plan is absent.

Reservation appends `canonical_apply_started` with only non-sensitive exact
bindings and then releases the lock. It does not authorize or execute apply.

After an externally authorized apply returns, success may be recorded only when
the exact-session automation planner formally proves the named canonical stage
complete and advanced. An exception or failed postcondition deliberately leaves
the start unresolved; it must not be converted to a retryable failure because
the process may have written a subset immediately before stopping.

Recovery performs no apply. It records:

- recovered success when formal canonical readers prove completion and plan
  advancement;
- recovered not completed only when every planned target is absent and the
  entire canonical inventory still equals the approved pre-apply fingerprint;
  or
- recovery blocked for partial, changed, invalid, symlinked, or ambiguous
  state.

Partial Identity publication may later use the existing separately authorized
`verify-then-complete` operation after diagnosis. It is never automatically
invoked by recovery. EOD recovery similarly relies on formal reread and never
overwrites an existing target.

No real journal root, plan, apply, recovery, `/data` write, authorization
artifact, provider request, publication, deployment, or scheduler is created by
this repository implementation.

## Consequences

- Canonical writes join the same global serial state machine as acquisition and
  calculation without sharing terminal event families.
- Unknown apply outcomes remain visibly unresolved instead of being retried.
- A complete target can be reconciled without replay; a provably untouched
  state can permit a later separately authorized retry.
- Partial or mutated state blocks the pipeline until explicit diagnosis.
- The real authorized apply capability can now be implemented without inventing
  weaker crash semantics inside the coordinator.

## Alternatives Considered

### Record every thrown exception as retryable failure

Rejected because an exception does not prove zero canonical writes.

### Hold the global journal lock throughout filesystem publication

Rejected because the immutable unresolved start already serializes later work,
while the existing apply boundary holds its own publication lock.

### Automatically run Identity verify-then-complete during recovery

Rejected because partial canonical publication requires diagnosis and separate
authorization, not an implicit recovery write.
