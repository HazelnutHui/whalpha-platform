# SEC Point-in-Time Fundamental Census

## Purpose

Measure the normalized five-year SEC occurrence ledger before selecting a
fundamental feature registry. This is network-free and writes only an
owner-only report/census package outside canonical `/data`.

ADR 0216 and
[SEC Company Facts Semantic Census V1](../data-contracts/sec-companyfacts-semantic-census-v1.md)
define the executable first stage. It is a source-semantic census, not a
feature build.

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
