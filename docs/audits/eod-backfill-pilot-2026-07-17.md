# Massive EOD Backfill Pilot Audit — 2026-07-17

## Result

Final classification: `completed_single_session_pilot`.

The authorized Instrument Master entrypoint ran once from `2026-08-16T13:35:49Z` to `13:39:13Z` and exited 0. It made 14 serial `/v3/reference/tickers` requests with zero retries. After successful same-day snapshot reread, the Grouped Daily entrypoint ran once from `13:40:05Z` to `13:40:13Z` and exited 0, making one adjusted=false request for 2026-07-17 with zero retries. The 52-second cross-entrypoint interval exceeded the required 15 seconds. No later session was attempted.

## Identity Publication

- raw / eligible / expected exclusion / malformed: 13,024 / 10,996 / 1,940 / 88
- resolved / unresolved eligible: 9,879 / 1,117
- canonical instruments / resolver entries: 9,879 / 9,879
- duplicate ticker groups: 2; ambiguous ticker records: 0; stable-ID collisions: 0; orphan canonical references: 0
- eligible identity coverage: 0.898418; malformed ratio: 0.006757
- instrument fingerprint / Parquet SHA-256: `9ee1c7238ecf8d0641e94e3eb52a91532d213114ef8f68c0fbefc5401bf41dae` / `9c5e788b3edd5f464a91c491f32a27a6e14748972c04d2a03a4ca7f933a6c875`
- identity fingerprint / Parquet SHA-256: `2860ad2c6152fb89a94c848521bac902895499f823d8b1736f5b2c71ea4cf78a` / `36eb3093e6bab5577989bd563f6ff8d9bc2e72df23bb58ecbc6032493e4728fc`
- resolver fingerprint / Parquet SHA-256: `56ce3e0e644011d878058c670c9c8eb12d759f2f1443d3ca4b363b949f0f3eb6` / `02a0d9aa987b38d40bb244715a0c7fc968680e1267e7832aa071a8e73613aee1`
- logical snapshot fingerprint: `32af2ffc1538b5cbd261cc5299f27e52e3a6532917d4c3f47a50aaf4e50bccad`

Explicit schemas, counts, ordering, fingerprints, hashes, UUID references, resolver uniqueness, logical completion, and zero staging residue passed formal reread. Provider and as-of date are `massive_stocks_basic` and 2026-07-17; no latest or future resolver was used.

## Grouped Daily Publication

- raw / unique ticker: 12,411 / 12,409
- exact duplicate ticker/record: 0 / 0
- conflicting duplicate ticker/record: 2 / 4 (ratio 0.000322), isolated by the existing policy
- resolved eligible / unresolved / expected exclusions: 9,848 / 1,000 / 1,461
- ambiguous / rejected / missing identity: 0 / 88 / 14
- identity coverage: 0.906647
- required numeric failures: 0; optional VWAP/trade-count missing: 4 / 4
- fractional-volume / zero-volume: 10,892 / 4
- nonpositive price, OHLC inconsistency, negative volume, timestamp mismatch, canonical validation failure: all 0
- canonical bars: 9,844; reconciliation and all hard quality gates passed
- content fingerprint: `c1bdf54e0ff421e74ffd5d57fe9e18ddca0dc8ac67d320dac6c06a8f4227b7c6`
- Parquet SHA-256: `ec733ebc0b4887ca742ffb03d2c2df7bc78a30ec8a1145765b2f44fc2417dba9`

The completed manifest references the 2026-07-17 identity snapshot exactly. Formal repository reread passed schema, count, stable-key uniqueness, latest revision, ordering, fingerprint, physical hash, and future-reference checks. All 9,844 rows retain `adjustment_factors_unverified`; the data is unadjusted OHLCV and dollar volume remains a proxy.

## Protected State and Boundaries

The original protected inventory remained byte-for-byte and metadata-identical: 34 files, 12,942,699 bytes, digest `398d3c8eb8a986ffc34a7f2fe19c50961eca0d9ed52bd980da95217561333f17`. Nine authorized files were added: three identity Parquets and manifests, the identity logical manifest, and the EOD Parquet and manifest. The resulting inventory is 43 files, 16,217,517 bytes, digest `e73bd3b39c871179a38ab712b7d6fe9f86995cf154728ffaafc87c641b971540`. Staging and raw-payload residues are zero.

Only the two authorized Massive endpoints were reached: 15 total requests, zero retries. SEC, OCI, other services, later sessions, scheduler, Dashboard/API/frontend, snapshot/bundle, deployment, and Universe activation were untouched. Credential handling was limited to metadata preflight and the existing loader inside the two authorized processes; no secret or header value was emitted.

## Offline Postflight

Preflight focused tests passed 139 cases; postflight focused ingestion, repository, transport, history, and credential-metadata tests passed 135 cases. Health regression passed 2 cases with 782 deselected and the two existing deprecation warnings; there were no skipped or xfailed tests. Compileall, required imports, FastAPI app import, shell syntax, 89-file/214-link Markdown validation, sensitive-information scan over 282 tracked-or-pending files, socket prohibition, process/listener checks, and `git diff --check` passed. Ordinary tests made zero external-network attempts.
