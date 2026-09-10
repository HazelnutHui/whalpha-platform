# Instrument Identity Resolution

## Purpose

This document records the V1 identity-resolution boundary required before publishing real EOD bars.

## Status

Implemented as deterministic UUIDv5 resolution helpers, a `ProviderInstrumentIdentityV1` contract, and a bounded Massive Instrument Master snapshot ingestion path. The first live Massive snapshot attempt completed pagination but did not publish because quality gates were too broad. After separating expected exclusions from malformed records and changing the coverage denominator to eligible records, the second run passed gates and published the 2026-08-13 point-in-time snapshots.

## Stable Identifier Priority

V1 uses the following priority order:

1. Share Class FIGI
2. Composite FIGI
3. Provider stable instrument identifier, only when present in the provider payload
4. Unresolved

Ticker alone and CIK alone are intentionally insufficient.

## UUID Strategy

Canonical `instrument_id` values are UUIDv5 values generated from a controlled project namespace and a normalized identity key such as:

- `share_class_figi:<value>`
- `composite_figi:<value>`
- `provider_stable_id:<value>`

The namespace is defined in code as `CANONICAL_INSTRUMENT_NAMESPACE`. Python random UUIDs and Python hash values are not used.

## Collision and Ambiguity

If the same stable identifier maps to incompatible provider records in the
same snapshot, the affected records are marked ambiguous and are excluded from
canonical Instrument Master and Resolver publication. The records remain in
the eligible denominator; no ticker winner or lifecycle interval is inferred.

ADR 0116 permits a collision-observation ratio no greater than 0.1% for
prospective/current snapshots. ADR 0201 adds a separate 1.0% catastrophic
ceiling for later-observed historical reconstruction, where provider alias
revisions can be materially denser. The applied ceiling and actual count/ratio
remain in immutable evidence. Crossing the applicable ceiling still blocks
the complete snapshot.

## Current Live Result

For the 2026-08-13 Massive All Tickers snapshot attempt:

- request_count: 14
- raw_record_count: 13,106
- unique_ticker_count: 13,104
- duplicate_ticker_count: 2
- resolved_count: 10,116
- unresolved_count: 1,536
- ambiguous_count: 0
- rejected_count: 1,454
- identity_coverage_ratio: 77.1860%
- publication status: first run blocked; corrected second run published with 9,932 canonical instruments and 9,932 resolver entries

No raw payload, Parquet partition, or completed snapshot marker was published.

## Deferred Work

- provider type mapping review for rejected records
- unresolved identity review
- duplicate ticker handling policy
- ticker-change continuity
- merger and spinoff lineage
- Issuer Master introduction
- historical identity backfill
