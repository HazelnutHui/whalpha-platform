# Massive EOD Backfill Batch Audit — 2026-07-31 through 2026-08-04

## Result

Final classification: `completed_three_session_batch`.

The authorized sessions 2026-07-31, 08-03, and 08-04 ran strictly in date order. Each same-day Instrument Master snapshot completed and passed formal reread before its one Grouped Daily request. All six entrypoints exited 0, each was invoked once, retries were zero, and no later session was started.

| Session | Identity UTC | Reference requests | Grouped Daily UTC | Grouped requests | Status |
| --- | --- | ---: | --- | ---: | --- |
| 2026-07-31 | 19:48:47–19:52:11 | 14 | 19:52:44–19:52:53 | 1 | `completed` |
| 2026-08-03 | 19:53:26–19:56:50 | 14 | 19:57:27–19:57:35 | 1 | `completed` |
| 2026-08-04 | 19:58:22–20:01:46 | 14 | 20:02:20–20:02:28 | 1 | `completed` |

All timestamps are UTC on 2026-08-16. Adjacent entrypoints were separated by at least 33 seconds, exceeding the 15-second minimum. Total requests were 45, below the batch ceiling of 63.

## Identity Results

| Metric | 2026-07-31 | 2026-08-03 | 2026-08-04 |
| --- | ---: | ---: | ---: |
| Raw | 13,048 | 13,044 | 13,062 |
| Eligible | 11,010 | 11,008 | 11,022 |
| Expected exclusions | 1,948 | 1,946 | 1,950 |
| Malformed/rejected | 90 | 90 | 90 |
| Resolved / unresolved eligible | 9,886 / 1,124 | 9,882 / 1,126 | 9,896 / 1,126 |
| Duplicate ticker groups | 2 | 2 | 2 |
| Ambiguous / stable-ID collision | 0 / 0 | 0 / 0 | 0 / 0 |
| Identity coverage | 0.897911 | 0.897711 | 0.897841 |
| Malformed ratio | 0.006898 | 0.006900 | 0.006890 |
| Canonical instruments / resolver | 9,886 / 9,886 | 9,882 / 9,882 | 9,896 / 9,896 |

Quality gates and atomic publication passed on all days. Formal reread verified Arrow schemas, counts, deterministic ordering, UUID/referential integrity, resolver uniqueness, zero orphan references, manifests, and same-day logical completion.

| Session | Instrument fingerprint / Parquet SHA-256 | Identity fingerprint / Parquet SHA-256 | Resolver fingerprint / Parquet SHA-256 | Snapshot fingerprint |
| --- | --- | --- | --- | --- |
| 07-31 | `c26d2d90d56f63fdc887dd445f9aa876b3e6259b3b9b2076909e44ed1e49551d` / `6cc411f5f881026e87d7bbf4b3f75612ccb2db231191738408fa374d6dff0095` | `05d3a0c1de17c49d942e123d415a4b993ed689c885d24732fab5cc1f3cbff36f` / `a40257d551fa12e39014f53058d2451a14a6ace2e463f63dc7a3cce32046b601` | `212e038109c842e5d13345170bf582423ed9c2bc3249bc6f243ec5040e180d59` / `32b56c5124dde24834b9afe1fcf260073f47eadf91ecd116520f0512028da621` | `1fa2dd339772d529ea97e9be1732b34054ebe41b6cf05befdca9447ecd63b90e` |
| 08-03 | `a25d587e4ef9de5adcd40585483241ec232679a4ac2675654630b607353e17e9` / `1bfbb7fccb6860a654da1dae5f971e2586ec77a2edce1c8684f755882912ff23` | `9f5cd80529b5ef94de0dc4f29d4a1831f4fa400ef88dfd2cfd706749a49efea6` / `52d82676133b50860f4350b70bb665bcaa3d5e5c34e0239eb3cda18404afee7a` | `2d3b682b0f8437a5bf5c7136676cd8491515a48766c5134857ebcf21a537d191` / `6bd295b1240a894282fbdd164ff637459bd305eac5f3dad0fad3198a1ebd91df` | `8be80efe2ce3a1bbd1f7b0694ab12b9a98a2a846b12f07c353460bf6b554ace5` |
| 08-04 | `668703fc2ad7ab1d6e104c45d856e0c3c3147ac0e732fc7dbd052e3eed213966` / `48458c21d675341e636ff6f7690d6099ef0b2ca130e26460e3e1461e0f4704fd` | `3e5ec4b7077b722a64d94d7bb5c74b6028ba702efcc23a96234cf7f173705480` / `58cde5256648f2a3309403f668e5b6e9f95c2521bf5878b7511b2d25928b763b` | `a1cb3fa4b4d0a9e16fbc4fde4c1db9b613107ff0fb4d125de534321ee21ef526` / `a8449e66049d6b73b87f2986f554d629f7937c48913d016b62a629cb239e1150` | `ba9dbd6712729ede900ba5d5634e626de4889d2639d1a2d24f91883cf7fa1a98` |

