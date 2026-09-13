# SEC Point-in-Time Fundamental Census

## Purpose

Measure the normalized five-year SEC occurrence ledger first at broad semantic
grain and then against a deliberately small registered query set. Both stages
are network-free and write only owner-only report/census packages outside
canonical `/data`.

ADR 0216 and
[SEC Company Facts Semantic Census V1](../data-contracts/sec-companyfacts-semantic-census-v1.md)
define the executable first stage. ADR 0225,
[SEC Fundamental Query Registry V1](../data-contracts/sec-fundamental-query-registry-v1.md),
and
[SEC Fundamental Query Readiness Census V1](../data-contracts/sec-fundamental-query-readiness-census-v1.md)
define the query-specific second stage. Neither stage is a feature build.

## Required measures

- exact occurrence, filer, concept, namespace, unit, form, and filing-year
  populations;
- required-period-field and admitted-clock coverage;
- exact duplicate occurrences within accession and semantic key;
- conflicting values within accession and semantic key;
- later-accession revision counts and value-change counts for the same key;
- instant versus duration populations;
- taxonomy and custom-extension concentration;
- filer coverage for an explicitly bound common-stock CIK-link population;
  and
- bounded samples for every conflict class without treating examples as a
  correction rule.

The census must stream or partition its work and must not construct the full
fact-by-session Cartesian product. Each report binds the normalized source,
clock ledger, code revision, exact date range, schemas, counts, hashes, and
zero authority fields.

## Stop and continue rules

Source/hash/schema/count drift or failure to reproduce the normalized ledger
denominator stops the census. A local fact conflict, unsupported concept, or
missing security link is counted and quarantined without stopping unrelated
facts. Do not create a feature mapping merely to make coverage look complete.

## Execution boundary

Use the sealed normalized Company Facts package and one explicitly selected
filer/security link diagnostic package. The source must have completed a full
formal readback before execution. The census itself verifies every bound
artifact's physical identity and streams every occurrence exactly once.

Run with at most the normalized package's worker count. Output must use a new
owner-only `build=...` path below the dedicated semantic-census state root.
The CLI refuses a dirty repository, an existing target or partial target, a
non-owner root, symlinks, and any input identity drift.

After completion, formally reread `census.json`, compare all source/link
bindings and aggregate invariants, record elapsed time and peak memory, and
retain the exact logical fingerprint in a dated audit. Do not register a
feature merely because it appears in the top-concept coverage table.

## Query-specific readiness stage

Run the readiness census only after the registry and implementation are
committed, because the CLI requires a clean repository and binds the exact
revision. Supply the same normalized package, semantic census, filer/security
link package, and canonical data root used by the semantic census. Use no more
processes than normalized source workers.

The stage scans the full occurrence denominator but materializes only the four
registered concepts in worker memory. It records sequential rejection reasons,
exact duplicates, value/availability conflicts, period-end shape ambiguity,
and filers with at least one clean period. It publishes no values and performs
no projection, outcome access, external request, `/data` write, publication,
deployment, or scheduler change.

The completed output must use a new owner-only `build=...` directory below the
dedicated readiness-census state root. Reread the package through
`read_sec_fundamental_query_readiness_census`; do not treat raw JSON inspection
as formal verification. A successful result permits only the later design of
a cutoff-aware issuer query reader and security-projection census.

## Cutoff-aware projection stage

Use the completed query-readiness package and the complete five-year
filer/security candidate. The CLI requires a clean repository and binds its
exact revision. Use eight processes for the normalized issuer-timeline build
and eight explicit formal-read workers for the transitive link verification.

The scan must recompute common-stock CIK cardinality within each session and
must not use the source package's all-security `cik_instrument_count` as the
share-class test. Every link row receives one structural/time disposition;
every structurally projectable row receives one selection state for every
registered query.

The report retains only query/tier/session aggregates and fact-age buckets.
No issuer value, security/fact row, signal, label, rank, or outcome may be
written. After completion, formally reread the report and both transitive input
chains, verify exact ownership/modes and absence of sibling partial residue,
and record runtime plus logical fingerprint in a dated audit.
