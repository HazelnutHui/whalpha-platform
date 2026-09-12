# Reconciled EOD Source Reacquisition Audit — 2026-09-12

## Purpose and boundary

Close the Grouped Daily source-package gaps for ADR 0204's rolling
2021-09-13 through 2026-09-11 Reconciled EOD Edition input. The work ran on
the Dell workstation from clean `main` source
`a968827f2a7a06b25ea56f8f0ff81f247452f539`, with the independent-gap
reporting correction later bound to
`ef19dd32a87afbe319f8e0db143d0603faa3439c`.

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
- The two invalid sessions are 2026-08-13 and 2026-08-19. The original census
  returned after finding absent Identity source custody and therefore did not
  also report that both dates lacked a Grouped Daily package. This was a
  diagnostic/reporting defect, not canonical data corruption.

## Bounded reacquisition

The 305 sessions explicitly classified as missing were fetched in eight
ordered invocations of at most 40 sessions. Every package was formally reread
immediately after acquisition.

| Result | Count |
| --- | ---: |
| Requested/fetched packages | 305 |
| Provider request attempts | 305 |
| Transient retries | 0 |
| Failed sessions | 0 |
| Reused packages during this run | 0 |

After the reporting correction, a second bounded invocation requested and
fetched the remaining two independently missing packages. Across both phases,
the total is 307 requests, 307 fetched packages, zero retries, and zero
failures.

The first package completed at 2026-09-12 01:33:28 UTC and the 305th at
01:46:11 UTC. Source Coverage was then corrected to accumulate independent
price and Identity reasons. The reacquisition runner was widened only for the
exact combined quarantine
`grouped_daily_source_package_missing` plus
`identity_source_custody_unavailable`; it still grants no candidate-build
readiness. That typed path acquired the two independently missing price
packages for 2026-08-13 and 2026-08-19 with two requests, zero retries, and
zero failures.

Final owner-only custody contains 307 session directories, 614 files, and
384,055,489 bytes. All directories are mode `0700`, all files are mode `0400`,
and symlink and staging-residue counts are zero. Credentials, provider response
bodies, request identifiers, and Authorization values are not represented in
this audit.

## Final sealed coverage

The final corrected census began at 02:18:35 UTC and completed at 02:27:10 UTC:

| Disposition | Sessions |
| --- | ---: |
| Selected retained original | 948 |
| Selected later reacquisition | 305 |
| Missing | 0 |
| Invalid Identity-source binding | 2 |
| Conflict | 0 |

- Coverage file SHA-256:
  `0756c715760aabf1c2b91789d4bb9c7694827bd21afbbac3d3ffe511ff27e439`
- Logical fingerprint:
  `6684fd3ba25edcb0add5bda3b4172ed9df8ae8f9a581fb7277dd11b67fd40987`
- Status: `incomplete`

All 307 discovered Grouped Daily gaps are closed. The final artifact observes
one later-reacquired price candidate for each of the two invalid dates and now
reports only `identity_source_custody_unavailable` for them. The two old
canonical Identity snapshots are intact, but their original provider responses
were not retained.

An isolated, write-free reconstruction diagnostic tested the later Identity
responses without relabeling them as originals. Both dates passed price quality
gates and had zero economic-value changes. The 2026-08-13 result nevertheless
omitted one canonical business key, and the 2026-08-19 result omitted five.
ADR 0204's no-removal gate therefore remains unchanged. ADR 0207 selects the
maximal preceding contiguous interval, 1,234 sessions from 2021-09-13 through
2026-08-12, for the first corrected-edition candidate; it contains 947 retained
original and 287 visibly later-reacquired price sources with no source gap.

## Authority

This work improves private source custody and selects a bounded candidate-build
route only. Canonical EOD V1, Historical Coverage, research admission,
performance claims, Candidate, Production, and the website remain unchanged
and unauthorized by this audit.
