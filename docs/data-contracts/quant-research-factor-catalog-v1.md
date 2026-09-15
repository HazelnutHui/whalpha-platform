# Quant Research Factor Catalog V1

## Purpose

`quant-research-factor-catalog/1.0` is the outcome-blind definition registry
created by ADR 0273. It broadens research inputs before the next strategy is
frozen while keeping factor definitions, model construction, and strategy
execution separate.

Every value is calculated from information available by the session close.
The earliest modeled execution remains the next session open. Prices and
volumes are split-reconciled to the signal-session basis; raw source facts are
never overwritten.

## Notation

- `t`: signal session;
- `C`, `O`, `H`, `L`, `V`: stock close, open, high, low, and volume;
- `B`: SPY close;
- `r(i,j) = ln(C[j]/C[i])` and `rb(i,j) = ln(B[j]/B[i])`;
- `ATR14[t-1]`: 14-session true range ending before the signal session; and
- all rolling windows contain only sessions at or before `t` as stated.

Zero denominators, non-positive log inputs, missing source sessions, ambiguous
split factors, or missing point-in-time membership produce explicit unavailable
evidence. They are never zero-filled.

## Initial definitions

| Factor | Role / expected relation | Exact formula |
| --- | --- | --- |
| `relative_return_spy_20s` | candidate Alpha / positive monotonic | `r(t-20,t) - rb(t-20,t)` |
| `relative_return_acceleration_5_vs_prior15` | candidate Alpha / positive monotonic | `[r(t-5,t)-rb(t-5,t)] - [r(t-20,t-5)-rb(t-20,t-5)]/3` |
| `signed_path_efficiency_10s` | candidate Alpha / positive monotonic | `sum(log(C[i]/C[i-1]), i=t-9..t) / sum(abs(log(C[i]/C[i-1])), i=t-9..t)` |
| `positive_session_share_10s` | candidate Alpha / positive monotonic | `count(C[i]/C[i-1]-1 > 0, i=t-9..t) / 10` |
| `largest_absolute_return_share_10s` | risk guard / negative monotonic | `max(abs(log(C[i]/C[i-1]))) / sum(abs(log(C[i]/C[i-1])))`, `i=t-9..t` |
| `prior_atr_ratio_5_to_14` | setup conditioner / no standalone Alpha claim | `ATR5[t-1] / ATR14[t-1]` |
| `prior_close_range_10s_atr14` | setup conditioner / no standalone Alpha claim | `(max(C[t-10:t-1]) - min(C[t-10:t-1])) / ATR14[t-1]` |
| `close_vs_prior_high_20s_atr14` | setup conditioner / no standalone Alpha claim | `(C[t] - max(C[t-20:t-1])) / ATR14[t-1]` |
| `dollar_volume_surprise_1_to_20` | setup conditioner / no standalone Alpha claim | `(C[t] * V[t]) / median(C[i] * V[i], i=t-20..t-1)` |
| `close_location_value_1s` | candidate Alpha / positive monotonic | `(C[t] - L[t]) / (H[t] - L[t])` |
| `absolute_overnight_gap_atr14` | risk guard / negative monotonic | `abs(O[t] - C[t-1]) / ATR14[t-1]` |
| `rolling_maximum_drawdown_10s` | risk guard / positive monotonic because less-negative is better | `min(C[j]/C[i]-1)` for `t-10 <= i < j <= t` |

The four conditioners may be described and checked for coverage/correlation,
but cannot be promoted from an attractive univariate outcome. Any later
threshold, interaction, or bounded-shape test consumes a separately registered
model-development trial.

## Outcome-blind first stage

The first executable report may contain only:

- per-factor and per-session availability;
- missing and quarantine reasons;
- ties, finite-value range, quantiles, and outlier counts;
- session and instrument concentration;
- pairwise same-session Spearman correlation and near-duplicate groups;
- source/code fingerprints and deterministic replay evidence; and
- explicit reconstructed-versus-as-operated limitations.

It contains no future return, IC, bucket performance, selected threshold,
factor pass/fail claim, model weight, Candidate rank, or strategy result.

## Transition boundary

A separate protocol must be committed after the outcome-blind coverage report
and before any forward outcome is read. That protocol owns the admitted cohort,
formal screen budget, multiplicity, label, costs, stability tests, factor
selection cap, and stopping rule. Development survivors still require locked
Validation, one sealed Holdout, prospective shadow evidence, and a separate
Candidate activation review.

The catalog authorizes no network request, `/data` write, Validation/Holdout
access, Lab performance publication, Candidate change, deployment, Production
write, broker integration, or order execution.
