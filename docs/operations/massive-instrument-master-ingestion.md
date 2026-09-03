# Massive Instrument Master Ingestion

## Current mandatory workflow

The administrator entrypoint no longer permits a network request to publish
directly. Every new date must use the four-stage [Same-Day Identity and EOD
Catch-Up V1](../data-contracts/same-day-identity-eod-catchup-v1.md) contract:
fetch-only to a private `/tmp` package, offline approval plan, separately
approved offline apply, and formal reread. Instrument Master, Provider
Instrument Identity, and Provider Ticker Resolver publish as immutable
components; the logical completion manifest is last. A completed logical
manifest is required before same-day EOD planning.

The historical command and execution records below describe completed runs;
that direct invocation form is disabled and must not be reused.

The completed 2026-08-14 snapshot is governed by the [read-only audit and acceptance record](data-audits/2026-08-14-instrument-snapshot-audit.md). Its content integrity passed, while original run request and pagination provenance is unavailable. It is accepted as `accepted_with_provenance_exception` and must not be requested again or overwritten.

## Purpose

This runbook records the bounded point-in-time Massive Stocks reference ticker ingestion path for building the Instrument Master, provider identity, and provider ticker resolver snapshots.

## Status

Implemented and executed for 2026-08-13. The first run used overly broad rejected/coverage gates and did not publish. The second run corrected the taxonomy, completed pagination, passed quality gates, and published the point-in-time snapshot.

## Historical command (disabled)

```bash
scripts/admin/ingest-massive-instrument-master.sh   --as-of-date 2026-08-13   --data-root /data/trading-intelligence-platform
```

## Network Boundary

Allowed endpoint: `/v3/reference/tickers`.

Initial query parameters:

- `market=stocks`
- `active=true`
- `date=2026-08-13`
- `limit=1000`
- `sort=ticker`
- `order=asc`

Pagination follows only same-host, same-path `next_url` values. The hard limits are 20 pages, 25,000 records, no retry, no concurrency, and at least 15 seconds between requests.

## Corrected Quality Classification

The corrected V1 classification distinguishes:

- eligible and resolved records
- eligible but unresolved records
- expected V1 universe exclusions
- truly malformed or rejected records
- ticker-level ambiguity
- stable-identifier collision

Expected exclusions are not counted as malformed records and are not included in the eligible identity coverage denominator.

Stable-identifier collisions are included in the eligible identity denominator
but remain quarantined from Instrument and Resolver outputs. ADR 0116 permits
only an observation ratio no greater than 0.1%; it never selects a conflicting
ticker or infers lifecycle facts.

## Live Execution Result

Execution date: 2026-08-14
Snapshot as-of date: 2026-08-13

Safe aggregate result:

- request_count: 14
- raw_record_count: 13,106
- eligible_record_count: 11,064
- expected_exclusion_count: 1,952
- malformed_rejected_count: 90
- resolved_eligible_count: 9,932
- unresolved_eligible_count: 1,132
- ambiguous_ticker_record_count: 0
- stable_identifier_collision_count: 0
- canonical_instrument_count: 9,932
- resolver_entry_count: 9,932
- unique_provider_ticker_count: 13,104
- duplicate_provider_ticker_count: 2
- eligible_identity_coverage_ratio: 89.7686%
- malformed_ratio: 0.6867%
- expected_exclusion_ratio: 14.8939%
- ticker_ambiguity_ratio: 0.0000%
- quality_gate_passed: true
- status: `published`

Provider type counts:

- ADRC: 376
- CS: 5,320
- ETF: 5,368
- ETN: 51
- ETS: 111
- ETV: 90
- FUND: 332
- PFD: 430
- RIGHT: 119
- SP: 159
- UNIT: 307
- WARRANT: 443

At this historical 2026-08-13 execution boundary, `ETV` was treated as an
unknown/malformed provider type and the malformed ratio remained below the V1
Candidate Gate. ADR 0124 later resolved the prospective mapping policy:
catalog-known `ETV` is now an unsupported expected exclusion, without inferring
ETF or another canonical security form. Completed immutable snapshots are not
rewritten; missing provider type remains malformed and quarantined.

## Published Paths

- `/data/trading-intelligence-platform/market-data/instrument-master/schema_version=1/as_of_date=2026-08-13/`
- `/data/trading-intelligence-platform/market-data/provider-instrument-identity/schema_version=1/provider=massive_stocks_basic/as_of_date=2026-08-13/`
- `/data/trading-intelligence-platform/market-data/provider-ticker-resolver/schema_version=1/provider=massive_stocks_basic/as_of_date=2026-08-13/`
- `/data/trading-intelligence-platform/market-data/snapshots/instrument-master/as_of_date=2026-08-13/manifest.json`

Published row counts:

- instrument-master: 9,932
- provider-instrument-identity: 13,106
- provider-ticker-resolver: 9,932

No raw provider payload was stored.

## Next Operational Focus

Use the completed resolver to rerun the 2026-08-13 Grouped Daily inspection once. Publish canonical EOD bars only if corrected OHLCV, identity, and persistence gates pass.


## 2026-08-12 Run

The 2026-08-12 All Tickers run completed with 14 requests, 13,106 raw records, 9,932 canonical instruments, 13,106 provider identity records, 9,932 resolver entries, 89.7686% eligible identity coverage, and published status. No raw payload was persisted.
