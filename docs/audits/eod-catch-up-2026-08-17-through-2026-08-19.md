# Latest EOD Catch-Up Audit — 2026-08-17 through 2026-08-19

## Result

Final classification: `completed_latest_eod_catch_up`.

At `2026-08-20T04:08:04Z` (`2026-08-19T22:08:04-06:00` in America/Denver and `2026-08-20T00:08:04-04:00` in America/New_York), the existing XNYS calendar service identified 2026-08-19 as the expected latest completed session. The canonical repository's actual latest session was 2026-08-14, for lag three. Therefore the exact authorized dates were 08-17, 08-18, and 08-19; the 08-15/16 weekend generated no request.

Each date ran strictly as same-day identity, formal reread, at least 15 seconds separation, then one adjusted=false Grouped Daily request. All six entrypoints exited 0, each ran once, and retries were zero.

| Session | Identity UTC | Reference requests | Grouped Daily UTC | Requests | Status |
| --- | --- | ---: | --- | ---: | --- |
| 2026-08-17 | 04:09:57–04:13:21 | 14 | 04:14:18–04:14:27 | 1 | `completed` |
| 2026-08-18 | 04:16:20–04:19:44 | 14 | 04:20:19–04:20:28 | 1 | `completed` |
| 2026-08-19 | 04:21:03–04:24:27 | 14 | 04:25:03–04:25:11 | 1 | `completed` |

All live timestamps are UTC on 2026-08-20. Total Massive requests were 45, below the ceiling of 63. Adjacent entrypoints were separated by at least 35 seconds.

## Identity Results

| Metric | 08-17 | 08-18 | 08-19 |
| --- | ---: | ---: | ---: |
| Raw | 13,113 | 13,120 | 13,120 |
| Eligible | 11,072 | 11,080 | 11,080 |
| Expected exclusions | 1,950 | 1,951 | 1,951 |
| Malformed/rejected | 91 | 89 | 89 |
| Resolved / unresolved | 9,939 / 1,133 | 9,947 / 1,133 | 9,947 / 1,133 |
| Canonical instruments / resolver | 9,939 / 9,939 | 9,947 / 9,947 | 9,947 / 9,947 |
| Coverage | 0.897670 | 0.897744 | 0.897744 |

Ambiguity, stable-ID collision, orphan reference, and resolver duplicate counts were zero. The 08-17 malformed count includes one missing provider type under the unchanged taxonomy. All schemas, ordering, fingerprints, references, logical markers, and formal rereads passed.

| Session | Instrument fingerprint / Parquet SHA-256 | Identity fingerprint / Parquet SHA-256 | Resolver fingerprint / Parquet SHA-256 | Snapshot fingerprint |
| --- | --- | --- | --- | --- |
| 08-17 | `c1a7fc3c4c3886fda993c26cabb93b65a2f196106abcec62e7804850de538905` / `e2ebf10e378e9cb3ba33a907199a2770cfae71ea89bfa12b2a55d0d59abb118b` | `766e14e0e4d4bac0d66e29ade2efbcbae1d68448e49a0aa0aae32b6ba7d3d1ce` / `34f5a7c9922c84a607eb7ff7e6448031fa1728a98ce4fddd72974bea86e73397` | `cb117839490f2f0e64108abe0a97875c946d0271e2fe622244bde7ac1ba004bd` / `b452268e550314d7db5094806dcddc62891ed7a430cc2ca0c57ce696437a4c04` | `ba66d7c9151d417f5aa74ebc301cb5690ce55194184f44a9d0cd22f91207032c` |
| 08-18 | `0b048a0b2f3cd69166e47146be7d4567ff211429a3549770684b7bb5a778f674` / `6236ee7743da8081695e73a7609786b41feab1d2eb6b8662f7fc323576f72847` | `0cc25d12a07750842cb5b2879f54169955075879f7893478570c40fb84b61908` / `a2e5cc7c3c300ed7f39a466c797f9d0894c19cee8c013aaea5231ee15071fb01` | `9d5fc1da1c37cd3795f22ec860a63274b42f4106d98182568c1737573dd47f53` / `da969ebd1b1ad7d59f30aff07e6e0395e3dfdb13183af5a474860b8cc1c1927a` | `aa958856f2b5b6fbdf090c62cdb74885d5cc8c60acbfa6422eaf3ad96ab3f662` |
| 08-19 | `a8722ff5993ff9db3a47bca6686f46c1027e6f3d3fadca33b33698c7588e9541` / `06104baf81b10a2b3ef5729adf932c575b244a23cf7924bb7dc2126fdb596f25` | `92c8981b0a1497afdcfcc64869c77cc40b3cd03d31d2feaaa6e555f85cbb55a8` / `c2b8cc65c95f0d7f262001a079098098e4ed6d65d7f939a1412560f074cca2bc` | `3a58dc3c19528f4d9946534450d5b33cf5821bb087223c54d490f00d2e4fe557` / `eab1c38ee1b0d8ab366d5d4c3b900b859bc56aeb43417b93735d06ecff0e5935` | `0627bfacedeea0b5dc013fc3bfc6abdff7b28740e689d32af19e0f7a7fe7e73b` |

