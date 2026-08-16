# SEC Issuer-Structure Evidence Boundary

## Status

Phase B2A implemented and fixture-validated the boundary offline. Phase B2B implements a bounded streaming transport and atomic source-cache, observation, canonical-evidence, and logical-completion layers. Six authorized B2B runs failed closed during official Series/Class CSV discovery. After the two-stage selector and source-cache/ZIP hardening were completed offline, the final authorized run progressed through Series/Class landing and selected-CSV validation and through CEF landing selection, then failed during the sixth request with the sanitized code `sec_transport_or_source_validation_failure`. No completed source cache or evidence snapshot was published. The generic operation diagnostic did not retain the successful schema `3.0` landing summaries or a narrower sixth-request subcondition, so those facts must not be reconstructed by guess or another request. Phase B2 is paused for the current product stage; Universe activation and Dashboard changes remain out of scope.

## Purpose

Massive provider type evidence primarily establishes listed security form. It does not normally establish whether the issuer is an operating company, fund, BDC, REIT subtype, SPAC, partnership, or other special structure. SEC evidence is therefore a separate provider-neutral layer that can strengthen issuer-structure and listing-scope decisions without changing Instrument Master identity.

## Layers

`SecIssuerEvidenceObservationV1` stores a normalized assertion and may have no canonical `instrument_id`. It retains only audit fields needed to explain the assertion; raw SEC HTML, ZIP, JSON, headers, and contact configuration are not canonical evidence.

`SecIssuerStructureEvidenceV1` contains only uniquely mapped observations. Its business key is `instrument_id + as_of_date + evidence_kind + evidence_version`. Identical observations deduplicate deterministically. Conflicting assertions quarantine the instrument rather than silently selecting one.

The future dataset root is:

`market-data/sec-issuer-structure-evidence/schema_version=1/as_of_date=YYYY-MM-DD/`

The approved layers are `source-cache/sec/security-classification/as_of_date=<date>`, `market-data/sec-issuer-structure-observation/schema_version=1/as_of_date=<date>`, `market-data/sec-issuer-structure-evidence/schema_version=1/as_of_date=<date>`, and `market-data/snapshots/sec-issuer-structure-evidence/as_of_date=<date>`. Readers must require the final logical completion manifest; a cache or individual partition is not sufficient.

The repository provides explicit Arrow schema, deterministic ordering and fingerprinting, manifest and Parquet hashes, reread validation, sibling staging, atomic publication, idempotent rerun, conflict rejection, corruption rejection, and symlink containment. Phase B2A invokes it only under pytest `tmp_path`.

The live transport permits HTTPS only to `www.sec.gov` and `data.sec.gov`, runs serially at no more than two requests per second, limits the operation to 12 HTTP attempts, uses bounded retry only for 429/recoverable 5xx responses, and never serializes the private User-Agent. The source cache contains exactly nine private provenance artifacts: two official ticker JSON files, three official landing HTML pages, the three selected CSV files, and `submissions.zip`. Landing HTML is retained only as private acquisition evidence and is not a Dashboard or public-serving artifact. Each manifest record contains its artifact role, official URL, byte size, and SHA-256; headers, User-Agent, contact identity, cookies, and credentials are excluded. All nine artifacts are reread and reconciled before the completion manifest is written last and the staging directory is atomically published.

Submissions ZIP validation rejects encryption, exact or normalized duplicate names, absolute paths, traversal, backslashes, percent-encoded traversal, symlinks, non-regular members, unexpected or nested names, excessive member count, per-member and total expansion, excessive compression ratio, inconsistent zero compressed-size metadata, malformed JSON, HTML/error payloads, wrong roots, CIK/filename mismatches, and invalid basic submissions schemas. Members are read one at a time through a fixed-size bounded stream; extracted content is never persisted to the source cache or production paths. The 2026-08-14 cutoff is applied before canonical reconciliation; current reference data without historical-effective semantics cannot be backfilled as historical classification evidence.

Official landing pages contain multiple tables and list multiple yearly CSV/XML releases. Discovery locates exactly one table whose normalized headers are `File / Format / Size`, then scans every row structurally; a historical template mismatch cannot terminate the scan. The file year comes from the anchor label; an explicit `Updated` date may follow the anchor as cell-tail text. Dates support deterministic two- or four-digit years and must agree with the file year. Selection ignores DOM and CSV/XML ordering, excludes releases after the inclusive evidence cutoff, deterministically deduplicates identical date/URL records, and chooses the unique maximum eligible date. Distinct URLs tied at the maximum date fail closed.

URL validation has two stages. Baseline URL Safety applies to every CSV candidate and requires resolved HTTPS on exact host `www.sec.gov`, no userinfo or nonstandard port, no query or fragment, no backslash, traversal, encoded traversal, control character, or abnormal decoding, a path under the controlled public investment-data root, and an explicit CSV extension. Any baseline failure in any year remains blocking. Exact Dataset Template then applies the existing per-dataset directory, basename, and file-year allowlists. Only the unique selected candidate must pass this second stage before transport can receive it.

Each dataset retains its exact, year-parameterized modern path rule. Series/Class retains only two independently evidenced exact historical exceptions: `/files/investment/data/other/investment-company-series-and-class-information/investment-company-series-class-2024.csv` for parsed file year 2024, and `/files/investment/data/other/investment-company-series-class-information/investment_company_series_class_2023.csv` for parsed file year 2023. No 2022-or-earlier path was added. A dated candidate whose baseline safety passes and whose only exact-rule failure is `path_template_mismatch` may become `historical_path_template_mismatch_ignored` only when its file year matches its parsed date and that date is strictly older than the selected date. It is never requested. A baseline-safe undated row may become `undated_historical_ignored` only when its explicit file year is strictly earlier than the selected file year and it contains no malformed or conflicting Updated text. Same-year, newer, future-invalid, malformed-date, unsafe-URL, selected-template, and maximum-date ambiguity cases fail closed; discovery never falls back to an older allowlisted source.

`application/octet-stream` is accepted only at the selected-CSV validation layer, after the URL has passed the dataset-specific rule and the non-empty file has passed the matching dataset header checks. The generic SEC transport is not relaxed.

## Landing discovery diagnostics

New landing discovery diagnostics use schema version `3.0`; existing schema `2.0` operation diagnostics remain audit-readable and are never rewritten. Schema `3.0` makes warning and blocking semantics explicit with baseline-safe, exact-allowlisted, blocking-rejection, historical-path-warning, undated-historical-warning, cutoff-eligible, future-candidate, and selected counts; selected year/date/template, status, failure code, warning codes, and a deterministic selection fingerprint are also explicit.

Each schema `3.0` candidate contains only bounded structural ordinals, normalized format and Size, file year/date, temporal relation, baseline and exact-template status, reason, action, and—only after baseline safety passes—the normalized public SEC path and basename. It never contains a complete dangerous URL, external hostname, query/fragment/userinfo values, raw HTML or row text, request/response headers, User-Agent, contact identity, credential, Authorization, cookie, or fixture sentinel. Unsafe or unparseable Size text becomes null.

Candidate-level records remain the single source for schema `3.0` aggregate counts. A completed selection has exactly one `selected` action; historical exceptions are `ignored_warning`; every blocking candidate is `hard_fail`. The source-acquisition boundary accepts a structured `SecCsvSelection`, revalidates its schema, counts, fingerprint, selected candidate, baseline safety, and exact template, and only then passes the selected URL to transport. Arbitrary URL strings and historical warning candidates cannot enter that download path.

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
