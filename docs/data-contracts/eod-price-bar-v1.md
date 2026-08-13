# EOD Price Bar V1

## Purpose

EOD Price Bar V1 records end-of-day price and volume facts for an instrument and trading session.

## Status

Accepted Logical Contract — Not Yet Implemented

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

Parquet-first. Partition by practical date boundaries such as year/month. Avoid one-file-per-ticker small-file proliferation. Raw, normalized, and derived datasets remain separate.

## Deferred Fields

- normalized comparable volume
- detailed market-session metadata
- intraday bars

## Non-Goals

- intraday data
- total-return index construction
- physical Parquet schema implementation
- provider adapter implementation
