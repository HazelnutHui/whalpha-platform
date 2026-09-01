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

The 2026-09-01 read-only inventory found one legacy private-Dashboard fallback
and 14 historical directories beneath `build/oci-dashboard`. None is the
current remote release `2026-09-01T123500Z-579a26759a9e`; the current immutable
Snapshot is retained under `/data`, and the source bundle was built and
formally reread in governed `/tmp` custody before deployment. A temporary
bundle is reproducible deployment evidence, not a durable rollback authority.

Retain the legacy fallback
`build/private-dashboard/2026-08-19T083341Z-7ed7fdc21686`. Do not delete any of
the 14 historical OCI directories until a separate exact checksum and rollback-
role audit reclassifies them. Their names are:

- `2026-08-19T083341Z-7ed7fdc21686`;
- `2026-08-26T053233Z-6c60502e4473`;
- `2026-08-26T094339Z-f9711d5403f6`;
- `2026-08-26T103119Z-f344a589a8c9`;
- `2026-08-26T151600Z-1f3eb5512eb0`;
- `2026-08-28T132100Z-eeccc22`;
- `2026-08-28T140332Z-f483d6999a3e`;
- `2026-08-28T141747Z-83f9b629279c`;
- `2026-08-28T162136Z-2737f81`;
- `2026-08-29T080928Z-785ab49dfedd`;
- `2026-08-29T133847Z-1490b37f25b3`;
- `2026-08-30T082200Z-6a8a37e79970`;
- `2026-08-30T085601Z-6c732e9cd602`; and
- `2026-08-30T092455Z-1894b9c9b95e`.

Historical bundles must validate against their own checksum inventories. Do
not assume any historical local directory still exists remotely or is a valid
rollback solely from its name.

## OCI retained set

The 2026-09-01 independent read-only OCI inspection verified
`/srv/whalpha/releases/2026-09-01T123500Z-579a26759a9e` as the active release
selected by `/srv/whalpha/current`. It also verified the exact source revision,
manifest/checksum fingerprints, service/listener health, equal guest and
credential route policy, a temporary guest Session, and zero staging/failed
residue. The report did not enumerate a complete list of prior remote releases,
so reread the exact remote inventory and rollback roles before proposing any
remote deletion.

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
