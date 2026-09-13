# Strong-Leader Pullback Evidence Blocker Census — 2026-09-13

## Scope

ADR 0221 intersects retained corporate-action and inactive-lifecycle evidence
with the fixed Strong-Leader Pullback reconstructed development paths. The run
is outcome-blind and network-prohibited. It wrote one immutable owner-only
diagnostic outside `/data`; it did not create a trigger, return, metric,
parameter choice, cohort choice, stable-ID assignment, canonical record,
Historical Coverage decision, Candidate artifact, publication, deployment, or
scheduler change.

## Fixed population

- signal sessions: 287 XNYS sessions, 2025-06-23 through 2026-08-12;
- Universe: `provider_classified_common_shares_v1`;
- Membership methodology:
  `provider-form-complete-base-point-in-time-v3`;
- evidence tier: reconstructed point in time from latest-vintage evidence,
  never `as_operated`;
- included paths: 437,402 across 2,161 stable instrument IDs;
- feature action window: `t-19` through `t`;
- labels: next-session-open entry and 1/3/5-session underlying-stock price
  returns.

The exact 2,656,006 Primary decisions and all 287 Membership partitions were
bound back to the rejected development census. Each custody marker, manifest,
Parquet physical hash, declared schema, Primary row, disposition total, and
included path was revalidated. No better-covered cohort was selected.

## Bound evidence

| Input | Manifest SHA-256 | Logical fingerprint / records |
| --- | --- | --- |
| Development coverage census | `c7d898d5d0f7efa3643ad696a52058279b21ff75a96d0fa4809e52c12a28c577` | `09ffe4edc38aeaccb3f101f5b1b784eb0769af0de9fde0c28fafbc18fe32388f` |
| Rejected admission decision | `697cad8452c73a1bd972f61c574ed9c4824c25721ecfcdea3e0bdf4fb9c01419` | `543fdd10e6c7df087d077754674f49660fd558a9f2dafcd4fe9dfa2131af36e8` |
| Corporate Action Resolution Shadow v2 | `b0d3e7438f8a1bd3d643a5fab564634fa203f92f08175dc9ceb5e166b1597c66` | `444077fb1ca39ba3ac210f19fc19dae7e94573d42fa3d1c4119216b2641a7c4a`; 242,235 typed rows |
| Unresolved action census v2 | `f1fbc2f8b76c34b3b44ff80c6292e458126762fe455f6e1953b759a642fd7f48` | `42a3b34e8354832c6505ac4a4c645145a2800390d0cfb99e12d31408cafe7f98`; 112,943 rows |
| Residual action evidence | `ba12436eababcb8b56b57d710a4e80cd83c26b33eca409c79a2d034bcbe8dd80` | `3fbcf2719047bf753ed4014017a82f6d3a659e2d90be724e2b35a90cbabce525`; 112,943 rows |
| Inactive lifecycle, 2026-07-16 | `f1d3008156bafb1eb10ae7a09f6d09741d25b21274b63c7993f70692f7effdac` | `c1e198951f73456a87dc1fb7c7045f25909c6e7278795e649b0783136c19585d`; 23,260 rows |
| Inactive lifecycle, 2026-09-03 | `0c7ec6904d13d6550522eb9edcd0de840f2c14571e65d3285ad0cd749df36240` | `ff57952511418baf1563d0322e6058365323884a206817ac4b757ce7320e2129`; 23,469 rows |

## Corporate-action intersection

The result contains 4,643 unique source-action/instrument exposure rows:

| Identity evidence | Cash dividend | Reverse split | Stock dividend | Stock split | Total |
| --- | ---: | ---: | ---: | ---: | ---: |
| Exact event-date stable ID | 4,579 | 11 | 20 | 13 | 4,623 |
| History candidate, unassigned | 19 | 1 | 0 | 0 | 20 |

The 20 unassigned rows remain explicit relations rather than assignments: 12
have one history-wide candidate and eight have multiple candidates. The single
reverse-split relation is not permitted to enter an adjustment ledger until
event-date ownership is proven. Cash dividends remain event context for the
declared price-return label; they do not silently change it to total return.

