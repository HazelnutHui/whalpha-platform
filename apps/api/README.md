# Trading Intelligence API

FastAPI backend scaffold for Trading Intelligence Platform.

## Purpose

The API package provides typed contracts for the future dashboard and canonical market-data boundary. The current HTTP scaffold only exposes the Health endpoint, while selected data contracts are implemented as provider-neutral Pydantic models.

## Current Endpoint

- `GET /api/v1/health`

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

These are validation models. EOD Price Bar V1 now has a bounded mocked-fixture Parquet persistence and one-session ingestion slice. A real 2026-08-13 Grouped Daily ingestion attempt ran once but failed publication gates, so no production EOD bar partition, analytics, or new API endpoints are implemented.

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

The boundary is synchronous and supports Instrument Master and EOD Price Bar retrieval only. It has deterministic in-memory tests, a Massive mocked adapter skeleton, a secure credential-file loader, and a minimal HTTPS transport. A bounded Massive All Tickers snapshot has published the 2026-08-13 Instrument Master and resolver datasets. The first real Grouped Daily publication attempt did not publish because quality gates failed. No Dashboard API endpoint or production EOD bar serving workflow exists.


## Massive Mocked Adapter Boundary

The Massive package is available from:

```python
from tip_api.providers.massive import MassiveMarketDataProvider, MassiveProviderConfig
```

It implements configuration validation, credential redaction, injected transport, mocked response mapping, deterministic tests, and a standard-library HTTPS transport for controlled operations. Approved live operations so far are the one-request Stocks reference smoke test, the one-request Grouped Daily inspection for 2026-08-13, the bounded All Tickers snapshot publication for 2026-08-13, and one Grouped Daily publication attempt for 2026-08-13. The Grouped Daily attempt failed quality gates and did not publish. The Massive adapter must not be used for backfill, dashboard data, or additional live requests without a separate authorization.

## Local Setup

Use the repository-level instructions in [Local Development](../../docs/development/local-development.md).

## Current Non-Goals

- No published real EOD bar ingestion
- No Dashboard API over real EOD bars
- No production `/data` writes from failed EOD quality-gated runs
- No database or ORM
- No authentication
- No order execution
- No production deployment configuration
