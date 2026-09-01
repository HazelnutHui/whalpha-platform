# ADR 0113: Treat degraded user systemd as review-available

## Status

Accepted.

## Context

The installed read-only wake timer correctly rejected its 2026-08-31 trigger
after the repository revision changed. That failed oneshot placed the `hui`
user manager in systemd's `degraded` aggregate state even though the manager,
timer and D-Bus control surface remained available. Candidate review required
exactly `running`, so the failure prevented rendering the repair candidate.

## Decision

Treat `running` and `degraded` as an available user manager for read-only
candidate review. Continue to reject initializing, starting, maintenance,
stopping, offline and unknown states. This changes review prerequisites only;
it does not install units, clear failures, invoke the coordinator, access
credentials, request data or write Production.

## Consequences

- A failed pinned oneshot can no longer deadlock its own exact repair review.
- Degraded does not mean healthy: the failed unit remains visible and must be
  inspected before any separately authorized reinstall/restart.
- Exact revision, clean main, Dell/hui, linger, systemd version, calendar and
  unit-byte checks remain unchanged.
