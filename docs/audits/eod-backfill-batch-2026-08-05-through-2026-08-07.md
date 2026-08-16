# Massive EOD Backfill Batch Audit — 2026-08-05 through 2026-08-07

## Result

Final classification: `completed_three_session_batch`.

The authorized sessions 2026-08-05, 08-06, and 08-07 ran strictly in date order. Each same-day Instrument Master snapshot completed and passed formal reread before its one Grouped Daily request. All six entrypoints exited 0, each was invoked once, retries were zero, and no later session was started.

| Session | Identity UTC | Reference requests | Grouped Daily UTC | Grouped requests | Status |
| --- | --- | ---: | --- | ---: | --- |
| 2026-08-05 | 20:23:16–20:26:40 | 14 | 20:27:13–20:27:21 | 1 | `completed` |
| 2026-08-06 | 20:27:57–20:31:21 | 14 | 20:32:01–20:32:09 | 1 | `completed` |
| 2026-08-07 | 20:32:44–20:36:08 | 14 | 20:36:43–20:36:51 | 1 | `completed` |

All timestamps are UTC on 2026-08-16. Adjacent entrypoints were separated by at least 33 seconds, exceeding the 15-second minimum. Total requests were 45, below the batch ceiling of 63.

## Identity Results

| Metric | 2026-08-05 | 2026-08-06 | 2026-08-07 |
| --- | ---: | ---: | ---: |
| Raw | 13,068 | 13,078 | 13,080 |
| Eligible | 11,026 | 11,035 | 11,036 |
| Expected exclusions | 1,952 | 1,953 | 1,954 |
| Malformed/rejected | 90 | 90 | 90 |
| Resolved / unresolved eligible | 9,898 / 1,128 | 9,907 / 1,128 | 9,907 / 1,129 |
| Duplicate ticker groups | 2 | 2 | 2 |
| Ambiguous / stable-ID collision | 0 / 0 | 0 / 0 | 0 / 0 |
| Identity coverage | 0.897696 | 0.897780 | 0.897698 |
| Canonical instruments / resolver | 9,898 / 9,898 | 9,907 / 9,907 | 9,907 / 9,907 |

Quality gates and atomic publication passed on all days. Formal reread verified Arrow schemas, counts, deterministic ordering, UUID/referential integrity, resolver uniqueness, zero orphan references, manifests, and same-day logical completion.

| Session | Instrument fingerprint / Parquet SHA-256 | Identity fingerprint / Parquet SHA-256 | Resolver fingerprint / Parquet SHA-256 | Snapshot fingerprint |
| --- | --- | --- | --- | --- |
| 08-05 | `bda261b2a6ad009c51a8d8c09e83a05e79e33109f4c20172fa3f5a4347ed040b` / `feb8a5446e0cda126d8fa43ab2539dc81c1851bc05348ad4c4df533e9e6c69d1` | `1899a12dd882f3d64528dd06b78ac200b971e1c5818cf928d1b520dc291a9780` / `1a5897708553606b73110a18fe0116f7bfb3b56da98d7e5a056a225f8ec37c85` | `8f9698272eeac7b3cd2d7a587304d65a240a4ec6d514eefcea48a2fd8b6ce0c1` / `3d9ac2e60a404304ebc7672ac4960432f7c018b55c1d3d23f6042e635efc4738` | `a6d6d4f44826063edc3c3cadcc431ddfab7c98dcb8b13c77bcb7564f8eee6bb3` |
| 08-06 | `b7a62af1eee845a9964c6eeaa56882593441a74d1fd9badfd22071efdd82e03e` / `f61a25a2ca5c7396b23295ee1eca0733d6709228dde754a094e7a5e688fad2c8` | `11dc193b2ef43bb3b5149e22222445b84fcd659f701aca654c275a6e63fbb37e` / `867711149ba5a60867ae5cfbc0f0554d9c5f974fb40f5b625aac70928e66b4ed` | `ddadf3ffad21c73c616baea510678182bb4afbe2ad98d5a718c230c92972aa75` / `e80d3ab25c2b2dfd9d7ad4368ed1f4c4c0cb9ca508aa926c3e3dd974de722f40` | `0cf49f3234c686c1916bbc38885ee0b08a971139db55a9611acc40297850a2b9` |
| 08-07 | `67d9b5a71cb5538efc0d5caca140067105218a2cc582a1d4557318cc60c686d0` / `0627cbc4b7ef2377226908ba51cc8135ac0297c49951c38be17646bedbc40c52` | `db7277b0d92db44c23d127d83afbc53989a843810d14c7570c68eeff8d70fdee` / `efa7270a1cac045def21d2ca162c7ca3132227bf8b9d114c2830637c3bcd42af` | `db228850a7a4f2ed0f9a324bb3afdd6c3e7b023c62778aae8d77ba9b8d5c67e4` / `95705b0c24b679495f21e911ac9e4af2f6f0177399622ed01e128a23be5cdc28` | `23426651b603fb78ea7399b0cc1ae7f086ccf1cb26fa56e518ab93678f7ba644` |

