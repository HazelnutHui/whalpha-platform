# Massive EOD Final Backfill Batch Audit — 2026-08-10 through 2026-08-11

## Result

Final classification: `completed_two_session_final_batch`.

The two authorized sessions ran strictly in date order. Each same-day Instrument Master snapshot completed and passed formal reread before its one Grouped Daily request. All four entrypoints exited 0, each was invoked once, retries were zero, and no other session was started.

| Session | Identity UTC | Reference requests | Grouped Daily UTC | Grouped requests | Status |
| --- | --- | ---: | --- | ---: | --- |
| 2026-08-10 | 20:48:32–20:51:56 | 14 | 20:52:30–20:52:39 | 1 | `completed` |
| 2026-08-11 | 20:53:13–20:56:37 | 14 | 20:57:12–20:57:20 | 1 | `completed` |

All timestamps are UTC on 2026-08-16. Adjacent entrypoints were separated by 34, 34, and 35 seconds, exceeding the 15-second minimum. Total Massive requests were 30, below the batch ceiling of 42.

## Identity Results

| Metric | 2026-08-10 | 2026-08-11 |
| --- | ---: | ---: |
| Raw | 13,084 | 13,095 |
| Eligible | 11,042 | 11,053 |
| Expected exclusions | 1,952 | 1,952 |
| Malformed/rejected | 90 | 90 |
| Resolved / unresolved eligible | 9,913 / 1,129 | 9,924 / 1,129 |
| Duplicate ticker groups | 2 | 2 |
| Ambiguous / stable-ID collision / orphan | 0 / 0 / 0 | 0 / 0 / 0 |
| Identity coverage | 0.897754 | 0.897856 |
| Canonical instruments / resolver | 9,913 / 9,913 | 9,924 / 9,924 |

Quality gates and atomic publication passed. Formal reread verified explicit Arrow schemas, counts, deterministic ordering, UUID/referential integrity, resolver uniqueness, logical completion, and zero staging residue.

| Session | Instrument fingerprint / Parquet SHA-256 | Identity fingerprint / Parquet SHA-256 | Resolver fingerprint / Parquet SHA-256 | Snapshot fingerprint |
| --- | --- | --- | --- | --- |
| 08-10 | `1c3f95ebb64c1fc9ae4d3a9e092dea67552ff981625aa8cb4ccac3ea2f234103` / `4e3239412a54599dba057f2a62b387b180277dd2225991249ecb3759f40849a7` | `52c3fa5537fb4cd9f8802c7ae3e5be3f6cde459ab67bc6f00c98bbb37889d9dc` / `1dd6a2b2586f1d19e6a6e47bc8e3366ccbe1962f0debc91c1bc507d7aa5fe6bc` | `be8c528bd3f51010e23633c4b25c79aa7ab55930b95ee512ee492885f83251b2` / `7f13d11cb1857cca62c156b91e7ddd1f8cd66668c1b68245e88bdf8528f1a998` | `99f2cf9ce0f34644800b3ce2462937221200d26606b1d28217491bdd7c658d6c` |
| 08-11 | `bbb7b6d58f324375c0111142898ecbbd0f989c6d75e691470b66a9769e4129d3` / `6b396a7168064e145b3ea04aeaf742ea97529737ac17b4d2861cd1d7fa3ae4a9` | `3b2bc0d3b984749835e4671d19e4068340ba9606cc17b41a5e1deb35db708621` / `0299c8944aaf11c152fd4aedf1b3aa479761e53be8e5d3f7579076e52b8a9ef1` | `53ee2ef47a38e837ca98159853336aec6df65ca6b1aff53580873fcc851719dd` / `fbbcd4ab7d810166c5c54fd3879915ada228336bc519f51980ff6ab6e681aa20` | `46b374bcb7c17e6582eef737a965e3021f4ab0692608e18d5d1d98ebd2102926` |

## Grouped Daily Results

