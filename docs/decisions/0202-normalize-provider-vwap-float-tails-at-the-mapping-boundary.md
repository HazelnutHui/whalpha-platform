# ADR 0202: Normalize provider VWAP float tails at the mapping boundary

- Status: Accepted
- Date: 2026-09-10

## Context

The exact five-year EOD/Identity continuation stopped while building the
2022-12-05 EOD plan. The immutable Massive Grouped Daily package contains
11,084 rows. Exactly 314 non-null `vw` values use scales from 16 through 20;
representative values end in long `999...` or `000...1` tails. OHLC and volume
do not exceed the canonical scale in this package.

Quantizing those 314 values to the existing EOD scale of 10 with
round-half-even changes each value by no more than `0.0000000000000001`. This
is provider JSON serialization noise below the canonical VWAP resolution, not
evidence that the provider supplied a materially different price. The exact
source response is already retained in immutable owner-only custody.

The provider-neutral Parquet repository correctly rejected the values because
it must never round arbitrary canonical inputs. Silently dropping VWAP would
discard a usable optional fact; widening the physical EOD schema for binary
float tails would weaken an established cross-family numeric boundary.

## Decision

The Massive Grouped Daily mapping boundary normalizes only non-null VWAP whose
input scale exceeds 10:

- use exact `Decimal` input and an isolated local decimal context;
- quantize once to `0.0000000001` with `ROUND_HALF_EVEN`;
- add `vwap_scale_normalized` to every affected canonical row;
- retain `vwap_scale_normalized_count` and the same warning in the session
  quality summary and safe operator output; and
- use the same canonicalized VWAP in duplicate-equivalence comparison.

The immutable provider response remains unchanged and is the evidence for the
pre-normalized value. OHLC, volume, trade count, and timestamp parsing are not
changed. The provider-neutral EOD repository continues to reject every Decimal
whose precision exceeds 38 or scale exceeds 10. A normalized VWAP that becomes
invalid under the canonical model, or still exceeds physical precision, still
fails closed.

## Consequences

- Provider serialization tails no longer block otherwise valid EOD sessions.
- Canonical VWAP remains deterministic, storage-compatible, and visibly
  transformed rather than silently rounded.
- Duplicate rows that differ only below canonical VWAP resolution no longer
  become false conflicts.
- Historical content fingerprints legitimately bind the normalized canonical
  value and quality flag; source-package fingerprints remain unchanged.
- This decision does not authorize generic numeric coercion, schema widening,
  provider-response rewriting, missing-value imputation, or a relaxed quality
  gate.

## Supersession scope

This decision refines only Massive Grouped Daily VWAP mapping into EOD Price
Bar V1. It does not supersede the provider-neutral Decimal128 persistence
contract, corporate-action rules, price-adjustment semantics, or research
readiness gates.
