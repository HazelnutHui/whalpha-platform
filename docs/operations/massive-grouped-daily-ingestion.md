# Massive Grouped Daily Ingestion

## Purpose

This runbook records the controlled Massive Grouped Daily canonical EOD ingestion attempt for the completed 2026-08-13 U.S. trading session. The workflow uses the completed point-in-time Massive ticker resolver to classify raw grouped bars before constructing canonical `EodPriceBarV1` records and publishing Parquet only when all gates pass.

## Status

Access verified; publication blocked by V1 quality gates. No EOD Price Bar partition was published.

## Execution Record

- Session date: 2026-08-13
- Identity snapshot as-of date: 2026-08-13
- Execution date: 2026-08-14
- Provider: Massive Stocks Basic
- Endpoint: `/v2/aggs/grouped/locale/us/market/stocks/2026-08-13`
- Request count: 1
- Retry count: 0
- Adjustment parameter: `adjusted=false`
- Credential transport: Authorization bearer header through the protected loader and transport boundary
- Raw response persistence: none
- Canonical record persistence: none
- EOD Parquet publication: none
- `/data` writes: none for EOD bars

## Identity Snapshot Dependency

The ingestion verified the completed 2026-08-13 Massive Instrument Master logical snapshot before the live request:

- canonical instruments: 9,932
- provider ticker resolver entries: 9,932
- completion status: completed
- provider: `massive_stocks_basic`

Only tickers with a unique resolved resolver entry are eligible for canonical EOD bar construction. Unresolved, expected-exclusion, ambiguous, rejected, and missing identity records are not converted into canonical bars.

## Safe Aggregate Result

The command output was limited to aggregate counts. It did not print raw JSON, headers, full ticker lists, prices, account identifiers, provider identifiers, FIGI/CIK values, or credentials.

Observed result:

- raw_result_count: 12,500
- unique_raw_ticker_count: 12,498
- exact_duplicate_count: 0
- conflicting_duplicate_count: 4
- resolved_eligible_bar_count: 601
- unresolved_eligible_bar_count: 992
- expected_exclusion_bar_count: 1,491
- ambiguous_bar_count: 0
- rejected_identity_bar_count: 90
- missing_identity_bar_count: 22
- identity_eligible_denominator: 1,615
- identity_resolved_coverage_ratio: 37.2136%
- required_field_missing_count: 0
- optional_vwap_missing_count: 1
- optional_trade_count_missing_count: 1
- numeric_conversion_failure_count: 9,300
- nonpositive_price_count: 0
- ohlc_consistency_failure_count: 0
- negative_volume_count: 0
- zero_volume_count: 1
- timestamp_session_mismatch_count: 0
- canonical_validation_failure_count: 0
- canonical_bar_count: 601
- written_record_count: 0
- publish_ready: false
- status: `quality_gate_failed`

## Gate Result

Publication was blocked for these exact reasons:

- `conflicting_duplicate_count_nonzero`
- `numeric_conversion_failure_count_nonzero`
- `identity_resolved_coverage_below_gate`
- `canonical_bar_count_below_gate`

No repository publish occurred and no completed EOD partition was created.

## Parser Note

The earlier inspection parser problem with ordinary integral JSON values was covered by local fixtures before this run. The live run still produced a high required numeric conversion failure count. Because raw payloads are not persisted, the next investigation must use separately authorized diagnostics or local safe fixtures and must not silently loosen canonical `EodPriceBarV1` validation.

## Duplicate Ticker Handling

Exact duplicate bars are eligible for deterministic deduplication. Conflicting duplicate bars are excluded from publication and remain a hard V1 gate failure. The 2026-08-13 live run observed four conflicting duplicate observations.

## Publication Boundary

The production EOD Price Bar path remains absent:

```text
/data/trading-intelligence-platform/market-data/eod-price-bars/schema_version=1/session_date=2026-08-13/
```

No raw provider response, canonical record dump, CSV, database row, or Parquet file was stored for this Grouped Daily run.

## Next Operational Focus

Investigate the Grouped Daily blockers without another live request until a separate authorization is granted: required numeric parsing, conflicting duplicate bars, and identity classification coverage. Publication should remain blocked until all V1 gates pass.

## Non-Goals

- calling any Massive endpoint other than the single authorized Grouped Daily request
- retrying the request
- storing raw provider payloads
- forcing ticker-only identity resolution
- publishing partial canonical bars
- writing outside the approved data root
- implementing scheduling, historical backfill, analytics, or Dashboard APIs
- accessing OCI
