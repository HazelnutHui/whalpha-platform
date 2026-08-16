# SEC Issuer-Structure Evidence Operation

## Scope

The Phase B2B command is `scripts/admin/ingest-sec-issuer-structure-evidence.sh`. With no arguments it performs only identity and target preflight. `--apply` is a separately authorized live operation; ordinary tests and dry-runs do not load the private User-Agent or use the network.

The command allows only the documented SEC bulk/reference URLs, a maximum of 12 HTTP attempts, and serial requests at no more than two per second. The generic transport supports bounded retry for 429/recoverable 5xx responses, but the current live entrypoint explicitly sets retries to zero. It must not be rerun after a failed authorized operation without a new review and authorization.

## Publication Gates

All downloaded sources must pass content, size, hash, and ZIP safety validation before atomic source-cache publication. Normalized inputs must reconcile completely; ambiguous canonical mappings, stable-identity collisions, canonical business-key conflicts, future-filing leakage, schema mismatch, fingerprint mismatch, or staging residue prevent evidence publication. The logical completion manifest is written last.

Failed operations write only a sanitized diagnostic under `operation-diagnostics/sec-issuer-structure-evidence/`. Historical schema `2.0` diagnostics remain audit records and are not rewritten. New discovery emits schema `3.0`, which separates baseline URL status, exact-template status, temporal relation, warning action, and blocking action and derives all aggregate counts from candidate records. It never includes the private User-Agent, contact address, headers, raw response, HTML, row text, cookies, credentials, arbitrary query or fragment values, userinfo, external hostnames, or provider payload.

## First B2B Run

The 2026-08-16 UTC operation made three requests and zero retries. Both ticker-reference JSON files passed format validation. The first CSV landing page response did not produce exactly one allowlisted official CSV candidate, so source acquisition failed closed. Staging was removed; no source cache, observation partition, canonical evidence partition, or logical completion marker was published. See the [audit](../audits/sec-issuer-structure-evidence-2026-08-14.md).

## Dated CSV Selection

The first correction remained incomplete: it expected year/date semantics in table headers, while the three official pages use `File / Format / Size`; the file anchor carries the year and its tail text carries `Updated ...`. The parser now normalizes whitespace, NBSP, and case, locates one unique matching table, scans every row, reads complete cell text, and treats the Format cell as authoritative. It accepts `M/D/YY`, `MM/DD/YY`, `M/D/YYYY`, and `MM/DD/YYYY`, expands two-digit years into 2000–2099, requires the date year to match the file year, and chooses the unique maximum date at or before the cutoff independently of row or XML/CSV order. Same-date identical URLs deduplicate; same-date distinct URLs fail closed.

Every CSV candidate first passes Baseline URL Safety: exact SEC HTTPS host, standard port, controlled public investment-data root, explicit CSV extension, and no userinfo, query, fragment, backslash, traversal, encoded traversal, control character, or abnormal decoding. Any baseline failure is blocking regardless of age. Discovery then selects from all structurally valid dated candidates without first discarding exact-template mismatches. The unique latest candidate must pass the existing dataset-specific Exact Dataset Template; otherwise the operation fails and must not fall back.

Only a baseline-safe, date-valid candidate strictly older than the selected date may ignore its sole `path_template_mismatch` as `historical_path_template_mismatch_ignored`. Only a baseline-safe undated candidate with a file year strictly older than the selected file year may become `undated_historical_ignored`. Neither warning candidate is requested. Same/newer or future-invalid candidates, malformed or conflicting dates, file-year/date mismatch, selected URL/template rejection, and maximum-date distinct-URL ties remain blocking. Series/Class still has only its modern rule plus the exact 2024 legacy-directory and exact 2023 underscore-basename contracts; no 2022-or-earlier allowlist entry exists, and CEF/BDC are unchanged.

The source-cache manifest records total, eligible, and future CSV candidate counts plus the selected dataset year, effective date, canonical URL, selection fingerprint, file hash, and size. Source acquisition accepts only the validated selection object, rechecks its schema `3.0` diagnostic, counts, fingerprint, selected record, baseline safety, and exact template before transport is called. It never records the private User-Agent or contact address.

## Second B2B Run

After the dated selector passed all offline tests, the separately authorized run on 2026-08-16 UTC made three requests and zero retries. Both reference JSON files again passed staging validation. The first Investment Company Series/Class landing request reached the dated-discovery gate, which returned `sec_csv_discovery_cardinality_failure`; no CSV or submissions request followed.

The diagnostic from that run intentionally omitted response bodies but collapsed several selector subconditions, so the exact failed row could not be reconstructed. The offline remediation now emits a non-content structural summary and exact reason code without retaining HTML or contact identity. Three minimal synthetic fixtures model the official page structures; no live SEC request was authorized or performed during this remediation.

## Fourth B2B Run

The one separately authorized post-schema run on 2026-08-16 UTC made three SEC requests and zero retries. Both approved ticker-reference JSON resources reached staging validation. Candidate-level schema `2.0` then showed that the 2026 and 2025 Series/Class CSV candidates matched the current template, while the 2024 candidate used the public `investment-company-series-and-class-information` directory variant and failed with `path_template_mismatch`. Query, fragment, and userinfo were absent. The operation failed closed before any CSV, CEF, BDC, or submissions request.

