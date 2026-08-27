# ADR 0040: Custody One Daily Alert Delivery Attempt

## Status

Accepted

## Date

2026-08-27

## Context

ADR 0039 supplies a stable alert intent and deduplication key but deliberately
does not persist or deliver it. A future email or other transport may accept a
message and then lose the process before returning. Blindly retrying that
ambiguous attempt could repeatedly notify the user; recording success before
the transport returns could instead lose the alert while falsely claiming
delivery.

Alert events also cannot be inserted into the daily data-transition journal:
doing so would interfere with its rule that the last unresolved start event
identifies acquisition, Apply, or calculation recovery.

## Decision

Add `daily-eod-alert-delivery-custody/1.0` with a separate immutable alert
journal. The alert root must be pre-provisioned, owner-only `0700`, outside the
repository, canonical `/data`, and daily transition run root. Custody creates
only its owner-only global lock and one directory per formal deduplication key.

One explicit invocation:

1. formally validates the complete ADR 0039 intent;
2. takes a non-blocking global alert lock;
3. rereads the exact per-key canonical hash chain;
4. appends owner-read-only `delivery_started` before calling a transport;
5. passes the exact deduplication key as the transport idempotency key; and
6. appends either `delivery_delivered` or `delivery_failed` only after bounded
   formal evidence returns.

A delivered result requires exactly one external request and a hashed delivery
reference; raw provider message identifiers are not retained. A known failure
may report zero or one request. Both results record zero Production data
writes. Invalid evidence or an exception after `delivery_started` leaves the
outcome deliberately unresolved.

The same delivered intent rereads as `already_delivered` without calling the
transport. A prior known failure or unresolved start blocks automatic retry and
requires operator review. This is at-most-once custody: preventing duplicate
alerts takes precedence over guessing that an ambiguous attempt failed.

No concrete email/notification adapter, external channel config, credential,
real alert root, or delivery is created by this decision.

## Consequences

- Concurrent invocations cannot send the same or different alert through this
  custody boundary simultaneously.
- Process interruption cannot silently trigger an automatic duplicate send.
- Delivery claims are supported by immutable terminal evidence rather than
  process exit alone.
- A transport with provider-side idempotency can later strengthen the same
  key; transport-specific status lookup and recovery remain separate.
- Known and ambiguous failures currently stop instead of retrying. Any retry
  policy requires a new reviewed decision with channel-specific evidence.

## Alternatives Considered

### Reuse the daily data-transition journal

Rejected because unrelated alert events would break unresolved action-family
detection and mix notification custody with data authority.

### Retry whenever no delivered terminal exists

Rejected because the transport may have accepted the message before process
interruption.

### Record delivery before calling the transport

Rejected because it would create a false delivered state when the request was
never made or accepted.
