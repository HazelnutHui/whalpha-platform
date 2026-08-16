# Trailing-Liquidity Readiness Audit — 2026-08-14

## Calendar and Window

- Calendar: XNYS, exchange-calendars 4.13.2
- Analysis session: 2026-08-14
- Previous/liquidity cutoff: 2026-08-13
- Window: 2026-07-17 through 2026-08-13
- Expected sessions: 2026-07-17, 07-20, 07-21, 07-22, 07-23, 07-24, 07-27, 07-28, 07-29, 07-30, 07-31, 08-03, 08-04, 08-05, 08-06, 08-07, 08-10, 08-11, 08-12, 08-13
- Completed in window: 2026-07-17, 2026-07-20, 2026-07-21, 2026-07-22, 2026-08-12, 2026-08-13
- Missing: 14
- Corrupt/unavailable: 0
- Readiness: `insufficient_history`
- Descriptor fingerprint: `08902ac267a1142069fe44272009b621c58a65acc4351364a54fafa5dedcdfc7`

The completed 2026-08-14 partition exists for return analytics but is excluded from this window.

## Session Integrity

| Session | Rows | Content fingerprint | Physical Parquet SHA-256 | Identity date | Identity fingerprint |
| --- | ---: | --- | --- | --- | --- |
| 2026-07-17 | 9,844 | `c1bdf54e0ff421e74ffd5d57fe9e18ddca0dc8ac67d320dac6c06a8f4227b7c6` | `ec733ebc0b4887ca742ffb03d2c2df7bc78a30ec8a1145765b2f44fc2417dba9` | 2026-07-17 | `32af2ffc1538b5cbd261cc5299f27e52e3a6532917d4c3f47a50aaf4e50bccad` |
| 2026-07-20 | 9,858 | `c2cbbb44859abb3c2810a23ceaa0f7e81dcdcd15e8f976fcecb820f1597b3042` | `0d26f1fedb0d29d8b5523c49866eaf59cf90bd600ff066b50d1be90f721a30de` | 2026-07-20 | `39a605a180ddf8a6da63e306d3a8c9197c33a03f7f71d74d89693831a212ab38` |
| 2026-07-21 | 9,846 | `8e11c2e65b6dcdd646dd4075d8f5e87527d23405e50e5979782f638951eb5703` | `bfcb03205ecd92a4e76689522778000d40be9bd4334751415e316c808819d969` | 2026-07-21 | `7f1a8de56c1ed6841be61efdd27859de1c34c696f9b4be5185332ca14007c6b5` |
| 2026-07-22 | 9,847 | `099492742e29c60c4873d00f4bab48710f3801e1a5c0230967b04b022f720063` | `edd697061a6de05effdd49d35441ff2634a96641e04884267a9a11eb1a13a3bc` | 2026-07-22 | `0c8f1572895312c942fff3f530abc94d70d43814ee2e4f465bcc53acb113e571` |
| 2026-08-12 | 9,900 | `dee4299a4c662af6eb5853aff30af7f261727e57c9de4489cc558441a8638bd3` | `924ae001fea34ec6f82aeca252adbacf176e50818a13dc51053807fdeb5b9aa1` | 2026-08-12 | `ab208fa5c0e2116d818a22c28d369324325b69d9ba05acd29da0028611cf872f` |
| 2026-08-13 | 9,901 | `aace64323774e1e91cc3f4dbbb8cd47923cdcc8df495216750a992cc2d9b8f1e` | `e2b7e6b0e79a627a2049e5aff16c98b770579afa8cc8791e2d7514bef05a9481` | 2026-08-13 | `2f4fe6a6c7266fea960449fedc98804b15ae72a65abed4632e8dde2ac4624f95` |

Future identity references, duplicate instrument/session rows, and multiple/non-latest revisions: all zero.

## Candidate Coverage

| Metric | Candidate A: 1,751 CS | Candidate B: 1,864 CS+ADRC |
| --- | ---: | ---: |
| 20/20 | 0 | 0 |
| 19/20 | 0 | 0 |
| 6 observations | 1,743 | 1,856 |
| 4 observations | 1 | 1 |
| 2 observations | 6 | 6 |
| 1 observation | 1 | 1 |
| Missing previous bar | 0 | 0 |
| Previous price gate pass/fail | 1,751 / 0 | 1,864 / 0 |
| Insufficient history | 1,751 | 1,864 |
| Zero-volume observations | 0 | 0 |
| Fractional-volume observations | 10,475 | 11,152 |
| Non-null 20-session median | 0 | 0 |

Candidate A coverage fingerprint: `292211db0d9b3c2021f47bd15c006721ea190ef49cf293ecdfaf1fa6bee55ef0`. Candidate B: `18e057c4ee313d8b7a406d1843ae0120223d1c13cf68714758a4c3f7b577aa18`.

## Planning Result and Boundaries

The successful first three-session batch leaves 14 missing EOD sessions, each requiring same-day identity/resolver acquisition. The updated planning estimate is 210–294 requests, with conservative ceiling 294 and five chronological batches of at most three sessions. Plan fingerprint: `913b8d07725384f14df27e4603276445f7730966abd5d878fd1d6cfa095e7935`.

The pilot and first batch added only their authorized same-day identity and EOD partitions. No trailing-liquidity dataset or Dashboard result was created; readiness remains `insufficient_history`, and the analysis-day bar remains excluded.
