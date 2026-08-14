# Provider Instrument Identity V1

## Purpose

Provider Instrument Identity V1 records a point-in-time provider identity candidate and its resolution state against the canonical `InstrumentMasterV1` identifier space.

## Status

Implemented as a provider-neutral Pydantic contract and Parquet snapshot dataset. The first live Massive reference snapshot attempt did not publish because quality gates failed.

## Grain

One provider ticker identity candidate for one provider and one `as_of_date`.

## Fields

- `schema_version`
- `provider`
- `as_of_date`
- `provider_ticker`
- `provider_instrument_id`
- `composite_figi`
- `share_class_figi`
- `cik`
- `canonical_instrument_id`
- `resolution_status`
- `resolution_method`
- `valid_from`
- `valid_to`
- `source_updated_at`
- `ingested_at`
- `quality_status`
- `quality_flags`

## Enumerations

`resolution_status`:

- `resolved`
- `unresolved`
- `ambiguous`
- `rejected`

`resolution_method`:

- `share_class_figi`
- `composite_figi`
- `provider_stable_id`
- `unresolved`

## Rules

- Resolved records must carry `canonical_instrument_id`.
- Unresolved, ambiguous, and rejected records must not carry `canonical_instrument_id`.
- Ambiguous and rejected records must carry quality flags.
- `provider_ticker` is normalized but is not treated as a permanent key.
- CIK is preserved as an issuer clue and is not used alone for security identity.
- Timestamps are timezone-aware UTC.
- The contract stores no raw provider payload.

## Implementation Status

Implemented in Python at:

```python
from tip_api.contracts.market_data.v1 import ProviderInstrumentIdentityV1
```

Physical persistence is implemented for the point-in-time Instrument Master snapshot boundary. The first live snapshot run for 2026-08-13 did not publish because quality gates failed.

