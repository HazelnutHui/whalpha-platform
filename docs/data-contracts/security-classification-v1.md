# Security Classification V1

Security Classification V1 is a provider-neutral, point-in-time overlay on stable Instrument Master identity. It does not alter canonical market-data partitions.

## Dimensions

- `security_form`: the legal form of the listed security.
- `issuer_structure`: the issuer's economic/legal operating structure.
- `listing_scope`: U.S. domestic primary, U.S.-listed foreign, depositary receipt, other, or unknown.
- `classification_status`: resolved, excluded resolved, unknown, ambiguous, or malformed.
- `universe_disposition`: core candidate, U.S.-listed international candidate, excluded, or quarantine.

These dimensions are separate. A legal label such as “Common Stock” does not prove that the issuer is an operating company; a listed closed-end fund can issue common shares.

## Time And Identity

An active record satisfies `effective_from <= session_date < effective_to`; null `effective_to` is open ended. One instrument may have only one active record per date. Overlap is a hard failure. Ticker is display metadata and never the permanent key.

## Evidence

Priority is authoritative filing/exchange/issuer evidence, explicit provider type evidence, verified identifier connections, and reviewed effective-dated overrides. Names and ticker patterns can only add review flags. CIK and FIGI connect identity but do not prove security type.

Weak or conflicting evidence never creates eligibility. Unknown, ambiguous, malformed, heuristic-only, and insufficient-evidence classifications are quarantined.

Provider Security Type Catalog V1 preserves official provider code, description, asset class, locale, endpoint, observation time, and evidence fingerprint. Provider Instrument Security Evidence V1 preserves the point-in-time type code and security-form evidence linked by stable identity. Neither contract treats `CS`, U.S. locale, CIK, FIGI, or name text as operating-company or domicile proof.

Provider Security Observation V1 is the complete normalized observation layer. `instrument_id` is nullable and reconciliation status distinguishes canonical mapped, expected unjoined, ambiguous, collision, and malformed observations. Its deterministic observation ID includes provider, date, ticker, type, exchange, and available stable identifiers; ticker alone is never the key. Canonical Provider Instrument Security Evidence contains only uniquely mapped observations and uses instrument/date/provider/evidence-kind/version as its business key.

A completed provider evidence snapshot additionally requires one logical completion manifest referencing the catalog, observation, and canonical evidence paths, counts, content fingerprints, and Parquet hashes. Readers reject component-only, conflicting, incomplete, or corrupt states.

## Candidate Policies

Core U.S. Domestic Operating Equities requires authoritative/provider-explicit domestic operating common or equity REIT classification. Broad U.S.-Listed Operating Equities additionally permits authoritative/provider-explicit ADR/ADS and foreign ordinary operating equities. Both apply supported exchange, two-session availability, previous close of at least USD 5, previous close-times-volume of at least USD 20 million, and material quality checks.

The one-day previous-session liquidity gate is provisional and is not 20-day ADV. A later phase requires trailing median dollar volume.
