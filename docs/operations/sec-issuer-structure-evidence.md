# SEC Issuer-Structure Evidence Operation

## Scope

The Phase B2B command is `scripts/admin/ingest-sec-issuer-structure-evidence.sh`. With no arguments it performs only identity and target preflight. `--apply` is a separately authorized live operation; ordinary tests and dry-runs do not load the private User-Agent or use the network.

The command allows only the documented SEC bulk/reference URLs, a maximum of 12 HTTP attempts, serial requests at no more than two per second, and bounded retry for 429/recoverable 5xx responses. It must not be rerun after a failed authorized operation without a new review and authorization.

## Publication Gates

All downloaded sources must pass content, size, hash, and ZIP safety validation before atomic source-cache publication. Normalized inputs must reconcile completely; ambiguous canonical mappings, stable-identity collisions, canonical business-key conflicts, future-filing leakage, schema mismatch, fingerprint mismatch, or staging residue prevent evidence publication. The logical completion manifest is written last.

Failed operations write only a sanitized diagnostic under `operation-diagnostics/sec-issuer-structure-evidence/`. It contains counts, timestamps, and a fixed failure category, never the private User-Agent, contact address, headers, raw response, cookies, credentials, or provider payload.

## First B2B Run

The 2026-08-16 UTC operation made three requests and zero retries. Both ticker-reference JSON files passed format validation. The first CSV landing page response did not produce exactly one allowlisted official CSV candidate, so source acquisition failed closed. Staging was removed; no source cache, observation partition, canonical evidence partition, or logical completion marker was published. See the [audit](../audits/sec-issuer-structure-evidence-2026-08-14.md).

## Dated CSV Selection

The original global “exactly one CSV link” rule was incorrect because SEC data tables retain multiple yearly CSV and XML releases. The corrected selector parses download-table rows and requires an explicit dataset year, update/effective date, format, and href. It accepts the documented SEC date formats, rejects future-dated versions relative to the evidence cutoff, and selects the maximum eligible date independently of HTML order. A tie between distinct canonical URLs is an error. HTTP, external-host, script/data, traversal, fragment, query, userinfo, or non-`/files/` CSV paths are rejected.

The source-cache manifest records total, eligible, and future CSV candidate counts plus the selected dataset year, effective date, canonical URL, file hash, and size. It never records the private User-Agent or contact address.

## Second B2B Run

After the dated selector passed all offline tests, the separately authorized run on 2026-08-16 UTC made three requests and zero retries. Both reference JSON files again passed staging validation. The first Investment Company Series/Class landing request reached the dated-discovery gate, which returned `sec_csv_discovery_cardinality_failure`; no CSV or submissions request followed.

The current sanitized diagnostic intentionally omits response bodies, but it also collapses the selector's no-candidate, malformed-row, no-cutoff-eligible, and tied-latest subconditions into one reason. Because staging HTML was removed, the exact DOM/subcondition cannot be reconstructed without another request. No such request was made. A future design must retain a non-content structural summary such as table/header counts and candidate-status counts without retaining HTML or contact identity.
