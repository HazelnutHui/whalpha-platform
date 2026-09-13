# SEC Filing-Clock Ledger — 2026-09-10

## Scope

Build and formally reread the first immutable daily-research filing-clock
package for every Company Facts accession filed from 2021-08-11 through
2026-09-09. The run used clean revision `12b00e2`, eight Dell workers, the
final Company Facts and Submissions source/census packages, and
`exchange-calendars` 4.13.2. It was network-free and wrote only the owner-only
historical-source state root, not `/data`.

## Result

| Measure | Count |
| --- | ---: |
| Total accession rows | 172,265 |
| Admitted filing clocks | 172,262 |
| Quarantined missing Submissions accessions | 3 |
| Exact single-acceptance clocks | 172,155 |
| Conflicting-acceptance clocks, latest retained | 107 |
| Repeated Submissions accessions | 17,845 |
| Exact filed-date sets | 172,247 |
| Filed-date disagreements | 15 |
| Selected midnight time-quality warnings | 1 |
| Missing forms | 0 |

The complete 3/107/17,845/15 residual counts independently reproduce the
sealed Submissions census. The three missing accession rows remain physically
present with no invented source time or eligible session.

The inspected conflict examples occur across multiple co-filer/member
contexts and include four-hour differences for the same accession. The package
preserves every timestamp and member, selects the later value, and does not
claim which duplicate is the provider's intended correction. All 15 inspected
filed-date disagreements retain both dates while the exact accession-bound
acceptance remains the conservative time source.

The one exact-midnight source value belongs to accession
`0001213900-26-037791`. It is flagged and becomes eligible on 2026-04-02 rather
than the 2026-04-01 source date. Across the package, the first/last eligible
XNYS sessions are 2021-08-11 and 2026-09-10.

## Integrity

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| `filing-clocks.parquet` | 4,060,498 | `e9a4fc02c8e70b9ec441412e9049fd6072c2f2187e55d2aa48c847a4526aeaeb` |
| `manifest.json` | 2,414 | `c3d56300d86848f01cf8cf06d48356a102b4c6a97da4cd2e53f63a8e2ed42bf1` |

The logical row fingerprint is
`5c657f34cded9fa6d484977e042578173fd85873c489813ded924aefa325abb8`;
the manifest logical fingerprint is
`da75607b52e044f003a10f9988023b4d6545e0ed7e1d01c75b42713a69e658bd`.
Both files are mode `0400` under a mode-`0700` package. Independent formal
reread revalidated modes, exact members/schema, physical identities, sorted
unique business keys, every conservative-time/session invariant, counts, and
fingerprints.

The SEC suite passed 238 tests. The full API regression passed 2,441 tests
with two unchanged dependency deprecation warnings.

## Alignment decision

The filing-clock family is complete for this exact source snapshot and range,
but it remains CIK/accession evidence rather than a security-level fundamental
dataset. The next stage may normalize every in-range Company Facts occurrence
and join this clock by accession. It must preserve original occurrences and
revisions, keep the three missing accessions quarantined, and leave
CIK-to-`instrument_id` resolution for a separate exact dated-identity stage.
