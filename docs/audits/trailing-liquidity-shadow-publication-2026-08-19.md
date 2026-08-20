# 2026-08-19 Trailing Liquidity V1 Shadow Publication Audit

## Outcome

The offline administrator entrypoint completed one dry-run and one authorized `--apply`. Apply ran once from 2026-08-20T05:20:26Z through 2026-08-20T05:26:35Z and exited 0. No provider transport or credential loader was called.

This is a completed shadow derived-data publication. It did not activate Candidate A/B, Core, Broad, or replace the production Legacy Universe. Dashboard, API, frontend, snapshot, bundle, OCI, and deployment state are unchanged.

## Inputs

- analysis session: 2026-08-19
- membership evidence as-of: 2026-08-14
- calendar: XNYS / exchange-calendars 4.13.2
- window: 20 sessions, 2026-07-22 through 2026-08-18; 20 completed, 0 missing, 0 corrupt
- descriptor fingerprint: `705a20e8664bd94a7f20c83f687445b4249865d1feb2f25b8636933ac38f775a`
- Candidate A audit fingerprint: `1b8b9757054130c04ac21266d3660107c0b38d37db0ba8e510a0dcb2ed9583fd`
- Candidate B audit fingerprint: `2404a29b818ac365db19dff9734eea10cbda7b88f16b93610ea49297bb03aa95`
- membership evidence logical fingerprint: `f4ad3b09c5ae605790232b824e1b69208ad3a10571b3b66ea265700114855a12`

The logical manifest records all 20 EOD dataset paths, row counts, content fingerprints, physical Parquet hashes, and same-day identity snapshot dates/fingerprints. The formal production reader reproduced every reference after publication. Session 2026-08-19 is excluded from its own liquidity window.

## Published artifacts

| Artifact | Rows | Bytes | SHA-256 |
| --- | ---: | ---: | --- |
| Metric manifest | — | 433 | `26da21290594424b9bcf409d3b44638d1806b2677342b2185cceba73a717fc9b` |
| Metric Parquet | 1,864 | 124,996 | `d19b0afcf53ff70803002e8aafdb34a1dc599823c8f37bf8a3d425c9035e0769` |
| Decision manifest | — | 442 | `57c97cab63ee37b011d3da5daa05453229036fa9b6da4f09d23a3940649a94c7` |
| Decision Parquet | 3,615 | 80,775 | `2034107d2693ee116d91510e8cceb713e907ad32068485b37b20998f2896a350` |
| Logical completion manifest | — | 13,243 | `9d4496872544c050277b5b111602439a7a56c2c486f9e2f56d58d7f07ab21432` |

Logical content fingerprints:

- metric: `8abe29f4deb064acea974590fe965ecb166405381e7632762eb2ecba783ea7fc`
- decision: `9f27f7babaf347cab590386d9229d97f1f4348e32e483a35deffddc25d0a3254`
- completion: `89b58983f8c51680d77662dee7e2bfbf25406e160039d1a842d624396b08e65a`

## Candidate reconciliation

| Candidate | Requested | Passed | Below liquidity | Below price | Missing previous | Insufficient | 20/20 | Non-null median |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| A: CS only | 1,751 | 1,641 | 97 | 4 | 1 | 8 | 1,742 | 1,738 |
| B: CS + ADRC | 1,864 | 1,747 | 103 | 4 | 1 | 9 | 1,854 | 1,850 |

Every primary bucket is mutually exclusive and both rows reconcile exactly. Metric IDs and `(universe_id, instrument_id)` decision keys are unique; orphan decisions are zero. Candidate A contains only `CS`; Candidate B contains only `CS` or `ADRC`; disallowed-form leakage and silent unknown inclusion are zero.

## Incomplete-history evidence

The following are the ten unique Candidate B records behind nine insufficient-history decisions plus one missing-previous decision. Candidate A contains every row except ADRC `YXT`. A record's identity-presence vector is retained in the administrator dry-run; the table gives the deterministic primary evidence category and does not infer IPO, suspension, merger, or corporate action.

| Ticker | Instrument ID | Type | Bars | First / last bar | Missing sessions | Primary evidence category |
| --- | --- | --- | ---: | --- | --- | --- |
| YXT | `150a8be0-ef74-5b11-ac28-2314264d7471` | ADRC | 19 | 07-22 / 08-18 | 08-04 | `missing_canonical_bar` |
| WVE | `157f3bc4-abef-52e0-baad-2a263d537648` | CS | 7 | 08-10 / 08-18 | 07-22–08-07 (13 sessions) | `identity_not_resolved_for_session` |
| APMD | `7944ce2b-a52a-5733-8bbc-c8db3072ab6e` | CS | 13 | 07-31 / 08-18 | 07-22–07-30 (7 sessions) | `identity_not_resolved_for_session` |
| INHD | `7fea4581-a747-5be0-987a-90a43102df2e` | CS | 13 | 07-31 / 08-18 | 07-22–07-30 (7 sessions) | `missing_canonical_bar` |
| RVII | `86f8a069-bb1b-51fc-9edc-75c1036415b2` | CS | 4 | 08-13 / 08-18 | 07-22–08-12 (16 sessions) | `missing_canonical_bar` |
| JMKE | `9e26c5cf-ab7b-532d-9a84-6faa4eaa6960` | CS | 14 | 07-30 / 08-18 | 07-22–07-29 (6 sessions) | `missing_canonical_bar` |
| IOND | `c266976e-6d4a-552d-8cfa-550936780ffd` | CS | 16 | 07-28 / 08-18 | 07-22–07-27 (4 sessions) | `identity_not_resolved_for_session` |
| ADIG | `cd5e2cf2-3bc1-5a37-b7a7-7df3eb1296d1` | CS | 14 | 07-30 / 08-18 | 07-22–07-29 (6 sessions) | `missing_canonical_bar` |
| REPL | `fb10cef8-e908-5bde-9338-59dccceecc0f` | CS | 19 | 07-22 / 08-18 | 07-30 | `missing_canonical_bar` |
| AVB | `fc156e95-09ac-53d0-ab50-5175493c96ab` | CS | 18 | 07-22 / 08-14 | 08-17, 08-18 | `no_previous_session_bar` |

Mixed identity/bar evidence remains visible in the underlying audit. These labels describe only locally provable absence states and do not alter canonical data or membership evidence.

## Safety and verification

The original protected canonical inventory remained byte- and metadata-identical: 223 files, 81,860,836 bytes, digest `e453c759200cdf1dfb603a38b4eb519a74092c0f594865c226c233a92d2306d2`. Exactly five derived files were added. Staging residue, partial targets, raw payloads, and credential artifacts are zero.

Focused implementation/history/provider tests passed 50 cases. The correctly rooted complete backend suite passed 800 cases with the two existing deprecation warnings and no skipped or xfailed tests. Frontend regression passed 40 cases across five files with existing Vite configuration warnings. Compileall, required imports, FastAPI Health, shell syntax and CLI argument checks, 101-file/223-link Markdown validation, sensitive scan, socket prohibition, and `git diff --check` passed. An earlier full-suite invocation from the API subdirectory produced 796 passes and three path-relative test failures; rerunning from the documented repository root passed and no test semantics changed.

External requests, provider requests, credential access/stat, SEC, Massive, OCI, snapshot/bundle generation, deployment, scheduler, and system configuration changes were zero.
