# 2026-08-14 Instrument Snapshot Audit

## Decision

- Audit date: 2026-08-15
- Provider: `massive_stocks_basic`
- As-of date: 2026-08-14
- Final status: `accepted_with_provenance_exception`

The user accepted this completed point-in-time identity snapshot as a production input after a read-only integrity audit. It must not be requested again, overwritten, deleted, or modified.

## Audited Datasets

| Dataset | Rows | Content SHA-256 | Result |
| --- | ---: | --- | --- |
| Instrument Master V1 | 9,939 | `16a67c09f3a43a324bc4b88bd4433816e385868229fd9c5ba21f53115868da65` | passed |
| Provider Instrument Identity V1 | 13,110 | `23b0a3460c8712b6e0d3d65c749c38ae5bdf6b1ad6bff6b8d880b1148a1fe24b` | passed |
| Provider Ticker Resolver V1 | 9,939 | `492b5e90105bfe2b3f64408bb0033e5df0edf000f7378d273652b3e3acd51668` | passed |
| Logical Instrument snapshot | 9,939 instruments / 13,110 identities / 9,939 resolver entries | `cc6b0f802196480339fc633645cedc62656047e70d8d7a86974ddcc15bc88dd0` | completed |

All four manifests declare schema version `1.0`, provider `massive_stocks_basic`, as-of date 2026-08-14, completion status `completed`, and creation time `2026-08-15T08:29:19.974535+00:00`.

## Integrity Evidence

The audit reread each Parquet file with the project's explicit Arrow schema and recomputed canonical content fingerprints. Manifest counts and fingerprints matched. Deterministic ordering, canonical key uniqueness, resolver ticker uniqueness, and referential integrity from resolved identities and resolver entries to Instrument Master all passed. The logical snapshot references exactly the three verified dataset fingerprints and counts.

Quality reconciliation:

- raw provider identity records: 13,110
- eligible records: 11,070
- resolved eligible: 9,939
- unresolved eligible: 1,131
- expected exclusions: 1,950
- malformed/rejected: 90
- ambiguous ticker records: 0
- stable identifier collisions: 0
- eligible identity coverage: 89.78319783197832%
- malformed ratio: 0.6864988558352402%
- ticker ambiguity ratio: 0%

## Provenance Assessment

Confirmed:

- dataset contents, schemas, counts, fingerprints, ordering, references, quality reconciliation, and logical completion;
- manifest provider, as-of date, and creation timestamp;
- no incomplete or staging artifact was present during the audit.

Strongly inferred:

- the datasets were produced by the repository's accepted bounded Instrument Master snapshot publisher because their layout, schemas, manifests, fingerprints, and quality summary match that implementation.

Unknown:

- the original run initiator and exact command;
- live request count and pagination sequence;
- a contemporaneous non-sensitive operation report.

The missing operational provenance is not evidence of data corruption. Conversely, verified content integrity does not prove that every upstream provider fact is absolutely correct. Every future live ingestion must retain a safe operation report containing request bounds, timestamps, quality statistics, publication result, and final fingerprint without credentials, headers, or raw provider payloads.