## Grouped Daily Results

| Metric | 2026-08-05 | 2026-08-06 | 2026-08-07 |
| --- | ---: | ---: | ---: |
| Raw / unique ticker | 12,406 / 12,404 | 12,399 / 12,397 | 12,414 / 12,412 |
| Exact duplicate ticker/record | 0 / 0 | 0 / 0 | 0 / 0 |
| Conflicting ticker/record | 2 / 4 | 2 / 4 | 2 / 4 |
| Conflict ratio | 0.000322 | 0.000323 | 0.000322 |
| Resolved / unresolved eligible | 9,873 / 966 | 9,879 / 973 | 9,881 / 983 |
| Expected exclusions | 1,463 | 1,444 | 1,448 |
| Ambiguous / rejected / missing identity | 0 / 90 / 14 | 0 / 90 / 13 | 0 / 89 / 13 |
| Identity coverage | 0.909702 | 0.909250 | 0.908431 |
| Required numeric failures | 0 | 0 | 0 |
| Optional VWAP / trade-count missing | 3 / 3 | 3 / 3 | 3 / 3 |
| Fractional / zero volume | 11,082 / 3 | 11,092 / 3 | 11,131 / 3 |
| Canonical bars | 9,869 | 9,875 | 9,877 |

Nonpositive price, OHLC inconsistency, negative volume, timestamp mismatch, and canonical validation failures were zero every day. Existing low-ratio conflict isolation generated warnings without changing gates. Reconciliation, publish readiness, and atomic publication passed.

| Session | EOD fingerprint | Parquet SHA-256 | Same-day identity fingerprint |
| --- | --- | --- | --- |
| 08-05 | `3f8a37fa6e171566f7baa5e8c7ea9e846a04af7ee37cf64a5e25df3e85bcfca5` | `6043cb59db04d09594bf002175b141ef52351c26f688d570da18d74999a187bd` | `a6d6d4f44826063edc3c3cadcc431ddfab7c98dcb8b13c77bcb7564f8eee6bb3` |
| 08-06 | `04ca5378d5b944f5501e2466ef2e0d740ed9e73851ba6c25e55b344437b29822` | `3c0dbd4f71d7eaac73b1bde363004c90fcefced68015c8e90bc3dc7f3ff95bc6` | `0cf49f3234c686c1916bbc38885ee0b08a971139db55a9611acc40297850a2b9` |
| 08-07 | `3dd0f45cf3cdd2116e6f090f0ed2f1cf822d150b8fc2269e3444848f8ea66af0` | `d09d440260a3c2ec711cf1902e7659d63cbceef4d1f6eb2d6f311df047896e59` | `23426651b603fb78ea7399b0cc1ae7f086ccf1cb26fa56e518ab93678f7ba644` |

Every manifest references its exact same-day identity snapshot. Future identity references, duplicate business keys, and multiple latest revisions are zero. All rows retain `adjustment_factors_unverified`; no raw payload was persisted.

## Inventory, Readiness, and Boundaries

The original 151-file, 55,540,570-byte protected inventory remained content- and metadata-identical, including digest `e775d09906593cd15bc5d324dac73d9042cbc46645d012d9e5bcaf66dd77a040`. Exactly 27 authorized files were added. Final inventory: 178 files, 65,388,676 bytes, digest `6033cd1b1dad4f74d62dec4d8addcdd64af4b73b8b3b99ab976f1c4eed65e2df`. Staging and raw/CSV/JSONL residue are zero.

The window now has 18 completed sessions, two missing sessions, and zero corrupt sessions. Candidate A/B remain wholly `insufficient_history`; 20/20, 19/20, and non-null median counts remain zero.

Only `/v3/reference/tickers` and the three authorized adjusted=false Grouped Daily paths were reached: 45 Massive requests, zero retries. SEC, OCI, other external services, later dates, scheduler, Dashboard/API/frontend, snapshot/bundle, deployment, and Universe activation were untouched. Credential content and authorization headers were not exposed.

Live preflight and postflight focused suites each passed 148 tests. Compileall, required imports, Health, shell syntax, Markdown links, sensitive scan, socket prohibition, `git diff --check`, staging/artifact, listener, and residual-process checks passed. Ordinary tests made zero external-network attempts.
