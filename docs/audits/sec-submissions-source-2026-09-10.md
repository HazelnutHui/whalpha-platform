# SEC Submissions Source — 2026-09-10

## Scope

Retain and formally reread one official SEC Submissions bulk snapshot in
private Dell source custody. The live run used clean revisions `3074224`,
`53dbab3`, and final `2e4d765` while correcting observed source-shape gates.
It used the configured owner-only SEC User-Agent and changed no `/data`,
analytics, Product, Production, deployment, or scheduler state.

## Result

The remote object reported Last-Modified 2026-09-10. One HEAD plus 12
consecutive ranges downloaded the exact object. Two later HEAD observations
revalidated the unchanged ETag/length/date while completed bytes were reused;
no range was downloaded twice.

| Measure | Result |
| --- | ---: |
| Successful requests | 15 = 3 HEAD + 12 ranges |
| Archive bytes | 1,562,779,836 |
| Archive SHA-256 | `6c7963d599a4b40da0bc361af5e332a8d80e73c4ed3a66bd629a4e9fc8163338` |
| ZIP members | 989,553 |
| Unique CIKs / root members | 984,189 |
| Historical shard members | 5,363 |
| Exact bounded placeholder | 1 |
| Total compressed member bytes | 1,400,321,436 |
| Total uncompressed member bytes | 5,734,737,323 |
| Manifest SHA-256 | `816915bce637b5ab11b1056d20f150321afbe6f5a755f384cecba45e68905d3b` |
| Logical fingerprint | `188863129a5dfc5324d337d23d67597cc048696dfbc2bc0e6b73a254344631b2` |

The completed directory is mode `0700`; all three package files are `0400`.
Every archive/chunk hash, exact remote identity, member path/type/encryption,
compression, size/expansion, unique member name, CIK root coverage, and exact
profile binding passed formal reread.

## Observed source-shape corrections

The first central-directory gate admitted only root CIK filenames. The real
official archive proved that older filing history is included as
`CIK##########-submissions-###.json` members. A second gate then found the
official 16-byte `placeholder.txt`. Both were corrected narrowly: root and
three-digit shard patterns plus that exact bounded printable placeholder are
allowed; arbitrary members remain rejected. The completed checkpoint was
reused after each correction.

This also exposed a stale validator in the older SEC classification cache: it
assumed every Submissions member had the root `{cik, filings}` shape, while
historical shards are direct columnar filing objects. The validator and
fixtures now distinguish root and shard schemas and require a root member for
every shard CIK.

The full API regression passed 2,435 tests after the shared range-engine
refactor. A focused 186-test SEC source/security set passed after the observed
shard and placeholder corrections.

## Alignment decision

Source custody is complete; accession-time coverage is not yet proven. Full
member CRC/JSON validation, column alignment, acceptance timestamp parsing,
root-to-shard reference reconciliation, and comparison to the 172,265
Company Facts in-range accessions remain the next bounded stage. No CIK was
treated as a stable security and no filing or fundamental became signal
eligible merely because it is present in this current snapshot.
