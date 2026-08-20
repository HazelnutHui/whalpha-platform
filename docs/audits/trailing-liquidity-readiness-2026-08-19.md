# Trailing-Liquidity Readiness Audit — 2026-08-19

## Window

- Calendar: XNYS, exchange-calendars 4.13.2
- Analysis session: 2026-08-19
- Previous/liquidity cutoff: 2026-08-18
- Window: 2026-07-22 through 2026-08-18
- Sessions: 07-22, 07-23, 07-24, 07-27, 07-28, 07-29, 07-30, 07-31, 08-03, 08-04, 08-05, 08-06, 08-07, 08-10, 08-11, 08-12, 08-13, 08-14, 08-17, 08-18
- Completed / missing / corrupt: 20 / 0 / 0
- Status: `ready`
- Descriptor fingerprint: `705a20e8664bd94a7f20c83f687445b4249865d1feb2f25b8636933ac38f775a`

The 08-19 bar is structurally excluded from its own liquidity eligibility. Every included partition passed manifest, schema, count, content fingerprint, physical Parquet hash, same-day identity reference, revision, and business-key validation.

## Candidate Coverage

Membership is the existing non-production 2026-08-14 Provider-Classified evidence: Candidate A has 1,751 CS members; Candidate B has 1,864 CS+ADRC members. This audit does not reclassify membership using newer identity snapshots.

| Metric | Candidate A | Candidate B |
| --- | ---: | ---: |
| Requested | 1,751 | 1,864 |
| 20/20 | 1,742 | 1,854 |
| 19/20 | 1 | 2 |
| 18 observations | 1 | 1 |
| 16 observations | 1 | 1 |
| 14 observations | 2 | 2 |
| 13 observations | 2 | 2 |
| 7 observations | 1 | 1 |
| 4 observations | 1 | 1 |
| Missing previous bar | 1 | 1 |
| Previous price pass / fail | 1,746 / 4 | 1,858 / 5 |
| Non-null median | 1,738 | 1,850 |
| Below liquidity | 97 | 103 |
| Below price | 4 | 4 |
| Passed | 1,641 | 1,747 |
| Insufficient history | 8 | 9 |
| Fractional-volume observations | 34,955 | 37,211 |
| Zero-volume observations | 0 | 0 |

Candidate A result fingerprint: `1b8b9757054130c04ac21266d3660107c0b38d37db0ba8e510a0dcb2ed9583fd`. Candidate B: `2404a29b818ac365db19dff9734eea10cbda7b88f16b93610ea49297bb03aa95`.

The descriptor is ready, but instrument-level missing bars and the previous-price gate remain fail-closed. Existing exact-Decimal code calculated medians only where its full gates permit. No derived production dataset, Dashboard result, or Universe activation was created.
