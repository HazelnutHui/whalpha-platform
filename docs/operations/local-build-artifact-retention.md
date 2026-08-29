# Build and Release Artifact Retention

## Purpose

Ignored frontend, private-Snapshot, OCI bundle, and deployed release outputs are reproducible
deployment artifacts, not authoritative data. This policy prevents failed and
superseded candidates from accumulating indefinitely or being mistaken for
active Production state.

Canonical EOD, Identity, Activation, Market Intelligence, and active Dashboard
Snapshot data under `/data/trading-intelligence-platform` are outside this
policy and must never be deleted through local build cleanup.

## Current local retained set

The 2026-08-29 offline reconciliation found eight checksum-valid historical
deployment bundles. They occupy less than 110 MiB in total, so deleting a
reviewed rollback artifact provides no meaningful capacity benefit. Retain:

1. `build/private-dashboard/2026-08-19T083341Z-7ed7fdc21686`, because the
   active Snapshot reader names it as the exact pre-pointer legacy fallback;
2. `build/oci-dashboard/2026-08-19T083341Z-7ed7fdc21686`, as the deliberate
   selectable-Universe rollback bundle;
3. `build/oci-dashboard/2026-08-26T053233Z-6c60502e4473`, as the last retained
   ordinary-fresh 2026-08-26 baseline;
4. `build/oci-dashboard/2026-08-26T094339Z-f9711d5403f6`,
   `build/oci-dashboard/2026-08-26T103119Z-f344a589a8c9`, and
   `build/oci-dashboard/2026-08-26T151600Z-1f3eb5512eb0`, as reviewed product
   progression and rollback evidence;
5. `build/oci-dashboard/2026-08-28T132100Z-eeccc22`, as the first Snapshot 1.9 /
   Dashboard 2.6 stale-review release;
6. `build/oci-dashboard/2026-08-28T162136Z-2737f81`, as the immediate prior
   deployed UI release; and
7. `build/oci-dashboard/2026-08-29T080928Z-785ab49dfedd`, as the active
   ordinary-fresh release.

The active Snapshot 1.9 release is formally retained under `/data`; a duplicate
`build/private-dashboard` copy is not required. Historical bundles validate
against their own checksum inventories, while only the current active bundle
is expected to match the active Snapshot/Market Intelligence lineage.

## OCI retained set

The 2026-08-29 deployment verified
`/srv/whalpha/releases/2026-08-29T080928Z-785ab49dfedd` as the active release
selected by `/srv/whalpha/current`. This offline documentation reconciliation
did not reconnect to OCI and therefore does not claim a current complete list
of prior remote releases. Reread the exact remote inventory and rollback roles
before proposing any remote deletion.

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
It removed 21 superseded or failed remote release directories. At that point,
OCI retained only the then-current and rollback releases; Nginx, the Auth
Service, localhost listener, and unauthenticated route boundary passed
immediately after cleanup. The later deployment temporarily expanded the
retained set as recorded above.

After deploying `2026-08-26T103119Z-f344a589a8c9`, the exact superseded
`2026-08-26T062038Z-895a073769ad` local bundle and remote release were verified
as regular directories distinct from the active pointer and removed. Current,
immediate rollback, and deliberate older fallback remained locally and
remotely. The later Candidate deployment added
`2026-08-26T151600Z-1f3eb5512eb0` as current and retained the three reviewed
prior/fallback releases listed above; there is no staging/partial residue.
