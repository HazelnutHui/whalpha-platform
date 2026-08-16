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
