# Historical Identity Package Equivalence Census — 2026-09-04

## Purpose

Determine how many retained, custody-valid Identity reference packages can
reproduce every accepted same-day Identity family exactly before broad
historical Universe Membership reconstruction. Package presence and package
custody were not treated as reconstruction equivalence.

## Boundary

- Dell source root: canonical EOD session index and same-day Identity
  snapshots under the formal data root.
- Retained source scope: 12 explicit, non-overlapping package roots below
  `/tmp`; no unrestricted temporary-directory scan.
- Execution: network disabled, four local worker processes, one atomic
  owner-only report below `/tmp`.
- Prohibited and unchanged: provider access, credentials, `/data` writes,
  Historical Coverage, membership publication, analytics, Production,
  scheduler, formulas, parameters, and Universes.

The three-session serial sample classified 2026-07-17 as missing,
2026-08-31 as mismatched, and 2026-09-03 as exact. The two-worker sample
completed in 15.99 seconds versus 26.09 seconds serially. After removing only
the declared `worker_count` execution field, their reports were byte-identical
with comparison SHA-256
`0d40e940aff867d4852d7c99cff116715fd8f25177b6b006d85a4a2f3ebd6ace`.

## Full census result

The full `full_canonical_index` run completed all 303 sessions in 12 minutes
25.56 seconds at 399% aggregate CPU. `/usr/bin/time` reported 293,388 KiB
maximum resident set size; this value is not represented as a summed
four-process peak.

| Classification | Sessions |
| --- | ---: |
| `exact_equivalent` | 58 |
| `identity_snapshot_mismatch` | 221 |
| `missing_source` | 24 |
| `package_custody_failed` | 0 |
| `duplicate_source_review_required` | 0 |
| `canonical_identity_unavailable` | 0 |
| Total | 303 |

All 279 discovered Identity packages passed custody. There were zero
unroutable manifests, zero sources outside the canonical index, and zero
duplicate-session sources. The scoped roots also contained 271 grouped-daily
packages, which discovery correctly ignored.

The exact sessions are the 55-session XNYS interval from 2025-06-23 through
2025-09-09 plus 2026-09-01 through 2026-09-03. The mismatches are the
213-session interval from 2025-09-10 through 2026-07-16 plus the eight sessions
from 2026-08-20 through 2026-08-31. The 24 physically missing sessions remain
2026-07-17 through 2026-08-19.

Every one of the 221 mismatches has the same family-level shape:

```text
Instrument Master = exact
Provider Identity = mismatch
Ticker Resolver    = exact
```

Report evidence:

- report mode / size: `0600` / 447,255 bytes;
- report SHA-256:
  `e07ee30c025467950942f734546ededcd2904f7ed939e5b56423addf02c3c79d`;
- canonical session-index fingerprint:
  `1447eebaad620406ac7740364b7e7f38bc93521c6416f697b732a3ae07cde7b9`;
- discovered package-inventory fingerprint:
  `e7fc70b7fd62e78b132f0b7ccd87e19b539f3badb51397fb718c0cbdc5941f96`;
- external requests / canonical writes: 0 / 0.

The report contains dates, counts, bounded match flags, observation times, and
content fingerprints. It contains no package path, ticker, provider response
row, credential, Authorization value, or other source body.

## Mismatch diagnosis

All-session evidence proves only the common family-level mismatch shape. A
separate read-only row comparison sampled four mismatched sessions:

| Session | Changed Identity rows | Provider ETV rows | Other stable-key difference |
| --- | ---: | ---: | ---: |
| 2025-09-10 | 68 | 68 | 0 |
| 2026-01-29 | 81 | 81 | 0 |
| 2026-08-28 | 90 | 90 | 0 |
| 2026-08-31 | 90 | 90 | 0 |

For all changed rows in those samples, only `resolution_status`,
`quality_status`, and `quality_flags` changed: the accepted older build marked
ETV as rejected `unknown_provider_type_etv`; current code marks the same
non-instrument rows as excluded `exchange_traded_vehicle`. Row counts, stable
keys, Instrument Master, and Resolver records remained equal.

Repository history supports this explanation: commit `4d820c7` added the
governed ETV exclusion on 2026-09-03. The first 55 historical snapshots contain
no triggering ETV difference, and the 9/1–9/3 snapshots were accepted after
that rule existed. This is strong evidence of a versioned classification
migration, not 221 corrupt packages, but the row-level cause has not yet been
proved across every mismatched session.

## Decision and next gate

- Do not reacquire or discard the 221 mismatched packages.
- Do not call them exact-equivalent under the current builder.
- First define a narrowly versioned legacy-ETV compatibility reconstruction,
  then prove against all 221 accepted Provider Identity fingerprints that no
  other row or field differs.
- Only packages that pass an exact accepted-profile reconstruction may enter
  broad `/tmp` membership batches.
- The 24 physical gaps remain a separate acquisition/custody problem.

This census changes source diagnosis only. It does not create canonical daily
membership, Historical Coverage, research readiness, or performance authority.

Twelve focused checks and all 2,017 backend tests passed with the two unchanged
dependency warnings.
