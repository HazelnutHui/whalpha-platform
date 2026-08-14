# Instrument Master V1

## Purpose

Instrument Master V1 maintains stable security identity. It does not store prices, classifications, universe membership, market cap, or volume.

## Status

Implemented Python Contract

## Grain

One record represents an instrument identity for a defined temporal validity range and source revision context.

## Stable Identifier

`instrument_id` is the stable internal key.

## Fields

Internal identity:

- instrument_id
- issuer_id
- instrument_type
- status
- schema_version

Market identity:

- ticker
- name
- primary_exchange
- listing_country
- currency
- figi
- cik

Temporal validity:

- valid_from
- valid_to
- first_trade_date
- last_trade_date
- as_of_date

Source and quality:

- source
- source_instrument_id
- ingested_at
- quality_status
- quality_notes

## Nullable Fields

- issuer_id
- figi
- cik
- valid_to
- first_trade_date
- last_trade_date
- quality_notes

Unknown values remain null.

## Enumerations

Initial `instrument_type` values:

- common_stock
- etf

Initial `status` values:

- active
- inactive
- delisted

## Validation Rules

- `instrument_id` is the stable internal key.
- `ticker` is not a permanent key.
- Ticker changes normally do not create a new instrument.
- Different share classes are different instruments.
- Issuer and instrument are different concepts.
- ETF and common stock are explicitly distinguished.
- Classifications do not belong in Instrument Master.
- Universe membership does not belong in Instrument Master.
- Market cap, price, and volume do not belong in Instrument Master.
- Temporal history is retained rather than silently overwritten.

## Temporal Semantics

Validity fields describe when the identity record applies. `as_of_date` records the reference date for the provider or mapping state.

## Revision Semantics

Instrument identity changes must be traceable. Ticker or status corrections should preserve historical auditability.

## Provider Mapping Boundary

Provider identifiers map into `source_instrument_id` and source-specific mapping records. Domain logic should use `instrument_id`.

## Deferred Fields

- complete Issuer Master
- full share-class relationship model
- detailed listing venue history beyond V1 needs

## Non-Goals

- issuer fundamentals
- price history
- universe membership
- classification membership
- provider adapter implementation

## Python Implementation

Import path:

```python
from tip_api.contracts.market_data.v1 import InstrumentMasterV1
```

The implementation is a provider-neutral Pydantic v2 model. It is immutable, forbids extra fields, normalizes ticker/exchange/country/currency text, preserves CIK as a string, requires timezone-aware `ingested_at`, and normalizes `ingested_at` to UTC.

Validation tests cover valid common stock and ETF records, optional issuer/FIGI/CIK fields, ticker normalization, accepted share-class ticker forms, date ordering, required string fields, country/currency formatting, UTC normalization, naive datetime rejection, frozen behavior, extra-field rejection, JSON serialization, and the fact that ticker does not determine `instrument_id`.

## Implementation Status

Provider Instrument Identity V1 and a bounded Instrument Master snapshot ingestion path now exist. The first live Massive All Tickers run for 2026-08-13 did not publish an Instrument Master snapshot because quality gates failed. Instrument Master V1 remains the canonical contract for resolved instruments only; unresolved provider identities are tracked separately.

- Provider-neutral Pydantic model implemented.
- Validation and serialization tests implemented.
- No provider mapping implemented.
- No persistence implemented.
- No Parquet writer implemented.
- No market-data ingestion implemented.
