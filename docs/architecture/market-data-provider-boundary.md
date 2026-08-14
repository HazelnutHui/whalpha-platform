# Market Data Provider Boundary

## Purpose

This document records the implemented minimal provider-neutral market-data provider boundary. The boundary defines how future providers must return canonical contracts before analytics or dashboard logic consumes data.

## Status

Implemented Minimal Boundary — First Provider Candidate Evaluated

The synchronous V1 Protocol, capabilities, query objects, provider error taxonomy, and deterministic in-memory contract test fake are implemented. Massive Stocks Basic is accepted as the first private EOD development provider candidate. The Massive adapter boundary now includes secure credential-file loading, standard-library HTTPS transport, and one successful read-only Stocks reference smoke test. It still has no ingestion, persistence, dashboard endpoint, rate-limit scheduler, Grouped Daily production download, or public provider-backed deployment.

## Synchronous V1 Boundary

V1 uses a synchronous Python Protocol. It intentionally avoids async, pagination, retry, caching, streaming, provider fallback, and persistence until real requirements justify them.

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

- bounded EOD ingestion workflow
- Grouped Daily production retrieval
- rate limiter implementation
- async support
- pagination
- retry and rate-limit handling beyond exception semantics
- caching
- provider registry or fallback
- data reconciliation across sources
- persistence and Parquet writing
- corporate actions, classifications, universe membership, options, real-time quotes, fundamentals, and news provider methods

## Non-Goals

- real provider adapter
- data download
- market-data ingestion
- provider entitlement probing
- credentials or secrets handling
- persistence
- analytics calculation
- Dashboard implementation
- API endpoint implementation

## Implementation Status

Implemented in `tip_api.providers.market_data` with tests under `apps/api/tests/providers`. The Massive credential loader and minimal HTTPS transport exist, and one reference smoke test has succeeded. A mocked-fixture EOD Price Bar ingestion and Parquet persistence slice now exists outside the provider package. No real provider ingestion, analytics, dashboard endpoint, or provider-backed deployment exists.
