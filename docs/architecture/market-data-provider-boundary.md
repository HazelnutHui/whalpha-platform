# Market Data Provider Boundary

## Purpose

This document records the implemented minimal provider-neutral market-data provider boundary. The boundary defines how future providers must return canonical contracts before analytics or dashboard logic consumes data.

## Status

Implemented Provider-Neutral Boundary — Massive Bounded Workflows Published

The synchronous V1 Protocol, capabilities, query objects, provider error taxonomy, and deterministic in-memory contract test fake are implemented. Massive Stocks Basic is the first private EOD development provider. Its adapter boundary includes secure credential-file loading, standard-library HTTPS transport, bounded All Tickers and Grouped Daily workflows, canonical mapping, and atomic Parquet persistence outside the Protocol itself. Completed identity/EOD datasets and default-disabled private Dashboard APIs exist. Automated scheduling, historical backfill, and unrestricted public provider-backed serving do not.

## Synchronous V1 Boundary

V1 uses a synchronous Python Protocol. The provider-neutral interface intentionally avoids async, pagination, retry, caching, streaming, provider fallback, and persistence. Provider-specific operational workflows may implement bounded pagination, pacing, transport, and persistence around the Protocol without leaking those concerns into canonical domain calculations.

Public import path:

```python
from tip_api.providers.market_data import (
    EodBarQuery,
    InstrumentQuery,
    MarketDataProvider,
    ProviderCapability,
    ProviderDataError,
    RevisionSelection,
    UnsupportedCapabilityError,
)
```

## Capabilities

Implemented capabilities:

- `instrument_master`
- `eod_price_bars`

Capabilities describe what a provider implementation supports. They do not prove that a user has entitlement to a real provider's data.

## Query Objects

`InstrumentQuery` expresses an as-of request for Instrument Master records:

- `as_of_date`
- optional internal `instrument_ids`
- `active_only`

`EodBarQuery` expresses an EOD bar request:

- internal `instrument_ids`
- inclusive `start_date` and `end_date`
- `revision_selection`

Queries are frozen Pydantic models, forbid extra fields, reject datetime values for date fields, and do not contain ticker filters or provider-specific IDs.

## Canonical Return Types

`MarketDataProvider` implementations return immutable tuples of canonical contracts:

- `tuple[InstrumentMasterV1, ...]`
- `tuple[EodPriceBarV1, ...]`

Providers must not return dictionaries, raw JSON, provider payloads, Pandas DataFrames, generators, or provider-specific objects.

## Stable Ordering

Provider implementations are responsible for deterministic ordering.

`get_instruments` ordering:

1. `instrument_id` string ascending

`get_eod_bars` ordering:

1. `instrument_id` string
2. `session_date`
3. `source`
4. `revision`

The deterministic in-memory fake verifies these ordering rules.

## Revision Selection

`RevisionSelection` values:

- `latest`: return records where `is_latest_revision=True`
- `all`: return all matching revisions

Latest selection uses the explicit `is_latest_revision` flag and does not infer latest from the maximum revision number.

If a relevant EOD logical group has multiple latest records, or if `latest` is requested and a relevant group has no latest record, the provider raises `ProviderDataError`.

## Error Semantics

Implemented exception hierarchy:

- `MarketDataProviderError`
- `ProviderUnavailableError`
- `ProviderAuthenticationError`
- `ProviderRateLimitError`
- `ProviderDataError`
- `UnsupportedCapabilityError`

Errors carry a non-empty provider ID and safe message. They do not store credentials, request headers, raw response bodies, or provider secrets. `ProviderRateLimitError` can carry a non-negative `retry_after_seconds` value, but it does not sleep or retry.

## In-Memory Test Fake

The deterministic `InMemoryMarketDataProvider` exists only under `apps/api/tests/providers/support`. It is not exported by the production package.

The fake verifies provider behavior for:

- capability enforcement
- as-of Instrument Master filtering
- active-only filtering
- overlapping Instrument Master versions
- EOD date-range filtering
- latest/all revision selection
- duplicate EOD business keys
- contradictory latest revision state
- stable ordering
- immutable tuple results

## Security Boundary

The provider-neutral boundary has no credential fields and does not require raw provider schemas. Massive credential loading and HTTPS transport live in the Massive-specific adapter package, keep credentials outside Git, and do not expose Massive-specific fields to canonical contracts. Additional provider-backed workflows must be reviewed for entitlement, licensing, redistribution, and access-control constraints before use.

## Deferred Concerns

- automated daily EOD ingestion
- historical backfill
- rate limiter implementation
- async support
- reusable pagination beyond the bounded Massive workflows
- retry and rate-limit handling beyond exception semantics
- caching
- provider registry or fallback
- broader data reconciliation across sources
- database/catalog introduction and Parquet lifecycle management
- corporate actions, classifications, universe membership, options, real-time quotes, fundamentals, and news provider methods

## Boundary Non-Goals

- vendor schemas in domain calculations
- credentials in provider-neutral query objects or canonical contracts
- unrestricted live requests from ordinary tests
- public redistribution authorization
- automatic trading or order execution
- treating the Protocol as a scheduler, database, or deployment layer

## Implementation Status

Implemented in `tip_api.providers.market_data` with tests under `apps/api/tests/providers`. Massive-specific configuration, credential, transport, adapter, inspection, identity, Grouped Daily, and security-evidence workflows live under `tip_api.providers.massive`; persistence remains behind provider-neutral repositories. Bounded live operations published completed point-in-time identity, EOD, and provider security evidence datasets. Default-disabled private analytics/Dashboard endpoints and a protected static snapshot deployment path consume canonical outputs. No automated ingestion, historical backfill, production API service, or unrestricted public provider-backed display exists.
