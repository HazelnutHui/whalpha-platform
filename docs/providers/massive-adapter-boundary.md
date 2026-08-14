# Massive Adapter Boundary

## Purpose

This document records the implemented Massive Stocks adapter skeleton boundary. The adapter exists to validate configuration, credential handling, transport injection, and provider response mapping against canonical contracts without making real network requests.

## Status

Implemented Mocked Boundary — No Real Network

Implemented:

- configuration contract
- credential safety boundary
- mocked HTTP transport boundary
- Massive All Tickers mapping to Instrument Master V1
- Massive Grouped Daily and Custom Bars mapping to EOD Price Bar V1
- deterministic internal UUID strategy for mocked mapping
- local mocked-response tests

Not implemented:

- real API key
- real account entitlement verification
- production HTTP transport
- real network request
- real data ingestion
- Parquet persistence
- scheduling
- rate limiter
- retry policy
- complete pagination/backfill
- split/dividend reconciliation
- production identity master
- private access control
- OCI deployment

## Configuration Environment-Variable Contract

The configuration model is `MassiveProviderConfig`.

Environment variables:

- `TIP_MASSIVE_API_KEY`: required future credential variable; real values must never be committed, pasted into chat, logged, placed in command history, or exposed in frontend bundles.
- `TIP_MASSIVE_BASE_URL`: optional override; defaults to `https://api.massive.com`.
- `TIP_MASSIVE_REQUEST_TIMEOUT_SECONDS`: optional positive finite timeout; defaults to `15`.

No `.env` file is committed. No `.env.example` is currently required.

## Credential Redaction Rules

The API key is represented with Pydantic `SecretStr`. It is trimmed, required, and excluded from normal representations. Adapter errors and transport call records must not include credential values.

The adapter must not place the API key in ordinary query parameters. Future real transport should send credentials through a dedicated server-side credential boundary, such as an authorization header or equivalent reviewed mechanism.

## Adapter Responsibilities

`MassiveMarketDataProvider` implements the provider-neutral `MarketDataProvider` Protocol for the currently supported capabilities:

- `instrument_master`
- `eod_price_bars`

It returns canonical contract tuples only:

- `tuple[InstrumentMasterV1, ...]`
- `tuple[EodPriceBarV1, ...]`

It does not return raw Massive JSON, dictionaries, provider-specific objects, DataFrames, generators, or frontend payloads.

## Transport Dependency Boundary

The adapter depends on the `MassiveHttpTransport` Protocol. No production HTTP transport is implemented. Tests use a deterministic fake under `apps/api/tests/providers/support`.

The fake records only sanitized request path, query params, timeout, and whether a credential was supplied. It does not record credential values.

## Endpoint Mapping Assumptions

Implemented mocked mappings:

- All Tickers: `/v3/reference/tickers`
- Grouped Daily: `/v2/aggs/grouped/locale/us/market/stocks/{date}`
- Custom Bars: `/v2/aggs/ticker/{ticker}/range/1/day/{from}/{to}`

Grouped Daily and Custom Bars requests explicitly send `adjusted=false` so raw OHLC can be mapped preferentially from unadjusted aggregate semantics.

## Deterministic Internal UUID Strategy

Mocked V1 mapping uses UUIDv5 with a controlled project namespace and a provider identity string composed from source ticker, Composite FIGI, Share Class FIGI, and CIK where available.

This is deterministic and reproducible, but it is not a complete production identity-resolution system. Provider identity continuity across ticker changes, mergers, share-class changes, delistings, and incomplete FIGI/CIK records remains an implementation limitation.

## Adjustment Limitations

The current mapper sets split, dividend, and total-return adjustment factors to neutral `1` and sets `adjusted_close` equal to raw close while marking `adjustment_factors_unverified` in quality flags.

This is a temporary mocked boundary behavior. Split/dividend reconciliation and adjusted history construction are not solved.

## Error Mapping

Transport response errors are mapped to provider-neutral errors:

- HTTP 401/403: `ProviderAuthenticationError`
- HTTP 429: `ProviderRateLimitError` with optional `retry_after_seconds`
- timeout/unavailable/other HTTP failure: `ProviderUnavailableError`
- malformed provider payload: `ProviderDataError`

The adapter does not sleep, retry, or expose raw response bodies.

## Pagination and Rate-Limit Boundary

The adapter includes minimal pagination support for deterministic mocked tests. It strips `apiKey` from `next_url` query params, validates the next URL host against the configured base URL, detects pagination loops, and enforces a page limit.

A real rate limiter is not implemented. Future adapter work must respect the Basic plan's 5 calls/minute limit with central pacing, no concurrency burst, resumable backfill, and request audit without secrets.

## Real-Network Activation Prerequisites

Before any real Massive request:

1. User account entitlement must be verified.
2. Credential storage must be selected and documented.
3. The real API key must be provisioned on `dell5820` without entering Git, documentation, chat, command history, process arguments, or logs.
4. A production HTTP transport must be reviewed.
5. One minimal read-only smoke test must be explicitly approved.
6. Provider terms and access boundary must be rechecked.

## Non-Goals

- creating or reading a real API key
- making Massive API calls
- implementing production HTTP transport
- implementing ingestion
- writing Parquet or database records
- implementing scheduling, retries, or full backfill
- implementing corporate actions
- implementing real identity resolution
- exposing provider-backed data publicly
