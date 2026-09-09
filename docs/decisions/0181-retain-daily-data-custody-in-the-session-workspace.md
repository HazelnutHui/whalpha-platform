# ADR 0181: Retain Daily Data Custody in the Session Workspace

## Status

Accepted

## Date

2026-09-09

## Context

The persistent daily workspace already assigns exact per-session paths for the
provider acquisition package and canonical Apply plan. The provider, custody,
coordinator, and standing-authorization layers nevertheless continued to
require direct `/tmp` paths. A reboot could therefore preserve the journal and
offline analytics while losing the package/plan evidence needed to resume the
data transition safely.

The change must not turn the workspace into a general writable directory,
relax session binding, or imply authority to request data or write canonical
state.

## Decision

Daily Identity and EOD data custody accepts exactly two modes:

- legacy temporary custody, retained for historical and controlled one-shot
  compatibility; or
- the exact same-session persistent pair
  `acquisition-package` and `canonical-apply-plan.json` below an owner-only
  `daily-eod/sessions/session_date=YYYY-MM-DD` directory.

Persistent package and plan paths must have their governed names, share one
session directory, match the requested session, remain outside Git, `/tmp`,
and `/data`, and have an owner-controlled `0700` workspace/session chain.
Temporary and persistent paths cannot be mixed. Hidden names, symlink
components, missing parents, changed custody, cross-session pairs, and
arbitrary persistent names fail closed.

The canonical plan's prepared files remain below its exact derived
`canonical-apply-plan.artifacts` directory. New persistent plans may reference
only regular non-symlink files below that directory. Legacy temporary plans
retain their existing broader `/tmp` reread behavior so historical plans that
were copied or renamed remain recoverable.

The same path policy is enforced by fetch/plan construction, normalized
same-day Identity source custody, acquisition reservation and operator review,
canonical Apply custody, the coordinator, authorized capability adapters, and
standing-authorization requests. Existing manifests, hashes, CAS bindings,
quality gates, immutable journal events, one-transition limits, and no-replay
recovery rules are unchanged.

This is repository capability only. It performs no provider request, canonical
Apply, publication, deployment, timer change, credential access, or runtime
artifact migration.

## Consequences

- A future live data transition can retain the package and Apply plan beside
  its exact session journal and resume after a process restart.
- Legacy `/tmp` evidence remains readable without weakening new persistent
  artifact containment.
- The activated runtime workspace is now structurally usable for data custody,
  but no live package/plan has yet proved that path end to end.
- Unattended daily publication remains incomplete; this decision supplies
  durable inputs, not scheduler authority.

## Alternatives Considered

### Keep data packages only in `/tmp`

Rejected because the supposedly persistent runtime would still lose the first
two data-transition artifacts across reboot or ordinary temporary cleanup.

### Accept arbitrary files below the persistent workspace

Rejected because it would weaken role, session, and recovery identity and make
cross-session reuse difficult to detect.

### Migrate or delete legacy temporary evidence now

Rejected because migration is unnecessary for forward operation and would add
destructive scope without improving the new-session boundary.
