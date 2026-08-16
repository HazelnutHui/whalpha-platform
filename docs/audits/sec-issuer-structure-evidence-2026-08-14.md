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

## Fifth Authorized Run — 2023 Candidate Discovery

Status: `failed_source_discovery`; evidence publication: `not_published`; production Universe activation: `deferred`.

The separately authorized run started at `2026-08-16T08:48:37Z` and ended at `2026-08-16T08:48:43Z` with exit code 1 and cutoff 2026-08-14. It made three SEC requests and zero retries: one each for `company_tickers_exchange.json`, `company_tickers_mf.json`, and the Series/Class landing page. The JSON files passed staging format validation. No CSV, CEF, BDC, or submissions request followed.

Schema `2.0` selected the second `File / Format / Size` table and scanned eight anchored rows. Its four CSV candidate records were:

| Candidate | Table | Row | Size | File year | Updated | Public SEC path | URL state | Selection state | Failure |
| --- | --- | --- | --- | ---: | --- | --- | --- | --- | --- |
| 1 | 2 | 3 | `7.68 MB` | 2026 | 2026-06-01 | `/files/investment/data/other/investment-company-series-class-information/investment-company-series-class-2026.csv` | accepted | `cutoff_eligible` | none |
| 2 | 2 | 5 | `7.25 MB` | 2025 | 2025-06-02 | `/files/investment/data/other/investment-company-series-class-information/investment-company-series-class-2025.csv` | accepted | `cutoff_eligible` | none |
| 3 | 2 | 7 | `7.21 MB` | 2024 | 2024-06-05 | `/files/investment/data/other/investment-company-series-and-class-information/investment-company-series-class-2024.csv` | accepted | `cutoff_eligible` | none |
| 4 | 2 | 9 | `7.4 MB` | 2023 | 2023-06-08 | `/files/investment/data/other/investment-company-series-class-information/investment_company_series_class_2023.csv` | rejected | `rejected` | `path_template_mismatch` |

All candidates had one anchor and normalized Format `csv`; query, fragment, and userinfo presence were false. Aggregate counts were candidate 4, allowlisted 3, parsed-date 4, rejected 1, cutoff-eligible 3, and selected 0. The aggregate consistency remediation therefore worked on the real fail-closed path. Because the fourth candidate failed before selection finalization, no selected year/date/path is recorded; it would be incorrect to claim that the 2026 CSV was selected or downloaded.

- Sanitized diagnostic: `operation-diagnostics/sec-issuer-structure-evidence/as_of_date=2026-08-14/run_id=sec-b2b-2026-08-14-20260816T084842Z`
- Diagnostic size: 4,798 bytes
- Diagnostic SHA-256: `70ae842c375add7094a4986afa337b92355c4a0848dac7757ba9b1d2cca62a2d`
- Completed source cache, observation partition, canonical evidence partition, and logical completion manifest: absent before and after
- Staging residue: zero; diagnostic run count increased from four to five
- Protected inventory: 34 files, 12,942,699 bytes, unchanged digest `398d3c8eb8a986ffc34a7f2fe19c50961eca0d9ed52bd980da95217561333f17`
- Existing identity, canonical EOD, and Massive evidence data: unchanged
- Snapshot, bundle, deployment, OCI access, and Universe activation: not performed

No new rule was added and no second run occurred. The underscore-style 2023 basename is retained only as sanitized public-path evidence.

## Offline Exact-2023 Remediation

The fifth-run evidence was reviewed offline and supports one exact additional contract: `/files/investment/data/other/investment-company-series-class-information/investment_company_series_class_2023.csv` is accepted only when the parsed file year is 2023 and the path matches character-for-character. The existing modern hyphen template and the separately evidenced exact 2024 legacy-directory rule remain unchanged. Underscore basenames for 2024 and later, all neighboring spellings and directories, and all 2022-or-earlier variants remain rejected or unknown rather than inferred.

A synthetic official-shape landing with the observed 2026 modern, 2025 modern, 2024 exact legacy, and 2023 exact underscore candidates yields candidate 4, allowlisted 4, rejected 0, cutoff-eligible 4, and selected 1. Selection is the 2026 release dated 2026-06-01 in normal and reversed row order; 2025, 2024, and 2023 are eligible but not selected. Existing duplicate exclusion, candidate-derived aggregates, CEF/BDC isolation, safe URL failure codes, sentinel redaction, and socket prohibition remain covered.

No live SEC run was authorized or executed. Credential metadata/content, `/data`, Massive, OCI, snapshots, bundles, deployment, EOD, backfill, scheduling, Dashboard, and Universe activation were not accessed or changed.

## Sixth Authorized Run — 2022 Candidate Discovery

Status: `failed_source_discovery`; evidence publication: `not_published`; production Universe activation: `deferred`.

