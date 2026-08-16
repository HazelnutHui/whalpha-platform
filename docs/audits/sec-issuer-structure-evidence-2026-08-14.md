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

## Offline Remediation

The discovery contract now parses the SEC download table by row, filters explicit CSV rows by update/effective date at or before 2026-08-14, and deterministically selects the latest eligible release. Local fixtures cover multi-year tables, mixed XML/CSV rows, future releases, date formats, tied latest URLs, missing/malformed dates, unsafe URLs, absent CSVs, deterministic statistics, and the three approved table header variants. This remediation does not itself alter the failed-run record or authorize production activation.
