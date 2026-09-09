# Normalized Market Data Contracts

## Classification Overlay

Security Classification V1 is an effective-dated overlay on stable Instrument Master identity. It adds legal security form, issuer economic structure, listing scope, evidence, status, and disposition without changing Instrument Master V1. U.S.-listed and U.S.-domiciled are independent facts; common-share legal form does not prove an operating-company issuer. Unknown and conflicting evidence is quarantined rather than coerced into `common_stock`. See [Security Classification V1](../data-contracts/security-classification-v1.md).

## Purpose

This document defines the accepted V1 logical contract boundary for normalized EOD market data. It describes the canonical contracts that Provider Adapters should produce before analytics and dashboard logic consume data.

## Current Status

Partially Implemented

Instrument Master V1 and EOD Price Bar V1 are implemented as provider-neutral
Python/Pydantic contracts with PyArrow persistence and formal readers. The
bounded Massive workflows have published the canonical sequence recorded in
current status. The historical boundary now has a provider-neutral corporate-
action source-observation repository, a sparse provider-neutral split-only fact
publication, a sparse affected-path split adjustment publication, and a daily
Universe-decision repository. The source observation does not substitute for
canonical action facts, and the split-only publications do not establish full
action coverage, absent-event neutrality, or total return. Neither family has
a general provider adapter or completed historical coverage.
Classification V1 now has provider-neutral source observations, canonical
definitions/memberships, explicit coverage decisions, immutable offline
Parquet persistence, and a formal reader. It has no real source, `/data`
partition, analytics consumer, or Production use. This Sector/Industry
classification remains separate from Security Classification V1. The bounded
300-session EOD
and point-in-time Identity acquisition is complete; this does not supply the
missing historical membership, lifecycle, corporate-action, adjustment or
coverage families. No SQL database exists. Exact volatile state belongs in
[current context](../project/current-context.md).

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

Partially implemented. Instrument Master V1, EOD Price Bar V1, and
Classification V1 have Python/Pydantic validation models and explicit PyArrow
persistence/read boundaries. Classification V1 remains fixture-only and
source-disabled. Other implementation state is recorded in the data-contract
index and current context; a completed contract does not imply real source
data, Production use, or research eligibility.

## Deferred Decisions

- Python/Pydantic model implementation for remaining logical contracts
- physical Parquet layout for contracts beyond implemented EOD,
  Classification, Membership, and historical-foundation boundaries
- source-specific provider mapping details
- source revision reconciliation policy
- validation test implementation
- database introduction threshold
- exact provider entitlement and coverage
