# Massive EOD Backfill Batch Audit — 2026-07-20 through 2026-07-22

## Result

Final classification: `completed_three_session_batch`.

The three authorized sessions ran strictly in date order. Each same-day Instrument Master snapshot completed and passed formal reread before its one Grouped Daily request. All six entrypoints exited 0, each was invoked once, retries were zero, and no later session was started.

| Session | Identity UTC | Reference requests | Grouped Daily UTC | Grouped requests | Status |
| --- | --- | ---: | --- | ---: | --- |
| 2026-07-20 | 13:59:59–14:03:23 | 14 | 14:04:12–14:04:21 | 1 | `completed` |
| 2026-07-21 | 14:05:33–14:08:57 | 14 | 14:09:16–14:09:24 | 1 | `completed` |
| 2026-07-22 | 14:10:10–14:13:33 | 14 | 14:14:19–14:14:27 | 1 | `completed` |

All timestamps are UTC on 2026-08-16. Cross-entrypoint gaps were 49, 72, 19, 46, and 46 seconds, each at least 15 seconds. Total requests were 45, below the batch ceiling of 63.

## Identity Results

| Metric | 2026-07-20 | 2026-07-21 | 2026-07-22 |
| --- | ---: | ---: | ---: |
| Raw | 13,026 | 13,025 | 13,024 |
| Eligible | 10,999 | 10,999 | 10,997 |
| Expected exclusions | 1,939 | 1,938 | 1,939 |
| Malformed/rejected | 88 | 88 | 88 |
| Resolved / unresolved eligible | 9,880 / 1,119 | 9,879 / 1,120 | 9,879 / 1,118 |
| Duplicate ticker groups | 2 | 2 | 2 |
| Ambiguous / stable-ID collision | 0 / 0 | 0 / 0 | 0 / 0 |
| Identity coverage | 0.898263 | 0.898173 | 0.898336 |
| Malformed ratio | 0.006756 | 0.006756 | 0.006757 |
| Canonical instruments / resolver | 9,880 / 9,880 | 9,879 / 9,879 | 9,879 / 9,879 |

All quality gates and atomic publications passed. Formal reread verified explicit Arrow schemas, row counts, deterministic ordering, UUID/referential integrity, resolver uniqueness, zero orphan references, manifests, and same-day logical completion.

| Session | Instrument fingerprint / Parquet SHA-256 | Identity fingerprint / Parquet SHA-256 | Resolver fingerprint / Parquet SHA-256 | Snapshot fingerprint |
| --- | --- | --- | --- | --- |
| 07-20 | `1e490bd4041811caefea98633d8db6df982cecd5a18bbbc2958352d528abb04f` / `a9099bf9b84a2aa78b72a2d88ceed4ebbe0dab3da8a3c019bde99f6992a6b8e6` | `394d01a146eab59cab564d37c5ae56593777456fc045554fe0d30ef4772893a2` / `df6928b5b04e3dc585cb3890049b73a2f7cc90bd5bc1c85af3c8c9e1c15d5810` | `3bdd499f90f1236df4e7c7c78ae8973f10e1283bd6946fb6f5b20b95b28bd046` / `6fb21d5398d85e524337af70049a77f59a69e3fe0da673e1fb76bbcb5de43722` | `39a605a180ddf8a6da63e306d3a8c9197c33a03f7f71d74d89693831a212ab38` |
| 07-21 | `10cb5b161888940cd3f9a52a56af9f8f6558bd85ac9bdcd473cd2ea218842640` / `3dafe7ff711e059273f82e755ad9f47fe851adb2dce20f1e1be74f12d763e8cb` | `e503911866d30c721771bbe1064fc16c7ca23198f18ee4682698246153e487a0` / `9bd700d988a8f29205fee140ca82794642b88f2f3fc862eb134a84a49f6b27f5` | `6140b1dbe42fe1b110f8ce2f7b5eca50de70af9bdfa3f13154db4ad65554efca` / `299850a998575c052f8e5ba97c9e3ab7ffc5639fe967f922d08d94e0283edc61` | `7f1a8de56c1ed6841be61efdd27859de1c34c696f9b4be5185332ca14007c6b5` |
| 07-22 | `b6535b826afbaa27168609c043fdc0bb19f16930a5e76ea19c9ea7da2b30ddc7` / `cdfeba4029cebeb21791e17ebc85e111faa444a271a43df3543a756c459ba150` | `5bd6919d32441cdd9c0a3eb8573358cfa17c98da8ebdc50492dab0173535345e` / `34d859cd42f0898d3c3edb5c73e1865fe76a58ab668d7a7163b3d90e5ba4de62` | `8fe49ab8a98b060f309d8c3be9b0048f3fc22c74feec80f77fe7199bf55d47be` / `2fc10ad0e6d161ca6997f91886fe0f0cb7ed804c8085281784787af660f23578` | `0c8f1572895312c942fff3f530abc94d70d43814ee2e4f465bcc53acb113e571` |

