# ADR 0303: Persist SEC Cash-Quality Readiness and Build Reusable Endpoint Evidence

## Status

Accepted

## Date

2026-09-18

## Context

ADR 0302 produced a bounded issuer-level readiness census, but its first real
execution retained only process output. Typed objects and matching forward and
reverse fingerprints are not durable custody. Reconstructing the result from
printed counts would not prove its canonical bytes or inputs.

Repeatedly rereading all 41.6 million normalized occurrences for each later
source-engineering question is also unnecessary. The next outcome-blind stage
needs exact selected values and lineage, but still cannot derive TTM values,
project issuers onto securities, or read outcomes.

## Decision

1. Add immutable owner-only atomic custody for the exact census plan, canonical
   result, and forward/reverse verification. The three-document closed set must
   exactly reread and reconcile every fingerprint. Terminal output is not an
   admissible substitute.
2. Register
   `quant-research-sec-cash-quality-endpoint-selection-package/1.0`. Its plan
   binds the exact readiness evidence and admits only the census's ready
   endpoints.
3. Extend the formal normalized-source reader with an optional exact-concept
   batch consumer. Filtering occurs during the same full formal reread that
   verifies every artifact; it does not create a second source scan.
4. Persist a reusable target-occurrence Parquet index with disposition, value,
   accession, knowledge time, eligible session, and source occurrence ID. A
   separate selected-endpoint Parquet contains exactly three query rows for
   every admitted ready endpoint and retains all duplicate occurrence IDs that
   support the clean selected state.
5. Require CFO and net-income accession coherence, exact query membership,
   source/result row budgets, physical hashes, Arrow schemas, owner-only modes,
   atomic directory rename, closed-set inventory, and formal exact reread.
6. Register a plan-only TTM feasibility contract. It may test the frozen
   consecutive-quarter and opening/closing-Assets requirements later, but this
   stage does not execute that test or calculate TTM.

No network request, security projection, applicability decision, TTM
derivation, factor materialization, outcome, Validation, Holdout, trial,
Candidate, canonical, or Production authority is granted.

## Consequences

The already printed first census cannot be retroactively published. A future
real build must reproduce and atomically retain its canonical plan/result/
verification evidence while producing the reusable index. Once exact reread
succeeds, later issuer-level feasibility work reads the approximately one
million-row target index rather than the 41.6-million-row normalized source.
