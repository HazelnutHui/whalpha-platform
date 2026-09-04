# Historical Identity Rebuild Profile Map Audit — 2026-09-04

## Purpose

Replace implicit or date-based historical Identity rule selection with an
immutable, fingerprint-bound session map, then prove that one bounded
membership batch can cross the real current/legacy profile boundary without
weakening package, Identity, EOD, or output-custody validation.

## Source reconciliation

The profile map was built from the completed full-index census reports:

| Source | Contract/profile | Report SHA-256 |
| --- | --- | --- |
| Current census | 1.0; implicit `current_v1` | `e07ee30c025467950942f734546ededcd2904f7ed939e5b56423addf02c3c79d` |
| Legacy census | 1.1; `pre_etv_governance_v1` | `ac68b70a7119c1d88c6bda9ce3b10f352f3eaa4ebb550200d0d16dc306735776` |

The builder formally parsed both owner-only reports and independently
recomputed their 303-session canonical-index and 279-package inventory
fingerprints. It rejected all failure classes except the expected exact,
Identity-only mismatch, and common missing states. For every retained session,
the selected profile matched all three accepted Identity families; the other
profile matched Instrument Master and Resolver and differed only in Provider
Identity.

## Materialized map

The formally reread contract
`historical-identity-rebuild-profile-map/1.0` contains:

| Classification | Sessions |
| --- | ---: |
| `current_v1` | 58 |
| `pre_etv_governance_v1` | 221 |
| Missing and intentionally unbound | 24 |
| Canonical total | 303 |

The owner-only map is 276,471 bytes, has physical SHA-256
`4fcc1a5eb23c9615e3478ad1b9dd477c906e587cf760cff3ac4b74383030c289`,
and logical fingerprint
`20e8b8f5b360d8a4ad4a78f0add69fb5eb88e1bc3ab5c6059dd87ca1035e0028`.
It contains no package path, ticker, provider response row, credential, or
Authorization value. A locator appears only as a SHA-256 binding.

Each binding covers session, selected profile, package locator/manifest/content
fingerprints, package observation time, all four accepted snapshot/family
fingerprints, and its own logical fingerprint. Moving or changing a source
package therefore requires a new census and map rather than an implicit
substitution.

## Real cross-profile membership proof

The adjacent XNYS sessions 2025-09-09 and 2025-09-10 straddle the real profile
boundary. One shared-panel batch selected `current_v1` for 9/9 and
`pre_etv_governance_v1` for 9/10 from the map, not from either date.

| Session | Profile | Evaluated base | Records | Logical fingerprint | Parquet SHA-256 |
| --- | --- | ---: | ---: | --- | --- |
| 2025-09-09 | `current_v1` | 8,864 | 17,728 | `a7b83387ca4ba58380c5a12a351647a37ee567e6925f2f2c45a1f1193e527bba` | `5688013df7c14197b6f22f154ee694a3fa14737341095f5d893efb6ada0a395d` |
| 2025-09-10 | `pre_etv_governance_v1` | 8,882 | 17,764 | `abc06a627243e947f625009cef27ee24c661e10223f192141a07a1349edabc93` | `75b102a519f494d9d57e4518da5ba0772700f021b759ca421defde8f68673bac` |

Both sessions published under a new `/tmp` root and passed formal reread. The
batch read 22 unique EOD partitions, completed in 2 minutes 03.60 seconds at
101% CPU, and `/usr/bin/time` reported 1,150,032 KiB peak resident memory.

An earlier run made from an independently generated map had identical binding
fingerprints, membership manifests, logical fingerprints, and Parquet bytes
for both sessions. The only intended difference was the whole-map fingerprint,
which includes its generation time and source-report envelope.

## Controls and conclusion

- Single-session and bounded-batch commands now require a formally validated
  profile map; there is no free-form profile CLI flag.
- The membership builder revalidates the selected profile, exact package
  locator/custody/observation evidence, and accepted canonical family
  fingerprints before membership calculation.
- A missing session, non-complementary profile result, changed package,
  malformed census, changed inventory, or invalid map fingerprint fails closed.
- External requests and canonical writes were zero. `/data`, Production,
  scheduler state, active pointers, analytics, and research readiness did not
  change.

This closes profile routing for the 279 retained packages. It does not close
durable source custody, the 24 physical gaps, canonical daily membership, or
Historical Coverage.

Eighteen focused checks and all 2,023 backend tests passed with the two
unchanged dependency warnings.
