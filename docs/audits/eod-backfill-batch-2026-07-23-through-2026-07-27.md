# Massive EOD Backfill Batch Audit — 2026-07-23 through 2026-07-27

## Result

Final classification: `completed_three_session_batch`.

The authorized sessions 2026-07-23, 07-24, and 07-27 ran strictly in date order. Each same-day Instrument Master snapshot completed and passed formal reread before its one Grouped Daily request. All six entrypoints exited 0, each was invoked once, retries were zero, and no later session was started.

| Session | Identity UTC | Reference requests | Grouped Daily UTC | Grouped requests | Status |
| --- | --- | ---: | --- | ---: | --- |
| 2026-07-23 | 18:51:00–18:54:24 | 14 | 18:55:00–18:55:08 | 1 | `completed` |
| 2026-07-24 | 18:55:53–18:59:17 | 14 | 18:59:53–19:00:02 | 1 | `completed` |
| 2026-07-27 | 19:00:47–19:04:11 | 14 | 19:04:48–19:04:57 | 1 | `completed` |

All timestamps are UTC on 2026-08-16. Cross-entrypoint gaps were 36, 45, 36, 45, and 37 seconds, all at least 15 seconds. Total requests were 45, below the batch ceiling of 63.

## Identity Results

| Metric | 2026-07-23 | 2026-07-24 | 2026-07-27 |
| --- | ---: | ---: | ---: |
| Raw | 13,023 | 13,025 | 13,031 |
| Eligible | 11,000 | 10,999 | 11,000 |
| Expected exclusions | 1,935 | 1,938 | 1,943 |
| Malformed/rejected | 88 | 88 | 88 |
| Resolved / unresolved eligible | 9,881 / 1,119 | 9,879 / 1,120 | 9,881 / 1,119 |
| Duplicate ticker groups | 2 | 2 | 2 |
| Ambiguous / stable-ID collision | 0 / 0 | 0 / 0 | 0 / 0 |
| Identity coverage | 0.898273 | 0.898173 | 0.898273 |
| Malformed ratio | 0.006757 | 0.006756 | 0.006753 |
| Canonical instruments / resolver | 9,881 / 9,881 | 9,879 / 9,879 | 9,881 / 9,881 |

Quality gates and atomic publication passed on all days. Formal reread verified Arrow schemas, counts, deterministic ordering, UUID/referential integrity, resolver uniqueness, zero orphan references, manifests, and same-day logical completion.

| Session | Instrument fingerprint / Parquet SHA-256 | Identity fingerprint / Parquet SHA-256 | Resolver fingerprint / Parquet SHA-256 | Snapshot fingerprint |
| --- | --- | --- | --- | --- |
| 07-23 | `f2ebde411baece95402a6ca1b80f21c29cbd95401bbc7c1cd0d12a97ede95d84` / `99cd129bb255e23793d46129ec4be91088b4318327d87ad3663f0dac87813c65` | `03f119c0ab2574bc16ac85691580d3add741325f435a335d23e9c645e3e7b503` / `9e03df7661b0fa4905d2597f42d8ce0f7229276a51cdc7d0cd4cc9270fc66d71` | `12d2b0b53177ecf8c7d93da7553b62950e684764f51ace004ac4ee62f7ad0c0b` / `bcec5bdab4c489e4f814eab798022e3f2a4ab042e7ff7330f02bb7769dd3e644` | `baac3d36b35a03a387d7443408967bef37bb0fc31184850ec0ccb5d1ae537246` |
| 07-24 | `16b9bc437f6a70310da032d5c3eb37e57aa7a3cf1f6e56d0b4ce8894d931582d` / `ffa575abc43d4ef93a62e4b2fe0875ffd3c8e0e2f5dfed7145d49046a9e8c5e9` | `029ed3af2cbb7b0312005151d3ba01853ca125a2359324695e48df2fcec7b227` / `0ef2f04c2610bbaead06b3997f4333d45e5c24afb408bf48eee593f5a01983f9` | `7306c7d0bae31dc42837bf266b91671b02c42cbfd8f6bd2e4700244c85f70165` / `0be344bb0bbe395ab75253b071d678232f60703bce78be0d25141ad315298431` | `90c78760416d3956c7258508a401f07ffa3719f018a47a399799f45ccfea0891` |
| 07-27 | `1519b4fecf3a32cd6d09cb0a06bc594fd7ef8ea64a081e108b9a7d6a61eebeab` / `e3966fdb0960fe9252653b3eb394d2b988b3f7061cb9e85a40bd83c0d0f7e9fc` | `d198fd30cc831ddac5c0a714f3d89bcd39e996089285168084ccc45ab1f19210` / `cd1940d43e89bf5f9ef1897841ef5e29c0b2ff6c3db48f2a11fa66f284a4b82e` | `6fe4e8945c748e48031b69899eb6f7b0ebf5aa65468ef80c8b7382a360a83d03` / `0bfc4b0154cd211dcb6da21b8dd2c1df3d5ceb0b1da421c5be1e4706ffb84ac0` | `45eff526287cd497fa8262343af3c018cf3df543954a4690f351c9e2af5f081c` |

