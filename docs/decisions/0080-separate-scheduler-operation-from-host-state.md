# ADR 0080: Separate Scheduler Operation from Host State

## Status

Accepted

## Date

2026-08-29

## Context

ADR 0079 installed and enabled the read-only user timer. The planner and its
rehearsal still emitted `scheduler_installed=false`, a field originally meant
to prove that a read-only planning call performed no installation. After the
host installation, that name could be misread as a claim about current systemd
state even though the planner never inspects the user manager.

An operation result must not claim host state it did not observe. Conversely,
host installation must not be inferred from a planning result.

## Decision

Rename the plan, scheduled-wake, and rehearsal field to
`scheduler_installation_performed`. It remains fixed at `false` and means only
that the current process neither installed nor changed scheduler units. Remove
the redundant `scheduler_installed` field from the systemd candidate review,
which already reports `installation_performed` and `activation_performed`.

Bump the affected additive/semantic contracts to:

- `daily-eod-scheduler-wake-plan/1.1`;
- `daily-eod-scheduled-wake/1.1`;
- `daily-eod-scheduler-rehearsal/1.1`; and
- `daily-eod-scheduler-systemd-review/1.1`.

The systemd candidate byte contract remains
`daily-eod-scheduler-systemd-candidate/1.0`; its unit semantics did not change.
Current host installation and activation state are established only by
read-only `systemctl --user`, `loginctl`, and journal inspection, then recorded
in the authoritative current context.

## Consequences

- Planner JSON can no longer contradict a separately installed host timer.
- A false operation field proves absence of an installation side effect, not
  absence of an installed unit.
- Historical 1.0 reports and their fingerprints remain valid evidence for
  their original pre-installation boundaries.
- No coordinator, provider, credential, `/data`, publication, deployment, or
  other Production capability is added by this contract correction.

## Alternatives Considered

### Make the planner query systemd

Rejected because it would mix exchange/data planning with host inspection and
make the portable planner environment-dependent.

### Keep both fields and document the difference

Rejected because two always-false fields would preserve the misleading host-
state interpretation without adding evidence.

### Report the installed state as true from code

Rejected because repository code cannot truthfully assert external host state
without inspecting that state at runtime.
