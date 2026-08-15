# Trading Intelligence API

FastAPI backend scaffold for Trading Intelligence Platform.

## Purpose

The API package provides typed contracts, canonical market-data read services, and default-disabled private EOD routes for the future dashboard boundary. The default HTTP scaffold exposes only the Health endpoint; private market-data routes are registered only when explicitly enabled for local/private development.

## Current Endpoints

Default route:

- `GET /api/v1/health`

Explicitly enabled private routes (`TIP_ENABLE_PRIVATE_MARKET_DATA_ROUTES=true`):

- `GET /api/v1/private/market-data/eod/sessions`
- `GET /api/v1/private/market-data/eod/sessions/latest`
- `GET /api/v1/private/market-data/eod/sessions/{session_date}/summary`
- `GET /api/v1/private/market-data/eod/sessions/{session_date}/bars`
- `GET /api/v1/private/market/summary/latest`
- `GET /api/v1/private/market/movers/latest`
- `GET /api/v1/private/market/liquidity-map/latest`
- `GET /api/v1/private/market/returns/latest`

Expected response:

```json
{
  "status": "ok",
  "service": "trading-intelligence-api",
  "version": "0.1.0"
}
```


## Implemented Python Contracts

Provider-neutral market-data contracts are available from:

```python
from tip_api.contracts.market_data.v1 import (
    EodPriceBarV1,
    InstrumentMasterV1,
    InstrumentStatus,
    InstrumentType,
    QualityStatus,
)
```

Implemented contracts:

- Instrument Master V1
- EOD Price Bar V1

These are validation models. EOD Price Bar V1 now has a bounded Parquet persistence path and one-session ingestion slice. The authorized 2026-08-13 Grouped Daily ingestion passed quality gates after Decimal volume correction and published the first production canonical EOD bar partition. A default-disabled private read/query API now serves completed canonical EOD sessions from Parquet. Market Summary V1, movers, returns, and Liquidity Map V1 private responses are implemented from completed canonical sessions. No frontend Dashboard flow, public routes, or authentication system is implemented.

Provider Instrument Identity V1 is also implemented for point-in-time provider identity mapping. The first live Massive Instrument Master snapshot attempt completed pagination but did not publish because quality gates failed.

Provider Ticker Resolver V1 is implemented for point-in-time ticker resolution. After refined quality gates, the 2026-08-13 Massive Instrument Master snapshot published 9,932 canonical instruments and 9,932 resolver entries under the project data root.


## Implemented Provider Boundary

Provider-neutral market-data provider types are available from:

```python
from tip_api.providers.market_data import (
    EodBarQuery,
    InstrumentQuery,
    MarketDataProvider,
    ProviderCapability,
    RevisionSelection,
)
```

The boundary is synchronous and supports Instrument Master and EOD Price Bar retrieval only. It has deterministic in-memory tests, a Massive mocked adapter skeleton, a secure credential-file loader, and a minimal HTTPS transport. A bounded Massive All Tickers snapshot has published the 2026-08-13 Instrument Master and resolver datasets. The corrected real Grouped Daily ingestion published the 2026-08-13 canonical EOD bars. No Dashboard API endpoint or production EOD bar serving workflow exists.


## Massive Mocked Adapter Boundary

The Massive package is available from:

```python
from tip_api.providers.massive import MassiveMarketDataProvider, MassiveProviderConfig
```

It implements configuration validation, credential redaction, injected transport, mocked response mapping, deterministic tests, and a standard-library HTTPS transport for controlled operations. Approved live operations so far are the one-request Stocks reference smoke test, the one-request Grouped Daily inspection for 2026-08-13, the bounded All Tickers snapshot publication for 2026-08-13, and the one-request Grouped Daily publication for 2026-08-13 that published canonical EOD bars. The Massive adapter must not be used for backfill, dashboard data, or additional live requests without a separate authorization.

## Local Setup

Use the repository-level instructions in [Local Development](../../docs/development/local-development.md).

## Current Non-Goals

- No public Dashboard serving of production `/data` EOD bars
- No authentication or authorization for private routes
- No database or ORM
- No authentication
- No order execution
- No production deployment configuration
