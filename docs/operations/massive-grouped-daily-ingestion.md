# Massive Grouped Daily Ingestion

## Purpose

This runbook records the controlled Massive Grouped Daily canonical EOD ingestion attempt for the completed 2026-08-13 U.S. trading session. The workflow uses the completed point-in-time Massive ticker resolver to classify raw grouped bars before constructing canonical `EodPriceBarV1` records and publishing Parquet only when all gates pass.

## Status

Access verified; parser, identity-ordering, and duplicate-isolation fixes tested; publication still blocked by V1 numeric quality gates. No EOD Price Bar partition was published.

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

## Root Cause Audit

The previous reported identity coverage of 37.2136% was not a valid full-session identity conclusion. The ingestion path performed numeric validation before every raw record had an independent identity classification outcome, so required numeric parsing failures removed many records from the identity denominator. The duplicate logic also treated any conflicting duplicate ticker as a hard failure instead of isolating the affected ticker when the conflict ratio was negligible.

The corrected implementation now uses one centralized Massive JSON number policy for prices, integer-semantic fields, optional fields, and timestamps. It classifies identity before numeric validation, reconciles raw identity counts separately from deduplicated numeric counts, and isolates conflicting duplicate tickers when the conflicting duplicate record ratio is at or below 0.1%.

The JSON decoder remains unchanged. The mapping boundary uses `Decimal(str(value))` for accepted JSON numbers and explicitly rejects bool, non-finite values, malformed strings, and fractional values for integer-semantic fields. This avoids binary-float propagation into canonical contracts while keeping one conversion helper shared by inspection-oriented and publication-oriented ingestion tests.

## Identity Snapshot Dependency

The ingestion verified the completed 2026-08-13 Massive Instrument Master logical snapshot before the live request:

- canonical instruments: 9,932
- provider ticker resolver entries: 9,932
- completion status: completed
- provider: `massive_stocks_basic`

Only tickers with a unique resolved resolver entry are eligible for canonical EOD bar construction. Unresolved, expected-exclusion, ambiguous, rejected, and missing identity records are not converted into canonical bars.

## Latest Corrected Safe Aggregate Result

The command output was limited to aggregate counts. It did not print raw JSON, headers, full ticker lists, prices, account identifiers, provider identifiers, FIGI/CIK values, or credentials.

Observed result from the corrected authorized run:

- raw_result_count: 12,500
- unique_raw_ticker_count: 12,498
- exact_duplicate_ticker_count: 0
- exact_duplicate_record_count: 0
- conflicting_duplicate_ticker_count: 2
- conflicting_duplicate_record_count: 4
- conflicting_duplicate_ratio: 0.0320%
- resolved_eligible_bar_count: 9,905
- unresolved_eligible_bar_count: 992
- expected_exclusion_bar_count: 1,491
- ambiguous_bar_count: 0
- rejected_identity_bar_count: 90
- missing_identity_bar_count: 22
- identity_classified_count: 12,500
- identity_eligible_denominator: 10,919
- identity_resolved_coverage_ratio: 90.7134%
- numeric_classified_count: 12,496
- numeric_valid_count: 1,288
- numeric_conversion_failure_count: 11,208
- numeric_conversion_failure_ratio: 89.6927%
- required_field_missing_count: 0
- required_field_missing_ratio: 0.0000%
- optional_vwap_missing_count: 4
- optional_trade_count_missing_count: 4
- nonpositive_price_count: 0
- ohlc_consistency_failure_count: 0
- negative_volume_count: 0
- zero_volume_count: 4
- timestamp_session_mismatch_count: 0
- identity_resolved_and_numeric_valid_count: 601
- canonical_validation_failure_count: 0
- canonical_bar_count: 601
- count_reconciliation_passed: true
- written_record_count: 0
- publish_ready: false
- status: `quality_gate_failed`

## Gate Result

Publication was blocked for these exact reasons in the latest corrected run:

- `numeric_conversion_failure_ratio_above_gate`
- `canonical_bar_count_below_gate`

Identity coverage now passes the V1 gate. Conflicting duplicate bars were isolated and recorded as a quality warning because the ratio was below 0.1%.

No repository publish occurred and no completed EOD partition was created.

## Parser Note

The earlier parser accepted too narrow a set of JSON number representations and the previous processing order let numeric failures short-circuit identity classification. Local tests now cover int, finite float, Decimal, numeric string, bool rejection, NaN/Infinity rejection, required null rejection, malformed string rejection, integral float/Decimal/string handling, fractional integer-semantic rejection, and no silent truncation.

The corrected live run still produced a high required numeric conversion failure count. Because raw payloads are not persisted, the next investigation must use field-level diagnostics under a separate authorization or local safe fixtures and must not silently loosen canonical `EodPriceBarV1` validation. If Massive required fields legitimately include non-integer aggregate volume semantics, that must be handled as an explicit contract decision rather than by truncation or rounding.

## Duplicate Ticker Handling

Exact duplicate bars are eligible for deterministic deduplication. Conflicting duplicate bars are excluded from publication and remain a hard V1 gate failure. The 2026-08-13 live run observed four conflicting duplicate observations.

## Publication Boundary

The production EOD Price Bar path remains absent:

```text
/data/trading-intelligence-platform/market-data/eod-price-bars/schema_version=1/session_date=2026-08-13/
```

No raw provider response, canonical record dump, CSV, database row, or Parquet file was stored for this Grouped Daily run.

## Next Operational Focus

Investigate the Grouped Daily blockers without another live request until a separate authorization is granted: required numeric parsing, conflicting duplicate bars, and identity classification coverage. Publication should remain blocked until required numeric-field semantics are resolved and all V1 gates pass.

## Non-Goals

- calling any Massive endpoint other than the single authorized Grouped Daily request
- retrying the request
- storing raw provider payloads
- forcing ticker-only identity resolution
- publishing partial canonical bars
- writing outside the approved data root
- implementing scheduling, historical backfill, analytics, or Dashboard APIs
- accessing OCI
