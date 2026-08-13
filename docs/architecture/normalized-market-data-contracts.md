# Normalized Market Data Contracts

## Purpose

This document defines the accepted V1 logical contract boundary for normalized EOD market data. It describes the canonical contracts that Provider Adapters should produce before analytics and dashboard logic consume data.

## Current Status

Accepted Logical Contracts — Not Yet Implemented

No Python models, Pydantic schemas, SQL tables, Parquet schemas, provider adapters, ingestion jobs, or market-data files exist for these contracts yet.

## Shared Contract Principles

- Contracts are provider-neutral.
- Provider Adapters map proprietary responses into canonical contracts.
- Internal business logic does not consume provider-specific response shapes.
- `ticker` is not a permanent primary key.
- Missing values remain null and are not silently converted to zero.
- Revisions must be traceable.
- Silent destructive overwrite is not allowed.
- Raw, normalized, and derived layers remain separate.
- V1 is EOD-first and Parquet-first.
- No database is introduced yet.
- Timestamps are stored in UTC.
- Market session dates follow exchange calendars.
- Frontend display time uses the appropriate market or user context.
- Every contract is schema-versioned.
- Data quality status is explicit.

## Contract Inventory

- [Instrument Master V1](../data-contracts/instrument-master-v1.md)
- [EOD Price Bar V1](../data-contracts/eod-price-bar-v1.md)
- [Corporate Action V1](../data-contracts/corporate-action-v1.md)
- [Classification V1](../data-contracts/classification-v1.md)
- [Universe Membership V1](../data-contracts/universe-membership-v1.md)

## Provider Boundary

Provider Adapters are responsible for translating vendor records into canonical logical contracts. Analytics and dashboard logic should depend on canonical fields and internal identifiers, not vendor response structures.

## Time Semantics

`session_date` represents the primary exchange trading session and must not be derived by naive UTC truncation. Operational timestamps such as `ingested_at`, `assigned_at`, and `evaluated_at` use UTC.

## Revision Semantics

Provider corrections create traceable revisions. Latest-record flags may identify the current record, but prior revisions should remain available for audit. Destructive overwrite is not allowed.

## Quality Semantics

Contracts carry explicit quality status, quality flags, review status, or quality notes as appropriate. Missing or uncertain values must be represented directly rather than converted into misleading numeric defaults.

## Storage Direction

The accepted direction is EOD-first, Parquet-first storage under the project data root. Physical layout remains deferred. Practical partitioning should avoid one-file-per-ticker small-file proliferation. Raw, normalized, and derived datasets remain separate.

## Implementation Status

Not implemented. These contracts are documentation-level decisions only.

## Deferred Decisions

- Python/Pydantic model implementation
- physical Parquet layout
- source-specific provider mapping details
- source revision reconciliation policy
- validation test implementation
- database introduction threshold
- exact provider entitlement and coverage
