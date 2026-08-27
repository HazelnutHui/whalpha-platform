# ADR 0032: Custody Provider Fetch Attempts Before Automation

## Status

Accepted

## Date

2026-08-27

## Context

ADR 0031 can decide when an exact-session provider fetch should be reviewed,
but an external request can still be duplicated if two operators act, a process
stops, or prior rate-limit/failure evidence is lost. A completed `/tmp` fetch
package also cannot be treated as belonging to the current attempt merely
because its path exists.

This custody layer must precede any standing provider authorization. It must
record intent and results without gaining the ability to load a credential or
make a request.

## Decision

Add contract `daily-eod-acquisition-custody/1.0` and extend the not-yet-
activated Dell run journal to `daily-eod-run-journal/1.1`. Provider attempts
and offline calculations share the same non-blocking global lock and
cross-session SHA-256 event chain, while using disjoint start/terminal event
families that cannot close one another.

Before a separately authorized Identity or EOD fetch, custody requires:

- one exact acquisition action and oldest-missing target session;
- an unchanged `daily-eod-readiness-plan/1.0` fingerprint whose next action is
  fetch-authorization review;
- a readiness observation no more than five minutes old;
- all prior same-action attempts projected from the formal journal and accepted
  by the bounded-backoff policy;
- no unresolved provider or offline attempt; and
- a new, direct, non-hidden `/tmp` package target with no staging residue.

Reservation appends `acquisition_started` and releases the lock. It explicitly
does not execute the fetch, load credentials, or authorize one. After an
externally authorized fetch, outcome recording reacquires the lock and accepts
only `not_ready`, rate-limited, transient failure, package ready, permanent
failure, or quality failure. `Retry-After` is allowed only for rate limits and
retains ADR 0031's bound.

A package-ready result must pass the existing formal frozen-package reader and
match the reserved operation, session, exact path, package type, bounded request
count, manifest/content hashes, and a package generation time between the
reservation and result event. Only hashes, counts, timing, and non-sensitive
custody are journaled; provider response content is not.

An interruption leaves the start unresolved and blocks all later transitions.
Recovery never makes a request. It records package ready only after the same
formal validation, not completed only when both target and staging are absent,
or blocked for residue/invalid custody. Completed terminal events are projected
back into ADR 0031 attempt evidence, so retry count and delay survive process
and task boundaries.

The journal root remains explicitly pre-provisioned, owner-only, outside Git
and `/data`. Repository implementation and tests do not create the real root or
run a real attempt.

## Consequences

- Duplicate or concurrent fetch reservation fails closed.
- Offline computation cannot start while a provider attempt is unresolved.
- Old, wrong-session, wrong-operation, wrong-path, pre-reservation, corrupt, or
  incomplete packages cannot be recorded as current success.
- Crash recovery distinguishes absence from completed immutable evidence and
  ambiguous residue without retrying.
- Custody records an externally supplied outcome but never claims that custody
  itself made the request.
- Standing authorization, the component that executes a reserved request,
  automatic alert delivery, canonical apply authorization, and scheduler
  activation remain separate work.

## Alternatives Considered

### Let the future scheduler keep retry count in memory

Rejected because restart would erase request history and duplicate protection.

### Hold the filesystem lock throughout the network request

Rejected because an external wait should not retain a process lock; the
unresolved immutable start event already blocks another transition.

### Treat any existing package directory as success

Rejected because path existence does not prove operation, session, content,
timing, or request custody.

### Use a separate provider lock and journal

Rejected because acquisition and calculation belong to one serial daily state
machine and must not run concurrently.
