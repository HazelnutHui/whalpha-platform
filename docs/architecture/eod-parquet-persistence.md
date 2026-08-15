# EOD Parquet Persistence

## Purpose

This document records the implemented V1 physical persistence boundary for canonical EOD Price Bar data. It is the first bounded storage slice for validated canonical records, not a full ingestion platform.

## Status

Implemented for EOD Price Bar V1. The first production canonical EOD session for 2026-08-13 has been published after Decimal aggregate volume correction. No historical backfill, scheduler, analytics, database, or Dashboard data API is implemented.

## Implemented Boundary

Implemented package boundary:

- `tip_api.ingestion.EodSessionIngestionService`
- `tip_api.persistence.EodPriceBarRepository`
- `tip_api.persistence.parquet.ParquetEodPriceBarRepository`

The ingestion service coordinates a single `session_date`, uses the existing provider-neutral `MarketDataProvider` boundary, validates canonical `EodPriceBarV1` records, and publishes through a repository. The repository accepts only canonical EOD Price Bar contracts and has no dependency on Massive-specific packages.

## Physical Layout

V1 layout:

```text
<root>/
  market-data/
    eod-price-bars/
      schema_version=1/
        session_date=YYYY-MM-DD/
          part-00000.parquet
          manifest.json
```

The physical `schema_version=1` partition corresponds to logical schema version `1.0`.

Tests use pytest `tmp_path` roots. The approved production root is `/data/trading-intelligence-platform`; the first completed EOD Price Bar partition is for session_date=2026-08-13.

## Arrow Schema

The repository uses an explicit PyArrow schema:

- `instrument_id`: string UUID representation
- `session_date`: `date32`
- OHLC, VWAP, notional, adjustment factors, and adjusted close: `decimal128(38, 10)`
- `volume`: `decimal128(38, 10)`
- `trade_count`: nullable int64
- `ingested_at`: UTC timestamp with microsecond precision
- `quality_flags`: deterministic list of strings
- source, revision, latest flag, quality status, and schema version fields are preserved

Decimal values exceeding precision 38 or scale 10 are rejected before write. Values are not converted to binary float.

## Determinism

Records are sorted by:

1. `instrument_id` string
2. `session_date`
3. `source`
4. `revision`

The content fingerprint is a SHA-256 hash over a stable JSON representation of sorted canonical rows. The fingerprint is independent of input order and excludes manifest creation time.

## Manifest

`manifest.json` contains:

- `manifest_version`
- `dataset_name`
- `schema_version`
- `session_date`
- `provider_id`
- `record_count`
- minimum and maximum instrument IDs
- minimum and maximum session dates
- `content_sha256`
- `parquet_file`
- `created_at`
- `quality_summary`
- `completion_status`

The manifest must not contain credentials, authorization headers, provider raw responses, account identifiers, or personal information.

## Atomic Publish

Publish behavior:

1. Validate canonical records for one session.
2. Sort records deterministically.
3. Compute content fingerprint.
4. Write Parquet into a same-parent staging directory.
5. Read the Parquet file back and validate schema, row count, session date, and fingerprint.
6. Write manifest via temporary file and atomic rename.
7. Atomically publish the completed partition directory.
8. Clean up this operation's staging directory on failure.

The implementation rejects symlink roots and symlink partition paths. It does not delete or overwrite existing completed partitions.

## Rerun Behavior

- Identical rerun: returns `already_present` and writes no rows.
- Conflicting rerun: raises a conflict error.
- Incomplete or corrupted existing partition: raises a corruption error.
- Empty session: rejected.

## Ingestion Service

The first service handles one explicit `session_date` and a caller-provided tuple of canonical `instrument_ids`. It builds an `EodBarQuery` where `start_date == end_date == session_date` and uses latest revision selection. Full-market Grouped Daily query semantics remain deferred.

The service rejects empty provider results, bars for the wrong session date, duplicate canonical business keys, and contradictory latest revision records.

## Non-Goals

## Instrument Master Snapshot Note

A separate Instrument Master snapshot repository now exists for `instrument-master` and `provider-instrument-identity` datasets with a logical snapshot marker. The first live Massive All Tickers run for 2026-08-13 did not publish because quality gates failed.

The refined repository now also publishes `provider-ticker-resolver` as part of the same logical snapshot. The corrected 2026-08-13 Massive snapshot is completed. The subsequent Decimal-volume-corrected Grouped Daily run published 9,901 canonical EOD bars for 2026-08-13 and linked the completed identity snapshot fingerprint in the manifest.

- Massive API calls
- credential loading
- raw provider payload persistence
- historical backfill
- scheduler, cron, or systemd
- retry or rate-limit implementation
- corporate-action adjustment reconciliation
- analytics or Dashboard data APIs
- database or catalog integration
