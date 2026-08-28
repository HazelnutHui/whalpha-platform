# Massive Adapter Boundary

## Security-Type Evidence

Phase B1 permits only one Ticker Types request and bounded point-in-time All Tickers pagination. The adapter preserves official codes/descriptions and joins with stable identifiers or the accepted point-in-time resolver. Raw responses are not persisted. Provider common-stock type proves security form only; it cannot establish issuer structure, domicile, or Core/Broad eligibility.

## Same-day catch-up boundary

Instrument Master and Grouped Daily administrator ingestion now use the
[Same-Day Identity and EOD Catch-Up V1](../data-contracts/same-day-identity-eod-catchup-v1.md)
four-stage contract. Only fetch-only can create a transport or load the Massive
credential. It can write only a hashed package below `/tmp`. Offline plan and
apply retain the existing mapping and quality semantics, but an apply is bound
to a separately approved deterministic plan and expected inventory state.
There is no remaining supported network-to-production caller or scheduler.

## Purpose

This document records the implemented Massive Stocks adapter skeleton boundary. The adapter exists to validate configuration, credential handling, transport injection, provider response mapping, and a controlled one-request reference smoke test against canonical boundaries.

## Status

Implemented Bounded Identity and EOD Boundary

Implemented:

- configuration contract
- credential safety boundary
- mocked HTTP transport boundary
- credential-file loader with ownership and permission checks
- standard-library HTTPS transport
- one-request read-only Stocks reference smoke test
- one-request read-only Grouped Daily inspection for 2026-08-13
- Massive All Tickers mapping to Instrument Master V1
- Massive Grouped Daily and Custom Bars mapping to EOD Price Bar V1
- deterministic internal UUID strategy for mocked mapping
- local mocked-response tests
- bounded point-in-time Identity and Grouped Daily acquisition/Apply workflows
- fixed serial pacing, request-count evidence, and immutable attempt custody at
  the administrator workflow layer

Not implemented:

- corporate-action and lifecycle adapters
- verified split/dividend/total-return adjustment ledgers
- general 252/504-session historical research backfill
- unattended scheduler activation
- complete inactive/delisted and successor reconciliation

## Configuration Environment-Variable Contract

The configuration model is `MassiveProviderConfig`.

Environment variables:

- `TIP_MASSIVE_API_KEY`: required credential variable; real values must never be committed, pasted into chat, logged, placed in command history, placed in process arguments, or exposed in frontend bundles.
- `TIP_MASSIVE_BASE_URL`: optional override; defaults to `https://api.massive.com`.
- `TIP_MASSIVE_REQUEST_TIMEOUT_SECONDS`: optional positive finite timeout; defaults to `15`.

No `.env` file is committed. No `.env.example` is currently required. The accepted credential file path is documented in [Massive Credential Provisioning](../operations/massive-credential-provisioning.md).

## Credential Redaction Rules

The API key is represented with Pydantic `SecretStr`. It is trimmed, required, and excluded from normal representations. Adapter errors and transport call records must not include credential values.

The adapter must not place the API key in ordinary query parameters. The standard-library HTTPS transport sends credentials through an Authorization bearer header. Credentials must remain server-side and must not enter ordinary query parameters.

## Adapter Responsibilities

`MassiveMarketDataProvider` implements the provider-neutral `MarketDataProvider` Protocol for the currently supported capabilities:

- `instrument_master`
- `eod_price_bars`

It returns canonical contract tuples only:

- `tuple[InstrumentMasterV1, ...]`
- `tuple[EodPriceBarV1, ...]`

It does not return raw Massive JSON, dictionaries, provider-specific objects, DataFrames, generators, or frontend payloads.

## Transport Dependency Boundary

The adapter depends on the `MassiveHttpTransport` Protocol. A minimal standard-library HTTPS transport is implemented for controlled operations. Tests continue to use a deterministic fake under `apps/api/tests/providers/support`; ordinary unit tests do not perform network access.

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

The adapter strips `apiKey` from `next_url` query params, validates the next URL
host against the configured base URL, detects pagination loops, and enforces a
page limit. Bounded administrator ingestion applies fixed serial pacing and no
concurrency burst; the adapter itself still does not sleep or retry. A future
252/504-session planner must preserve central pacing, bounded `Retry-After`,
resumability, idempotency, and request audit without secrets.

## Real-Network Activation Prerequisites

The 2026-08-13 Grouped Daily inspection verified access and payload shape without publishing. After the point-in-time resolver was published and Decimal aggregate volume was accepted, one authorized Grouped Daily ingestion for 2026-08-13 passed quality gates and published canonical EOD bars. Duplicate-bar isolation and identity-ordering fixes remain in force.

Before any additional Massive request:

1. Persistence and validation boundaries must be reviewed.
2. Request pacing and failure handling must be designed.
3. Provider terms and access boundary must be rechecked.
4. Any one-session real retrieval must be separately authorized.
5. No provider-backed data may be exposed publicly without private access control and licensing review.

## Non-Goals

## Instrument Master Snapshot Status

A bounded All Tickers pagination path now exists for point-in-time Instrument Master snapshot ingestion. It uses the existing credential and transport boundary and does not store raw provider payloads. The first live run completed 14 reference requests for 2026-08-13 but did not publish because the initial gates were too broad. After refining expected exclusions, eligible coverage, and ticker ambiguity handling, the second run published the point-in-time Instrument Master, identity, and ticker resolver snapshots.

- storing, printing, logging, or committing a real API key
- writing database records
- implementing corporate actions
- implementing complete lifecycle/lineage resolution
- implementing a general research-history backfill
- activating an unattended scheduler
- exposing provider-backed data publicly
