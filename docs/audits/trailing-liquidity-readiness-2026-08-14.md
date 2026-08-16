# Trailing-Liquidity Readiness Audit — 2026-08-14

## Calendar and Window

- Calendar: XNYS, exchange-calendars 4.13.2
- Analysis session: 2026-08-14
- Previous/liquidity cutoff: 2026-08-13
- Window: 2026-07-17 through 2026-08-13
- Expected sessions: 2026-07-17, 07-20, 07-21, 07-22, 07-23, 07-24, 07-27, 07-28, 07-29, 07-30, 07-31, 08-03, 08-04, 08-05, 08-06, 08-07, 08-10, 08-11, 08-12, 08-13
- Completed in window: 2026-07-17, 2026-08-12, 2026-08-13
- Missing: 17
- Corrupt/unavailable: 0
- Readiness: `insufficient_history`
- Descriptor fingerprint: `b5bafb2dad55df9fbac8a773f321e77a6ae2a45f842b90116541540506df0490`

The completed 2026-08-14 partition exists for return analytics but is excluded from this window.

## Session Integrity

| Session | Rows | Content fingerprint | Physical Parquet SHA-256 | Identity date | Identity fingerprint |
| --- | ---: | --- | --- | --- | --- |
| 2026-07-17 | 9,844 | `c1bdf54e0ff421e74ffd5d57fe9e18ddca0dc8ac67d320dac6c06a8f4227b7c6` | `ec733ebc0b4887ca742ffb03d2c2df7bc78a30ec8a1145765b2f44fc2417dba9` | 2026-07-17 | `32af2ffc1538b5cbd261cc5299f27e52e3a6532917d4c3f47a50aaf4e50bccad` |
| 2026-08-12 | 9,900 | `dee4299a4c662af6eb5853aff30af7f261727e57c9de4489cc558441a8638bd3` | `924ae001fea34ec6f82aeca252adbacf176e50818a13dc51053807fdeb5b9aa1` | 2026-08-12 | `ab208fa5c0e2116d818a22c28d369324325b69d9ba05acd29da0028611cf872f` |
| 2026-08-13 | 9,901 | `aace64323774e1e91cc3f4dbbb8cd47923cdcc8df495216750a992cc2d9b8f1e` | `e2b7e6b0e79a627a2049e5aff16c98b770579afa8cc8791e2d7514bef05a9481` | 2026-08-13 | `2f4fe6a6c7266fea960449fedc98804b15ae72a65abed4632e8dde2ac4624f95` |

Future identity references, duplicate instrument/session rows, and multiple/non-latest revisions: all zero.

## Candidate Coverage

| Metric | Candidate A: 1,751 CS | Candidate B: 1,864 CS+ADRC |
| --- | ---: | ---: |
| 20/20 | 0 | 0 |
| 19/20 | 0 | 0 |
| 3 observations | 1,743 | 1,856 |
| 2 observations | 7 | 7 |
| 1 observation | 1 | 1 |
| Missing previous bar | 0 | 0 |
| Previous price gate pass/fail | 1,751 / 0 | 1,864 / 0 |
| Insufficient history | 1,751 | 1,864 |
| Zero-volume observations | 0 | 0 |
| Fractional-volume observations | 5,244 | 5,583 |
| Non-null 20-session median | 0 | 0 |

Candidate A coverage fingerprint: `00302d114aace40c0866a5a9966034c4b9c975df800621226f80b57e52fb3767`. Candidate B: `098792173e3a83373939085e67b7b0834521598f22d52a8776f59d1c6765e3ab`.

## Planning Result and Boundaries

The successful single-session pilot leaves 17 missing EOD sessions, each requiring same-day identity/resolver acquisition. The updated planning estimate is 255–357 requests, with conservative ceiling 357 and six chronological batches of at most three sessions. Plan fingerprint: `e39efe5c1ea2d694d609c812ee0a71046864d9ebc6628cef6040bd1c23b6306a`.

The 2026-07-17 pilot added only the authorized same-day identity and EOD partitions. No trailing-liquidity dataset or Dashboard result was created; readiness remains `insufficient_history`, and the analysis-day bar remains excluded.
