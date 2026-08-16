# Provider Security-Type Evidence

## Purpose

Phase B1 preserves Massive's official ticker-type catalog and point-in-time All Tickers type fields without changing Instrument Master, identity, resolver, or EOD datasets. The evidence is an overlay keyed to stable canonical identity.

## Datasets

- `market-data/provider-security-type-catalog/schema_version=1/provider=<provider>/observed_date=<UTC-date>/`
- `market-data/provider-instrument-security-evidence/schema_version=1/provider=<provider>/as_of_date=<date>/`

Each completed partition contains `part-00000.parquet` and `manifest.json`, an explicit Arrow schema, deterministic ordering, content SHA-256, Parquet SHA-256, record count, source endpoint, and completion status. The instrument manifest references the catalog content fingerprint.

## Semantics

Provider type proves only what the provider explicitly states. `CS` proves common-share form, not operating-company structure or issuer domicile. `locale=us` is market geography. CIK and FIGI connect identities but do not classify securities. Names only create review flags.

Explicit ETF/ETN/preferred/warrant/right/unit and similar forms can be excluded deterministically. Generic fund form does not prove a CEF subtype. Unknown codes are quarantined.

Identity matching prefers stable identifiers. Ticker fallback is permitted only through the accepted point-in-time resolver. Raw responses are neither logged nor persisted.
