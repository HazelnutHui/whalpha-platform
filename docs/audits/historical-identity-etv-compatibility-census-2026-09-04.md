# Historical Identity ETV Compatibility Census — 2026-09-04

## Purpose

Test whether the 221 Provider Identity-only mismatches from the ADR 0134
current-builder census are explained completely by the explicitly versioned
pre-ADR-0124 ETV representation, without changing current classification or
using a session-date heuristic.

## Profile boundary

ADR 0135 defines `pre_etv_governance_v1`. It can transform only a current-build
Identity row that is already an excluded, unresolved, warning-quality,
non-canonical `exchange_traded_vehicle`. The derived legacy row is rejected
with rejected quality and `unknown_provider_type_etv`, exactly matching the
pre-governance representation. Instrument Master and Resolver rows are never
changed.

`current_v1` remains the default. The compatibility profile is historical
comparison evidence only; it does not change provider mapping, Universe
eligibility, canonical data, or Production.

## Bounded proof

The serial three-session sample produced the required positive and negative
boundaries:

- 2025-09-10: legacy exact;
- 2026-08-31: legacy exact;
- 2026-09-03: legacy mismatch because the accepted snapshot uses current ETV
  semantics.

The serial run took 29.57 seconds. A two-worker repeat took 19.93 seconds and,
after excluding only the declared worker-count field, was byte-identical with
comparison SHA-256
`190828ad05a125e0f7dbaf9e0e4f8856f4da392dd0f84d2ae5c08c53266b90f4`.

## Full legacy-profile census

The four-worker `full_canonical_index` run completed in 12 minutes 22.98
seconds at 398% aggregate CPU. `/usr/bin/time` reported 295,772 KiB maximum
resident set size; this is not represented as a summed four-process peak.

| Classification under `pre_etv_governance_v1` | Sessions |
| --- | ---: |
| `exact_equivalent` | 221 |
| `identity_snapshot_mismatch` | 58 |
| `missing_source` | 24 |
| Other failure classes | 0 |
| Total | 303 |

All 279 discovered packages again passed custody. There were no duplicates,
unroutable manifests, outside-index sources, or canonical Identity failures.

The 443,879-byte owner-only report has SHA-256
`ac68b70a7119c1d88c6bda9ce3b10f352f3eaa4ebb550200d0d16dc306735776`.
It contains no source path, ticker, response row, credential, or Authorization
value. External requests and canonical writes were zero.

## Two-profile reconciliation

The current-profile report and the legacy-profile report have identical
canonical session-index and discovered package-inventory fingerprints. Their
session sets reconcile exactly:

| Check | Result |
| --- | ---: |
| Union of exact sets | 279 |
| Intersection of exact sets | 0 |
| Current mismatches equal legacy exact set | yes; 221 |
| Current exact set equals legacy mismatches | yes; 58 |
| Missing sets equal | yes; 24 |

The 58 current-profile sessions are the 55 XNYS sessions from 2025-06-23
through 2025-09-09 plus 2026-09-01 through 2026-09-03. The 221 legacy-profile
sessions are 2025-09-10 through 2026-07-16 and 2026-08-20 through 2026-08-31.
The non-monotonic date placement reflects the actual descending historical
backfill and later current-session creation. No date threshold is a valid
profile selector.

A current-default real regression on 2026-09-03 also reproduced all three
accepted family fingerprints after the profile implementation.

## Conclusion

Every retained package has exactly one accepted reconstruction result across
the two profiles. The 221 prior mismatches are fully explained by the versioned
ETV representation; they are neither corrupt nor reacquisition candidates.
The remaining source gap is exactly the 24 physically missing sessions.

Next work must bind each session to the profile that actually matches all three
accepted fingerprints, then pass that explicit mapping into disconnected
membership batches. Durable source custody and the 24 missing sessions remain
separate gates. No canonical membership or Historical Coverage publication is
authorized by this result.

Thirteen focused checks and all 2,018 backend tests passed with the two
unchanged dependency warnings.
