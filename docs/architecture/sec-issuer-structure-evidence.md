# SEC Issuer-Structure Evidence Boundary

## Status

Phase B2A implemented and fixture-validated the boundary offline. Phase B2B implements a bounded streaming transport and atomic source-cache, observation, canonical-evidence, and logical-completion layers. The first authorized B2B run failed closed during official CSV discovery and produced no completed source cache or evidence snapshot. Universe activation and Dashboard changes remain out of scope.

## Purpose

Massive provider type evidence primarily establishes listed security form. It does not normally establish whether the issuer is an operating company, fund, BDC, REIT subtype, SPAC, partnership, or other special structure. SEC evidence is therefore a separate provider-neutral layer that can strengthen issuer-structure and listing-scope decisions without changing Instrument Master identity.

## Layers

`SecIssuerEvidenceObservationV1` stores a normalized assertion and may have no canonical `instrument_id`. It retains only audit fields needed to explain the assertion; raw SEC HTML, ZIP, JSON, headers, and contact configuration are not canonical evidence.

`SecIssuerStructureEvidenceV1` contains only uniquely mapped observations. Its business key is `instrument_id + as_of_date + evidence_kind + evidence_version`. Identical observations deduplicate deterministically. Conflicting assertions quarantine the instrument rather than silently selecting one.

The future dataset root is:

`market-data/sec-issuer-structure-evidence/schema_version=1/as_of_date=YYYY-MM-DD/`

The approved layers are `source-cache/sec/security-classification/as_of_date=<date>`, `market-data/sec-issuer-structure-observation/schema_version=1/as_of_date=<date>`, `market-data/sec-issuer-structure-evidence/schema_version=1/as_of_date=<date>`, and `market-data/snapshots/sec-issuer-structure-evidence/as_of_date=<date>`. Readers must require the final logical completion manifest; a cache or individual partition is not sufficient.

The repository provides explicit Arrow schema, deterministic ordering and fingerprinting, manifest and Parquet hashes, reread validation, sibling staging, atomic publication, idempotent rerun, conflict rejection, corruption rejection, and symlink containment. Phase B2A invokes it only under pytest `tmp_path`.

The live transport permits HTTPS only to `www.sec.gov` and `data.sec.gov`, runs serially at no more than two requests per second, limits the operation to 12 HTTP attempts, uses bounded retry only for 429/recoverable 5xx responses, and never serializes the private User-Agent. ZIP validation rejects traversal, links, unexpected members, and configured compressed or expanded size limits. The 2026-08-14 cutoff is applied before canonical reconciliation; current reference data without historical-effective semantics cannot be backfilled as historical classification evidence.

## Evidence Semantics

Evidence grades, strongest first, are:

- `authoritative_explicit`
- `authoritative_filing_cover`
- `authoritative_state_machine`
- `corroborating_reference`
- `heuristic_review_only`
- `insufficient`

All filings are evaluated against an as-of filing cutoff. A future filing cannot be backfilled into an earlier classification. Effective intervals are half-open.

CIK identifies a filer, not a listed security. SIC is review-only. `company_tickers_exchange` is an identity seed. Presence in `company_tickers_mf` is fund-exclusion evidence; absence is not proof that an instrument is not a fund. Official Investment Company Series/Class, closed-end-fund, and BDC sources can establish exclusions. N-54A/N-54C are interpreted as a point-in-time BDC state machine. N-2 alone does not distinguish CEF from BDC. A 10-K alone does not prove domestic operating common equity. 20-F/40-F establish foreign-private reporting evidence but not ADR form.

Inline XBRL cover-page `Security12bTitle`, `TradingSymbol`, and `SecurityExchangeName` can establish strong security-form evidence only when their point-in-time identity join is consistent. They do not independently establish issuer operating structure or domicile.

## Identity Resolution

Resolution priority is:

1. stable `instrument_id`
2. exact Share Class FIGI
3. unique Composite FIGI
4. explicit provider stable identifier
5. CIK plus cover-page ticker, exchange, and point-in-time consistency

Ticker-only final linkage is prohibited. One CIK can own multiple securities. Reused tickers and multiple candidates remain unjoined, ambiguous, or quarantined as appropriate.

## Universe Decisions

The fixture-only decision engine preserves accepted product policy:

- Core requires high-confidence U.S.-domestic operating common/ordinary equity or equity REIT evidence.
- Broad includes Core and may additionally admit high-confidence ADR/ADS or U.S.-listed foreign operating ordinary equity.
- Fund, BDC, mortgage REIT, SPAC, preferred, unit, warrant, right, debt, structured, partnership, royalty-trust, unknown, and ambiguous records cannot enter either candidate.

Production Core/Broad activation remains deferred.
