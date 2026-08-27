# ADR 0038: Route One Interrupted Daily Transition

## Status

Accepted

## Date

2026-08-27

## Context

The acquisition, canonical-Apply, and offline-action custody layers already
had separate recovery functions, but ADR 0037's one-transition CLI only
reported the name of the required recovery. An operator or future scheduler
still lacked one common entry that could formally reread the exact unresolved
journal event and call only its matching recovery boundary.

## Decision

Add `daily-eod-one-transition-recovery/1.0` and an explicit
`--recover-unresolved` CLI mode. One invocation:

1. reads the current unresolved start event through the shared locked journal;
2. requires it to equal the coordinator's exact event, including attempt and
   event fingerprints;
3. maps only `acquisition_started`, `canonical_apply_started`, or
   `action_started` to its existing family-specific recovery function;
4. reconstructs recovery inputs from the coordinator's explicit paths and the
   immutable start-event bindings; and
5. returns one bounded terminal event as coordinator evidence.

Recovery never issues a provider request, performs canonical Apply, or replays
an offline calculation. Canonical Apply recovery uses only the approved-plan
SHA and expected inventory fingerprint retained in `canonical_apply_started`;
new command-line values cannot replace them. All recovery evidence must report
zero external requests, zero canonical Production writes, and
`action_replayed=false`. A partial, changed, malformed, wrong-family, or
otherwise ambiguous state fails closed or becomes operator diagnosis.

Recovery mode is mutually exclusive with authorized capability installation
and offline execution, and the CLI socket guard stays active. It still invokes
the coordinator once and never retries, loops, publishes, deploys, or enables
a scheduler. A successful recovery only closes the interrupted custody event;
a later invocation must plan the next transition.

This repository change does not provision a run root or external config and
does not execute recovery against real state.

## Consequences

- The code path from one unresolved journal event to its existing recovery
  boundary is complete and independently testable.
- Recovery can append one terminal custody event, but cannot repeat the
  interrupted external or calculation side effect.
- A concurrent event change is detected by the family-specific recovery after
  the router's locked reread and cannot produce false success.
- Host/authorization provisioning, alert delivery, controlled rehearsal, and
  scheduler activation remain separate operational decisions.

## Alternatives Considered

### Automatically recover whenever a pending event exists

Rejected because inspection and mutation of the run journal must remain an
explicit operator choice until controlled rehearsal is complete.

### Retry the interrupted action during recovery

Rejected because the process may have completed its external side effect
before interruption. Recovery classifies durable state; it never guesses or
duplicates work.

### Accept fresh Apply bindings from the recovery command

Rejected because recovery must preserve the identity of the already-started
Apply rather than authorize a different plan or inventory boundary.
