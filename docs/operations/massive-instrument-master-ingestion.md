# Massive Instrument Master Ingestion

## Purpose

This runbook records the bounded point-in-time Massive Stocks reference ticker ingestion path for building the first Instrument Master and provider identity snapshot.

## Status

Implemented and executed once for 2026-08-13. The Massive All Tickers pagination completed, but publication was blocked by quality gates. No production snapshot was written.

## Command

```bash
scripts/admin/ingest-massive-instrument-master.sh   --as-of-date 2026-08-13   --data-root /data/trading-intelligence-platform
```

The script accepts only an explicit as-of date and the approved production data root. It does not accept an API key, output path, force flag, concurrency option, or quality-gate bypass.

## Network Boundary

Allowed endpoint:

- `/v3/reference/tickers`

Initial query parameters:

- `market=stocks`
- `active=true`
- `date=2026-08-13`
- `limit=1000`
- `sort=ticker`
- `order=asc`

Pagination follows only same-host, same-path `next_url` values. The hard limits are 20 pages, 25,000 records, no retry, no concurrency, and at least 15 seconds between requests.

## Credential Boundary

Credentials are loaded through the existing protected Massive credential loader. The key is sent through the Authorization bearer header by the transport boundary. The command must not print or persist the key, headers, raw response, account identity, or credential file content.

## Live Execution Result

Execution date: 2026-08-14
Snapshot as-of date: 2026-08-13

Safe aggregate result:

- request_count: 14
- raw_record_count: 13,106
- unique_ticker_count: 13,104
- duplicate_ticker_count: 2
- resolved_count: 10,116
- unresolved_count: 1,536
- ambiguous_count: 0
- rejected_count: 1,454
- canonical_instrument_count: 10,116
- identity_coverage_ratio: 77.1860%
- quality_gate_passed: false
- quality_gate_failures: `identity_coverage_below_gate`, `rejected_ratio_above_gate`, `duplicate_ticker_count_nonzero`
- status: `quality_gate_failed`

## Publish Result

No production Instrument Master snapshot was published. The following were not written:

- `market-data/instrument-master/schema_version=1/as_of_date=2026-08-13/`
- `market-data/provider-instrument-identity/schema_version=1/provider=massive_stocks_basic/as_of_date=2026-08-13/`
- `market-data/snapshots/instrument-master/as_of_date=2026-08-13/`

No raw provider payload was stored.

## Next Operational Focus

Review rejected and unresolved identity categories using bounded, non-secret diagnostics before attempting publication again. Grouped Daily EOD bars must not be published until the Instrument Master snapshot gates pass.

