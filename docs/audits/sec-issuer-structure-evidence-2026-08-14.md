# SEC Issuer-Structure Evidence Audit — 2026-08-14

## Decision

Status: `failed_source_discovery`; evidence publication: `not_published`; production Universe activation: `deferred`.

The first bounded Phase B2B operation ran on 2026-08-16 UTC with evidence cutoff 2026-08-14. It made three SEC requests and no retries. The first two approved JSON sources were downloaded into staging and passed their tabular-format checks. On the third request, the Investment Company Series/Class landing page did not resolve to exactly one allowlisted CSV candidate under the conservative discovery rule. The operation stopped without another request.

## Safe State

- Sanitized diagnostic: `operation-diagnostics/sec-issuer-structure-evidence/as_of_date=2026-08-14/run_id=sec-b2b-2026-08-14-20260816T033444Z`
- Completed source cache: absent
- SEC observation partition: absent
- Canonical SEC evidence partition: absent
- Logical completion manifest: absent
- Staging residue: none observed
- Existing Instrument Master, Provider Identity, Ticker Resolver, Massive security evidence, and EOD partitions: unchanged
- Production snapshot and OCI deployment: not performed

No source hash is reported because the cache was not completed and staged files were removed. No provider-type, SEC evidence, Core/Broad shadow, edge-ticker, or coverage counts are available from this failed run; inferring them would be incorrect. The diagnostic contains no User-Agent, contact address, raw headers, raw response, credential data, or password.

## Next Gate

Review the landing-page CSV discovery contract offline using a small sanitized official-shape fixture or an explicitly reviewed URL-selection rule before considering any additional SEC request. A new request requires separate authorization.

## Initial Offline Remediation

The first remediation added dated row selection but modeled table headers as carrying year/date semantics. That did not match the official pages' actual `File / Format / Size` structure, so it was insufficient. This does not alter the failed-run record or imply an SEC access failure.

## Second Authorized Run

Status: `failed_source_discovery`; evidence publication: `not_published`; production Universe activation: `deferred`.

The second and final authorized run in this phase began at `2026-08-16T04:20:02.777992Z`. It made three requests and zero retries. The two ticker-reference JSON sources reached and passed staging format validation. Request 3 was the Investment Company Series/Class landing page; dated discovery returned `sec_csv_discovery_cardinality_failure`, so no CSV or submissions download occurred.

- Sanitized diagnostic: `operation-diagnostics/sec-issuer-structure-evidence/as_of_date=2026-08-14/run_id=sec-b2b-2026-08-14-20260816T042002Z`
- Completed source cache: absent
- SEC observation partition: absent
- Canonical SEC evidence partition: absent
- Logical completion manifest: absent
- Staging residue: none observed

The diagnostic category proves the failure stage but not the selector subcondition because current sanitization merges several landing-discovery errors and the staged HTML is deleted. It would be incorrect to claim a specific selected year/date, source hash, evidence distribution, Core/Broad shadow count, or edge-ticker result. Existing canonical data and the production legacy Universe remain unchanged.

## DOM-Coverage Remediation

The parser now uses the unique normalized `File / Format / Size` table, reads year from the file anchor and `Updated` date from complete cell text including anchor-tail nodes, and handles the two- and four-digit official date forms. Three minimal synthetic fixtures cover Series/Class, CEF, and BDC structures, including unrelated tables, CSV/XML pairs, relative links, NBSP/whitespace, undated historical rows, and reversed historical format order.

Selection is cutoff-aware, row-order independent, and constrained by three exact year-parameterized SEC path rules. Current/later undated candidates, malformed or conflicting dates, unsafe paths, and ambiguous tables fail closed. The new structured diagnostic distinguishes table, row, date, URL, eligibility, and tie failures using only bounded counts and sanitized selection metadata. No raw HTML was retained. This remediation made zero SEC/Massive requests, did not access credentials or `/data`, and did not generate a snapshot or deploy OCI. Both failed live runs remain non-publishing and caused no production data damage. A future live run remains separately authorized work.

## Third Authorized Run

Status: `failed_source_discovery`; evidence publication: `not_published`; production Universe activation: `deferred`.

Before this run, SEC live retry behavior was changed and independently committed so recoverable failures permit no retry. The single authorized run started at `2026-08-16T05:34:38Z` and ended at `2026-08-16T05:34:48Z`, using evidence cutoff 2026-08-14. It made three requests and zero retries: the two approved ticker-reference JSON resources followed by the Investment Company Series/Class landing page. No CSV, CEF/BDC landing page, submissions archive, Massive endpoint, or other service was requested.

The landing parser found two tables, uniquely selected the normalized `File / Format / Size` table, scanned six anchored rows, and found three CSV candidates. Two candidates passed the dataset allowlist; the next candidate failed closed with `href_rejected`. No raw href or page content was retained, so this record does not infer the rejected path.

- Sanitized diagnostic: `operation-diagnostics/sec-issuer-structure-evidence/as_of_date=2026-08-14/run_id=sec-b2b-2026-08-14-20260816T053442Z`
- Completed source cache: absent
- SEC observation partition: absent
- Canonical SEC evidence partition: absent
- Logical completion manifest: absent
- Staging residue: zero
- Protected pre/post inventory: 34 files, identical SHA-256 inventory
- Production snapshot, bundle, deployment, and Universe change: not performed

Because discovery failed before a CSV was selected, no release date, file year, CSV header result, source file size, or source hash exists for any of the three datasets. No second live run is authorized.

