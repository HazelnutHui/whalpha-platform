# ADR 0078: Render a Non-Installed Read-Only systemd Wake

## Status

Accepted

## Date

2026-08-29

## Context

ADR 0077 proves that one scheduled wake cannot loop through coordinator
transitions, but no host timer candidate yet binds Dell identity, exact source,
system clock, exchange-close timing, or user-manager prerequisites. Installing
a timer before reviewing those facts would mix repository design with host
activation authority.

## Decision

Add `daily-eod-scheduler-systemd-candidate/1.0` and its write-free review
contract. The candidate is a user-level systemd oneshot owned by `hui`; it is
not a root/system service and assumes no sudo authority. It binds the Dell
hostname, user, canonical repository, `main`, exact clean Git revision,
canonical data root, exact planner entrypoint, service/timer names, calendar
expressions, project Python launcher/resolved interpreter, and SHA-256 of both
future unit files.

The service invokes only the ADR 0076 read-only planner. It supplies no fixed
date: the planner CLI uses the current timezone-aware UTC clock when
`--checked-at` is omitted. Before reading canonical EOD it independently
requires Dell/hui, clean `main`, and the exact revision embedded in the unit.
The unit clears inherited Python path/home overrides, fixes its executable
search path and project interpreter, and rechecks the resolved interpreter.
It never passes `--review-enabled-candidate`, loads no host authorization or
credential config, and cannot call the ADR 0077 bridge or coordinator.

The timer proposes two weekday New York times:

- 13:30 for an XNYS early close plus the current 30-minute stabilization
  window; and
- 16:30 for a normal close plus that window.

The planner, not systemd, remains authoritative for sessions, holidays,
early-close truth, oldest missing session, and the exact next-check decision.
`Persistent=true` is proposed, but a user timer requires an active user manager
after logout/reboot. Dell read-only inspection found systemd 255 and a running
user manager, while `hui` linger is currently disabled. The enabled-candidate
review must therefore report a missing prerequisite.

The review only emits canonical JSON and exact unit text. It performs no unit
file write, installation, daemon reload, enablement, start, credential access,
network request, coordinator call, `/data` write, publication, or deployment.
The service proposal also uses a read-only filesystem view, the planner's
socket guard plus an `AF_UNIX` address-family restriction, no new privileges,
and an exact 120-second bound. User-manager runtime rehearsal subsequently
showed that `PrivateNetwork`, `PrivateDevices`, and an explicit empty
capability set are not supported on this Dell user manager; they are excluded
instead of being presented as effective hardening.

## Consequences

- DST-safe normal and early-close wake times are reviewable without relying on
  the Dell host timezone, which remains UTC.
- A later source commit invalidates the candidate until it is regenerated at
  the new clean revision.
- At this candidate-review boundary, `Persistent=true` did not conceal the
  observed `linger=no` prerequisite. Enabling linger or choosing a system-level
  unit remained a separate host decision later resolved by ADR 0079.
- Installing this candidate would still run only read-only planning. Repeated
  retry/transition cadence and composition with the real coordinator remain a
  later separately reviewed boundary.
- A separate installation decision must verify the exact candidate bytes and
  must not infer data, publication, deployment, alert, or scheduler-transition
  authority from this review.

## Alternatives Considered

### Install a system service under `/etc/systemd/system`

Rejected for this candidate because it assumes root provisioning before the
user has chosen the host persistence model.

### Put the full coordinator command in `ExecStart`

Rejected because target-session paths and authorization bindings are dynamic,
and a fixed timer command would bypass the existing exact planning boundary.

### Use one fixed UTC wake time

Rejected because New York daylight-saving changes and XNYS early closes would
either delay normal operation or run before the stabilization window.
