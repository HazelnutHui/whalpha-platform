# Trailing-Liquidity Readiness Audit — 2026-08-14

## Calendar and Window

- Calendar: XNYS, exchange-calendars 4.13.2
- Analysis session: 2026-08-14
- Previous/liquidity cutoff: 2026-08-13
- Window: 2026-07-17 through 2026-08-13
- Expected sessions: 2026-07-17, 07-20, 07-21, 07-22, 07-23, 07-24, 07-27, 07-28, 07-29, 07-30, 07-31, 08-03, 08-04, 08-05, 08-06, 08-07, 08-10, 08-11, 08-12, 08-13
- Completed in window: 2026-08-12, 2026-08-13
- Missing: 18
- Corrupt/unavailable: 0
- Readiness: `insufficient_history`
- Descriptor fingerprint: `48892347525deb28284846dd0ab8314d81a5535bee3a4009be806fefc9f1aa84`

The completed 2026-08-14 partition exists for return analytics but is excluded from this window.

## Session Integrity

| Session | Rows | Content fingerprint | Physical Parquet SHA-256 | Identity date | Identity fingerprint |
| --- | ---: | --- | --- | --- | --- |
| 2026-08-12 | 9,900 | `dee4299a4c662af6eb5853aff30af7f261727e57c9de4489cc558441a8638bd3` | `924ae001fea34ec6f82aeca252adbacf176e50818a13dc51053807fdeb5b9aa1` | 2026-08-12 | `ab208fa5c0e2116d818a22c28d369324325b69d9ba05acd29da0028611cf872f` |
| 2026-08-13 | 9,901 | `aace64323774e1e91cc3f4dbbb8cd47923cdcc8df495216750a992cc2d9b8f1e` | `e2b7e6b0e79a627a2049e5aff16c98b770579afa8cc8791e2d7514bef05a9481` | 2026-08-13 | `2f4fe6a6c7266fea960449fedc98804b15ae72a65abed4632e8dde2ac4624f95` |

Future identity references, duplicate instrument/session rows, and multiple/non-latest revisions: all zero.

## Candidate Coverage

| Metric | Candidate A: 1,751 CS | Candidate B: 1,864 CS+ADRC |
| --- | ---: | ---: |
| 20/20 | 0 | 0 |
| 19/20 | 0 | 0 |
| 2 observations | 1,750 | 1,863 |
| 1 observation | 1 | 1 |
| Missing previous bar | 0 | 0 |
| Previous price gate pass/fail | 1,751 / 0 | 1,864 / 0 |
| Insufficient history | 1,751 | 1,864 |
| Zero-volume observations | 0 | 0 |
| Fractional-volume observations | 3,501 | 3,727 |
| Non-null 20-session median | 0 | 0 |

Candidate A coverage fingerprint: `6bd4287ef30f55411c4cb8e383670d16525fffd9b797934fbaaa8460c72fd885`. Candidate B: `a453c05d5ff99e3a17e26e0acc0ee5289a24c7d1deb178f6b83307466bcf8481`.

## Planning Result and Boundaries

All 18 missing EOD sessions also require same-day identity/resolver acquisition. The planning estimate is 270–378 requests, with conservative ceiling 378 and six chronological batches of at most three sessions. Plan fingerprint: `34c1a1a7e896a193e59d11bbf5e46641ce8d7340d57b7eade21792bd86bd2e98`.

This audit read `/data` only and wrote its non-production report under `/tmp`. It made zero SEC, Massive, or other provider requests; accessed no credential; and created no production dataset, API/frontend response, Dashboard calculation, snapshot, bundle, deployment, backfill, scheduler, or Universe activation.
