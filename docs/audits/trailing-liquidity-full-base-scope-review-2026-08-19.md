# 2026-08-19 Full-Base Trailing-Liquidity Scope Review

## Status

Implementation and offline dry-run passed. The single authorized apply ran from 2026-08-20T10:35:59Z to 2026-08-20T10:45:59Z and exited 1 before staging because an audit-only previous-session `close × volume` Decimal exceeded the approved persisted scale. No shadow target was published and no second apply was attempted. Production Activation, Dashboard snapshot, API/frontend, and OCI release are unchanged.

## Root cause and reproduction gate

Formal code and reader inspection confirmed that Provider-Classified Candidate A/B first applied the previous-session `close × volume >= USD 20M` gate. Trailing Liquidity V1 then calculated its 20-session median only for those 1,751/1,864 requested IDs. The resulting policy was therefore the intersection of the old one-day liquidity gate and the new 20-session gate.

The frozen V1 decision ledger was rebuilt from its formal inputs. All 3,615 decisions matched after excluding only the publication timestamp; Candidate fingerprints reproduced as:

- A: `1b8b9757054130c04ac21266d3660107c0b38d37db0ba8e510a0dcb2ed9583fd`
- B: `2404a29b818ac365db19dff9734eea10cbda7b88f16b93610ea49297bb03aa95`

Legacy/Activation were used only after the corrected calculation for reproduction and set comparison.

## Formal inputs

- analysis session: 2026-08-19
- membership evidence: 2026-08-14
- XNYS window: 2026-07-22 through 2026-08-18
- completed/missing/corrupt: 20/0/0
- descriptor: `705a20e8664bd94a7f20c83f687445b4249865d1feb2f25b8636933ac38f775a`
- provider evidence: 9,939 rows—4,193 CS, 372 ADRC, 5,374 ETF
- immutable V1: 1,864 metric rows and 3,615 decision rows
- pre-activation review: 3,388 rows; reviewed overrides: 2
- Activation: 2 rows; current members 1,641/1,747

## Corrected sequential funnels

| Stage | Primary input | Primary excluded | Primary remaining | Secondary input | Secondary excluded | Secondary remaining |
|---|---:|---:|---:|---:|---:|---:|
| provider evidence base | 4,193 | 0 | 4,193 | 4,565 | 0 | 4,565 |
| target security form | 4,193 | 0 | 4,193 | 4,565 | 0 | 4,565 |
| supported exchange | 4,193 | 200 | 3,993 | 4,565 | 207 | 4,358 |
| current and previous bars | 3,993 | 25 | 3,968 | 4,358 | 36 | 4,322 |
| previous close at least USD 5 | 3,968 | 918 | 3,050 | 4,322 | 1,051 | 3,271 |
| complete 20-session history | 3,050 | 47 | 3,003 | 3,271 | 53 | 3,218 |
| median proxy at least USD 20M | 3,003 | 1,284 | 1,719 | 3,218 | 1,387 | 1,831 |
| outlier quarantine policy | 1,719 | 0 | 1,719 | 1,831 | 0 | 1,831 |
| reviewed overlay | 1,719 | 0 | 1,719 | 1,831 | 0 | 1,831 |
| final shadow | 1,719 | 0 | 1,719 | 1,831 | 0 | 1,831 |

Overlapping quality/review reasons are persisted separately and are not presented as sequentially subtractable counts.

## Set comparison

- corrected Primary: 1,719 CS; fingerprint `80bbe0331ce4e477c4517bcd79fe82ae6a1fcb89388fad717cdd283116a370bd`
- corrected Secondary: 1,831 = 1,719 CS + 112 ADRC; fingerprint `2dce08e728774510878c47dc80898e10236952dacd146990ad344c4dcb75a295`
- Primary retained/removed/added versus production: 1,641/0/78
- Secondary retained/removed/added versus production: 1,747/0/84
- Secondary minus Primary: 112, all ADRC
- Primary minus Secondary: 0
- rescued additions with previous-session proxy below USD 20M: 32 Primary / 34 Secondary
- prohibited security-type leakage: 0

VCX's reviewed exclusion and AKAN's reviewed allow remain stable-ID, point-in-time inputs. Neither changes final counts because the quantitative gates already exclude them; allow does not bypass those gates. BCPC/TPC sibling isolation and VXT/AZ/YXT dispositions are recorded from canonical stable-ID evidence without name-based inference.

## Offline analytics

Corrected Primary has 971 advancers, 740 decliners, 8 unchanged, equal-weight return `0.007636627190675724010091731617`, and median return `0.004340868541578531094229956`.

Corrected Secondary has 1,046 advancers, 776 decliners, 9 unchanged, equal-weight return `0.007879379350919177914624322742`, and median return `0.004847950639048038783605112`.

These are offline audit values only. No Dashboard snapshot or production derived analytics dataset was generated.

## Publication result

Dry-run produced 4,565 metric/status rows, 8,758 decision rows, 3,550 membership rows, 3,550 diff rows, and 20 funnel rows. Dry-run wrote zero `/data` files.

The only apply failed at the pre-staging row-validation gate. The persistence contract correctly refused to round a higher-scale daily proxy into `decimal128(38,10)`. The offline repair removes that audit-only Decimal from the physical contract and preserves only the exact boolean fact `previous_dollar_volume_below_threshold`; the eligibility median and previous close remain Decimal. A regression proves publication round-trip without narrowing the source product. The repaired code was not applied to production in this task.

Postflight found zero full-base targets, zero staging residue, and an unchanged 243-file / 82,189,948-byte protected inventory with digest `3f5e4a3c23776c9dc269dd1d520cda079b54c26f9974d6336d1031f6496c148e`. There are no publication Parquet hashes or logical fingerprint to report.

## Boundaries

Provider requests, credential access, Git remote, OCI, public web, EOD ingestion, canonical mutation, Dashboard/API/frontend/snapshot change, and deployment were all zero. SEC B2 remains paused. Authenticated desktop selector validation is complete; mobile, tablet, and keyboard validation remain open.
