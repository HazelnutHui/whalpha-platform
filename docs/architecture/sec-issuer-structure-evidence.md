# SEC Issuer-Structure Evidence Boundary

## Status

Phase B2A implemented and fixture-validated the boundary offline. Phase B2B implements a bounded streaming transport and atomic source-cache, observation, canonical-evidence, and logical-completion layers. Four authorized B2B runs failed closed during official Series/Class CSV discovery and produced no completed source cache or evidence snapshot. The fourth run's schema `2.0` record directly supports one exact 2024 Series/Class legacy path; the offline contract now accepts only that observed year/path/basename combination alongside the modern template. No later live run has exercised the correction. Universe activation and Dashboard changes remain out of scope.

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

Official landing pages contain multiple tables and list multiple yearly CSV/XML releases. Discovery locates exactly one table whose normalized headers are `File / Format / Size`, then parses each row structurally. The file year comes from the anchor label; an explicit `Updated` date may follow the anchor as cell-tail text. Dates support deterministic two- or four-digit years and must agree with the file year. Selection ignores DOM and CSV/XML ordering, excludes releases after the inclusive evidence cutoff, and chooses the unique maximum eligible date.

Each dataset has its own exact, year-parameterized `https://www.sec.gov` modern path rule. Series/Class additionally accepts only `/files/investment/data/other/investment-company-series-and-class-information/investment-company-series-class-2024.csv` when the parsed file year is exactly 2024. This is a single observed historical exception, not a directory wildcard or a rule for 2023 and earlier; the legacy directory remains invalid for 2025, 2026, and future years. CEF and BDC are unchanged. Historical undated CSV rows are excluded only when their year is strictly earlier than an already selected dated release; a current/later undated row fails closed. Unsafe URLs, malformed or conflicting dates, ambiguous download tables, and tied maximum dates fail with bounded reason codes. Diagnostics contain only structural counts, normalized known headers, reason counts, and sanitized selection metadata; they never retain HTML, row text, headers, contact configuration, or arbitrary query values.

`application/octet-stream` is accepted only at the selected-CSV validation layer, after the URL has passed the dataset-specific rule and the non-empty file has passed the matching dataset header checks. The generic SEC transport is not relaxed.

## Landing discovery diagnostics

Landing discovery diagnostics use schema version `2.0`. The existing top-level failure reason remains stable (for example, `href_rejected`), while each CSV candidate records its deterministic ordinal, download-table ordinal, DOM row index, normalized format and bounded size text, parsed file year and update date, anchor count, selection state, URL validation state, and a finite detailed failure code. Candidate diagnostics may retain the normalized public SEC path, basename, and template-match result. They never retain a complete URL, external hostname, query or fragment values, userinfo, headers, User-Agent, contact identity, raw HTML, or response content.

URL failures distinguish HTTPS scheme, userinfo, host, port, backslash, literal or encoded traversal, query, fragment, dataset path template, CSV extension, file-year mismatch, and malformed URL. Those failure codes are diagnostic-only; the exact 2024 exception above is the sole path-selection change, and all other dataset and fail-closed rules remain unchanged. Unsafe or unparseable Size text becomes null rather than being copied into the diagnostic, and all serialized candidate order follows the source DOM so repeated parsing of the same input is deterministic.

Candidate-level records are the single source for CSV candidate, allowlisted, parsed-date, future, historical-undated, rejected, cutoff-eligible, and selected aggregate counts. Schema `2.0` includes `selected_count`; a completed unique selection has exactly one selected candidate, while a fail-closed exception before selection has zero. Exact duplicate candidates are marked `duplicate_excluded` rather than creating multiple selected records. The compatible top-level reason codes are unchanged.

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
