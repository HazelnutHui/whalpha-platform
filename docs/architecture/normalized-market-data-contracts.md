# Normalized Market Data Contracts

## Purpose

This document defines the accepted V1 logical contract boundary for normalized EOD market data. It describes the canonical contracts that Provider Adapters should produce before analytics and dashboard logic consume data.

## Current Status

Partially Implemented

Instrument Master V1 and EOD Price Bar V1 are implemented as provider-neutral Python/Pydantic contracts with validation tests. A minimal synchronous provider boundary can return these canonical contracts, and a mocked-only Massive adapter skeleton maps local fixture responses into them. EOD Price Bar V1 now has an explicit PyArrow Parquet schema and mocked-fixture one-session repository tests. Corporate Action V1, Classification V1, and Universe Membership V1 remain accepted logical contracts only. A first production canonical EOD Price Bar Parquet partition exists for 2026-08-13 under the approved project data root. Corporate Action V1, Classification V1, and Universe Membership V1 remain accepted logical contracts only; no SQL tables, historical ingestion jobs, analytics, or Dashboard data APIs exist yet.

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

Contracts carry explicit quality status, quality flags, review status, or quality notes as appropriate. Missing or uncertain values must be represented directly rather than converted into misleading numeric defaults. EOD aggregate volume is an exact non-negative Decimal; trade count and provider timestamps remain integer-semantic.

## Storage Direction

The accepted direction is EOD-first, Parquet-first storage under the project data root. Physical layout remains deferred. Practical partitioning should avoid one-file-per-ticker small-file proliferation. Raw, normalized, and derived datasets remain separate.

## Implementation Status

Partially implemented. Instrument Master V1 and EOD Price Bar V1 have Python/Pydantic validation models. A mocked-only Massive adapter skeleton maps local fixture responses into those two contracts. The remaining V1 contracts are documentation-level decisions only. No physical schema, production HTTP transport, real provider request, ingestion job, or persistence writer exists yet.

## Deferred Decisions

- Python/Pydantic model implementation for remaining logical contracts
- physical Parquet layout for contracts beyond EOD Price Bar V1
- source-specific provider mapping details
- source revision reconciliation policy
- validation test implementation
- database introduction threshold
- exact provider entitlement and coverage