## Offline actionable-diagnostic remediation

The third run's sanitized record established only that candidate 3 failed under the aggregate `href_rejected` reason after two candidates passed the exact allowlist. It did not retain candidate ordinal, DOM row, file year/date, Format/Size, public path structure, or the specific URL rule, so it cannot establish whether that candidate was a legitimate target variant, an historical row, unrelated CSV, or suspicious URL.

The offline remediation adds landing-discovery diagnostic schema `2.0` with deterministic candidate-level context and finite URL failure codes while preserving the compatible top-level reason. Complete URLs, external hostnames, query/fragment/userinfo values, headers, User-Agent, contact identity, raw HTML, and response bodies remain excluded. Exact Series/Class, CEF, and BDC allowlists and selection behavior were not changed. The third live candidate therefore remains `unknown`; no path interpretation is recorded without a future separately authorized observation. This remediation made zero network requests, did not inspect credentials or `/data`, and did not generate or deploy any production artifact.

## Fourth Authorized Run — Schema 2.0 Evidence

Status: `failed_source_discovery`; evidence publication: `not_published`; production Universe activation: `deferred`.

The separately authorized one-run operation started at `2026-08-16T07:46:45Z` and ended at `2026-08-16T07:46:51Z` with exit code 1 and evidence cutoff 2026-08-14. It made exactly three SEC requests and zero retries: one request each for `company_tickers_exchange.json`, `company_tickers_mf.json`, and the Investment Company Series/Class landing page. The two JSON sources reached staging validation. Discovery then failed closed with top-level `href_rejected`; no Series/Class CSV, CEF landing/CSV, BDC landing/CSV, or submissions archive was requested.

Schema `2.0` found the unique second `File / Format / Size` table, scanned six anchored rows, and retained these bounded candidate records:

| Candidate | Table | Row | Format | Size | File year | Updated | Public SEC path | Basename | Template | URL state | Failure | Query | Fragment | Userinfo |
| --- | --- | --- | --- | --- | ---: | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 2 | 3 | `csv` | `7.68 MB` | 2026 | 2026-06-01 | `/files/investment/data/other/investment-company-series-class-information/investment-company-series-class-2026.csv` | `investment-company-series-class-2026.csv` | match | accepted | none | false | false | false |
| 2 | 2 | 5 | `csv` | `7.25 MB` | 2025 | 2025-06-02 | `/files/investment/data/other/investment-company-series-class-information/investment-company-series-class-2025.csv` | `investment-company-series-class-2025.csv` | match | accepted | none | false | false | false |
| 3 | 2 | 7 | `csv` | `7.21 MB` | 2024 | 2024-06-05 | `/files/investment/data/other/investment-company-series-and-class-information/investment-company-series-class-2024.csv` | `investment-company-series-class-2024.csv` | mismatch | rejected | `path_template_mismatch` | false | false | false |

The third candidate therefore provides direct evidence of a public SEC directory-name variant, but this run does not decide that the variant should be accepted. The strict allowlist and selection code were not changed, and no second run was made.

- Sanitized diagnostic: `operation-diagnostics/sec-issuer-structure-evidence/as_of_date=2026-08-14/run_id=sec-b2b-2026-08-14-20260816T074649Z`
- Diagnostic size: 3,903 bytes
- Diagnostic SHA-256: `9abd62a6ef9dc4f61e41b6e32c9dde54b594d33dbf8b640c5673b764ede05c50`
- Completed source cache, observation partition, canonical evidence partition, and logical completion manifest: absent before and after
- Staging residue: zero
- Protected inventory: 34 files and 12,942,699 bytes before and after; the deterministic relative-path/size/content-hash inventory digest remained `398d3c8eb8a986ffc34a7f2fe19c50961eca0d9ed52bd980da95217561333f17`
- Existing Instrument Master, Provider Identity, Ticker Resolver, Massive security evidence, and EOD partitions: unchanged
- Source downloads, CSV header checks, source sizes/hashes, observation/evidence reconciliation, snapshot/bundle generation, OCI access, deployment, and Universe activation: not reached or not performed

The private SEC credential was consumed only by the existing in-process loader after metadata checks; no User-Agent/contact value was printed, copied, hashed, committed, or recorded in the diagnostic.

## Offline Exact-2024 Remediation

The observed 2024 public-path variant has been reviewed and implemented offline as one exact exception: `/files/investment/data/other/investment-company-series-and-class-information/investment-company-series-class-2024.csv` is accepted only for parsed file year 2024 and the exact 2024 basename. The modern path remains valid, CEF and BDC are unchanged, and no rule is inferred for 2023 or earlier, 2025, 2026, or future legacy paths.

The same remediation removes independently maintained candidate aggregate counters. Schema `2.0` now derives candidate, allowlisted, parsed-date, future, historical-undated, rejected, cutoff-eligible, and selected counts from candidate diagnostics. The fourth-run shape therefore reproduces two cutoff-eligible candidates before the rejected third candidate, rather than the prior inconsistent top-level zero. With the exact legacy exception, the three observed synthetic candidates yield eligible count three, selected count one, and deterministic 2026 selection regardless of row order.

No new live SEC run was authorized or executed. Credential metadata/content and `/data` were not accessed; Massive, OCI, snapshot, bundle, deployment, EOD, backfill, and scheduling remained untouched. A future live request still requires separate explicit one-run authorization.

## Current Next Gate

Review the completed offline contract and regression evidence before deciding whether to authorize at most one additional bounded SEC evidence run. This audit does not authorize that request.
