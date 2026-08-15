# ADR 0010: Represent Aggregate Volume as Decimal

## Status

Accepted

## Date

2026-08-14

## Context

Massive Stocks Aggregates documentation reviewed on 2026-08-14 defines aggregate volume `v` as a JSON number, while trade count `n` and timestamp `t` are integer-semantic fields. The first Grouped Daily publication attempts exposed that treating aggregate volume as an integer caused valid provider records with fractional aggregate volume to fail numeric validation before the first canonical EOD session could be published.

No completed production EOD Price Bar partition existed before this decision, so the V1 contract can be corrected before first production publication without migrating existing EOD data.

## Decision

`EodPriceBarV1.volume` is represented as an exact non-negative `Decimal`.

Provider mapping boundaries must convert accepted JSON numeric values to Decimal with `Decimal(str(value))`. Canonical contracts continue to reject direct binary-float Decimal field input. Bool, non-finite values, malformed strings, and silent rounding or truncation are rejected.

`trade_count` remains a nullable non-negative integer. Provider timestamps remain required integer milliseconds.

EOD Price Bar Parquet volume uses `decimal128(38, 10)`. The physical `schema_version=1` partition is retained because no production EOD Price Bar partition existed before this pre-first-publication correction.

## Consequences

- Fractional aggregate volume is valid when supplied by a provider as a finite number.
- Provider adapters must not truncate aggregate volume.
- Duplicate bar comparison and content fingerprints use canonical Decimal numeric normalization, so `10`, `10.0`, and `10.00` are equivalent for volume.
- Future providers must map aggregate volume into the same canonical Decimal semantics.
- Existing Instrument Master snapshots are unaffected.

## Alternatives Considered

- Keep volume as integer: rejected because it conflicts with the provider aggregate field contract and fractional-share activity.
- Store provider volume as string: rejected because canonical analytics and Parquet persistence require typed numeric validation.
- Upgrade physical EOD schema version: rejected for now because no completed production EOD Price Bar partition existed before this correction.

## Non-Goals

- split/dividend adjustment reconciliation
- historical backfill
- intraday volume semantics
- migration of previously published EOD datasets
- Dashboard or API exposure
