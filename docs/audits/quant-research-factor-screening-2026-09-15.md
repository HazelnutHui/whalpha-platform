# Factor Catalog V1 Development Screening Audit — 2026-09-15

## Verdict

`closed_no_candidate_alpha`

Factor Catalog V1 completed its single frozen Development screen and one full
exact replay. None of the five candidate-Alpha hypotheses passed. One of the
three risk guards, `rolling_maximum_drawdown_10s`, passed every registered
gate and is retained as risk evidence only. A risk guard without admitted
Alpha cannot open Model Construction.

## Frozen boundary

- Protocol: `quant-research-factor-screening/1.0.0`
- Protocol fingerprint:
  `222b14dd358f5d4e6e260c77226b11f3ac2130f8850f96abe5ae5d48a07a8a60`
- Implementation revision:
  `bb8cd4888eaace1fb9fca8e9e2456e04c47e239e`
- Development signals: 106 sessions, 2025-07-22 through 2026-01-07
- Cohort: 167,860 complete observations
- Labels: 503,580 independent 1/3/5-session factor-bound rows
- Formal trial budget: five candidate-Alpha plus three risk-guard hypotheses
- Setup conditioners: four definitions, zero outcome trials in this campaign
- Primary horizon: three sessions; one and five sessions are decay diagnostics
- Inference: deterministic circular five-session block bootstrap, 10,000
  replications, 90% intervals, and separate Holm family-wise control
- Costs: 0/10/25/50 basis points per side as diagnostics, not execution
  calibration or an admission gate

No Strong-Leader Pullback outcome was reused. Validation and Holdout were not
opened.

## Label reconciliation

| State | Rows |
| --- | ---: |
| Observed EOD exact | 503,214 |
| Terminal reference exact | 92 |
| Terminal reference interval | 46 |
| Unavailable evidence | 156 |
| Unexecutable without next open | 72 |
| **Total** | **503,580** |

Missing and terminal paths were retained as explicit states. They were not
silently removed, delayed to a later entry, or filled with zero.

## Registered decisions

| Factor | Role | Robust effect | 90% lower bound | Holm p | Decision |
| --- | --- | ---: | ---: | ---: | --- |
| `relative_return_spy_20s` | candidate Alpha | -0.0218 | -0.0513 | 1.0000 | rejected |
| `relative_return_acceleration_5_vs_prior15` | candidate Alpha | -0.0082 | -0.0381 | 1.0000 | rejected |
| `signed_path_efficiency_10s` | candidate Alpha | -0.0052 | -0.0327 | 1.0000 | rejected |
| `positive_session_share_10s` | candidate Alpha | -0.0047 | -0.0291 | 1.0000 | rejected |
| `largest_absolute_return_share_10s` | risk guard | 0.0065 | -0.0078 | 0.2292 | rejected |
| `close_location_value_1s` | candidate Alpha | -0.0055 | -0.0226 | 1.0000 | rejected |
| `absolute_overnight_gap_atr14` | risk guard | 0.0147 | -0.0016 | 0.1526 | rejected |
| `rolling_maximum_drawdown_10s` | risk guard | 0.2540 | 0.2322 | 0.0003 | retained risk evidence |

The retained risk guard also passed the registered chronological-half,
positive-session, bucket-monotonicity, concentration, partial-rank, decay, and
multiplicity gates. It is not a return predictor or a tradable strategy.

## Reproduction

- Report contract: `quant-research-factor-screening-report/1.0`
- Logical fingerprint:
  `5e40cd9ab11dd20a98aabdf0834dc3cfb5c5a173a94929eca73891db8f8f789a`
- Report SHA-256:
  `184bc3f92f97809fbc69ea13877857d78a81472d0fbd15fa48bbce0891c62704`
- First write: `published`
- Full second execution: `already_present` with identical logical and physical
  identities
- External requests: 0
- Canonical-data writes: 0
- Production writes: 0

The immutable owner-only report remains outside `/data` under the Dell
historical-evidence custody tree. Repository and Product records expose only
reviewed aggregate evidence and its reproducibility identities.

## Limits and next decision

The result is Development-only and retains these limitations: reconstructed
Membership is not as-operated, historical classification is unavailable,
split-neutral absence is unproven, broad Regime diversity is unproven, fixed
costs are not execution-calibrated, and the screen contains 106 signal
sessions.

Factor Catalog V1 is closed without retuning. Model Construction, Strategy
Expression, Validation, Holdout, Candidate activation, publication authority,
and trading authority remain closed. The next research action is a separately
registered Factor Discovery campaign with a new finite hypothesis budget and
an explicit cumulative-trial ledger; it must not present V1's failed factors
as an active model or reopen V1 under revised gates.
