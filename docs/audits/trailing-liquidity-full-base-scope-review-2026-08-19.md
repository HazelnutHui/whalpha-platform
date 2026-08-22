# 2026-08-19 Full-Base Trailing-Liquidity Scope Review

## HSAI authoritative security-form readiness (offline, 2026-08-21)

Manual review accepted AKR, UNIT, and DFNS warnings as non-blocking. AKR remains common beneficial interest despite its REIT/trust wording; UNIT remains common stock despite its ticker matching a provider type token; DFNS retains the daily-proxy anomaly flag while the frozen 20-session median/no-winsorization rule remains unchanged.

HSAI stable instrument `c66e6ab5-b3e2-5b32-845f-90f8eceed5a3` is blocked from activating the existing shadow as-is. Reviewed authoritative evidence is recorded by reference only: Hesai Group Form 20-F ([official SEC filing](https://www.sec.gov/Archives/edgar/data/1861737/000110465926048025/hsai-20251231x20f.htm), document/reporting date 2025-12-31) identifies HSAI as ADSs, and the 2026-07-10 Form 6-K ([official SEC filing](https://www.sec.gov/Archives/edgar/data/1861737/000110465926082432/tm2620203d1_6k.htm)) states that each ADS represents eight Class B ordinary shares after the ratio change. No filing was fetched this turn.

The new provider-neutral reviewed security-form boundary changes HSAI's effective form from provider `CS` to `ADR/ADS` from 2026-07-10. Formal dry-run recomputation yields Primary 1,718 CS (fingerprint `c3665203965b96528c9be07db3c49d18023104e346da16050f1170d4fe148978`) and Secondary 1,831 = 1,718 CS + 113 ADRC (fingerprint unchanged at `2dce08e728774510878c47dc80898e10236952dacd146990ad344c4dcb75a295`). HSAI fails Primary at `target_security_form` and passes every existing Secondary quantitative gate: supported exchange, current/previous bars, previous close 17.11, 20 observations, and median proxy `24932582.63967815500000000000`.

The planned superseding manifest uses schema 2.0 and immutable revision `authoritative-security-form-v1`. The offline dry-run wrote and formally reread only a temporary target: one reviewed-form row, 4,565 metrics, 9,130 complete decisions, 3,549 memberships, 3,549 diffs, and 20 funnels. Fraction-oracle mismatches and V1 reproduction mismatches were zero. No `--apply` ran; production remains 1,641/1,747, and the completed 1,719/1,831 shadow remains unchanged.

## Status

Implementation and the final offline dry-run passed. The separately authorized publication apply ran exactly once from 2026-08-20T11:25:45Z to 2026-08-20T11:35:34Z and exited 1 before staging because a metric Decimal exceeded the approved persisted scale. No shadow target was published and no second apply was attempted. Production Activation, Dashboard snapshot, API/frontend, and OCI release are unchanged.

## Root cause and reproduction gate

Formal code and reader inspection confirmed that Provider-Classified Candidate A/B first applied the previous-session `close × volume >= USD 20M` gate. Trailing Liquidity V1 then calculated its 20-session median only for those 1,751/1,864 requested IDs. The resulting policy was therefore the intersection of the old one-day liquidity gate and the new 20-session gate.

The frozen V1 metric and decision ledgers were rebuilt from formal inputs. The publication gate compares all 1,864 metrics (including observation counts, Decimal median values, statuses, and reasons) and all 3,615 decisions after excluding only the publication timestamp. Decimal values compare by numeric value rather than serialized trailing-zero scale; both gates reproduced exactly. Candidate fingerprints reproduce as:

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

The final dry-run exited 0 and produced 4,565 metric/status rows, 8,758 decision rows, 3,550 membership rows, 3,550 diff rows, and 20 funnel rows. It reproduced the 1,864 V1 metrics and 3,615 V1 decisions exactly, closed all 20 sequential funnel stages, and wrote zero `/data` files.

The one authorized apply failed at the pre-staging metric row-validation gate with `TrailingLiquidityPersistenceError: Decimal exceeds approved scale`. The earlier repair had removed the audit-only previous-session product and preserved only its full-precision comparison boolean, but at least one remaining metric Decimal (`previous_close` or `median_dollar_volume_proxy_20s`) still exceeds the physical `decimal128(38,10)` scale contract. The guard refused to round, quantize, or truncate it. Because the exception does not identify the field or record, this audit does not infer one. Resolving the physical Decimal contract requires a separate offline task; this run did not change schema or calculation semantics.

Postflight found zero full-base targets, zero staging residue, and an unchanged 243-file / 82,189,948-byte protected inventory with digest `3f5e4a3c23776c9dc269dd1d520cda079b54c26f9974d6336d1031f6496c148e`. There are no publication Parquet hashes or logical fingerprint to report. The apply count for this authorization is one and will not be repeated.

## Offline Decimal physical-contract diagnosis

The separately authorized offline diagnosis executed no apply. Across 4,565 planned metrics, `previous_close` has 4,527 non-null values, maximum precision 16 and scale 10, with zero values outside `decimal128(38,10)`. The 20-session median has 3,218 non-null values, maximum observed precision 28 and scale 20. Exactly two values cannot be represented losslessly at scale 10:

- JUNS, instrument `0d334e89-9b01-51eb-8ff5-665a44936897`: `320686.75045605845000000000` (precision 26, scale 20);
- HERZ, instrument `692e5dee-b7e7-5ff3-ae28-364b189b8772`: `61601.80674210025000000000` (precision 25, scale 20).

All 3,550 diff medians have maximum observed precision 28 and scale 20 and happen to quantize exactly to scale 10 in this session, but they use the same theoretical-safe contract as metric medians. The source canonical Arrow contract is Decimal128(38,10) for both close and volume. Product precision/scale can reach 76/20; summing two middle products can require precision 77, and dividing an odd coefficient by two can require scale 21. Decimal256's maximum precision 76 is insufficient for that full contract.

The offline repair uses a bounded exact Decimal tuple for medians and retains Decimal128(38,10) for previous close. A formal dry-run exited 0 and wrote/read all 4,565 metrics, 8,758 decisions, 3,550 memberships, 3,550 diffs, and 20 funnels through temporary Parquet. V1 metric and decision reproduction remained exact, corrected membership fingerprints remained unchanged, `/data` stayed byte-identical, and no target or staging was created. Corrected shadow publication remains pending separate authorization.

## Boundaries

Provider requests, credential access, Git remote, OCI, public web, EOD ingestion, canonical mutation, Dashboard/API/frontend/snapshot change, and deployment were all zero. SEC B2 remains paused. Authenticated desktop selector validation is complete; mobile, tablet, and keyboard validation remain open.

## Offline Decimal arithmetic-context audit

Python 3.12.3 started with precision 28, `ROUND_HALF_EVEN`, `Emin=-999999`, `Emax=999999`; only `InvalidOperation`, `DivisionByZero`, and `Overflow` were trapped, while `Inexact` and `Rounded` were not. Code inspection confirmed that the former daily `close * volume` and `(middle_10 + middle_11) / 2` paths inherited that context and could therefore round silently in the theoretical 76/20 and 77/21 domain. Threshold comparisons themselves do not round.

A pre-fix, read-only integer-coefficient oracle compared all available full-base daily products and all complete medians: daily-product mismatches 0, median mismatches 0, threshold crossings 0, maximum absolute and relative errors 0. The final formal dry-run independently reconciled 90,506 available daily observations and 4,435 complete-window medians with `Fraction`; daily, median, decision, membership, and 1,864-row immutable-V1 metric mismatch counts were all zero. Thus the current 2026-08-19 data happened to fit the default context exactly, but the algorithm was not safe for its declared physical domain.

The repaired calculation uses arbitrary-precision integer coefficients for daily products, median ordering, addition, division-by-two parity, previous-session audit comparisons, and ratio-gate cross multiplication. Global precisions 9/28/50, alternate rounding modes, and active `Inexact`/`Rounded` traps produce identical results. A separate `Fraction` oracle is now part of the formal dry-run gate. No apply ran; the corrected 1,719/1,831 shadow remains unpublished, production remains 1,641/1,747, and all production data and deployment state remain unchanged.

## Decimal context boundary remediation

The authorization review found three remaining integration defects: EOD fingerprint rendering called context-sensitive `Decimal.normalize()`, the Fraction audit reused derived full-base metric states for decisions, and nonmembership analytics inherited caller `Inexact`/`Rounded` traps. The remediation replaces fingerprint rendering with pure tuple/coefficient/exponent encoding, reconstructs every oracle decision and membership from raw canonical bars, provider evidence, exchange metadata, and overrides, and gives analytics a fresh explicit precision-78 local context whose traps and flags cannot leak across the boundary.

Formal production-root dry-runs at process precisions 9, 28, and 50, plus precision 28 with caller `Inexact` and `Rounded` traps enabled, all exited 0. Every run reread the completed EOD inputs with zero stored-fingerprint mismatch, reconciled 90,506 daily observations, 4,435 complete medians, 8,758 decisions, both memberships, and 1,864 immutable V1 metrics with zero mismatch, and left caller flags clear. Results remain 1,719 CS and 1,831 CS+ADRC with fingerprints `80bbe0331ce4e477c4517bcd79fe82ae6a1fcb89388fad717cdd283116a370bd` and `2dce08e728774510878c47dc80898e10236952dacd146990ad344c4dcb75a295`.

No apply ran. The corrected shadow is still unpublished, production remains 1,641/1,747, and Activation, Dashboard, snapshot, OCI, credentials, canonical data, and existing publications were unchanged.
