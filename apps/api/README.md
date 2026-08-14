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

These are validation models only. They do not implement provider adapters, persistence, Parquet writing, market-data ingestion, analytics, or new API endpoints.


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

The boundary is synchronous and supports Instrument Master and EOD Price Bar retrieval only. It has deterministic in-memory tests, but no production provider adapter, network access, credentials, ingestion, persistence, or API endpoint.

## Local Setup

Use the repository-level instructions in [Local Development](../../docs/development/local-development.md).

## Current Non-Goals

- No market data provider integration
- No database or ORM
- No authentication
- No order execution
- No production deployment configuration
