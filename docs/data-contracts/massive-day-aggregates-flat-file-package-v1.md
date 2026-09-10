# Massive Day Aggregates Flat File Package V1

## Purpose

This contract adds a fetch-only source boundary for Massive Stocks Day
Aggregates Flat Files. It preserves the provider's compressed CSV and a
deterministic REST-shaped normalized view so the existing offline EOD planner,
quality gates, stable-ID resolution, atomic Apply, and formal reader can be
reused unchanged.

It does not authorize a download, canonical Apply, historical completeness,
public redistribution, strategy execution, publication, or deployment.

## Fixed source

| Field | Value |
| --- | --- |
| Endpoint | `https://files.massive.com` |
| Bucket | `flatfiles` |
| Dataset | `us_stocks_sip/day_aggs_v1` |
| Object | `YYYY/MM/YYYY-MM-DD.csv.gz` |
| Adjustment basis | unadjusted |
| Requests per session | exactly one |
| Compressed ceiling | 5 MiB |
| Decompressed ceiling | 32 MiB |
| Row ceiling | 30,000 |

The expected CSV header is exactly `ticker, volume, open, close, high, low,
window_start, transactions` in that order. Schema drift fails closed until the
source contract is reviewed; unknown columns are not silently ignored.

`window_start` must be an exact non-negative nanosecond integer convertible to
milliseconds, and every row must resolve to the requested U.S. market session.
Ticker rows must be unique and non-empty. Numeric and Identity quality remain
the responsibility of the existing EOD quality gates rather than being coerced
during source parsing.

## Transitive custody

The acquisition package contains exactly:

- `source.csv.gz`, retained byte-for-byte and mode `0400`;
- `response-01.json`, the normalized grouped-daily envelope; and
- `package.json`, the existing typed acquisition manifest.

The normalized envelope binds the bucket, object key, source file name,
compressed byte count, SHA-256, ETag when supplied, provider last-modified time
when supplied, and unadjusted semantics. Formal package readback rehashes the
raw gzip, reparses it, and requires exact row equality with the normalized
payload. Package and Apply-plan fingerprints therefore remain transitively
bound to the raw provider artifact.

Access Key ID and Secret Key use Pydantic secret types and a separate
owner-only UTF-8 credential file. They never enter the package, Git, command
output, endpoint string, exception detail, or canonical data.

## Implementation

- source adapter and strict credential loader:
  `tip_api.providers.massive.flat_file_day_aggregates`;
- exact-authorization CLI:
  `scripts/admin/fetch-massive-day-aggregate-flat-file.sh`;
- existing package/plan/apply custody:
  `tip_api.providers.massive.same_day_catchup`.

The optional local dependency group is `flat-files`; OCI does not need this
dependency because acquisition and heavy data work remain on Dell.

