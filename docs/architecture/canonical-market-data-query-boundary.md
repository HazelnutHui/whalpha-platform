# Canonical Market Data Query Boundary

## Purpose

This document records the first read/query boundary for completed canonical EOD market data. The boundary reads provider-neutral Parquet datasets, joins completed identity metadata, and returns typed read models for private API responses.

## Status

Implemented for the completed 2026-08-13 EOD Price Bar session.

This is not an analytics engine, full export API, public data service, or authentication system.

## Implemented Boundary

Implemented package boundary:

- `tip_api.persistence.eod_read.EodReadRepository`
- `tip_api.persistence.parquet.eod_read.CanonicalEodReadRepository`
- `tip_api.services.eod_market_data.EodMarketDataQueryService`
- `tip_api.read_models.eod`
- `tip_api.schemas.private_eod`
- `tip_api.api.v1.private_eod`

The repository reads only completed partitions and returns typed read models. It does not expose Arrow tables, raw provider payloads, storage manifests, or filesystem paths to the API layer.

## Data Root

The default data root is `/data/trading-intelligence-platform` and can be configured with `TIP_MARKET_DATA_ROOT` for tests or local development. The configured root must be absolute, must exist, and must not be a symlink.

API callers cannot provide a filesystem path. Session partitions are derived only from strict `date` values and fixed dataset layout rules.

## Completed Session Validation

The read repository validates:

- completed EOD partition manifest
- explicit Arrow schema
- row count
- session date consistency
- content fingerprint
- linked Instrument Master logical snapshot completion marker
- Instrument Master dataset manifest and fingerprint
- Provider Ticker Resolver dataset manifest and fingerprint
- resolver ticker uniqueness
- resolver instrument IDs existing in Instrument Master
- duplicate canonical EOD business keys

Invalid, incomplete, corrupted, or mismatched datasets are reported as data unavailable. The API response must not leak absolute paths, raw manifest content, or tracebacks.

## Read Models

The query boundary exposes immutable provider-neutral read models:

- `EodSessionDescriptor`
- `EodMarketBarReadModel`
- `EodSessionPage`
- `EodSessionSummary`

`EodMarketBarReadModel` joins canonical EOD bars with Instrument Master metadata and point-in-time resolver ticker values. It does not include provider raw records, request IDs, credential information, or filesystem paths.

## Query Service

The service supports:

- `list_sessions()`
- `get_latest_session()`
- `get_session_summary(session_date)`
- `get_bars_page(session_date, limit, offset, ticker, instrument_type)`

Pagination is bounded to `1 <= limit <= 200` and `offset >= 0`. Sorting is fixed by ticker then instrument ID. Supported filters are ticker and canonical instrument type only. There is no arbitrary sort, expression filter, or full-data download endpoint.

## Response Semantics

Private API response contracts serialize Decimal values as strings to preserve exact canonical values. They do not convert Decimal values to binary floats.

The first summary intentionally avoids analytics that require more data, including close-to-close returns, breadth, gainers/losers, sector performance, turnover, market-cap weighting, or heatmap values.

## Security Boundary

Private market-data routes are controlled by `TIP_ENABLE_PRIVATE_MARKET_DATA_ROUTES`, which defaults to false. When false, the router is not registered and is absent from OpenAPI.

This flag is only a development-time exposure control. It is not authentication, authorization, or a public deployment approval. Provider-backed responses require a formal private access-control mechanism before OCI or public deployment.

## Non-Goals

- frontend Dashboard changes
- authentication or authorization
- public market-data endpoints
- all-record download endpoint
- analytics calculations
- prior-session return calculations
- sector/theme joins
- database or catalog service
- Massive API calls
- credential access
- writes to `/data`
- OCI deployment
