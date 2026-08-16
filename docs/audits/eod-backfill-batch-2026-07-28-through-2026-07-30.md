# Massive EOD Backfill Batch Audit — 2026-07-28 through 2026-07-30

## Result

Final classification: `completed_three_session_batch`.

The authorized sessions 2026-07-28, 07-29, and 07-30 ran strictly in date order. Each same-day Instrument Master snapshot completed and passed formal reread before its one Grouped Daily request. All six entrypoints exited 0, each was invoked once, retries were zero, and no later session was started.

| Session | Identity UTC | Reference requests | Grouped Daily UTC | Grouped requests | Status |
| --- | --- | ---: | --- | ---: | --- |
| 2026-07-28 | 19:17:33–19:20:57 | 14 | 19:21:37–19:21:45 | 1 | `completed` |
| 2026-07-29 | 19:22:42–19:26:06 | 14 | 19:26:47–19:26:56 | 1 | `completed` |
| 2026-07-30 | 19:27:41–19:31:09 observed | 14 | 19:31:51–19:31:59 | 1 | `completed` |

All timestamps are UTC on 2026-08-16. The 07-30 Identity publisher wrote its final completed marker at 19:31:06 and process exit was observed by 19:31:09. Adjacent entrypoints were separated by at least 40 seconds, exceeding the 15-second minimum. Total requests were 45, below the batch ceiling of 63.

## Identity Results

| Metric | 2026-07-28 | 2026-07-29 | 2026-07-30 |
| --- | ---: | ---: | ---: |
| Raw | 13,034 | 13,036 | 13,042 |
| Eligible | 11,002 | 11,002 | 11,009 |
| Expected exclusions | 1,942 | 1,944 | 1,943 |
| Malformed/rejected | 90 | 90 | 90 |
| Resolved / unresolved eligible | 9,881 / 1,121 | 9,882 / 1,120 | 9,888 / 1,121 |
| Duplicate ticker groups | 2 | 2 | 2 |
| Ambiguous / stable-ID collision | 0 / 0 | 0 / 0 | 0 / 0 |
| Identity coverage | 0.898109 | 0.898200 | 0.898174 |
| Malformed ratio | 0.006905 | 0.006904 | 0.006901 |
| Canonical instruments / resolver | 9,881 / 9,881 | 9,882 / 9,882 | 9,888 / 9,888 |

Quality gates and atomic publication passed on all days. Formal reread verified Arrow schemas, counts, deterministic ordering, UUID/referential integrity, resolver uniqueness, zero orphan references, manifests, and same-day logical completion.

| Session | Instrument fingerprint / Parquet SHA-256 | Identity fingerprint / Parquet SHA-256 | Resolver fingerprint / Parquet SHA-256 | Snapshot fingerprint |
| --- | --- | --- | --- | --- |
| 07-28 | `3a11f75b8f787491f3b14bb5f35288ad9429d928a1448543afa0505f0b655296` / `ee7608c1d5155f0ecee62e707508a5e950b4c78d7b701c785d87367bc02e2f0b` | `d0b3f8999aad6cb0ea4e8c8753b9c3813522ecb572c3f5220dcfcf99685c5394` / `cc62c886869b48036e8bb4e87458cdd5a90ff01b58b9bfc9fa11ada723775400` | `95062428908ebf63150cbbb29567886ffa157df15415edca1ddffa940b22d784` / `d8650903cdc4f1801daa8e33d7d7793d7c6d45f29bbac288e078ebb6704a32d5` | `2a02c457a4fd1fc74fb2231765ff7af3cd79f44e82ddbcae678ed85a6fab39c2` |
| 07-29 | `609f76b80a892df034f731a0c4840b956546a9134c2a5d1055b58c4a24a18ea6` / `43d3258c385dd117b60455804c0e61a39c67dba62bbf860cbd293908d4389a74` | `3ce8c4e7f155104d55e25910ee3fd2ebea086b02c29dbf83bceaefc4dcc22ae7` / `5187f7c9089aa2decfdef7b8b1766c9b7ba5b409fa00df1bc59aba6180914d0d` | `6c604ee4146d5e084722b14390a78864764bdae78a17f9698d651dc73e7d2985` / `265967cd09c665087f9c434e3c3192c2929b046cbe8353bb1c45aa89e520a062` | `8486b15eec9ac2b354b9270544594277044dcad1bb0dcbd88a414837b76d1b50` |
| 07-30 | `1998d32e812dc9aebb2f7184123c59f1f40d950c3f76c5a7806c7e8d2a0211ae` / `565adf3636f20d965f159112e6457f80abf9d14f72da7183d105269f4f4c32b9` | `58b54fac8f189ddd01e74de2b51985b5003a3f07b3245ca77f3f5f06db9afe28` / `433ee6cd7580998567817375b3f697a184ddadbd46d9b577634cc3636c483406` | `873b88d4f7907bff0f2139dee615ad73e4aabbf7dffdd023e1f247f6e3974f3c` / `fc256cb422b920906f48005ebedb92e44d61d9f6dbf3d29ad347201eb6619c00` | `3750e3625271634f2da5739eee0b7a3604783c6db3eda4ef805a11a15afdd973` |

