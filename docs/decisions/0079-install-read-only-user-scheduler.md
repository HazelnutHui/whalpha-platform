# ADR 0079: Install the Read-Only User Scheduler

## Status

Accepted

## Date

2026-08-29

## Context

ADR 0078 produced an exact but non-installed user-systemd candidate and found
that `hui` linger was disabled. The user explicitly selected the recommended
user-level persistence model and authorized enabling linger plus installation
of the read-only timer. This authority does not include coordinator execution,
provider access, `/data` writes, publication, or deployment.

## Decision

Enable linger for `hui` and install the exact owner-controlled service/timer
under the user systemd manager. Unit files remain mode `0600`; the timer is
enabled with the two ADR 0078 New York calendar expressions and
`Persistent=true`.

The first controlled service start exposed a Dell user-manager limitation:
explicit capability bounding failed with status `218/CAPABILITIES`, while
`PrivateNetwork` was unsupported. `PrivateDevices` also implies capability
changes and produced the same failure. The timer was stopped during diagnosis.
Remove those three unsupported directives from both the candidate template and
installed service rather than claiming ineffective sandboxing.

The compatible unit retains:

- exact Dell/hui, clean `main`, Git revision, and Python bindings;
- cleared Python environment overrides and a fixed executable search path;
- the planner's in-process socket guard plus systemd `AF_UNIX` restriction;
- `NoNewPrivileges`, read-only system/home views, `LockPersonality`,
  `RestrictSUIDSGID`, owner-only unit custody, and a 120-second timeout; and
- a read-only planner command with no enabled candidate or coordinator port.

A controlled manual systemd start then completed successfully in about three
seconds. It reported canonical EOD current through 2026-08-28, next target
2026-08-31, zero coordinator invocation, and zero credential, external request,
filesystem write, or Production write.

## Consequences

- The `hui` user manager can now persist after logout and restart after reboot.
- The installed timer performs only read-only planning. Full daily data and
  analytics automation is still not enabled.
- Every later repository commit invalidates the pinned service revision. The
  timer must remain stopped or its exact unit must be regenerated and reread
  before it is restarted at a new revision.
- The next operational checkpoint is one real calendar-triggered read-only
  wake, including its journal result and next-trigger state.
- Connecting ADR 0077 to the installed timer remains a separate architecture,
  authorization, and controlled-rehearsal decision.

## Alternatives Considered

### Keep unsupported hardening directives and ignore the failure

Rejected because the service would never run and the unit would falsely imply
protections the host cannot apply.

### Replace the user timer with a root system service

Rejected because the user-level service works after the compatible hardening
set and avoids unnecessary privilege expansion.

### Connect the coordinator during installation

Rejected because timer persistence, read-only host execution, and real daily
transition authority require separate evidence and rollback boundaries.
