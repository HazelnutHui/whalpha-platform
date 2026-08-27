# ADR 0039: Separate Daily Alert Intent from Delivery

## Status

Accepted

## Date

2026-08-27

## Context

ADR 0031 identifies missed-session and terminal readiness states that require
operator attention. The coordinator also exposes blocked and interrupted
transitions. Until now that signal was either lost at the coordinator boundary
or represented only by a nonzero process exit. No notification channel has
been selected, and treating a printed message as delivered would create false
operational confidence and duplicate-message risk.

The external standing authorization and host runtime also bind an exact Git
revision. Provisioning them while alert and rehearsal code is still changing
would make the artifacts stale on the next commit.

## Decision

Add `daily-eod-alert-intent/1.0` as a channel-neutral, non-delivering contract.
Coordinator contract 1.3 preserves an exact `alert_required` bit in its own
logical fingerprint. It is true only for:

- a blocked planner, readiness, or recovery state;
- an unresolved interrupted transition awaiting explicit recovery; or
- a missed-session state that has reached manual authorization review.

An alert intent binds the target session, category, severity, coordinator
status, next action, reason codes, and exact coordinator-result fingerprint.
Its deterministic deduplication key excludes wall-clock emission time, so
repeated observation of the same formal state produces the same key. The first
categories are `pipeline_blocked`, `interrupted_transition`, and
`missed_session_attention`.

The one-transition CLI may emit the intent only with explicit
`--emit-alert-intent`. Emission performs no network request, persistence, or
delivery attempt and records `delivery_attempted=false`, zero external
requests, and zero Production writes. A normal state emits `null`. The CLI
does not accept or install a notification transport in this slice.

Real external authorization and host-runtime provisioning remain deferred
while repository control-plane code is still changing. Manual approvals remain
the active operational model.

## Consequences

- Scheduler and transport work can consume one stable, non-sensitive envelope
  without parsing prose or inventing alert policy.
- Stable deduplication identity exists before any channel is selected.
- No result can claim that a user was notified merely because an intent was
  created.
- Actual transport, durable reservation/receipt custody, channel credentials,
  retries, escalation, and process-crash monitoring remain separate work.
- Exceptions that occur before a formal coordinator result still produce the
  existing rejected CLI result, not an alert intent; future watchdog or
  transport integration must cover that failure class.

## Alternatives Considered

### Send email or chat messages directly from the coordinator

Rejected because it would mix data-transition authority, channel credentials,
delivery retries, and provider access in one invocation.

### Use process exit code as the alert contract

Rejected because it lacks severity, session, reason, source identity, and a
stable deduplication key.

### Provision external authorization before finishing alert code

Rejected because the exact-revision binding would immediately require new
reviewed artifacts after the next repository commit.