The separately authorized run started at `2026-08-16T09:30:12Z` and ended at `2026-08-16T09:30:18Z` with exit code 1, cutoff 2026-08-14, request ceiling 12, and zero retries. It invoked the live entrypoint exactly once and made three SEC requests: one each for `company_tickers_exchange.json`, `company_tickers_mf.json`, and the Series/Class landing page. Both JSON sources passed staging format validation. No Series/Class CSV, CEF landing/CSV, BDC landing/CSV, or submissions archive was requested.

Schema `2.0` selected the second `File / Format / Size` table and scanned ten anchored rows. Its five CSV candidate records were:

| Candidate | Table | Row | Size | File year | Updated | Public SEC path | URL state | Selection state | Failure |
| --- | --- | --- | --- | ---: | --- | --- | --- | --- | --- |
| 1 | 2 | 3 | `7.68 MB` | 2026 | 2026-06-01 | `/files/investment/data/other/investment-company-series-class-information/investment-company-series-class-2026.csv` | accepted | `cutoff_eligible` | none |
| 2 | 2 | 5 | `7.25 MB` | 2025 | 2025-06-02 | `/files/investment/data/other/investment-company-series-class-information/investment-company-series-class-2025.csv` | accepted | `cutoff_eligible` | none |
| 3 | 2 | 7 | `7.21 MB` | 2024 | 2024-06-05 | `/files/investment/data/other/investment-company-series-and-class-information/investment-company-series-class-2024.csv` | accepted | `cutoff_eligible` | none |
| 4 | 2 | 9 | `7.4 MB` | 2023 | 2023-06-08 | `/files/investment/data/other/investment-company-series-class-information/investment_company_series_class_2023.csv` | accepted | `cutoff_eligible` | none |
| 5 | 2 | 11 | `7.55 MB` | 2022 | 2022-06-27 | `/files/investment/data/other/investment-company-series-and-class-information/investment_company_series_class_2022.csv` | rejected | `rejected` | `path_template_mismatch` |

Every candidate had normalized Format `csv`, one anchor, and no query, fragment, or userinfo. Aggregate counts were candidate 5, allowlisted 4, rejected 1, cutoff-eligible 4, and selected 0. Because candidate 5 failed before selection finalization, no selected year/date/path was recorded and it would be incorrect to claim the 2026 CSV was selected or downloaded.

- Sanitized diagnostic: `operation-diagnostics/sec-issuer-structure-evidence/as_of_date=2026-08-14/run_id=sec-b2b-2026-08-14-20260816T093016Z`
- Diagnostic size: 5,674 bytes
- Diagnostic SHA-256: `703daffbda0f590782a8dff0e627ba63e160c1269402636636139bc1388ce4cc`
- Completed source cache, observation partition, canonical evidence partition, and logical completion manifest: absent before and after
- Staging residue: zero; diagnostic run count increased from five to six
- Protected inventory: 34 files, 12,942,699 bytes, unchanged digest `398d3c8eb8a986ffc34a7f2fe19c50961eca0d9ed52bd980da95217561333f17`
- Existing identity, canonical EOD, and Massive evidence data: unchanged
- Massive/OCI access, snapshot, bundle, deployment, EOD, backfill, scheduling, Dashboard work, and Universe activation: not performed

The credential was only parsed inside the unique run by the existing loader after a regular-file, non-symlink, hui-owner, mode-600 metadata check. No credential or contact value was printed, copied, hashed, committed, or recorded. No rule was modified and no second run occurred.

## Offline Selection-Policy Clarification

The sixth-run schema `2.0` evidence does not justify a new 2022 path allowlist. It instead exposed that the then-current parser validated every historical candidate against Exact Dataset Template before determining which source would be selected. That policy allowed a safe but unused historical filename variation to block a fully validated unique latest source.

The offline remediation replaces that policy with two gates. Baseline URL Safety applies without exception to every CSV candidate. Selection then uses all structurally and temporally valid candidates to find the unique latest date at or before cutoff. Only that selected source must pass its dataset-specific exact template before download. A strictly older dated candidate may ignore only `path_template_mismatch`, and only after baseline safety, explicit date parsing, and file-year/date agreement pass. The action is `historical_path_template_mismatch_ignored`; the candidate never reaches transport. Strictly older baseline-safe undated rows use the separate `undated_historical_ignored` rule. All other safety, date, same/newer, future-invalid, tie, and selected-template failures remain blocking, with no fallback to an older source.

The local 2026–2022 fixture therefore produces selected year 2026, selected date 2026-06-01, the existing modern 2026 path, one 2022 historical-path warning, zero blocking rejections, and one selected record. The 2022 public path remains absent from the allowlist. Diagnostics emitted by new code are schema `3.0`; all six existing schema `2.0` operation diagnostics remain unchanged and audit-readable.