| Metric | 2026-08-10 | 2026-08-11 |
| --- | ---: | ---: |
| Raw / unique ticker | 12,415 / 12,413 | 12,410 / 12,408 |
| Exact duplicate ticker/record | 0 / 0 | 0 / 0 |
| Conflicting ticker/record | 2 / 4 | 2 / 4 |
| Conflict ratio | 0.000322 | 0.000322 |
| Resolved / unresolved eligible | 9,896 / 999 | 9,889 / 982 |
| Expected exclusions | 1,418 | 1,436 |
| Ambiguous / rejected / missing identity | 0 / 90 / 12 | 0 / 90 / 13 |
| Identity coverage | 0.907307 | 0.908581 |
| Required numeric failures | 0 | 0 |
| Optional VWAP / trade-count missing | 3 / 3 | 3 / 3 |
| Fractional / zero volume | 11,253 / 3 | 11,164 / 3 |
| Canonical bars | 9,892 | 9,885 |

Nonpositive price, OHLC inconsistency, negative volume, timestamp mismatch, and canonical validation failures were zero. Existing low-ratio conflict isolation produced expected warnings without weakening gates. Reconciliation and publication passed.

| Session | EOD fingerprint | Parquet SHA-256 | Same-day identity fingerprint |
| --- | --- | --- | --- |
| 08-10 | `02b557b24c9afbae0714e406ee8b8c2c6bc8c187b2edbec2981d01e059f086ca` | `30ae1c52ef14d44812f7667ab4066f418ded15b8b4fda9892d908358e3e0b2da` | `99f2cf9ce0f34644800b3ce2462937221200d26606b1d28217491bdd7c658d6c` |
| 08-11 | `55b55ff32340ea65376d8ab4d31c649432a5943c4cd5313c9883fa109aae9dd6` | `0d6e045eb5842c3af837f0840431484adcf9546fb5eb730093e5e5828c96bdaa` | `46b374bcb7c17e6582eef737a965e3021f4ab0692608e18d5d1d98ebd2102926` |

Every EOD manifest references its exact same-day completed identity snapshot. Future identity references, duplicate business keys, and multiple latest revisions are zero. All rows retain `adjustment_factors_unverified`; raw payload was not persisted.

## Inventory, Readiness, and Boundaries

The original 178-file, 65,388,676-byte protected inventory remained content- and metadata-identical, including digest `6033cd1b1dad4f74d62dec4d8addcdd64af4b73b8b3b99ab976f1c4eed65e2df`. Exactly 18 authorized files were added. Final inventory: 196 files, 71,959,289 bytes, digest `eb86f69336e567019b7e1553501e38e8545be6a60e5c43e2da0544b7b04c98c0`. Staging and raw/CSV/JSONL residue are zero.

The XNYS descriptor now has all 20 expected sessions completed, none missing or corrupt, and status `ready`; fingerprint `c403e32f323a80ad3ce77add6969373ef7b14920b53709c4c673d704d4d5d37c`. Candidate A has 1,742 members at 20/20, one at 19/20, and nine total insufficient-history results. Candidate B has 1,854 at 20/20, two at 19/20, and ten insufficient-history results. Existing Decimal logic naturally computed 1,742/1,854 non-null medians in memory. No reviewed production publisher exists, so no derived dataset, Dashboard result, or Universe activation was created.

Only `/v3/reference/tickers` and the two authorized adjusted=false Grouped Daily paths were reached: 30 Massive requests, zero retries. SEC, OCI, other external services, scheduler, API/frontend, snapshot/bundle, deployment, and Universe activation were untouched. Credential content and authorization headers were not exposed.

Live preflight and postflight focused suites each passed 148 tests. Compileall, required imports, FastAPI/Health, shell syntax, Markdown links, sensitive scan, socket prohibition, `git diff --check`, staging/artifact, listener, and residual-process checks passed. Health emitted one existing Starlette TestClient/httpx deprecation warning; skipped and xfailed tests were zero. Ordinary tests made zero external-network attempts.