## Grouped Daily Results

| Metric | 2026-07-31 | 2026-08-03 | 2026-08-04 |
| --- | ---: | ---: | ---: |
| Raw / unique ticker | 12,408 / 12,406 | 12,402 / 12,400 | 12,456 / 12,454 |
| Exact duplicate ticker/record | 0 / 0 | 0 / 0 | 0 / 0 |
| Conflicting ticker/record | 2 / 4 | 2 / 4 | 2 / 4 |
| Conflict ratio | 0.000322 | 0.000323 | 0.000321 |
| Resolved / unresolved eligible | 9,857 / 1,004 | 9,862 / 987 | 9,881 / 995 |
| Expected exclusions | 1,444 | 1,463 | 1,478 |
| Ambiguous / rejected / missing identity | 0 / 90 / 13 | 0 / 90 / 0 | 0 / 90 / 12 |
| Identity coverage | 0.906474 | 0.909024 | 0.907513 |
| Required numeric failures | 0 | 0 | 0 |
| Optional VWAP / trade-count missing | 4 / 4 | 0 / 0 | 3 / 3 |
| Fractional / zero volume | 11,033 / 4 | 11,203 / 0 | 11,125 / 3 |
| Canonical bars | 9,853 | 9,858 | 9,877 |

Nonpositive price, OHLC inconsistency, negative volume, timestamp mismatch, and canonical validation failures were zero every day. Existing low-ratio conflict isolation generated warnings without changing gates. Reconciliation, publish readiness, and atomic publication passed.

| Session | EOD fingerprint | Parquet SHA-256 | Same-day identity fingerprint |
| --- | --- | --- | --- |
| 07-31 | `c4999bc6e0be6397cf3562765439540bf6d7b9110f179c8e2b8bba0e28f80530` | `8b9c52cdc2f769696c4bdbceb25f5309ffe1a4f0e6008ef60820ff574c591442` | `1fa2dd339772d529ea97e9be1732b34054ebe41b6cf05befdca9447ecd63b90e` |
| 08-03 | `675c2179d66ad33363d1fea83a8d882a8fd240a6108a3f5bb82e130acdcb7c1a` | `be782b93cd816d9014d5ef8172f34ded813b46a2581eef4e72e9cb9a117b9926` | `8be80efe2ce3a1bbd1f7b0694ab12b9a98a2a846b12f07c353460bf6b554ace5` |
| 08-04 | `ba513ecc74bbb5641236ada4d9a0965a7449e8fb2e71c4f357f4307f8fc28273` | `c90ee2ed00bcc21a8f2322e057f06657223cf9956927e37be4c63135dceee6a1` | `ba9dbd6712729ede900ba5d5634e626de4889d2639d1a2d24f91883cf7fa1a98` |

Every manifest references its exact same-day identity snapshot. Future identity references, duplicate business keys, and multiple latest revisions are zero. All rows retain `adjustment_factors_unverified`; no raw payload was persisted.

## Inventory, Readiness, and Boundaries

The original 124-file, 45,701,023-byte protected inventory remained content- and metadata-identical, including digest `1187d3de85c668dbb459e3808640b86325daf9e5f247a553b99785bfe465e9b1`. Exactly 27 authorized files were added. Final inventory: 151 files, 55,540,570 bytes, digest `e775d09906593cd15bc5d324dac73d9042cbc46645d012d9e5bcaf66dd77a040`. Staging and raw/CSV/JSONL residue are zero.

The window now has 15 completed sessions, five missing sessions, and zero corrupt sessions. Candidate A/B remain wholly `insufficient_history`; 20/20, 19/20, and non-null median counts remain zero.

Only `/v3/reference/tickers` and the three authorized adjusted=false Grouped Daily paths were reached: 45 Massive requests, zero retries. SEC, OCI, other external services, later dates, scheduler, Dashboard/API/frontend, snapshot/bundle, deployment, and Universe activation were untouched. Credential content and authorization headers were not exposed.

Live preflight and postflight focused suites each passed 148 tests. Compileall, required imports, Health, shell syntax, Markdown links, sensitive scan, socket prohibition, `git diff --check`, staging/artifact, listener, and residual-process checks passed. Ordinary tests made zero external-network attempts.
