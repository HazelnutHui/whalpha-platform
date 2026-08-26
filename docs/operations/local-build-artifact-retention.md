# Build and Release Artifact Retention

## Purpose

Ignored frontend, private-Snapshot, OCI bundle, and deployed release outputs are reproducible
deployment artifacts, not authoritative data. This policy prevents failed and
superseded candidates from accumulating indefinitely or being mistaken for
active Production state.

Canonical EOD, Identity, Activation, Market Intelligence, and active Dashboard
Snapshot data under `/data/trading-intelligence-platform` are outside this
policy and must never be deleted through local build cleanup.

## Retained set

Keep only:

1. `build/private-dashboard/2026-08-19T083341Z-7ed7fdc21686`, because the
   active Snapshot reader names it as the exact pre-pointer legacy fallback;
2. `build/oci-dashboard/2026-08-19T083341Z-7ed7fdc21686`, as the deliberate
   selectable-Universe rollback bundle;
3. `build/oci-dashboard/2026-08-26T062038Z-895a073769ad`, as the active
   deployed bundle.

The active Snapshot 1.5 release is formally retained under `/data`; a duplicate
`build/private-dashboard` copy is not required. The report validates every
retained or candidate OCI bundle against its own checksum inventory and the
active Snapshot/Market Intelligence lineage.

## OCI retained set

Keep only:

1. `/srv/whalpha/releases/2026-08-26T062038Z-895a073769ad`, selected by
   `/srv/whalpha/current`;
2. `/srv/whalpha/releases/2026-08-19T083341Z-7ed7fdc21686`, as the reviewed
   rollback release.

Remote cleanup requires separate exact path, type, symlink, active-pointer,
service, and rollback verification. It must never infer remote state from a
local bundle name.

## Removal rules

- Remove superseded, failed, or duplicate directories only after resolving
  exact regular, non-symlink targets beneath the two approved build roots.
- Remove `apps/web/dist` after build verification; it is a transient Vite
  output and is rebuilt for every candidate.
- Never select a deletion target through an unresolved environment variable,
  broad parent directory, or unreviewed symlink.
- Never treat a local directory name as evidence of the remote active release.
- Never remove the retained fallback/current set without a new reviewed policy
  update and exact rollback analysis.
- Never remove the active remote target or retained rollback release without a
  new reviewed rollback plan.

## 2026-08-26 cleanup

The context-reconciliation task verified the active `/data` pointers, the
deployed bundle checksum inventory, exact directory types, and absence of
local build staging/partial residue before removing all other ignored build
directories and the transient Vite `dist` output. This cleanup changed no Git
source, canonical data, or active pointer.

The same task then live-verified the OCI current pointer, rollback target,
directory types, and absence of any other symlink or staging/partial residue.
It removed 21 superseded or failed remote release directories. OCI now retains
only the current and rollback releases listed above; Nginx, the Auth Service,
localhost listener, and unauthenticated route boundary passed immediately after
cleanup.
