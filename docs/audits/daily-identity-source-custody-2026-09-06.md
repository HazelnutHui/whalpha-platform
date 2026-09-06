# 2026-09-06 Daily Identity Source Custody Audit

## Scope

Close the routine 2026-09-04 normalized Identity source-observation gap and
prevent recurrence without changing completed Identity, EOD, Universe,
analytics, Snapshot, Production, deployment, or scheduler state.

## Implementation evidence

- Source commit: `aa662ec93fd0823ac958ef1fe7acd5232308b96f`.
- ADR 0150 introduces direct daily Source Custody 1.1 and same-day Identity
  Plan 1.1 while preserving historical Source Custody 1.0 and daily Plan 1.0
  readers.
- New Identity plans contain five ordered targets and nine files. Normalized
  source is fourth and the logical Identity completion marker remains last.
- The source-only repair port has no fetch mode, requires exact `current_v1`
  reconstruction, binds a whole-`/data` pre-state, and rejects an existing or
  changed target outside explicit recovery.
- Full backend regression: 2,091 passed with two existing dependency warnings.

## Exact 2026-09-04 plan

| Evidence | Value |
| --- | --- |
| Approval-plan file SHA-256 | `c7419c32d70350e4b96ef15292c405536c4f78df1a17d5565bd8566e7efd6d12` |
| Plan logical fingerprint | `609f77697786516c961c5cb193014a02a39a331ff59ff19d78283fc9efef1c28` |
| Bound pre-state fingerprint | `81b2eaaa15efb82c27b6adbeeb3dc3861606f0359d3db1157e10fac37fd03056` |
| Provider source rows / pages | 13,155 / 14 |
| Planned files / bytes | 2 / 998,251 |
| Source content fingerprint | `c3813eef36d1905d50b5b69f36a70e6e519b6ebe7400c25cb9dd015844d6ef52` |
| Source-custody fingerprint | `0733e19a92bbece357ff633b06f02414331e2394329b08706151e34005efff7b` |
| Bound Identity fingerprint | `5eed9166d609cea7693aed324908427f113ab72c221921690bcbdc29f71727f7` |

Planning made zero external requests and zero `/data` writes. Apply revalidated
the exact package, plan hashes, absent target, and inventory pre-state under the
shared publication lock with network access prohibited.

## Postflight

- Source Custody `historical-identity-source-custody/1.1` formally reread
  13,155 rows and 14 source artifacts.
- Manifest SHA-256:
  `6160f40d5835875ce0087bf5cf49468cb5295ee775dd0e20326ef8fc8122e9dc`.
- Parquet SHA-256:
  `6b626707c26d61f6f947372d05054396b5c44205730286ba6ae8981cb2b7809d`.
- Instrument Master, Provider Identity, and Resolver reconstruction all match
  their accepted canonical fingerprints.
- Re-running the same approval in verify-then-complete mode left both target
  files' hashes, sizes, modes, and modification times unchanged.
- Canonical source inventory is 302 partitions / 3,700,330 rows / 3,858 source
  artifacts. Missing EOD-aligned source dates are exactly 2026-08-13 and
  2026-08-19; both remain provider-revised and explicitly unbound.
- Whole `/data`: 4,055 files / 2,008,560,616 bytes, fingerprint
  `a49348fc48219771d96ddc8bafed4fc3d5b32774ac61e45f102eef4fc0bb4f56`,
  zero symlinks, and zero publication residue.
- Current-context status remains `data_blocked`, with strategy-development
  readiness and performance authority both false.

## Boundary

The new source is knowledge-time eligible only at its actual observation time.
It is not evidence that the provider record was known at the 2026-09-04 close.
No Membership or Historical Coverage partition was produced, and the existing
301-session disconnected Membership evidence was not relabelled as 302-session
evidence by the source Apply.

## Subsequent disconnected Membership proof

The first 2026-09-04 V3 attempt failed before output publication because its
success path still read the historical-only profile-binding field. The common
binding accessor was applied to that path and a focused 20-test regression
passed. The corrected run then produced:

| Evidence | Value |
| --- | --- |
| Evaluated Instrument base | 9,982 |
| Membership decisions | 19,964 |
| Primary included / excluded / quarantined | 1,680 / 8,242 / 60 |
| Secondary included / excluded / quarantined | 1,796 / 8,113 / 73 |
| Shared EOD partitions read | 21 |
| Logical fingerprint | `ea95ca155b1666392dc2a596d4ffa97c9edc9b4313501ed253f59419ad132130` |
| Physical SHA-256 | `94411a02fff000eb2f6ea2288964ce22097cc4539433000ea665e0a9dd847532` |
| External requests / canonical writes | 0 / 0 |

Physical audit found the newly created direct `/tmp` output root at `0775`.
No symlink, residue, external request, or canonical write occurred, but the
mode was weaker than the established owner-only custody standard. Batch path
validation now atomically creates an absent root as owner-owned `0700`,
requires that exact mode for reuse, and rejects symlinked or group-writable
roots. The existing exact root was tightened to `0700`; a full rerun returned
`already_present` with all tree metadata unchanged. Its two files total
461,208 bytes.

Combining the prior 301-session evidence with this separately retained session
yields 302 available-source sessions and 5,611,048 decisions. This is still
retrospective, disconnected mechanics. It does not create canonical Membership
or Historical Coverage authority. Final full backend regression remained
2,091 passed with the same two dependency warnings.