No live SEC request was authorized or performed for this clarification. No credential was read or statted, `/data` and OCI were not accessed, and no source cache, evidence, snapshot, bundle, deployment, Dashboard, EOD, scheduling, or Universe change occurred.

## Current Next Gate

The final bounded run for this product stage has completed unsuccessfully. Do not perform another SEC B2 live run or add another historical exception in this phase. Keep the Legacy Liquid Screen provisional and return to EOD history, trailing liquidity, sector taxonomy, and website functionality.

## Offline Source-Cache and ZIP Safety Completion

The publication preflight review found that the existing acquisition code intentionally retained the three official landing HTML pages, but their role and exact nine-artifact cache contract were not explicit. The offline correction formalizes the private cache as two ticker JSON files, three landing HTML pages, three selected CSV files, and `submissions.zip`. Landing HTML is private provenance evidence, not Dashboard or public content. Every artifact now carries a role, official URL, size, and SHA-256 and is reread before a last-written completion manifest and atomic rename. Existing/symlink targets and partial or mismatched staging inventories fail closed.

The same offline change completes the submissions ZIP safety gate for encrypted, duplicate/normalized-duplicate, absolute, traversing, backslash, percent-encoded, symlink, non-regular, nested, and unexpected members; member-count, per-member, total-expansion, compression-ratio, and zero compressed-size boundaries; and bounded JSON parsing with filename/CIK and basic filings-schema validation. No extracted member is persisted.

All evidence for this correction came from local synthetic ZIPs, fake transports, and pytest `tmp_path`. No SEC, Massive, or other external request was made; no credential was read or statted; `/data` and OCI were not accessed; and no production cache, evidence, snapshot, bundle, deployment, or Universe activation was created. The historical failed diagnostics remain unchanged, production SEC evidence remains unpublished, and a live run remains separately authorized work.

## Final Authorized Run — CEF Selected-Source Attempt

Status: `sec_transport_or_source_validation_failure`; evidence publication: `not_published`; production Universe activation: `deferred`; SEC B2 phase: `paused`.

The final authorized entrypoint invocation began at `2026-08-16T10:39:44Z`, ended at `2026-08-16T10:39:51Z`, and returned exit code 1. It was invoked exactly once, used cutoff 2026-08-14, request ceiling 12, and zero retries. The deterministic request sequence was:

1. `company_tickers_exchange.json`
2. `company_tickers_mf.json`
3. Investment Company Series/Class landing page
4. selected Series/Class CSV
5. Closed-End Fund landing page
6. selected CEF CSV attempt

The transition to request 5 establishes that Series/Class discovery returned a validated structured selection and that its selected CSV passed response/header validation. The transition to request 6 establishes that CEF discovery also returned a validated structured selection. BDC landing/CSV and `submissions.zip` were not reached. Historical warning URLs were not requested by the selected-object acquisition path.

The retained operation diagnostic is `operation-diagnostics/sec-issuer-structure-evidence/as_of_date=2026-08-14/run_id=sec-b2b-2026-08-14-20260816T103948Z/diagnostic.json`, size 329 bytes, SHA-256 `b82dd884f4fe3a78507faab26111063a8fc6e0b6667d107081710b8bfacfab0b`. It records request count 6, retry count 0, generic failure code `sec_transport_or_source_validation_failure`, schema `1.0`, and an empty quality summary. Because source-cache staging was cleaned, no surviving run evidence contains the successful landing candidate/warning counts, selected years/dates/paths, artifact sizes/hashes, or the narrower sixth-request failure. Claiming those values would be speculation; no second request was made to recover them.

Postflight results:

- Four completed SEC targets: absent
- Staging residue: zero
- Sanitized diagnostic count: seven
- Protected inventory: 34 files, 12,942,699 bytes, unchanged digest `398d3c8eb8a986ffc34a7f2fe19c50961eca0d9ed52bd980da95217561333f17`
- Instrument Master / Provider Identity / Resolver / resolved identities: 9,939 / 13,110 / 9,939 / 9,939, with manifests, fingerprints, schemas, and references revalidated
- Existing identity, EOD, and Massive evidence: unchanged
- Source cache, observations, canonical evidence, logical manifest, and Core/Broad shadow audit: not produced
- Massive/OCI/EOD/Dashboard/snapshot/bundle/deployment/Universe operations: not performed

The credential was used only inside the authorized process after metadata verified a regular non-symlink file owned by `hui` with mode 600. No credential/contact value, header, or raw response was printed or retained. Focused offline postflight tests passed, with zero external network attempts. This was the final SEC live run for the current product stage; the code and rules were not modified, and SEC B2 is now paused.
