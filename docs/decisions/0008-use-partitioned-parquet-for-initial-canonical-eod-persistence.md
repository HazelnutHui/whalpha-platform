# ADR 0008: Use Partitioned Parquet for Initial Canonical EOD Persistence

## Status

Accepted

## Date

2026-08-14

## Context

The project has accepted normalized EOD logical contracts and has implemented provider-neutral Python contracts for Instrument Master V1 and EOD Price Bar V1. The next bounded implementation step needs a deterministic persistence slice for canonical EOD Price Bars before any real provider retrieval or production data-root write is authorized.

The workstation remains the source of truth for data processing. The future production data root is `/data/trading-intelligence-platform`, but this decision is implemented first through tests that write only to pytest temporary directories.

## Decision

Use partitioned, provider-neutral Parquet as the initial physical persistence format for canonical EOD Price Bar V1 records. Use PyArrow directly as the Parquet engine with an explicit Arrow schema rather than relying on DataFrame inference.

The initial V1 physical layout is:

```text
<root>/
  market-data/
    eod-price-bars/
      schema_version=1/
        session_date=YYYY-MM-DD/
          part-00000.parquet
          manifest.json
```

The physical `schema_version=1` partition represents canonical EOD Price Bar schema version `1.0`.

## Serialization

EOD Price Bar V1 records are sorted by canonical business key before serialization:

1. `instrument_id` string
2. `session_date`
3. `source`
4. `revision`

Decimals use explicit Arrow `decimal128(38, 10)` fields. Values that exceed the accepted precision or scale are rejected before writing rather than silently rounded. UTC timestamps use Arrow timestamp fields with an explicit UTC timezone. `session_date` uses Arrow `date32`.

## Manifest and Audit Metadata

Each completed partition has a `manifest.json` separate from the Parquet file. The manifest records non-sensitive audit metadata including dataset name, schema version, session date, provider ID, record count, content SHA-256, Parquet filename, quality summary, completion status, and creation timestamp.

The content fingerprint is generated from a stable JSON representation of the sorted canonical records. It excludes manifest creation time and does not use Python `hash()`.

## Atomic Publish and Idempotency

A publish writes to a staging directory beside the target partition, validates the written Parquet file, writes the manifest with an atomic rename, and then atomically publishes the completed partition directory.

Rerun behavior:

- Missing target partition: create it.
- Existing completed partition with identical content fingerprint: return idempotent `already_present` status.
- Existing completed partition with different content fingerprint: reject as a conflict.
- Existing incomplete, corrupted, or inconsistent partition: reject and do not overwrite.

No `--force` overwrite path is introduced.

## Storage Boundary

The repository implementation accepts an explicit caller-provided root. Production use should point to `/data/trading-intelligence-platform` only after a separate production retrieval and publishing review. Current tests use only pytest `tmp_path` directories.

Provider raw payloads are not persisted in this slice. Raw, normalized, and derived layers remain conceptually separate.

## Consequences

- The project now has an executable, deterministic persistence boundary for one-session canonical EOD Price Bars.
- Parquet persistence is still limited to EOD Price Bar V1.
- Identical reruns are safe to recognize without rewriting data.
- Conflicting reruns are intentionally rejected instead of silently overwriting prior content.
- PyArrow becomes an explicit backend runtime dependency.

## Deferred Decisions

- One-session real Massive Grouped Daily retrieval and validation.
- Production publishing to `/data/trading-intelligence-platform`.
- Full-market ticker-to-instrument identity resolution.
- Raw provider payload retention.
- Corporate-action adjustment reconciliation.
- Revision replacement workflow.
- Parquet compaction and retention.
- Catalog or database introduction threshold.
- Historical backfill and scheduling.

## Non-Goals

- Calling Massive or any real provider.
- Reading provider credentials.
- Writing production datasets under `/data`.
- Implementing Parquet persistence for Instrument Master, Corporate Actions, Classification, or Universe Membership.
- Implementing analytics, Dashboard APIs, scheduler, retry, rate limiting, or database/catalog infrastructure.
