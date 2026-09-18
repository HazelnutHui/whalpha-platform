# SEC Cash-Quality Source-Readiness Census V1

## Scope

`quant-research-sec-cash-quality-source-readiness-census/1.0` measures local,
issuer-level occurrence readiness for the three ADR 0300 queries before any
TTM construction. It is an aggregate source diagnostic, not feature coverage.

## Plan and budgets

The immutable plan binds the normalized source and filing clock, every
occurrence artifact, the occurrence schema, query registry, source interval,
knowledge cutoff, and evaluated session. It fixes ceilings for scanned rows,
target rows, observed endpoints, rows retained per worker, batch size, workers,
and processes. A ceiling breach, missing artifact, schema/count/hash drift, or
formal source-read failure stops the run.

The first plan uses one process and 65,536-row batches. It may scan only the
exact bound occurrence denominator, retain at most 2,000,000 target rows,
evaluate at most 1,000,000 observed endpoints, and retain at most 300,000
target rows in any worker partition.

## Measures

For each query the result records:

- target occurrence count and sequential rejection dispositions;
- selected, not-available, and quarantined endpoint counts; and
- typed endpoint ambiguity/missing reasons.

The joint result records observed issuers and endpoints, fiscal-period counts,
ready versus blocked endpoints, time boundaries, and aggregate blockers. The
denominator is only the union of CIK/fiscal-year/fiscal-period/end-date keys
observed in at least one target concept. Entirely absent issuer endpoints are
not measured.

No source value, CIK, accession, or occurrence ID is retained in the result.

## Deterministic verification

A primary forward traversal and independent reverse traversal must produce
identical logical fingerprints and canonical bytes. Replay mismatch fails
closed and grants no downstream authority.

## Prohibited interpretation

The census does not calculate discrete quarters, TTM CFO, TTM net income,
average Assets, or the cash-quality factor. It performs no security projection
or nonfinancial applicability decision and reads no return, Development,
Validation, or Holdout outcome. It authorizes no trial, Candidate, canonical
write, or Production use.

See [ADR 0302](../decisions/0302-census-local-sec-cash-quality-source-readiness-before-ttm.md).
