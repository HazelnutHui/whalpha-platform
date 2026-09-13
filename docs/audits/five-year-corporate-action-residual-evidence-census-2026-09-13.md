# Five-Year Corporate-Action Residual Evidence Census — 2026-09-13

## Scope

ADR 0220 joined every unresolved typed row in the current five-year Corporate
Action Resolution Shadow to already retained Identity-history candidates,
inactive-listing evidence, and the official FINRA OTC Daily List range. The
run was network-prohibited and wrote only a new immutable owner-only diagnostic
outside `/data`.

The unit below is an unresolved source-action row, or a row/candidate
occurrence where lifecycle state is discussed. It is not one of ADR 0218's
2,387 distinct ticker/instrument candidate relations. No result assigns stable
identity or promotes a canonical action.

## Bound inputs

| Input | Bound identity |
| --- | --- |
| Corporate Action Resolution Shadow v2 | manifest `b0d3e7438f8a1bd3d643a5fab564634fa203f92f08175dc9ceb5e166b1597c66`; logical `444077fb1ca39ba3ac210f19fc19dae7e94573d42fa3d1c4119216b2641a7c4a` |
| Unresolved census v2 | manifest `f1fbc2f8b76c34b3b44ff80c6292e458126762fe455f6e1953b759a642fd7f48`; logical `42a3b34e8354832c6505ac4a4c645145a2800390d0cfb99e12d31408cafe7f98` |
| Inactive lifecycle, 2026-07-16 | manifest `f1d3008156bafb1eb10ae7a09f6d09741d25b21274b63c7993f70692f7effdac`; 23,260 source/decision rows |
| Inactive lifecycle, 2026-09-03 | manifest `0c7ec6904d13d6550522eb9edcd0de840f2c14571e65d3285ad0cd749df36240`; 23,469 source/decision rows |
| FINRA OTC Daily List | 62 packages / 68,714 rows, 2021-08-11 through 2026-09-09; package-chain `f40142ea94d4c5d43f594fc65e3a616831b0770c8237c09d455e3ba1b1589c0c` |

## Result

All 112,943 unresolved typed source rows are present exactly once.

### Lifecycle state of row/candidate occurrences

| State | Count | Interpretation |
| --- | ---: | --- |
| Inside canonical observed span | 19 | strongest retained temporal support, still not event ownership |
| Unverified terminal gap | 2,386 | after last observation but no later than provider delisting candidate |
| Before canonical first observation | 1,251 | temporal contradiction |
| After provider delisting candidate | 198 | temporal contradiction |
| Mixed anchor boundary | 0 | none |
| No lifecycle evidence | 20,208 | no retained lifecycle window for the row's history candidate |

The 2,386 terminal-gap occurrences cannot be merged with the 19 observed-span
occurrences. A provider delisting candidate is not a proven last tradable date.

### Other retained evidence

| Evidence | Source rows |
| --- | ---: |
| FINRA exact date/symbol candidate | 20,679 |
| FINRA exact numeric candidate | 10,261 |
| Inactive-provider ticker match | 9,445 |
| Inactive match with one stable source identity | 5,368 |
| Inactive match with no stable source identity | 4,076 |
| Inactive match with multiple stable source identities | 1 |

FINRA flags touched 1,714 symbol-change rows, 81 deletion rows, 14 addition
rows, and three bankruptcy rows. These are exact retained source flags, not
interpreted terminal outcomes. Inactive-provider type evidence is dominated by
`FUND` and `PFD`; it is security-scope evidence only because the connection to
the unresolved action remains ticker-based.

Across the three evidence sources, 29,127 rows (25.79%) have at least one
cross-evidence lead and 83,816 (74.21%) have none. Of the touched rows, 26,381
are cash dividends, 1,934 reverse splits, 649 stock splits, and 163 stock
dividends. Coverage is therefore useful for targeting, not sufficient for
canonical completion.

## Custody and validation

The private package is
`historical-source/corporate-action-residual-evidence-census/build=20260913-v1`.
It contains two files / 4,183,894 bytes: a 4,180,927-byte Parquet result and a
2,967-byte manifest. Directories are mode `0700`, files are mode `0400`, owner
is `hui`, and no symlink, partial, or staging residue exists.

- implementation revision:
  `d8a0e827ec3a20c2ef7f716fc86f18b17d529f97`;
- manifest SHA-256:
  `ba12436eababcb8b56b57d710a4e80cd83c26b33eca409c79a2d034bcbe8dd80`;
- logical fingerprint:
  `3fbcf2719047bf753ed4014017a82f6d3a659e2d90be724e2b35a90cbabce525`;
- record logical fingerprint:
  `ba76a19dbd0a8e1b6450635080bdfb6bf0a6108dd2e3c97c056744852d72383b`.

The real command and built-in formal reread completed in approximately 125
seconds. A separate output-only formal reread reproduced all rows, hashes, and
aggregates without repeating the five-year Resolver scan. The implementation
stage passed 33 focused tests and the complete API suite passed 2,596 tests
with two unchanged dependency deprecation warnings.

## Decision and next boundary

This census completes the current local-source composition stage. Repeating
the same scan cannot improve evidence. The measured global residual is large
enough to justify evaluating a paid cross-venue lifecycle/corporate-action
sample, but it does not justify buying or ingesting a source blindly.

Before attempting global resolution, intersect the residual with the first
registered strategy's declared reconstructed development cross-sections and
price-return semantics. This does not make latest-vintage Membership
signal-eligible; it only distinguishes current development blockers from
irrelevant security forms and dates. Use the resulting named sample to compare
paid sources; keep every unmatched or conflicting record quarantined.

Stable-ID assignments, source mutations, canonical writes, Adjustment Ledger,
Historical Coverage, analytics, Candidate, publication, deployment, scheduler
changes, and external requests were all zero.
