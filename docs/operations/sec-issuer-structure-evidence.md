# SEC Issuer-Structure Evidence Operation

## Scope

The Phase B2B command is `scripts/admin/ingest-sec-issuer-structure-evidence.sh`. With no arguments it performs only identity and target preflight. `--apply` is a separately authorized live operation; ordinary tests and dry-runs do not load the private User-Agent or use the network.

The command allows only the documented SEC bulk/reference URLs, a maximum of 12 HTTP attempts, serial requests at no more than two per second, and bounded retry for 429/recoverable 5xx responses. It must not be rerun after a failed authorized operation without a new review and authorization.

## Publication Gates

All downloaded sources must pass content, size, hash, and ZIP safety validation before atomic source-cache publication. Normalized inputs must reconcile completely; ambiguous canonical mappings, stable-identity collisions, canonical business-key conflicts, future-filing leakage, schema mismatch, fingerprint mismatch, or staging residue prevent evidence publication. The logical completion manifest is written last.

Failed operations write only a sanitized diagnostic under `operation-diagnostics/sec-issuer-structure-evidence/`. Landing discovery schema `2.0` preserves the existing top-level reason and adds one bounded record per CSV candidate: candidate/table/row ordinals, normalized format and safe Size, parsed year/date, anchor count, selection and URL-validation states, detailed reason code, and public SEC path diagnostics. It never includes the private User-Agent, contact address, headers, raw response, HTML, row text, cookies, credentials, arbitrary query or fragment values, userinfo, external hostnames, or provider payload.

## First B2B Run

The 2026-08-16 UTC operation made three requests and zero retries. Both ticker-reference JSON files passed format validation. The first CSV landing page response did not produce exactly one allowlisted official CSV candidate, so source acquisition failed closed. Staging was removed; no source cache, observation partition, canonical evidence partition, or logical completion marker was published. See the [audit](../audits/sec-issuer-structure-evidence-2026-08-14.md).

## Dated CSV Selection

The first correction remained incomplete: it expected year/date semantics in table headers, while the three official pages use `File / Format / Size`; the file anchor carries the year and its tail text carries `Updated ...`. The parser now normalizes whitespace, NBSP, and case, locates one unique matching table, reads complete cell text, and treats the Format cell as authoritative. It accepts `M/D/YY`, `MM/DD/YY`, `M/D/YYYY`, and `MM/DD/YYYY`, expands two-digit years into 2000–2099, requires the date year to match the file year, and selects the unique maximum date at or before the cutoff independently of row or XML/CSV order.

Undated archive rows are tolerated only when strictly older than the selected dated release. Each of Series/Class, CEF, and BDC has an exact year-parameterized path allowlist. HTTP, lookalike/external hosts, userinfo, nonstandard ports, backslashes, traversal (including encoded traversal), queries, fragments, wrong dataset directories, and non-CSV paths are rejected. Discovery errors retain top-level codes such as `download_table_header_mismatch`, `updated_date_parse_failed`, `href_rejected`, and `max_date_distinct_url_tie`. For `href_rejected`, inspect the candidate's finite detail code: `scheme_not_https`, `userinfo_present`, `host_not_allowed`, `nonstandard_port`, `backslash_present`, `traversal_present`, `encoded_traversal_present`, `query_present`, `fragment_present`, `path_template_mismatch`, `extension_not_csv`, `file_year_mismatch`, or `malformed_url`. Do not infer rejected query, fragment, userinfo, or external-host values because they are intentionally not retained.

The source-cache manifest records total, eligible, and future CSV candidate counts plus the selected dataset year, effective date, canonical URL, file hash, and size. It never records the private User-Agent or contact address.

## Second B2B Run

After the dated selector passed all offline tests, the separately authorized run on 2026-08-16 UTC made three requests and zero retries. Both reference JSON files again passed staging validation. The first Investment Company Series/Class landing request reached the dated-discovery gate, which returned `sec_csv_discovery_cardinality_failure`; no CSV or submissions request followed.

The diagnostic from that run intentionally omitted response bodies but collapsed several selector subconditions, so the exact failed row could not be reconstructed. The offline remediation now emits a non-content structural summary and exact reason code without retaining HTML or contact identity. Three minimal synthetic fixtures model the official page structures; no live SEC request was authorized or performed during this remediation.
