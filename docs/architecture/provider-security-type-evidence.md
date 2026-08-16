# Provider Security-Type Evidence

## Purpose

Phase B1 preserves Massive's official ticker-type catalog and point-in-time All Tickers type fields without changing Instrument Master, identity, resolver, or EOD datasets. Phase B1A separates normalized provider observations from evidence that has a unique canonical identity.

## Datasets

- `market-data/provider-security-type-catalog/schema_version=1/provider=<provider>/observed_date=<UTC-date>/`
- `market-data/provider-security-observation/schema_version=1/provider=<provider>/as_of_date=<date>/`
- `market-data/provider-instrument-security-evidence/schema_version=1/provider=<provider>/as_of_date=<date>/`

Each completed partition contains `part-00000.parquet` and `manifest.json`, an explicit Arrow schema, deterministic ordering, content SHA-256, Parquet SHA-256, record count, source endpoint, and completion status. The instrument manifest references the catalog content fingerprint.

## Semantics

Provider type proves only what the provider explicitly states. `CS` proves common-share form, not operating-company structure or issuer domicile. `locale=us` is market geography. CIK and FIGI connect identities but do not classify securities. Names only create review flags.

Explicit ETF/ETN/preferred/warrant/right/unit and similar forms can be excluded deterministically. Generic fund form does not prove a CEF subtype. Unknown codes are quarantined.

## Observation And Canonical Evidence

A provider observation has a deterministic SHA-256 `provider_observation_id` derived from provider, as-of date, ticker, provider type, exchange, and available stable identifiers. It may have no canonical `instrument_id`. Its status is `canonical_mapped`, `expected_unjoined`, `ambiguous`, `collision`, or `malformed`. Exact duplicate observations are represented once with an occurrence count.

Canonical evidence contains only uniquely mapped observations. Its business key is `instrument_id + as_of_date + provider + evidence_kind + evidence_version`. Identical evidence deduplicates deterministically; conflicting type evidence for that key is a hard failure.

Identity matching order is exact Share Class FIGI, unique Composite FIGI, exact provider stable ID, then point-in-time ticker fallback. Ticker fallback is permitted only when the accepted identity snapshot contains exactly one observation for that ticker and the resolver agrees. An excluded or unresolved observation sharing a ticker with a resolved observation is `expected_unjoined`; it is never forced onto the resolved instrument.

Canonical linkage is measured only over observations eligible for canonical identity: mapped + ambiguous + collision. Expected exclusions, unresolved identities, rejected records, malformed records, and exact duplicate occurrences do not inflate the denominator.

## Failed Diagnostics

Failed-run diagnostics live under `operation-diagnostics/provider-security-type-evidence/`, outside all completed evidence datasets. They contain only counters, reason codes, identifier-presence types, optional canonical IDs, and sanitized ticker/type summaries. They never contain raw JSON, HTTP headers, credentials, or authorization values, and no completed-evidence reader treats them as data.

Raw responses are neither logged nor persisted.