## Grouped Daily Results

| Metric | 2026-07-23 | 2026-07-24 | 2026-07-27 |
| --- | ---: | ---: | ---: |
| Raw / unique ticker | 12,392 / 12,390 | 12,410 / 12,408 | 12,402 / 12,400 |
| Exact duplicate ticker/record | 0 / 0 | 0 / 0 | 0 / 0 |
| Conflicting ticker/record | 2 / 4 | 2 / 4 | 2 / 4 |
| Conflict ratio | 0.000323 | 0.000322 | 0.000323 |
| Resolved / unresolved eligible | 9,848 / 983 | 9,837 / 991 | 9,863 / 996 |
| Expected exclusions | 1,460 | 1,481 | 1,439 |
| Ambiguous / rejected / missing identity | 0 / 87 / 14 | 0 / 87 / 14 | 0 / 87 / 17 |
| Identity coverage | 0.908068 | 0.907305 | 0.906859 |
| Required numeric failures | 0 | 0 | 0 |
| Optional VWAP / trade-count missing | 3 / 3 | 3 / 3 | 6 / 6 |
| Fractional / zero volume | 10,958 / 3 | 10,967 / 3 | 10,981 / 6 |
| Canonical bars | 9,844 | 9,833 | 9,859 |

Nonpositive price, OHLC inconsistency, negative volume, timestamp mismatch, and canonical validation failures were zero every day. Existing low-ratio conflict isolation generated warnings without changing gates. Reconciliation, publish readiness, and atomic publication passed.

| Session | EOD fingerprint | Parquet SHA-256 | Same-day identity fingerprint |
| --- | --- | --- | --- |
| 07-23 | `97cbb22530fc10bf1711390d7de19e560fbc093fd810c503bf652d3c1d0dcf28` | `f9b9949f61be5eca1113daff4ea9ce629d41004bf38f362a17f7e001583e6747` | `baac3d36b35a03a387d7443408967bef37bb0fc31184850ec0ccb5d1ae537246` |
| 07-24 | `0cd88aa82c3c1707cadaf5a131039dd6606c14046d012359c33a00381135375f` | `a83adb81b7f7d40aad07d7da120e0e57c6fc715119538ae7d61b7598d5db43ab` | `90c78760416d3956c7258508a401f07ffa3719f018a47a399799f45ccfea0891` |
| 07-27 | `85d3c7cb2c2a9dda14ed5ce7edd897cb26b8c76ff1edb7d0f2655baf8615d75e` | `e8f882444f3be9874fa57f90e25e925cdf3d2ebeca4132ffbd3a310c470b5b86` | `45eff526287cd497fa8262343af3c018cf3df543954a4690f351c9e2af5f081c` |

Every manifest references its exact same-day identity snapshot. Future identity references, duplicate business keys, and multiple latest revisions are zero. All rows retain `adjustment_factors_unverified`; no raw payload was persisted.

## Inventory and Boundaries

The original 70-file, 26,035,416-byte protected inventory remained content- and metadata-identical, including digest `b2537a2d3627f1915c38540ea7af32a93b960a8c826ef1913151c426ae169fe3`. Exactly 27 authorized files were added. Final inventory: 97 files, 35,868,019 bytes, digest `27fe6529ca6b7789f5901065f0d9dad405c8532a835be04846022437e7c330dc`. Staging and raw/CSV/JSONL residue are zero.

Only `/v3/reference/tickers` and the three authorized adjusted=false Grouped Daily paths were reached: 45 Massive requests, zero retries. SEC, OCI, other external services, later dates, scheduler, Dashboard/API/frontend, snapshot/bundle, deployment, and Universe activation were untouched. Credential content and authorization headers were not exposed.

Preflight and postflight focused suites each passed 135 tests with zero ordinary-test external network attempts. Final shell syntax, Markdown-link, sensitive-information, diff, listener, and residual-process checks passed.
