# ADR 0096: Resume Persistent Workspace Planning After Proof

## Status

Accepted

## Date

2026-08-30

## Context

ADR 0094 intentionally stopped the daily planner after Identity and canonical
EOD whenever its artifacts used the persistent Dell workspace. At that time,
several writers and formal readers accepted only `/tmp`, and allowing the
planner to reserve a real offline action would have overstated executable
custody.

ADR 0095 introduced one exact shared custody policy and physically proved all
nine analytics directories. The separately authorized continuation then made
one persistent MI 1.3 lineage active, applied Snapshot 1.11 / Dashboard 2.8,
formally reread both the standard and persistent serving bundles with the same
logical fingerprint, deployed that lineage, and passed guest and independent
OCI postflight. The factual condition required by ADR 0094 is therefore
satisfied.

## Decision

Advance the read-only planner to `daily-eod-automation-plan/1.8` and remove
only the unconditional
`persistent_workspace_cli_custody_unreconciled` early stop. Keep the exact
persistent workspace layout validator and every existing stage reader,
session/fingerprint binding, downstream-residue check, and single-next-action
result unchanged.

This revision does not change the executor, coordinator, publication Apply,
deployment capability, scheduler, or host-runtime contracts. A plan continues
to report `publication_authorized=false`, `deployment_authorized=false`,
`scheduler_enabled=false`, zero external requests, and zero Production writes.
Any later execution still requires its existing unchanged plan fingerprint,
durable custody, and separately supplied capability.

## Physical proof

The formally retained 2026-08-27 Phase 1b and Candidate audits were copied into
the exact owner-only prior-session workspace after formal reread. No `/data`
or Production state changed. Two credential-free, socket-guarded Plan 1.8 runs
then reread all 18 current/prior stages for 2026-08-28 and deterministically
returned:

- status `analytics_ready`;
- next action `review_bundle_deployment`;
- reason `serving_bundle_ready_for_deployment_review`;
- plan fingerprint
  `0782f8793a8564b7b17f354eb81e602afe49c1fe8154bcc371e39ebacee51d83`;
- zero external requests and Production writes; and
- no publication, deployment, or scheduler authority.

The focused planner, workspace, pipeline scheduler, cadence, executor, and
coordinator suite passed 119 tests before the real replay.

## Consequences

- Persistent Dell planning now describes the real next stage instead of a
  superseded custody warning.
- A complete session stops at deployment review rather than recalculating or
  implying that deployment should repeat.
- The installed timer remains read-only and is not connected to the
  coordinator by this decision.
- The next weekday validation may exercise the planner against a new missing
  session, but acquisition, canonical Apply, publication, and deployment remain
  separate authorization boundaries.

## Alternatives Considered

### Keep the ADR 0094 stop indefinitely

Rejected because its explicit removal condition has now been physically met;
retaining it would hide valid stage state and force manual path substitution.

### Treat successful planning as scheduler activation

Rejected because path custody and planning correctness do not authorize
provider access, Production writes, publication, deployment, or unattended
execution.
