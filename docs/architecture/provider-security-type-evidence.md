# Provider Security-Type Evidence

## Reviewed security-form correction boundary

Provider classifications remain immutable source evidence. A separate `ReviewedSecurityFormEvidenceV1` may supersede the effective security form for a stable `instrument_id` over a half-open interval when already-reviewed authoritative filings support the correction. Ticker and company name are display-only. Duplicate business keys, overlapping/conflicting intervals, unsafe source URLs, orphan instruments, and a correction whose security-form fact has no source coverage at its proposed effective date fail closed.

The first planned record corrects HSAI (`c66e6ab5-b3e2-5b32-845f-90f8eceed5a3`) from provider `CS` to reviewed `ADR/ADS`, effective 2023-02-09 and open-ended. Its four-source ledger references the IPO Form 424B4, 2023 and 2025 Forms 20-F, and 2026-07-10 Form 6-K; no SEC content was fetched or stored. Each source has separate document/reporting date, optional filing-acceptance date, covered fact, and fact-effective date, while the evidence row separately records review/record timestamps. Filing dates are populated only where supplied by the reviewed evidence; the two annual-report acceptance dates are not inferred offline. The 2026-07-10 filing supports only the ADS ratio change from 1:1 to 1:8; it does not model a CS-to-ADRC conversion. `adjustment_factors_unverified` remains set. This correction cannot bypass exchange, current/previous bar, USD 5 previous-close, 20/20 history, USD 20M median proxy, quality, or reviewed-eligibility gates.

## Purpose

Phase B1 preserves Massive's official ticker-type catalog and point-in-time All Tickers type fields without changing Instrument Master, identity, resolver, or EOD datasets. Phase B1A separates normalized provider observations from evidence that has a unique canonical identity.

## Datasets

- `market-data/provider-security-type-catalog/schema_version=1/provider=<provider>/observed_date=<UTC-date>/`
- `market-data/provider-security-observation/schema_version=1/provider=<provider>/as_of_date=<date>/`
- `market-data/provider-instrument-security-evidence/schema_version=1/provider=<provider>/as_of_date=<date>/`
- `market-data/snapshots/provider-security-evidence/as_of_date=<date>/manifest.json`

Each partition contains `part-00000.parquet` and `manifest.json`, an explicit Arrow schema, deterministic ordering, content SHA-256, Parquet SHA-256, record count, source endpoint, and completion status. A consumer accepts the three partitions as one completed evidence snapshot only through the logical manifest. That marker is written atomically after all component manifests, Parquet schemas, counts, content fingerprints, and file hashes are reread and verified.

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

When transport or pagination fails before reconciliation, unknown statistics are serialized as `null` with `statistics_complete=false`; zero is never used to guess an unavailable count. Request attempts remain exact through a bounded counting transport.

Raw responses are neither logged nor persisted.
