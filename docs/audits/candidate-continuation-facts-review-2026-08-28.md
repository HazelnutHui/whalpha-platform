# Candidate Continuation Facts Review — 2026-08-28

## Result

`MECHANICALLY_RECONCILED_NOT_PERFORMANCE_VALIDATED`

The new descriptive continuation fact layer is deterministic and completely
covered on the retained 2026-08-26 Candidate population. It does not justify a
formula, threshold, rank, or return claim.

## Scope and custody

The review ran on Dell using the formally verified 2026-08-26 Candidate,
Entry Geometry, Strategy Channel, and content-addressed Market Regime panel
artifacts. Their relevant source identities were:

| Evidence | Verified identity |
| --- | --- |
| Candidate audit manifest SHA-256 | `83f60a72f0e522d7cbd95e853f39dfb1ccb061ca43f7086e12d8cc8820236a61` |
| Entry Geometry audit fingerprint | `b3e54546f297bcca9e9a23bb011e0137342777dedc979eca1b4cda71f173ff46` |
| Strategy audit fingerprint | `1c2036a6266647482de12d1ed7a1f9adf0f41311bc886979324ba3a0859c2877` |
| Panel cache key | `5f054560922bc5e3f81017e33dc9495f94f4a29f5d3e9e5b55b136dfa7e80276` |
| Panel history fingerprint | `ebb3a7ef9fc2faf68b355929a08af77e91183d5821b1fec07219febcff88fb5a` |

The operation was read-only and offline. It made no `/data`, publication,
Snapshot, bundle, deployment, scheduler, provider, credential, or Production
change.

## Mechanical result

| Universe | Candidate rows | Available | Unavailable | Oracle mismatch | Permutation match | Fact-batch fingerprint |
| --- | ---: | ---: | ---: | ---: | --- | --- |
| Primary CS | 1,715 | 1,715 | 0 | 0 | true | `4e4bba5af663a7b5d1306cdb1663f676f4f5f2087a843a9f66fef15fac2e30cb` |
| Secondary CS+ADRC | 1,828 | 1,828 | 0 | 0 | true | `94a411fdb576417f1cd2b73376d2456434490b4589bfdcc71f1722fbce861990` |

## Descriptive cross-section

The table compares medians only. “Qualifying” means the existing frozen trend-
continuation status is Advance or Watch. It is not a future-return label.

| Fact | Primary qualifying | Primary deprioritized | Secondary qualifying | Secondary deprioritized |
| --- | ---: | ---: | ---: | ---: |
| Existing population count | 425 | 1,271 | 451 | 1,358 |
| Information discreteness, 10 sessions | -0.200 | -0.200 | -0.200 | -0.200 |
| Return-path efficiency, 10 sessions | 0.303 | 0.251 | 0.306 | 0.248 |
| Largest absolute day share | 0.250 | 0.246 | 0.250 | 0.246 |
| Closes above SMA10 share | 0.800 | 0.300 | 0.800 | 0.400 |
| SMA10 five-session slope / ATR14 | 0.759 | -0.377 | 0.773 | -0.358 |
| ATR5 / ATR14 | 0.958 | 0.904 | 0.965 | 0.906 |
| Closing-high drawdown / ATR14 | 0.385 | 2.392 | 0.393 | 2.384 |
| Recent high versus prior high / ATR14 | 0.779 | -0.766 | 0.779 | -0.725 |
| Recent/prior median volume | 0.944 | 0.845 | 0.945 | 0.848 |

## Interpretation

- Trend slope, time above SMA10, closing-high proximity, and high/low structure
  strongly describe the existing filter. This is expected because its current
  inputs already emphasize trend and entry geometry; it is not independent
  evidence of predictive power.
- Information discreteness and largest-day share show almost no median
  separation. Return-path efficiency separates only modestly. These facts may
  still describe individual names but should not be promoted into weights from
  this one cross-section.
- ATR5/ATR14 is slightly higher in the qualifying group. The current channel
  therefore includes both orderly and expanding-volatility trends. A future
  contraction/consolidation setup should remain distinct from generic trend
  continuation until chronological evidence supports combining them.
- Median recent volume remains below the prior-fifteen median even among the
  qualifying group. Volume is supporting participation context, not required
  proof of sponsorship and never fund flow.

## Next valid research step

Keep the facts in shadow. Add no score or UI threshold. Once at least 252
point-in-time sessions, governed membership, adjustment, and lifecycle evidence
exist, preregister competing continuation definitions and evaluate sealed
signals with chronological walk-forward splits, purge/embargo, stability by
Regime, turnover, false-positive rate, and multiple-testing custody. The
current 29-session history remains implementation evidence only.
