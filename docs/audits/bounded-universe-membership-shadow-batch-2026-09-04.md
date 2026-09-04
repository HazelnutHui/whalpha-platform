# Bounded Universe Membership Shadow Batch Audit — 2026-09-04

## Scope

This audit measures the disconnected, network-disabled optimization accepted
by ADR 0133. All outputs were written below new `/tmp` roots and formally
reread. Canonical `/data`, Production, scheduler, active pointers, publications,
and provider state were not changed.

## Profile finding

The unchanged 2026-09-03 single-session path originally completed in 149.72
seconds with 975,264 KiB peak resident memory. A function-level profile showed
that the path performed 41 EOD partition validations: 20 window inspections,
20 formal history reads, and one current-session read. Identity/Resolver data
were also parsed once by formal snapshot inspection and again for join-index
construction.

The optimized path formally reads the current and available trailing EOD
partitions once, derives the same descriptor from those reads, builds indexes
from the package reconstruction only after all three accepted Identity-family
fingerprints match, and shares one formally read type catalog per batch.

## Exact single-session equivalence

The optimized 2026-09-03 replay completed in 111.18 seconds with 979,308 KiB
peak resident memory, a 38.54-second or 25.7% wall-time reduction with no
material memory increase.

The following evidence remained exact:

| Evidence | Value |
| --- | --- |
| Evaluated stable-ID base | 9,979 |
| Membership rows | 19,958 |
| Logical fingerprint | `c3fe7e7d190abbf0e711a31df52704edaed4efeda06a8d52571c4b45c60d7c02` |
| Parquet SHA-256 | `a20cf85d30b879c5683ba6acff12366881570465dcff5fee066560987d120c0e` |

## Two-session shared-panel proof

The adjacent 2026-09-02 and 2026-09-03 batch read 22 unique EOD partitions,
completed both sessions in 139.71 seconds, and peaked at 1,217,720 KiB. Two
independent optimized runs require 222.47 seconds, so the shared batch saved
82.76 seconds or 37.2%. Relative to two original 149.72-second paths, it saved
159.73 seconds or 53.3%.

An independent 2026-09-02 run completed in 111.29 seconds and exactly matched
the batch:

| Evidence | Value |
| --- | --- |
| Evaluated stable-ID base | 9,980 |
| Membership rows | 19,960 |
| Logical fingerprint | `9a8db13926bf1786a6a93c8bc420551f744b3e1aabdeb549aec5de89a2d431cc` |
| Parquet SHA-256 | `b1113a3a6bd167e6b7ee796dd68595de745b3f3329d1e373eba74cf73014946b` |

## Five-session boundary and newly exposed source gap

The correct adjacent five-session batch covered 2026-08-28, 2026-08-31, and
2026-09-01 through 2026-09-03. It read 25 unique EOD partitions, completed in
195.04 seconds, and peaked at 1,296,388 KiB. Three sessions completed and were
formally reread. The 2026-08-28 and 2026-08-31 packages were rejected before
partition publication because, although custody-valid, they did not exactly
reconstruct the accepted same-day Instrument Master, provider Identity, and
ticker Resolver fingerprints.

This is not canonical corruption. It establishes a narrower evidence rule:
the prior 279/303 count measures retained custody-valid packages, not 279
proven exact-equivalent reconstruction sources. The exact-equivalent package
count remains unverified. A complete equivalence census is required before
planning an all-available shadow run.

The successful 2026-09-01 result contained 19,958 rows over 9,979 stable IDs,
with logical fingerprint
`c6ea0c9d3ebcac9afa8202c9267f49cc56d073af9134652e020c05ad6fb37467`
and Parquet SHA-256
`6c165ed87ee8ff8caecb820db2b1376533238611e65df616af529cecf4262fcc`.
The 2026-09-02 and 2026-09-03 results matched the independent evidence above.

## Controls and next gate

- Batches are limited to one through five adjacent XNYS sessions.
- Explicit session/package mappings are required; duplicate or skipped dates
  fail before EOD reads.
- Shared EOD or output-custody failure stops the batch. A package-specific
  mismatch is recorded for that date and does not contaminate other sessions.
- Execution remains serial and memory-bounded. CPU process parallelism remains
  unproven and is not enabled.
- The next gate is a read-only exact-equivalence census of all 279 retained
  packages, followed by a revised source-gap plan. Efficient execution alone
  does not grant canonical publication or research authority.

Source compilation, 77 expanded focused checks, and all 2,014 backend tests
passed. The full suite emitted only the two unchanged dependency deprecation
warnings.
