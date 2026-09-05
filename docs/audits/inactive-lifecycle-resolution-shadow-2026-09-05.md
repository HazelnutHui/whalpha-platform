# Inactive Lifecycle Resolution Shadow Audit — 2026-09-05

## Scope and boundary

ADR 0148 introduces a disconnected resolution shadow between the completed
inactive-provider packages and any future canonical lifecycle dataset. It
normalizes every source occurrence into one Parquet row and writes exactly one
resolution decision for that occurrence. Ticker and CIK never create positive
identity; the only accepted identity priority is share-class FIGI followed by
composite FIGI.

The shadow remains owner-only below `/tmp`, is
`outcome_reconciliation_only`, and has no canonical Apply path. A
`review_candidate` is not a confirmed delisting or terminal outcome. Last
tradable session, terminal reason, successor, consideration, and historical
source-availability time remain unverified.

## Implementation and regression evidence

The implementation is bound to clean-main revision
`62be872aa8c5a8518803204c224cc29312078fa1`. It rejects unreviewed source
fields, malformed row types, symlinks, unsafe permissions, unexpected files,
schema drift, physical or logical hash drift, duplicate occurrence keys, and
any non-one-to-one source/decision relation. Writes use an owner-only staging
directory followed by atomic rename; completed partitions are immutable and
exactly reusable.

All 2,088 backend tests passed in 154.86 seconds. The two warnings are the
existing Python `crypt` and Starlette/httpx deprecation notices. Dependency
inspection found no broken requirements. Focused tests cover unique stable
identity, missing identity, stable-key collision, absent canonical identity,
future/malformed lifecycle dates, temporal contradiction, ticker conflict,
immutable reuse, tamper refusal, and contract gate enforcement.

## Real dual-anchor result

Both builds used the source-of-truth Dell repository and formally reread every
canonical Instrument logical snapshot no later than the relevant anchor.

| Evidence | 2026-07-16 | 2026-09-03 |
| --- | ---: | ---: |
| Source / decision rows | 23,260 / 23,260 | 23,469 / 23,469 |
| Canonical history sessions | 268 | 303 |
| Canonical Instrument row occurrences | 2,468,052 | 2,815,421 |
| Unique canonical instruments | 10,593 | 10,802 |
| Review candidates | 471 | 547 |
| Quarantined | 22,789 | 22,922 |
| Resolved identity | 1,156 | 1,245 |
| Ambiguous identity | 1,179 | 1,222 |
| Unresolved identity | 20,925 | 21,002 |
| Missing stable identity | 17,474 | 17,536 |
| Stable identity absent from canonical history | 3,451 | 3,466 |
| Stable-key collision | 1,179 | 1,222 |
| Canonical observation after claimed date | 370 | 382 |
| Ticker conflict after stable-ID match | 507 | 496 |

The missing-date count is 506 at each anchor across the full source. Reason
counts overlap and therefore must not be summed as mutually exclusive
populations.

The exact multiset comparison reports 262 later-anchor additions and 53
earlier rows absent or revised, for net growth of 209. All 262 additions carry
a `delisted_utc` date from 2026-07-17 through 2026-09-03. Of those additions,
76 are review candidates and 186 are quarantined. None of the 53 removed rows
was a review candidate, and no shared exact source row changes disposition.

| Anchor | Manifest SHA-256 | Logical fingerprint |
| --- | --- | --- |
| 2026-07-16 | `e73b9e124237ec853f0d5f7f4f3c9afc9c908ae83e5eb7d26be6aba7aa5b2a75` | `117eaaa231e99ec417a1df7299bf49fed36785d223c91f501ef5a982b38a633c` |
| 2026-09-03 | `e639bf985652f7ad44ededc81fc72f3a7f60efc737dc3c3af7afb9b3845cfe72` | `95e40f197a0f4a15d694bbcaa02ba52391bd7d7b1a724f72adc690b15e82f539` |

The temporary result contains six immutable files / 8,892,156 bytes, with
inventory fingerprint
`f8bb5e1fe8ec7cffc32586b26f202e7f79f2c4771c84a3203456a65c0405bc10`.
All directories are mode `0700`, all files are mode `0400`, and symlink,
staging, and partial residue counts are zero.

## Canonical and Production invariants

The network-prohibited current-context report after both builds still reports
3,958 `/data` files / 1,877,724,006 bytes, inventory fingerprint
`12b35440e876f8f61fa0bccef8cc06b4c1721c0dc751ebdaa6c572c2df166345`,
zero symlinks, and zero publication residue. EOD, Identity, Activation, Market
Intelligence, Snapshot, OCI release, scheduler, and website state did not
change. External requests, canonical writes, analytics executions,
publications, and deployments are all zero.

## Consequence

The inactive source is now losslessly normalized and conservatively resolved,
so ticker-only joins and unsupported terminal facts are no longer tempting
shortcuts. Research readiness remains `data_blocked`. Before canonical
lifecycle or performance work, review candidates still require an explicit
corroboration/source-availability design, while corporate actions, adjustment,
cost, chronological evaluation, and sealed holdout families remain incomplete.

The serial formal input scan took roughly seven minutes for 303 sessions and
six minutes for 268 sessions while using about one CPU core. This is acceptable
for the one-time evidence build but is a measured optimization candidate:
independent snapshot verification may be parallelized on Dell only after exact
serial/parallel output equivalence is proven.
