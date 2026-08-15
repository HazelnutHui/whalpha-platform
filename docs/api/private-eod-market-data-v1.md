# Private EOD Market Data V1

## Purpose

Private EOD Market Data V1 exposes read-only, provider-neutral responses for completed canonical EOD sessions.

## Status

Implemented for local/private development. Routes are default-disabled and must not be treated as public access control.

## Enablement

Routes are registered only when:

```text
TIP_ENABLE_PRIVATE_MARKET_DATA_ROUTES=true
```

Default is false. In the default app and default OpenAPI schema, these routes are absent.

The market-data root is configured by `TIP_MARKET_DATA_ROOT`, defaulting to `/data/trading-intelligence-platform`. API callers cannot override this path.

## Routes

- `GET /api/v1/private/market-data/eod/sessions`
- `GET /api/v1/private/market-data/eod/sessions/latest`
- `GET /api/v1/private/market-data/eod/sessions/{session_date}/summary`
- `GET /api/v1/private/market-data/eod/sessions/{session_date}/bars`

`bars` supports:

- `limit`: default 100, minimum 1, maximum 200
- `offset`: default 0, minimum 0
- `ticker`: optional canonical ticker filter
- `instrument_type`: optional canonical instrument type filter

There is no full export endpoint, arbitrary sort parameter, arbitrary filter expression, or raw manifest endpoint.

## Response Contracts

Responses are Pydantic models under `tip_api.schemas.private_eod`.

Decimal values are serialized as exact strings:

- `open`
- `high`
- `low`
- `close`
- `volume`
- `vwap` when present

Responses may include joined ticker and name from the completed point-in-time Instrument Master and Provider Ticker Resolver snapshots. Responses do not include raw provider payloads, filesystem paths, raw manifest content, credentials, or authorization headers.

## Errors

- Unknown session: `404`
- Invalid query/date: `422`
- Corrupted, incomplete, or unavailable dataset: `503`

Error responses intentionally avoid leaking local paths, manifest details, tracebacks, or provider payloads.

## Non-Goals

- authentication or authorization
- frontend integration
- public data service
- analytics, returns, breadth, heatmap, or sector calculations
- Massive API requests
- writes to Parquet or `/data`
- OCI deployment