## Grouped Daily Results

| Metric | 2026-07-20 | 2026-07-21 | 2026-07-22 |
| --- | ---: | ---: | ---: |
| Raw / unique ticker | 12,388 / 12,386 | 12,524 / 12,522 | 12,427 / 12,425 |
| Exact duplicate ticker/record | 0 / 0 | 0 / 0 | 0 / 0 |
| Conflicting ticker/record | 2 / 4 | 2 / 4 | 2 / 4 |
| Conflict ratio | 0.000323 | 0.000319 | 0.000322 |
| Resolved / unresolved eligible | 9,862 / 981 | 9,850 / 1,005 | 9,851 / 974 |
| Expected exclusions | 1,442 | 1,568 | 1,501 |
| Ambiguous / rejected / missing identity | 0 / 87 / 16 | 0 / 87 / 14 | 0 / 87 / 14 |
| Identity coverage | 0.908187 | 0.906247 | 0.908848 |
| Required numeric failures | 0 | 0 | 0 |
| Optional VWAP / trade-count missing | 3 / 3 | 3 / 3 | 3 / 3 |
| Fractional / zero volume | 10,987 / 3 | 10,928 / 3 | 10,912 / 3 |
| Canonical bars | 9,858 | 9,846 | 9,847 |

Nonpositive price, OHLC inconsistency, negative volume, timestamp mismatch, and canonical validation failures were zero for every day. Existing low-ratio duplicate isolation produced warnings without weakening any gate. Reconciliation, quality gates, publish-ready, and atomic publication passed.

| Session | EOD fingerprint | Parquet SHA-256 | Same-day identity fingerprint |
| --- | --- | --- | --- |
| 07-20 | `c2cbbb44859abb3c2810a23ceaa0f7e81dcdcd15e8f976fcecb820f1597b3042` | `0d26f1fedb0d29d8b5523c49866eaf59cf90bd600ff066b50d1be90f721a30de` | `39a605a180ddf8a6da63e306d3a8c9197c33a03f7f71d74d89693831a212ab38` |
| 07-21 | `8e11c2e65b6dcdd646dd4075d8f5e87527d23405e50e5979782f638951eb5703` | `bfcb03205ecd92a4e76689522778000d40be9bd4334751415e316c808819d969` | `7f1a8de56c1ed6841be61efdd27859de1c34c696f9b4be5185332ca14007c6b5` |
| 07-22 | `099492742e29c60c4873d00f4bab48710f3801e1a5c0230967b04b022f720063` | `edd697061a6de05effdd49d35441ff2634a96641e04884267a9a11eb1a13a3bc` | `0c8f1572895312c942fff3f530abc94d70d43814ee2e4f465bcc53acb113e571` |

Every manifest references its exact same-day identity snapshot. Future identity references, duplicate business keys, and multiple latest revisions are zero. All rows retain `adjustment_factors_unverified`; no raw payload was persisted.

## Inventory and Boundaries

The original 43-file, 16,217,517-byte protected inventory remained content- and metadata-identical, including digest `e73bd3b39c871179a38ab712b7d6fe9f86995cf154728ffaafc87c641b971540`. Exactly 27 authorized files were added. Final inventory: 70 files, 26,035,416 bytes, digest `b2537a2d3627f1915c38540ea7af32a93b960a8c826ef1913151c426ae169fe3`. Staging and raw/CSV/JSONL residue are zero.

The operation reached only `/v3/reference/tickers` and the three authorized adjusted=false Grouped Daily paths: 45 Massive requests, zero retries. SEC, OCI, other external services, later dates, scheduler, Dashboard/API/frontend, snapshot/bundle, deployment, and Universe activation were untouched. Credential content and authorization headers were not exposed.

Preflight and postflight focused suites each passed 135 tests with zero ordinary-test external network attempts. Final shell syntax, Markdown-link, sensitive-information, diff, listener, and residual-process checks passed.
