# ADR 0034: Coordinate Exactly One Daily Transition

## Status

Accepted

## Date

2026-08-27

## Context

The exact-session automation planner, provider readiness policy, shared run
journal, acquisition custody, offline executor, and inactive standing-
authorization contract are individually fail-closed. A timer or operator still
needs one entry point that joins their decisions without turning a wake-up into
permission to run the whole daily pipeline.

The coordinator must not loop through multiple stages, retry in-process, infer
`latest` paths, bypass interruption recovery, or treat analytics readiness as
publication permission.

## Decision

Add contract `daily-eod-one-transition-coordinator/1.0`. One invocation accepts
an exact target session, latest canonical session, explicit automation paths,
run root, package/plan custody paths, and observation time. It formally reads
the automation plan and shared journal, then returns or invokes at most one of:

- wait for close, stabilization, or bounded retry;
- request acquisition recovery for an unresolved provider attempt;
- request offline recovery for an unresolved calculation;
- request operator diagnosis for blocked state;
- request manual fetch/apply authorization when no authorized capability is
  installed;
- invoke exactly one installed fetch or apply capability;
- invoke exactly one ADR 0030 offline analytics action; or
- stop at publication review when analytics are complete.

Provider and canonical-apply capabilities are explicit optional ports and are
absent by default. A future real adapter must independently satisfy ADR 0032
custody and ADR 0033 authorization before returning formal bounded evidence.
The coordinator validates the requested operation, exact precondition
fingerprint, target session, result class, and maximum one-request/one-write
counts. It never supplies authorization itself.

Offline execution is also opt-in per invocation and delegates to ADR 0030's
exact-plan executor. The coordinator never performs more than one action and
never calls itself again after a result.

No CLI, real capability adapter, authorization artifact, run root, scheduler,
notification, publication, Snapshot, bundle, deployment, or rollback is
activated by this repository slice.

## Consequences

- One common state-machine entry can later be woken by a scheduler without
  changing business or safety semantics.
- Waiting, authorization review, recovery, diagnosis, calculation, and
  publication review remain visibly different outcomes.
- A capability cannot claim a second request/write or return evidence for a
  different action or stale precondition.
- Completing the coordinator core does not yet make daily provider/apply
  operation unattended; real authorized adapters, alert delivery, controlled
  rehearsal, and scheduler activation remain separate.

## Alternatives Considered

### Loop until publication readiness

Rejected because one invocation would silently share authorization and failure
state across acquisition, canonical writes, heavy calculation, and publication.

### Put provider credentials and `/data` apply directly in the coordinator

Rejected because orchestration must not become its own authority or duplicate
the existing formal provider/apply boundaries.

### Let a shell script branch only on exit codes

Rejected because exit codes do not bind exact sessions, fingerprints, journal
state, retry policy, or formal completion evidence.
