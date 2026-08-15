# EOD Price Bar V1

## Purpose

EOD Price Bar V1 records end-of-day price and volume facts for an instrument and trading session.

## Status

Implemented Python Contract

## Grain

One record represents one instrument, one exchange trading session, one source, and one revision.

## Business Key

`instrument_id + session_date + source + revision`

## Fields

Core fields:

- instrument_id
- session_date
- open
- high
- low
- close
- volume
- vwap
- trade_count
- notional
- currency

Adjustment fields:

- split_adjustment_factor
- dividend_adjustment_factor
- total_return_adjustment_factor
- adjusted_close

Audit and quality:

- source
- source_record_id
- ingested_at
- revision
- is_latest_revision
- quality_status
- quality_flags
- schema_version

## Nullable Fields

- vwap
- trade_count
- source_record_id
- quality_flags

Missing VWAP or trade count remains null.

## Enumerations

`quality_status` values remain implementation-defined but must distinguish usable, suspect, missing, and rejected records.

## Validation Rules

- Basic OHLC consistency must be validated.
- A halt or no-trade session must not be represented as OHLC=0.
- Raw OHLC is never replaced by adjusted OHLC.
- Missing values are not silently converted to zero.
- Volume adjustment semantics must be explicit.
- V1 retains provider raw volume and allows normalized comparable volume separately.

## Temporal Semantics

`session_date` follows the primary exchange trading calendar and must not be derived by naive UTC truncation. `ingested_at` uses UTC.

## Revision Semantics

Provider corrections create traceable revisions. `is_latest_revision` identifies the current preferred revision, but previous revisions remain auditable.

## Return Conventions

- Default market-strength price return uses split-adjusted price behavior.
- Price return and total return remain separate.
- Cash dividends must not automatically be interpreted as genuine price weakness.
- Total-return analysis is used only when dividend effects are intentionally included.
- Chart display defaults to raw OHLC.
- Continuous historical analytics can construct adjusted OHLC from explicit factors.

## Provider Mapping Boundary

Provider bar records map into this contract. Analytics should consume canonical fields and explicit adjustment factors, not provider-specific adjustment assumptions.

## Storage Direction

Parquet-first. EOD Price Bar V1 now has an explicit PyArrow schema and a bounded one-session partition layout documented in [EOD Parquet Persistence](../architecture/eod-parquet-persistence.md). Current implementation writes mocked-fixture test partitions under pytest temporary directories. One real 2026-08-13 Grouped Daily publication attempt was blocked by quality gates, so no production EOD Price Bar partition exists.

## Deferred Fields

- normalized comparable volume
- detailed market-session metadata
- intraday bars

## Non-Goals

- intraday data
- total-return index construction
- production Parquet publishing
- provider adapter implementation

## Python Implementation

Import path:

```python
from tip_api.contracts.market_data.v1 import EodPriceBarV1
```

The implementation is a provider-neutral Pydantic v2 model. It is immutable, forbids extra fields, validates Decimal price and adjustment values without converting them to binary floats, requires timezone-aware `ingested_at`, normalizes `ingested_at` to UTC, rejects datetime input for `session_date`, and normalizes `quality_flags` to deduplicated lowercase snake_case while preserving first occurrence order.

Validation tests cover valid bars, nullable fields, zero volume, revision bounds, non-negative volume/trade count/notional, positive OHLC and adjustment values, OHLC consistency, source and currency validation, naive datetime rejection, UTC normalization, NaN/Infinity rejection, float rejection for Decimal fields, quality flag normalization, frozen behavior, extra-field rejection, Decimal JSON serialization, `session_date` strictness, and the fact that the model does not calculate `notional` or `adjusted_close`.

## Implementation Status

- Provider-neutral Pydantic model implemented.
- Validation and serialization tests implemented.
- Mocked-fixture one-session ingestion service implemented.
- Explicit PyArrow Parquet repository implemented for EOD Price Bar V1.
- Manifest, deterministic content fingerprint, idempotency, conflict rejection, and corruption checks implemented.
- No corporate-action adjustment calculation implemented.
- Real Grouped Daily ingestion entrypoint implemented with strict quality gates.
- One real 2026-08-13 publication attempt failed gates and did not publish.
- No production EOD Price Bar `/data` partition exists.
- No historical backfill, scheduler, analytics, or Dashboard data API implemented.
