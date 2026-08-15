# Provider Ticker Resolver V1

## Purpose

Provider Ticker Resolver V1 is a strict point-in-time projection from provider ticker to canonical `instrument_id` for EOD bar resolution.

## Status

Implemented as a Pydantic contract and Parquet dataset for the 2026-08-13 Massive Instrument Master snapshot.

## Grain

One unique `(provider, as_of_date, provider_ticker)` resolver entry.

## Fields

- `schema_version`
- `provider`
- `as_of_date`
- `provider_ticker`
- `canonical_instrument_id`
- `resolution_method`
- `source_identity_key`
- `ingested_at`

## Rules

- Only unique, eligible, resolved provider tickers enter the resolver.
- Unresolved, excluded, rejected, and ticker-ambiguous records are absent.
- The resolver is point-in-time and must not be projected backward into history.
- Ticker is a lookup key for a specific provider/date, not a permanent canonical primary key.

## Implementation Status

Implemented in Python at:

```python
from tip_api.contracts.market_data.v1 import ProviderTickerResolverV1
```

The first completed Massive resolver snapshot for 2026-08-13 contains 9,932 entries.