## EOD Results

| Metric | 08-17 | 08-18 | 08-19 |
| --- | ---: | ---: | ---: |
| Raw / unique ticker | 12,549 / 12,547 | 12,482 / 12,480 | 12,548 / 12,546 |
| Conflicting ticker / records | 2 / 4 | 2 / 4 | 2 / 4 |
| Resolved / unresolved eligible | 9,920 / 1,016 | 9,913 / 982 | 9,930 / 1,014 |
| Expected exclusions | 1,508 | 1,486 | 1,489 |
| Rejected / missing identity | 91 / 14 | 89 / 12 | 88 / 27 |
| Identity coverage | 0.905936 | 0.908866 | 0.905113 |
| Fractional / zero volume | 11,377 / 3 | 11,271 / 3 | 11,304 / 5 |
| Optional VWAP / trade-count missing | 3 / 3 | 3 / 3 | 5 / 5 |
| Canonical bars | 9,916 | 9,909 | 9,926 |

Required numeric, nonpositive price, OHLC, negative-volume, timestamp, and canonical validation failures were zero. Conflicting duplicates were isolated under the unchanged low-ratio rule. Reconciliation and all publication gates passed.

| Session | EOD fingerprint | Parquet SHA-256 | Same-day identity fingerprint |
| --- | --- | --- | --- |
| 08-17 | `8c6ba86a8c8d7acb8f0114e7f30960a74540cfdb34f443af9d2dea50fff156f4` | `557de550c2e418a7d1a6c155e2a7ade6088f01560bbd82995d019ad3a22d3a2d` | `ba66d7c9151d417f5aa74ebc301cb5690ce55194184f44a9d0cd22f91207032c` |
| 08-18 | `123e1f0672dc846658236ecfd285e51659ad683d5c240f60eb294155207b1508` | `cc282d24fea87b2328478445374cc95e5fb69fe50a3b7286d59eb8786da9d21d` | `aa958856f2b5b6fbdf090c62cdb74885d5cc8c60acbfa6422eaf3ad96ab3f662` |
| 08-19 | `09e74538ae5b4b7d9eee1de3dbdd12183ddbf523e29686eb96d32e092280bb71` | `914398d01f3609e0b36c3372997e1ddcab2a2d76fa84dea5c7ce1f5d1d62707b` | `0627bfacedeea0b5dc013fc3bfc6abdff7b28740e689d32af19e0f7a7fe7e73b` |

Every EOD partition references its exact same-day completed identity. Future identity reference, duplicate business key, and multiple-latest counts are zero. All rows retain `adjustment_factors_unverified`; raw provider payload was not stored.

## Inventory and Boundaries

The original 196-file, 71,959,289-byte protected inventory remained content- and metadata-identical, including digest `eb86f69336e567019b7e1553501e38e8545be6a60e5c43e2da0544b7b04c98c0`. Exactly 27 authorized files were added. Final inventory: 223 files, 81,860,836 bytes, digest `e453c759200cdf1dfb603a38b4eb519a74092c0f594865c226c233a92d2306d2`.

Only `/v3/reference/tickers` and the three authorized Grouped Daily endpoints were reached. SEC, OCI, Git remote, other services, other dates, scheduler, Dashboard/API/frontend, Universe activation, derived publication, snapshot/bundle, and deployment were untouched.

Live preflight and postflight focused suites each passed 157 tests. Compileall, required imports, FastAPI/Health, shell syntax, Markdown links, sensitive scan, socket prohibition, `git diff --check`, inventory, staging/artifact, listener, and residual-process checks passed. Health emitted one existing Starlette TestClient/httpx deprecation warning; skipped and xfailed tests were zero. Ordinary tests made zero external-network attempts. Postflight freshness was `fresh`: actual and expected latest completed session both 2026-08-19, lag zero.
