# ADR 0009: Use Stable Provider Identifiers for Canonical Instrument Identity

## Status

Accepted

## Date

2026-08-14

## Context

The first Massive Grouped Daily inspection verified data access and payload structure, but EOD bar publication was blocked because provider tickers could not yet be resolved to canonical `instrument_id` values. The platform needs a point-in-time Instrument Master snapshot and a provider identity map before canonical EOD bars can be safely persisted.

Tickers are not permanent security identifiers. CIK is an issuer clue and may not identify a security or share class. The project therefore needs a stable, provider-neutral identity resolution strategy before using real provider bars.

## Decision

V1 canonical instrument IDs are deterministic UUIDv5 values generated from stable provider identifiers using a controlled project namespace.

Identifier priority:

1. `share_class_figi`
2. `composite_figi`
3. explicit provider stable instrument identifier when the provider payload actually contains one
4. otherwise unresolved

CIK alone and ticker alone do not generate canonical security-level instrument IDs.

A new `ProviderInstrumentIdentityV1` contract records provider identity candidates, resolution status, resolution method, quality flags, point-in-time validity, and optional canonical `instrument_id` linkage.

## Snapshot Persistence

Instrument Master snapshots are persisted as two Parquet datasets plus a logical snapshot manifest:

```text
<root>/
  market-data/
    instrument-master/
      schema_version=1/
        as_of_date=YYYY-MM-DD/
          part-00000.parquet
          manifest.json
    provider-instrument-identity/
      schema_version=1/
        provider=massive_stocks_basic/
          as_of_date=YYYY-MM-DD/
            part-00000.parquet
            manifest.json
    snapshots/
      instrument-master/
        as_of_date=YYYY-MM-DD/
          manifest.json
```

The snapshot manifest is the final logical completion marker. Readers must not treat dataset partitions as complete without the completed snapshot marker.

## Quality Gates

V1 Candidate Gates are implementation guards, not permanent thresholds:

- raw record count greater than 5,000
- unique ticker ratio at least 99.9%
- resolved identity coverage at least 80%
- ambiguous identity count is zero
- rejected or malformed ratio no greater than 5%
- canonical Instrument Master validation passes
- no stable-ID collision
- pagination reaches completion within 20 requests
- no raw payload or credential persistence

Failed gates block publication.

## Consequences

## Clarification: Quality Gates

Expected V1 universe exclusions are not malformed provider data and do not enter the eligible identity coverage denominator. Ticker-level ambiguity is tracked separately from stable-identifier collision. ADR 0116 narrowly supersedes the original absolute-zero collision gate: every collision remains quarantined, but a collision-observation ratio no greater than 0.1% may be isolated from Instrument/Resolver output without blocking unrelated instruments. A higher ratio remains a hard failure.


- Canonical identity is stable across reruns for the same stable identifier.
- Provider identity mapping is auditable and point-in-time.
- Ticker-only and CIK-only records remain unresolved instead of receiving weak IDs.
- Real EOD bar publication remains blocked until identity coverage and quality gates pass.

## Deferred Decisions

- ticker-change continuity across history
- merger, spinoff, and successor lineage
- Issuer Master introduction
- corporate-action identity reconciliation
- historical identity backfill
- database/catalog service
- provider raw payload retention

## Non-Goals

- Grouped Daily bar publication
- corporate-action ingestion
- provider raw response persistence
- Dashboard data API
- scheduling or backfill
- OCI deployment
