# ADR 0094: Block Unreconciled Persistent Workspace Execution

## Status

Accepted

## Date

2026-08-30

## Context

The pipeline-aware scheduler derives durable per-session paths outside `/tmp`,
`/data`, and the repository. Several pre-existing audit and approval tools
still accept or formally reread only `/tmp` paths. Read-only planning and
mocked runners verified the layout shape and orchestration, but did not prove
that the real CLIs could write and reread that layout.

## Decision

Automation Plan 1.7 fails closed after same-day Identity and canonical EOD are
verified whenever analytics paths use the persistent workspace. It returns
`persistent_workspace_cli_custody_unreconciled` and no executable offline
action. Direct-child `/tmp` one-shot workflows remain supported.

The block may be removed only after calculation, audit reader, MI/Snapshot
approval, and bundle paths share one exact owner-controlled, non-symlink
persistent-session policy and a real multi-stage CLI rehearsal passes.
Coordinator 1.14 carries the new planner boundary.

## Consequences

- The read-only installed timer cannot invoke an unproven path.
- Current reviewed `/tmp` development remains available.
- Persistent automation is visibly incomplete rather than failing inside an
  audit writer.
- No filesystem provisioning, `/data` write, network call, publication,
  deployment, or scheduler capability is added.

## Alternatives Considered

### Let each real action fail independently

Rejected because the incompatibility is known and should be reported before
durable action reservation.

### Loosen every `/tmp` check without a shared custody contract

Rejected because broad path acceptance would weaken safety and still would not
prove atomic creation, formal reread, or recovery behavior.
