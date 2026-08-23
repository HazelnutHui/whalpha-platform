# Massive Grouped Daily Ingestion

## Current mandatory workflow

The administrator entrypoint now implements the four-stage [Same-Day Identity
and EOD Catch-Up V1](../data-contracts/same-day-identity-eod-catchup-v1.md)
contract. Fetch-only freezes one exact-date `adjusted=false` response below
`/tmp`; offline planning binds the exact same-day completed Identity logical
fingerprint and canonical artifacts; approved apply has no socket access and
requires the plan path, plan SHA-256, and expected state fingerprint; formal
reread completes the operation. Previous-date and `latest` resolver fallbacks
are rejected. The older network-to-publication Python function is disabled.

The records below are historical evidence and do not authorize or document the
current CLI invocation sequence.

## Purpose

This runbook records the controlled Massive Grouped Daily canonical EOD ingestion attempt for the completed 2026-08-13 U.S. trading session. The workflow uses the completed point-in-time Massive ticker resolver to classify raw grouped bars before constructing canonical `EodPriceBarV1` records and publishing Parquet only when all gates pass.

## Status

Published. Decimal volume correction, identity-ordering, numeric validation, duplicate isolation, and V1 quality gates passed for the authorized 2026-08-13 run.

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
- Canonical record persistence: 9,901 `EodPriceBarV1` records
- EOD Parquet publication: completed
- `/data` writes: one approved EOD Price Bar partition

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
- numeric_valid_count: 12,496
- numeric_conversion_failure_count: 0
- numeric_conversion_failure_ratio: 0.0000%
- required_field_missing_count: 0
- required_field_missing_ratio: 0.0000%
- optional_vwap_missing_count: 4
- optional_trade_count_missing_count: 4
- nonpositive_price_count: 0
- ohlc_consistency_failure_count: 0
- negative_volume_count: 0
- zero_volume_count: 4
- timestamp_session_mismatch_count: 0
- identity_resolved_and_numeric_valid_count: 9,901
- canonical_validation_failure_count: 0
- canonical_bar_count: 9,901
- count_reconciliation_passed: true
- written_record_count: 9,901
- publish_ready: true
- status: `published`

## Gate Result

Publication passed all V1 gates. Identity coverage passed, numeric conversion failures were zero, and conflicting duplicate bars were isolated as a quality warning because the ratio was below 0.1%. The repository published the completed canonical EOD partition atomically.

## Parser Note

The earlier parser accepted too narrow a set of JSON number representations and the previous processing order let numeric failures short-circuit identity classification. Local tests now cover int, finite float, Decimal, numeric string, bool rejection, NaN/Infinity rejection, required null rejection, malformed string rejection, integral float/Decimal/string handling, fractional integer-semantic rejection, and no silent truncation.

The later explicit contract decision [ADR 0010](../decisions/0010-represent-aggregate-volume-as-decimal.md) changed aggregate volume to exact Decimal because Massive `v` is a number. The live rerun produced 11,208 fractional-volume records, all accepted under the corrected contract, with zero required numeric conversion failures.

## Duplicate Ticker Handling

Exact duplicate bars are eligible for deterministic deduplication. Conflicting duplicate bars are excluded from publication. Low-ratio conflicts at or below 0.1% are isolated and recorded as quality warnings; above that gate they remain a hard failure. The published 2026-08-13 run isolated four conflicting duplicate observations.

## Publication Boundary

The production EOD Price Bar path is completed:

```text
/data/trading-intelligence-platform/market-data/eod-price-bars/schema_version=1/session_date=2026-08-13/
```

No raw provider response, canonical record dump, CSV, or database row was stored. Only the canonical Parquet partition and manifest were published.

## Next Operational Focus

Design and implement the first canonical EOD read/query service and private FastAPI response contracts for the completed 2026-08-13 session. No frontend changes or OCI deployment are included in that next step.

Future live runs must retain a non-sensitive operation report with endpoint path, session and identity reference, adjusted/request/retry counts, UTC start/completion times, quality statistics, publication result, and final fingerprint. Reports must never contain raw payloads, credentials, authorization headers, or secret query parameters.

The 2026-08-14 operation followed this requirement. Its [safe run report](data-audits/2026-08-14-grouped-daily-run.md) records one `adjusted=false` request, zero retries, all quality results, 9,912 published bars, and the final fingerprint without raw data or credentials.

## Non-Goals

- calling any Massive endpoint other than the single authorized Grouped Daily request
- retrying the request
- storing raw provider payloads
- forcing ticker-only identity resolution
- publishing partial canonical bars
- writing outside the approved data root
- implementing scheduling, historical backfill, analytics, or Dashboard APIs
- accessing OCI

## 2026-08-12 Run

The 2026-08-12 Grouped Daily run used one `adjusted=false` request, passed V1 quality gates, and published 9,900 canonical EOD bars. It recorded 4 isolated conflicting duplicate records, 11,158 fractional-volume records, 5 missing optional VWAP values, 5 missing optional trade-count values, and 5 zero-volume records. No raw payload was persisted.
