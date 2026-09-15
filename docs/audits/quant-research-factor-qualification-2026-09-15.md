# Quant Research Factor Qualification V1 Audit — 2026-09-15

## Decision

Factor Catalog V1 has completed deterministic, outcome-blind qualification on
the frozen reconstructed Primary research cohort. The original run and a full
independent replay produced the same logical report fingerprint. This verifies
calculation, coverage, distribution, concentration, pairwise redundancy, and
reproducibility; it does **not** admit a factor, establish Alpha, authorize
outcome screening, construct a model, define a strategy, or change Stock
Candidates.

The next permitted research action is a separately committed
**before-outcomes screening protocol**. It must freeze the label, cohort,
horizon, trial budget, related-hypothesis groups, multiplicity treatment,
stability gates, costs, selection cap, and stopping rule before any future
return is read.

## Frozen scope

| Field | Verified value |
| --- | --- |
| Catalog | `whalpha.factor-catalog.price-volume-v1` |
| Catalog fingerprint | `699fff686d2b05c53ba5f586934224794e17cef8d38690ced6a7da2dcd5a9368` |
| Protocol | `quant-research-factor-qualification/1.0.0` |
| Report contract | `quant-research-factor-diagnostics/1.0` |
| Interval | 2025-06-23 through 2026-08-12 |
| Declared sessions | 287 |
| Eligible sessions with complete vectors | 255 |
| Instruments represented | 2,161 |
| Registered factors | 12 across five economic families |
| Roles | five candidate-Alpha measurements, four setup conditioners, three risk guards |

The cohort, factor formulas, quantile convention, outlier rule, correlation
minimums, near-duplicate rule, concentration measures, and authority flags
were frozen in [ADR 0275](../decisions/0275-freeze-outcome-blind-factor-qualification-protocol.md)
before the runner read the real cohort.

## Coverage and missingness

| Measure | Count |
| --- | ---: |
| Expected instrument-session paths | 437,402 |
| Complete 12-factor vectors | 418,756 |
| Incomplete vectors | 18,646 |
| Expected factor cells | 5,248,824 |
| Available factor cells | 5,025,072 |
| Unavailable factor cells | 223,752 |

Complete-vector coverage is 95.7371%. Every factor has the same 418,756
available and 18,646 unavailable paths. The only unavailability reason is
`complete_cross_section_split_evidence_quarantined`; no missing or invalid
input was converted to zero, and no factor-specific denominator or source-data
failure was observed. This factor-catalog cohort is independent of the retained
Pullback method's feature-complete session count; the two methods have different
registered inputs and must not be blended.

## Distribution review

| Factor | Min | Median | Max | Tie rate | Outer-outlier rate |
| --- | ---: | ---: | ---: | ---: | ---: |
| Relative return vs SPY, 20 sessions | -2.1692 | -0.0025 | 2.6019 | 0.0010 | 0.0120 |
| Relative acceleration, 5 vs prior 15 | -2.0432 | -0.0007 | 2.1080 | 0.0000 | 0.0129 |
| Signed path efficiency, 10 sessions | -1.0000 | 0.0407 | 1.0000 | 0.0020 | 0.0000 |
| Positive-session share, 10 sessions | 0.0000 | 0.5000 | 1.0000 | 0.9939 | 0.0000 |
| Largest absolute-return share, 10 sessions | 0.1195 | 0.2509 | 0.9897 | 0.0000 | 0.0088 |
| Prior ATR5 / ATR14 | 0.0227 | 0.9882 | 2.5652 | 0.0002 | 0.0016 |
| Prior 10-session close range / ATR14 | 0.0465 | 2.2671 | 11.9971 | 0.0003 | 0.0021 |
| Close vs prior 20-session high / ATR14 | -66.7424 | -1.4323 | 23.3116 | 0.0015 | 0.0019 |
| Dollar-volume surprise vs prior 20 | 0.0233 | 0.9901 | 199.7116 | 0.0000 | 0.0255 |
| Close-location value | 0.0000 | 0.4988 | 1.0000 | 0.0700 | 0.0000 |
| Absolute overnight gap / prior ATR14 | 0.0000 | 0.1659 | 24.1809 | 0.0357 | 0.0196 |
| Rolling maximum drawdown, 10 sessions | -0.9118 | -0.0511 | 0.0000 | 0.0018 | 0.0163 |

The positive-session-share tie rate is expected because the factor has only 11
possible values. Heavy tails in dollar-volume surprise, breakout distance,
overnight gap, and related measurements are visible evidence to govern in the
next protocol; they do not authorize outcome-guided winsorization or another
formula revision.

## Redundancy and concentration

All 66 factor pairs were measured with same-session Spearman correlation over
255 eligible sessions and 418,756 shared observations. No pair met the frozen
near-duplicate rule. The strongest absolute weighted relationship was 0.7812
between signed path efficiency and close distance from the prior 20-session
high. The absence of near duplicates does not establish incremental or
predictive information.

The largest single-session observation share was 0.4239%; the largest
single-instrument share was 0.0609%. These figures show that the report is not
numerically dominated by one date or one instrument. Historical sector and
industry classifications are unavailable, so classification concentration was
not inferred from current labels.

## Reproduction and custody

| Evidence | Value |
| --- | --- |
| Logical report fingerprint | `fb92e95acb146af66fb4d9e286c96852374a51884936f5d69536c4accacdab02` |
| Physical report SHA-256 | `3767c39e327e8e3959d184ae8a16d2c5be3e1425fda416093b6aeefc51485e5e` |
| Calculation code SHA-256 | `65213f7770634a2b97c4737ec126fa862921065372d66622d266a34e504d5fc8` |
| Diagnostics code SHA-256 | `bd8e9aae9d04c4da211cb4059c7a1a4dee29f133d6c14a7a3b29f6ed65e97bd6` |

The immutable private report is retained under owner-only Dell historical-
evidence custody. Directory modes are `0700`, the report mode is `0400`, and
the run left zero staging residue. The first run and the independent full
replay matched the logical fingerprint; the existing immutable physical file
remained unchanged.

## Limits and authority

The report retains these explicit limitations:

- `historical_classification_unavailable`;
- `reconstructed_membership_not_as_operated`;
- `split_neutral_absence_unproven`; and
- `temporal_coverage_limited_to_287_sessions`.

It contains zero forward outcomes and zero performance metrics. Factor
screening, factor admission, model construction, strategy expression,
Validation, Holdout, Product activation, provider request, canonical-data
write, publication, deployment, and broker/order authority all remain false.