The full unresolved denominator remains 112,943 rows. Within the extended
strategy dates, 29,115 unresolved source rows fall on XNYS sessions, 24,005 of
those have no history candidate, and 53 additional rows fall on non-session
dates. There are 5,134 scoped history-candidate relations, of which 48 point to
an instrument ever included in the fixed population. Only 20 relations
actually intersect a declared feature or label path. Zero-candidate rows are
unmapped, not proven irrelevant.

| Window | Path relations | Unique affected paths |
| --- | ---: | ---: |
| Feature (`t-19..t`) | 81,740 | 80,568 |
| Label, 1 session | 4,117 | 4,071 |
| Label, 3 sessions | 12,463 | 12,325 |
| Label, 5 sessions | 20,854 | 20,626 |

## Lifecycle intersection

Eighty-nine retained review-candidate instruments intersect 8,677 included
paths. Their last-observation crossings are:

| Label horizon | Crossing paths | Instruments |
| --- | ---: | ---: |
| 1 session | 10 | 10 |
| 3 sessions | 135 | 63 |
| 5 sessions | 252 | 64 |

One scoped candidate has a provider delisting-date candidate equal to its last
canonical observation; the other 88 are later. Across the complete retained
lifecycle queue, 22 of 2,283 candidates are equal and none precedes the last
observation. The contract therefore admits equality as valid source evidence
while retaining both dates and granting no terminal-outcome authority.

## Custody and validation

The private package is
`historical-evidence/strong-leader-pullback-evidence-blocker-census/build=20260913-v1`.
It contains three files / 231,752 bytes:

- action Parquet: 217,713 bytes; SHA-256
  `ef0932711e7d932b4aa6f1629444cb43eb4c90e5c69e1159a390703ffe617687`;
- lifecycle Parquet: 8,731 bytes; SHA-256
  `f62603018a7a0875b7c24496c8273e8d3e24c68657afaf7ce47e982d9ef8b440`;
- manifest: 5,308 bytes; SHA-256
  `63fb6694ef0e6284bea3dc9cd5aafe431353e443a4239eff8f598f1d6baecb15`.

The package logical fingerprint is
`4abebf27774d0da398f029f152ce51b66e925201506365cf7084d8294f75243d`
and implementation revision is
`c80e0617b78eeb4fdfa8de1b95acedc45345cd3a`. Directories are mode `0700`,
files are mode `0400`, and no symlink, partial, or temporary member exists.
The successful build and built-in reread took 256.59 seconds at about one CPU
core with 2,222,116 KiB peak RSS. A separate output-only formal reread
reproduced all rows, hashes, fingerprints, and aggregates.

The first implementation redundantly materialized every row of both Universes
for every daily Membership partition and did not complete within its bounded
execution window. Revision `205040b4f2f5aed466ba2af3a351789e34bff082`
kept formal custody, manifest, Parquet hash, schema, disposition and path
validation while projecting only the declared Primary rows, reducing the real
run to about 4.3 minutes. A subsequent fail-closed run exposed the 22 valid
same-session lifecycle candidates described above and left no output. The
final rule correction was regression-tested before publication. Twenty-eight
focused tests pass. The complete API suite passes 2,602 tests with the same two
dependency deprecation warnings already present elsewhere in the project.

The project state report after publication still reports the exact prior
canonical `/data` inventory: 18,175 files / 7,022,164,015 bytes, fingerprint
`eda858b1db23dc58f22cdd0faa290f2141691fecf15862dc5bd6d095354834ff`,
zero symlinks. The package is outside `/data` and changed no canonical state.

## Decision and next boundary

The strategy intersection stage is complete and should not be repeated unless
a bound upstream artifact changes. It does not admit development: all 437,402
paths still lack proven sparse-action neutrality and canonical lifecycle/
terminal evidence.

Next work should be restricted to the measured blockers:

1. define and verify adjustment semantics for the 44 exact-resolved split-like
   exposures, while keeping the one unresolved reverse split quarantined;
2. use the 20 unassigned action relations and the 64 five-session lifecycle-
   crossing instruments as bounded cross-venue source acceptance samples;
3. retain cash dividends as event context for price-return research and prove
   missing-event neutrality separately; and
4. publish no final Historical Coverage and rerun no ADR 0195 admission
   decision until those mandatory evidence families materially change.

No global rescan, blind source purchase, outcome inspection, parameter tuning,
Candidate refresh, website publication, or deployment is justified by this
result.
