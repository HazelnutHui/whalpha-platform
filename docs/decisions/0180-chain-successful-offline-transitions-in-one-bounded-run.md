# ADR 0180: Chain Successful Offline Transitions in One Bounded Run

## Status

Accepted

## Date

2026-09-09

## Context

The daily control plane already reserves, executes, verifies, and journals one
offline transition at a time. The persistent workspace has also completed a
real end-to-end custody proof. The remaining process-level rule inherited from
ADRs 0082 and 0084 requires a separate wake and at least five minutes between
every successful transition. With eleven offline stages, that delay is not a
data-quality gate and prevents a healthy same-evening run from completing
efficiently.

Provider waiting, canonical Apply, Market Intelligence Apply, Dashboard
Snapshot Apply, and OCI deployment have different side-effect and authority
boundaries. They must not be made implicit merely to remove the artificial
delay between deterministic Dell-local stages.

## Decision

Add `daily-eod-bounded-offline-run/1.0`, a finite Dell-local controller above
the unchanged single-action offline executor.

One invocation:

- formally replans before every action;
- supplies the exact new plan fingerprint to the existing executor;
- executes only actions already admitted by `OFFLINE_ACTIONS`;
- preserves the existing action-level reservation, terminal event, lock,
  postcondition reread, and immutable journal chain for every action;
- advances only after a formally succeeded result with a changed plan;
- stops immediately at authorized-input, publication, Snapshot, deployment,
  blocked, known-failure, or unresolved-action boundaries;
- never retries, recovers, sleeps, polls, requests provider data, applies
  canonical data, publishes, or deploys; and
- is bounded by at most eleven action attempts and at most four elapsed hours,
  with narrower defaults of eleven actions and two hours.

The runner owns only the timestamps required by offline plan preparation. A
Market Intelligence plan still requires an explicit current-state fingerprint;
if it is absent, the runner stops before that action. Snapshot-plan and serving-
bundle timestamps are taken from the injected UTC clock immediately before
their respective actions.

The runner does not create a second durable run record. The existing per-action
journal remains the operational source of truth, while the bounded result is a
fingerprinted invocation summary. After a process exit, the next invocation
must replan from artifacts and the journal. Any unresolved action continues to
block through the existing recovery route.

For successful offline transitions only, this decision supersedes ADR 0082's
distinct-process and five-minute spacing requirement and ADR 0084's extra
cadence reservation. The older cadence/runtime contracts remain readable and
useful for provider waiting and historical evidence, but they are not the
execution path for this bounded offline chain.

The CLI is default review-only. Explicit `--execute` is required to cross an
offline action boundary. It derives only the governed persistent workspace
layout and keeps a socket guard active for the entire invocation.

No service, timer, runtime checkout, standing authorization, credential,
publication capability, deployment capability, or Production invocation is
installed or changed by this decision.

## Consequences

- Healthy deterministic analytics can run consecutively without artificial
  five-minute idle periods.
- A crash or failed stage remains isolated to one existing action reservation;
  later stages cannot run and no side effect is replayed.
- Publication and deployment reviews remain visible rather than being folded
  into a generic success state.
- This is a necessary offline automation step, not completion of unattended
  daily publication. Data acquisition/Apply and the three external serving
  transitions still require their separately governed composition.
- The next controlled rehearsal can prove multi-action timing without provider,
  `/data`, publication, or OCI access.

## Alternatives Considered

### Keep one process and five minutes per successful offline action

Rejected because the delay does not add evidence after a formally completed
and reread local transition, while it makes the daily chain unnecessarily slow.

### Run all calculations inside one unjournaled pipeline command

Rejected because a failure would erase the existing per-stage custody and make
restart location ambiguous.

### Include publication and deployment automatically in the first runner

Rejected because those operations require dynamic current-state evidence and
separate installed capabilities. Their later composition must preserve those
contracts rather than bypass them.
