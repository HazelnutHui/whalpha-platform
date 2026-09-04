# ADR 0139: Apply Historical Identity Source Custody Atomically

- Status: Accepted
- Date: 2026-09-04

## Context

ADR 0138 produced one complete no-write plan for 279 normalized historical
Identity source partitions. The plan binds 558 immutable candidate files,
their absent canonical targets, and the complete `/data` pre-state. A bulk
Apply can nevertheless stop after one or more partition renames. Treating that
exception as a clean failure, deleting completed targets, or replaying every
target would weaken immutable custody and could overwrite valid evidence.

## Decision

Implement an explicitly invoked, plan-pinned Apply boundary with these rules:

- require the exact plan file SHA-256, plan logical fingerprint, expected
  canonical pre-state fingerprint, operation, provider, session/file counts,
  and approved Dell data root;
- acquire one Dell-local advisory publication lock and repeat all custody and
  compare-and-swap checks while holding it;
- prohibit network access inside publication;
- publish one session partition at a time through a same-parent staging
  directory, copy exactly its manifest and Parquet file, set canonical modes,
  fsync files and directories, verify hashes, and atomically rename;
- never replace, merge, delete, or roll back an existing completed partition;
- after all partitions exist, formally parse and validate every canonical
  partition against its manifest and the plan before reporting success.

Ordinary Apply requires the complete `/data` inventory to equal the plan's
pre-state and every target to be absent. Recovery is a separately selected
`verify_then_complete` mode. It accepts each planned target only when it is
either absent or an exact completed two-file partition. It recomputes the
canonical inventory while excluding the planned target directories and
requires that base to equal the original pre-state. It then skips exact
completed partitions and publishes only absent ones.

An incomplete target, changed byte, wrong mode, unexpected file, symlink,
staging residue, plan drift, source drift, or unrelated canonical inventory
change blocks recovery. Recovery does not clean or delete ambiguous state.

The repository implementation and `/tmp` tests do not execute the real
279-partition `/data` transition. A real invocation remains a separate
reviewed action using the exact plan SHA and expected pre-state. Successful
source custody still does not authorize Universe Membership, Historical
Coverage, research performance, publication, deployment, or scheduling.

## Consequences

- A process interruption can be resumed without overwriting already completed
  immutable partitions.
- A thrown exception never falsely proves zero writes; actual target state is
  the recovery authority.
- Planned targets are excluded only for recovery base comparison. Any
  unplanned file or directory content remains visible to inventory drift.
- The final proof is typed canonical reread, not file-count success.
- No destructive rollback path exists.

## Alternatives Considered

### Copy the full tree and treat any exception as failure

Rejected because an exception after an atomic directory rename may leave valid
canonical data even though the caller did not receive success.

### Delete completed targets after interruption

Rejected because completed canonical partitions are immutable evidence and
deletion would make recovery destructive.

### Overwrite every target on retry

Rejected because replay must not replace or silently normalize changed
canonical state.

### Mark success from hashes without parsing Parquet

Rejected because physical equality alone does not prove the canonical reader
can interpret the governed schema and record fingerprints.
