# ADR 0084: Reserve One Pipeline Wake Before Invocation

## Status

Accepted

## Date

2026-08-30

## Context

Pipeline Wake Plan 2.0, Bounded Cadence Plan 1.0, and ADR 0083's result
adapters can describe and retain one wake, but merely invoking an action and
then appending its result leaves a crash gap. If the process exits after the
action's terminal evidence but before cadence evidence is appended, a later
wake could undercount the cadence and continue too soon. Holding the existing
run-journal lock across invocation is not viable because the coordinator and
offline executor acquire that same lock for their own action custody.

## Decision

Advance the existing run journal to 1.8 and cadence custody to 1.1. Add one
standalone `cadence_wake_reserved` event before an invocation and retain the
existing `cadence_wake_recorded` event as its known terminal result. Both use
the same deterministic attempt identity, full enabled cadence plan, exact
Pipeline plan identity, cadence sequence, immutable cadence start, and action.
The reservation carries an `unknown` in-progress outcome; it is not presented
as a completed wake.

The reservation is written and reread under the existing owner-only journal
lock. The lock is then released so exactly one separately supplied data or
offline capability may use the normal action custody. A known, validated
result closes the same reservation under a new short journal lock. Action
events may therefore appear between the reservation and its result without a
second store or lock hierarchy.

An exception, invalid return contract, process interruption, or failure to
retain the known result leaves the reservation open. A second reservation and
all later-session custody are rejected until manual diagnosis; automatic
replay, retry, recovery, and inference from partial state remain prohibited.
Legacy journal 1.2–1.7 events and direct 1.7 cadence evidence remain readable.

Add a repository-only `daily-eod-pipeline-runtime/1.0` bridge. Its default path
only reports waiting, review-ready, or stopped state. Explicit invocation
requires exact Pipeline and cadence fingerprints, both enabled candidates, and
exactly one capability matching the planned data/offline scope. It invokes at
most once, never loops, and returns the reservation/result event identities.

No CLI, persistent runtime root, capability implementation, credential,
provider/OCI request, `/data` write, service/timer change, publication,
deployment, or Production invocation is included. The installed timer remains
bound to the read-only planner. A natural timer trigger remains required before
any runtime installation or activation decision.

## Consequences

- A crash cannot silently erase evidence that one wake may have crossed its
  side-effect boundary.
- Existing action-level locking remains authoritative and is not nested under
  another long-held lock.
- A known failure is retained and stops; an ambiguous outcome remains visibly
  unresolved and stops across both process and session boundaries.
- The bridge is now testable as a complete one-process composition, but it is
  not an unattended runner and has no installed entry point.
- Manual classification of an unresolved cadence reservation is still future
  work and must not replay the underlying action.

## Alternatives Considered

### Invoke first and append cadence evidence afterward

Rejected because process exit between those operations would undercount the
wake and weaken the minimum interval and finite budget.

### Hold the run-journal lock across the action

Rejected because existing action custody must acquire the same lock and would
deadlock or require a broad executor rewrite.

### Add a second runtime lock or database

Rejected because it would introduce another operational truth and lock order
without solving durable crash ambiguity as directly as a journal reservation.
