# SEC Point-in-Time Fundamental Census

## Purpose

Measure the normalized five-year SEC occurrence ledger before selecting a
fundamental feature registry. This is network-free and writes only an
owner-only report/census package outside canonical `/data`.

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