## Grouped Daily Results

| Metric | 2026-07-28 | 2026-07-29 | 2026-07-30 |
| --- | ---: | ---: | ---: |
| Raw / unique ticker | 12,482 / 12,480 | 12,481 / 12,479 | 12,459 / 12,457 |
| Exact duplicate ticker/record | 0 / 0 | 0 / 0 | 0 / 0 |
| Conflicting ticker/record | 2 / 4 | 2 / 4 | 2 / 4 |
| Conflict ratio | 0.000320 | 0.000320 | 0.000321 |
| Resolved / unresolved eligible | 9,852 / 1,030 | 9,855 / 1,015 | 9,859 / 1,005 |
| Expected exclusions | 1,498 | 1,509 | 1,492 |
| Ambiguous / rejected / missing identity | 0 / 90 / 12 | 0 / 90 / 12 | 0 / 89 / 14 |
| Identity coverage | 0.904351 | 0.905624 | 0.906325 |
| Required numeric failures | 0 | 0 | 0 |
| Optional VWAP / trade-count missing | 3 / 3 | 3 / 3 | 3 / 3 |
| Fractional / zero volume | 10,992 / 3 | 10,968 / 3 | 10,963 / 3 |
| Canonical bars | 9,848 | 9,851 | 9,855 |

Nonpositive price, OHLC inconsistency, negative volume, timestamp mismatch, and canonical validation failures were zero every day. Existing low-ratio conflict isolation generated warnings without changing gates. Reconciliation, publish readiness, and atomic publication passed.

| Session | EOD fingerprint | Parquet SHA-256 | Same-day identity fingerprint |
| --- | --- | --- | --- |
| 07-28 | `cb6f8af12b89dec66d26664917197209545e9d577f55573e85e66aa22857f34c` | `430fb66ad378ac206c4cf968996ec963c32bd19a144bfea64fbaad960a1b1cd1` | `2a02c457a4fd1fc74fb2231765ff7af3cd79f44e82ddbcae678ed85a6fab39c2` |
| 07-29 | `e88e356c3d553dca4e20412051181174f0ad4c05f61e3dfdd3f57c6a5f128b7a` | `c988f791aac67505b6324bd38e4267c7732bb850b18272d4cdd186c680e0dd6b` | `8486b15eec9ac2b354b9270544594277044dcad1bb0dcbd88a414837b76d1b50` |
| 07-30 | `1f943e10a6ff9ee5c03176d8b7c3af078656fdd406749dc54687a13231c8621b` | `2924815ce0d50d49c665655f9c005d750787f820a510153369c4e937bce632c7` | `3750e3625271634f2da5739eee0b7a3604783c6db3eda4ef805a11a15afdd973` |

Every manifest references its exact same-day identity snapshot. Future identity references, duplicate business keys, and multiple latest revisions are zero. All rows retain `adjustment_factors_unverified`; no raw payload was persisted.

## Inventory and Boundaries

The original 97-file, 35,868,019-byte protected inventory remained content- and metadata-identical, including digest `27fe6529ca6b7789f5901065f0d9dad405c8532a835be04846022437e7c330dc`. Exactly 27 authorized files were added. Final inventory: 124 files, 45,701,023 bytes, digest `1187d3de85c668dbb459e3808640b86325daf9e5f247a553b99785bfe465e9b1`. Staging and raw/CSV/JSONL residue are zero.

Only `/v3/reference/tickers` and the three authorized adjusted=false Grouped Daily paths were reached: 45 Massive requests, zero retries. SEC, OCI, other external services, later dates, scheduler, Dashboard/API/frontend, snapshot/bundle, deployment, and Universe activation were untouched. Credential content and authorization headers were not exposed.

The window now has 12 completed sessions, eight missing sessions, and zero corrupt sessions. Candidate A/B remain wholly `insufficient_history`; 20/20, 19/20, and non-null median counts remain zero.

Live preflight focused tests passed 135 tests; postflight ingestion/contracts/persistence/history/credential regressions passed 148 tests. Health passed one test with the existing Starlette TestClient/httpx deprecation warning. Compileall, required imports, shell syntax, 92-file/214-link Markdown validation, sensitive scan, socket prohibition, `git diff --check`, staging/artifact, listener, and residual-process checks passed. Ordinary tests made zero external-network attempts.
