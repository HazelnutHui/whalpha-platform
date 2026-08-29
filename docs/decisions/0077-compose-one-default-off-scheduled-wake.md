# ADR 0077: Compose One Default-Off Scheduled Wake

## Status

Accepted

## Date

2026-08-29

## Context

ADR 0076 can determine the oldest missing XNYS session and when a coordinator
wake may be reviewed, but it intentionally cannot invoke the coordinator. The
next boundary must prove that a future timer wake cannot turn retry, recovery,
alert, publication, or deployment state into an in-process loop.

## Decision

Add `daily-eod-scheduled-wake/1.0` between an exact unchanged ADR 0076 plan and
one supplied coordinator callable. The bridge remains disabled unless both the
plan is an explicitly enabled candidate and the caller separately requests one
invocation. It validates the complete plan fingerprint before any call and
recomputes and retains the formal coordinator-result fingerprint after the
call.

One invocation may return any existing coordinator state, including waiting,
manual authorization, recovery required, transition executed, publication or
deployment review, or blocked. The bridge records that result and returns. It
never calls the coordinator a second time, never routes recovery, never emits
or delivers an alert, and rejects any result claiming scheduler, publication,
or deployment authorization. A malformed or field-tampered coordinator result
is rejected. If the coordinator raises, the wake fails with an unknown outcome
and automatic replay remains prohibited.

Add a credential-free synthetic rehearsal containing five separate wakes:
current/up-to-date, oldest missing session, retry waiting, unresolved
interruption, and alert required. Synthetic coordinator results test the
bridge; they are not provider, publication, or Production evidence.

No CLI in this boundary accepts host config, standing authorization,
credentials, execution paths, or network capabilities. No service or timer is
installed.

## Consequences

- A future timer may request at most one existing coordinator transition per
  process and cannot loop based on the returned state.
- Recovery-required and alert-required results remain visible without replay
  or notification delivery.
- Publication and OCI deployment remain manual/separately enabled even if
  earlier data and offline calculation stages are later scheduled.
- The next step is exact host/runtime configuration and a write-free systemd
  unit/timer candidate, followed by a separate installation decision.

## Alternatives Considered

### Keep calling until the coordinator reports analytics ready

Rejected because one wake would share authority and crash state across several
data and calculation transitions.

### Automatically route recovery-required results

Rejected because an unresolved start may already have produced a durable side
effect; recovery must remain an explicit distinct wake and never replay.

### Deliver alerts directly from the scheduler bridge

Rejected because notification custody and transport configuration are separate
boundaries and SMTP is deliberately unset.
