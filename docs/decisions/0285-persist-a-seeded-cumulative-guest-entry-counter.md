# ADR 0285: Persist a Seeded Cumulative Guest-Entry Counter

## Status

Accepted

## Date

2026-09-15

## Context

WH Alpha needs one low-noise public activity indicator at the bottom of the
protected workspace. The requested metric is a cumulative guest-entry count,
not daily unique people, IP addresses, page views, authenticated owner visits,
or a research/product metric. It must survive Auth Service restarts and static
release deployment without adding a database or affecting page responsiveness.

The owner-selected display baseline is 1,050. That baseline is configuration,
not observed historical traffic, so it remains explicit in internal code,
tests, and documentation even though the compact public line does not explain
it.

## Decision

1. The displayed value is `1,050 + recorded successful guest entries`.
2. A guest entry is recorded only when a valid guest Session first loads the
   protected React workspace and calls the same-origin visit endpoint. Creating
   a Session alone, deployment curl checks, page refreshes, and credential
   Sessions do not increment the counter.
3. Guest and credential Sessions retain identical product capability. Entry
   source exists only to decide whether this operational counter increments.
4. The localhost-only Auth Service owns one small, versioned JSON state file in
   a systemd-managed state directory. Writes are atomic, owner-restricted, and
   fail closed; the static bundle does not contain mutable counter state.
5. The public projection exposes only the cumulative integer and its truthful
   label, `Cumulative guest entries` / `累计游客进入` / `Entradas acumuladas de
   invitados`. It does not call the value unique people or verified historical
   traffic.
6. The endpoint accepts only a valid Session and same-origin POST. Repeated
   calls from the same Session return the current value without incrementing.
7. This feature records no IP address, user agent, cross-day identifier,
   credential, or browsing path, and adds no third-party analytics service.

## Consequences

The feature costs one very small same-origin request per workspace load and one
atomic file update per newly counted guest Session. It cannot estimate unique
people or audience quality. A malicious visitor can still create multiple
guest Sessions within existing rate limits, so the number is a simple product
activity counter rather than an audited analytics measure.

## Rejected alternatives

- count every page refresh;
- retain raw IP addresses or browser fingerprints;
- call the seeded value unique visitors;
- store mutable state inside an immutable release directory;
- add a database, external analytics vendor, or role-dependent product access.
