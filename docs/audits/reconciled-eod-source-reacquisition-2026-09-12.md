# Reconciled EOD Source Reacquisition Audit — 2026-09-12

## Purpose and boundary

Close the Grouped Daily source-package gaps for ADR 0204's rolling
2021-09-13 through 2026-09-11 Reconciled EOD Edition input. The work ran on
the Dell workstation from clean `main` source
`a968827f2a7a06b25ea56f8f0ff81f247452f539`.

The first and final coverage censuses were network-disabled and used four
worker processes. Reacquisition wrote only immutable owner-only source
packages below the approved Dell private state root. It wrote zero canonical
`/data` files and performed no research, analytics, publication, deployment,
activation, scheduler, or Production action.

## Initial sealed coverage

The 2026-09-12 01:23:08 UTC census formally reread all 1,255 XNYS sessions and
completed at 01:31:27 UTC:

| Disposition | Sessions |
| --- | ---: |
| Selected retained original | 948 |
| Missing Grouped Daily package | 305 |
| Invalid Identity-source binding | 2 |
| Conflict | 0 |

- Coverage file SHA-256:
  `f1045098382d42d2ff00a25569d0d309bfd616b075ef31ef94bcc1f24d9a7a9a`
- Logical fingerprint:
  `f8f808ed52d83ab097696b198177cabc564170d17fc0e71581c5b43a5ae9b2e0`
- Missing interval: 2025-06-23 through 2026-09-11, with only exact XNYS
  session dates selected by the sealed artifact.
- The two invalid sessions are 2026-08-13 and 2026-08-19, both with reason
  `identity_source_custody_unavailable`.

## Bounded reacquisition

The 305 missing sessions were fetched in eight ordered invocations of at most
40 sessions. Every package was formally reread immediately after acquisition.

| Result | Count |
| --- | ---: |
| Requested/fetched packages | 305 |
| Provider request attempts | 305 |
| Transient retries | 0 |
| Failed sessions | 0 |
| Reused packages during this run | 0 |

The first package completed at 2026-09-12 01:33:28 UTC and the last at
01:46:11 UTC. Final owner-only custody contains 305 session directories, 610
files, and 381,337,205 bytes. All directories are mode `0700`, all files are
mode `0400`, and symlink and staging-residue counts are zero. Credentials,
provider response bodies, request identifiers, and Authorization values are
not represented in this audit.

## Final sealed coverage

The 01:46:20 UTC post-acquisition census completed at 01:54:45 UTC:

| Disposition | Sessions |
| --- | ---: |
| Selected retained original | 948 |
| Selected later reacquisition | 305 |
| Missing | 0 |
| Invalid Identity-source binding | 2 |
| Conflict | 0 |

- Coverage file SHA-256:
  `e9d330dec6e002a9dadde88b95ad61d2e1280ac7479194962c430d9ba5a2d3cc`
- Logical fingerprint:
  `44a3cefe9a17059ad43c37954ac1e5056e748571e89ac900204e94b1f6fce749`
- Status: `incomplete`

The 305 Grouped Daily gaps are closed. Candidate construction remains blocked
because ADR 0204 currently requires exact same-session Identity source custody
for every session. The two old canonical Identity snapshots are intact, but
their original provider responses were not retained. Later reacquisition is
known to contain genuine provider revisions and therefore cannot be relabeled
as original evidence. The next decision must either define a narrowly typed,
non-silent legacy provenance treatment or choose an exact contiguous research
interval that excludes the gap; it must not manufacture equivalence.

## Authority

This work improves private source custody only. Canonical EOD V1, Historical
Coverage, research admission, performance claims, Candidate, Production, and
the website remain unchanged and unauthorized by this audit.