No completed source cache, observation, canonical evidence, or logical manifest was published. Staging was empty after the run, the 34-file protected inventory was unchanged, the allowlist was not changed, and no second run occurred. Review the path variant offline before proposing any narrowly tested rule change; another SEC request requires new explicit authorization.

## Offline Exact-2024 Remediation

The fourth run's sanitized evidence is sufficient for one narrow historical rule: Series/Class file year 2024 may use the exact observed legacy directory and exact 2024 basename. Synthetic `File / Format / Size` fixtures prove that 2026 modern, 2025 modern, and 2024 legacy candidates are all eligible at cutoff 2026-08-14, while the unique latest 2026 release is selected independently of row order. Only the selected 2026 CSV would be downloaded.

Diagnostic candidate records now deterministically derive the top-level candidate, allowlisted, rejected, cutoff-eligible, and selected counts in both normal and fail-closed paths. If two candidates become cutoff-eligible before a third is rejected, the diagnostic reports two eligible, one rejected, and zero selected. Schema remains `2.0` and top-level reason codes remain compatible. This remediation was entirely offline: no credential metadata/content, `/data`, SEC/Massive endpoint, OCI, snapshot, bundle, or deployment was accessed.

## Fifth B2B Run

The one separately authorized post-remediation run on 2026-08-16 UTC made three SEC requests and zero retries. The two ticker-reference JSON sources passed staging validation. Series/Class discovery then accepted the 2026 and 2025 modern candidates plus the exact 2024 legacy candidate, reporting allowlisted and cutoff-eligible counts of three. A fourth 2023 CSV candidate used the modern directory but an underscore-style `investment_company_series_class_2023.csv` basename; it failed with `path_template_mismatch`.

The operation failed closed before selection, so `selected_count` was zero and no Series/Class CSV, CEF, BDC, or submissions request followed. No completed cache or evidence target was published, staging was removed, the protected inventory was unchanged, and no second run occurred. The 2023 path is evidence for offline review only and must not be accepted without a separately authorized code task.

## Offline Exact-2023 Remediation

The fifth run's schema `2.0` evidence supports one narrow filename contract: parsed file year 2023 may use the exact modern directory with exact basename `investment_company_series_class_2023.csv`. Relative paths and absolute `https://www.sec.gov` URLs are accepted only after the existing scheme, host, userinfo, port, query, fragment, backslash, traversal, encoded-traversal, and extension checks pass. The rule does not cover 2022 or earlier, another directory or mixed spelling, or underscore basenames for 2024 and later. The independently evidenced exact 2024 legacy-directory rule remains unchanged.

An official-shape four-candidate fixture produces four CSV candidates, four allowlisted and cutoff-eligible candidates, zero rejected candidates, and exactly one selection: the 2026 release dated 2026-06-01. The 2025, 2024, and 2023 releases remain eligible but unselected, and reversing row order yields the same result. Source acquisition consumes only the returned selection, so historical CSVs are not download targets. This remediation changed no diagnostic schema or aggregate semantics.

No live run was authorized or executed during this remediation. Credentials were not read or statted, `/data` and OCI were not accessed, and no snapshot, bundle, deployment, EOD, backfill, scheduling, Dashboard, or Universe work occurred. A future SEC request still requires separate explicit one-run authorization.

## Sixth B2B Run

The one separately authorized post-2023-remediation run started at `2026-08-16T09:30:12Z` and ended at `2026-08-16T09:30:18Z` with exit code 1. It used cutoff 2026-08-14, request ceiling 12, and zero retries. The two approved ticker-reference JSON resources passed staging validation. Request 3 reached Series/Class landing discovery; no other request followed.

Schema `2.0` selected the unique second `File / Format / Size` table and scanned ten anchored rows. It recorded five CSV candidates: 2026 modern, 2025 modern, exact 2024 legacy, and exact 2023 underscore were accepted and cutoff-eligible; a fifth 2022 candidate used the modern directory with basename `investment_company_series_class_2022.csv` and failed `path_template_mismatch`. Counts were candidates 5, allowlisted 4, rejected 1, cutoff-eligible 4, and selected 0. The failure occurred before selection finalization, so the 2026 CSV was not downloaded and CEF, BDC, and submissions were not reached.

The run failed closed, retained one sanitized diagnostic, removed its staging, and published no completed source cache, observation, canonical evidence, or logical manifest. The 34-file protected inventory remained byte-for-byte identical. No rule was changed, no second run occurred, and the 2022 path must be reviewed offline without inferring a general rule for earlier years.

## Offline Selected-Source Gate Remediation

The sixth-run evidence was used only to expose the selector-policy defect; the observed 2022 path was not added to any allowlist. A fully local five-candidate fixture reproduces 2026 modern, 2025 modern, exact 2024 legacy, exact 2023 underscore, and the 2022 historical mismatch. Schema `3.0` selects the 2026 release dated 2026-06-01, reports five baseline-safe candidates, four exact-allowlisted candidates, one historical path warning, zero blocking rejections, and exactly one selected candidate. The 2022 candidate is `older`, `ignored_warning`, and `historical_path_template_mismatch_ignored`; fake transport receives only the 2026 URL.

This remediation performed no SEC or Massive request, credential read or metadata check, `/data` or OCI access, snapshot/bundle generation, deployment, EOD/backfill/scheduling, Dashboard work, or Universe activation. Production SEC evidence remains unpublished. A live validation run remains a separate operation requiring explicit authorization.
