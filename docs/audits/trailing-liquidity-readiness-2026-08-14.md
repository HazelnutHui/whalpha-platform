# Trailing-Liquidity Readiness Audit — 2026-08-14

## Calendar and Window

- Calendar: XNYS, exchange-calendars 4.13.2
- Analysis session: 2026-08-14
- Previous/liquidity cutoff: 2026-08-13
- Window: 2026-07-17 through 2026-08-13
- Expected sessions: 2026-07-17, 07-20, 07-21, 07-22, 07-23, 07-24, 07-27, 07-28, 07-29, 07-30, 07-31, 08-03, 08-04, 08-05, 08-06, 08-07, 08-10, 08-11, 08-12, 08-13
- Completed in window: 2026-07-17, 2026-07-20, 2026-07-21, 2026-07-22, 2026-07-23, 2026-07-24, 2026-07-27, 2026-08-12, 2026-08-13
- Missing: 11
- Corrupt/unavailable: 0
- Readiness: `insufficient_history`
- Descriptor fingerprint: `4f0b6e81771c1f3a44da50a7b78a940b14229020bf7e6c3cfefc0708d4ca7301`

The completed 2026-08-14 partition exists for return analytics but is excluded from this window.

## Session Integrity

| Session | Rows | Content fingerprint | Physical Parquet SHA-256 | Identity date | Identity fingerprint |
| --- | ---: | --- | --- | --- | --- |
| 2026-07-17 | 9,844 | `c1bdf54e0ff421e74ffd5d57fe9e18ddca0dc8ac67d320dac6c06a8f4227b7c6` | `ec733ebc0b4887ca742ffb03d2c2df7bc78a30ec8a1145765b2f44fc2417dba9` | 2026-07-17 | `32af2ffc1538b5cbd261cc5299f27e52e3a6532917d4c3f47a50aaf4e50bccad` |
| 2026-07-20 | 9,858 | `c2cbbb44859abb3c2810a23ceaa0f7e81dcdcd15e8f976fcecb820f1597b3042` | `0d26f1fedb0d29d8b5523c49866eaf59cf90bd600ff066b50d1be90f721a30de` | 2026-07-20 | `39a605a180ddf8a6da63e306d3a8c9197c33a03f7f71d74d89693831a212ab38` |
| 2026-07-21 | 9,846 | `8e11c2e65b6dcdd646dd4075d8f5e87527d23405e50e5979782f638951eb5703` | `bfcb03205ecd92a4e76689522778000d40be9bd4334751415e316c808819d969` | 2026-07-21 | `7f1a8de56c1ed6841be61efdd27859de1c34c696f9b4be5185332ca14007c6b5` |
| 2026-07-22 | 9,847 | `099492742e29c60c4873d00f4bab48710f3801e1a5c0230967b04b022f720063` | `edd697061a6de05effdd49d35441ff2634a96641e04884267a9a11eb1a13a3bc` | 2026-07-22 | `0c8f1572895312c942fff3f530abc94d70d43814ee2e4f465bcc53acb113e571` |
| 2026-07-23 | 9,844 | `97cbb22530fc10bf1711390d7de19e560fbc093fd810c503bf652d3c1d0dcf28` | `f9b9949f61be5eca1113daff4ea9ce629d41004bf38f362a17f7e001583e6747` | 2026-07-23 | `baac3d36b35a03a387d7443408967bef37bb0fc31184850ec0ccb5d1ae537246` |
| 2026-07-24 | 9,833 | `0cd88aa82c3c1707cadaf5a131039dd6606c14046d012359c33a00381135375f` | `a83adb81b7f7d40aad07d7da120e0e57c6fc715119538ae7d61b7598d5db43ab` | 2026-07-24 | `90c78760416d3956c7258508a401f07ffa3719f018a47a399799f45ccfea0891` |
| 2026-07-27 | 9,859 | `85d3c7cb2c2a9dda14ed5ce7edd897cb26b8c76ff1edb7d0f2655baf8615d75e` | `e8f882444f3be9874fa57f90e25e925cdf3d2ebeca4132ffbd3a310c470b5b86` | 2026-07-27 | `45eff526287cd497fa8262343af3c018cf3df543954a4690f351c9e2af5f081c` |
| 2026-08-12 | 9,900 | `dee4299a4c662af6eb5853aff30af7f261727e57c9de4489cc558441a8638bd3` | `924ae001fea34ec6f82aeca252adbacf176e50818a13dc51053807fdeb5b9aa1` | 2026-08-12 | `ab208fa5c0e2116d818a22c28d369324325b69d9ba05acd29da0028611cf872f` |
| 2026-08-13 | 9,901 | `aace64323774e1e91cc3f4dbbb8cd47923cdcc8df495216750a992cc2d9b8f1e` | `e2b7e6b0e79a627a2049e5aff16c98b770579afa8cc8791e2d7514bef05a9481` | 2026-08-13 | `2f4fe6a6c7266fea960449fedc98804b15ae72a65abed4632e8dde2ac4624f95` |

Future identity references, duplicate instrument/session rows, and multiple/non-latest revisions: all zero.

## Candidate Coverage

| Metric | Candidate A: 1,751 CS | Candidate B: 1,864 CS+ADRC |
| --- | ---: | ---: |
| 20/20 | 0 | 0 |
| 19/20 | 0 | 0 |
| 9 observations | 1,743 | 1,856 |
| 7 observations | 1 | 1 |
| 2 observations | 6 | 6 |
| 1 observation | 1 | 1 |
| Missing previous bar | 0 | 0 |
| Previous price gate pass/fail | 1,751 / 0 | 1,864 / 0 |
| Insufficient history | 1,751 | 1,864 |
| Zero-volume observations | 0 | 0 |
| Fractional-volume observations | 15,707 | 16,723 |
| Non-null 20-session median | 0 | 0 |

Candidate A coverage fingerprint: `caa830710375ca549161d89676533b374927f6111f258a830aa5637372064d3a`. Candidate B: `dca5d1dd04cd2e9f0022b757d1d0e62d41a6005607b9edf4f22f6a6235ad5b62`.

## Planning Result and Boundaries

The successful second three-session batch leaves 11 missing EOD sessions, each requiring same-day identity/resolver acquisition. The updated planning estimate is 165–231 requests, with conservative ceiling 231 and four chronological batches of at most three sessions. Plan fingerprint: `675dc6d5cebe3f8a66349768b61c8c8bbb7bffc69f51969f32ba3b5edf65b95c`.

The pilot and first two batches added only their authorized same-day identity and EOD partitions. No trailing-liquidity dataset or Dashboard result was created; readiness remains `insufficient_history`, and the analysis-day bar remains excluded.
