# Strong-Leader Pullback Reconstructed Development Statistics V1

## Purpose

`strong-leader-pullback-reconstructed-development-statistics/1.0` binds one
private development-only comparison to the immutable reconstructed dataset,
canonical method, exact 24-combination budget, and the frozen policy in ADR
0271. The policy fingerprint is
`a420675be6c7eb580bc95906f4ef0588eccee0d9640047a57d459423e5708f37`.
It is an event study, not a portfolio backtest or Product model.

## Evaluation matrix

The report contains exactly 216 summaries:

```text
24 parameter combinations × 3 horizons × 3 endpoint scenarios
```

The endpoint scenarios are `all_lower`, `all_upper`, and
`contrast_adverse`, where the last uses signal lower/control upper interval
values. Exact labels are identical in every scenario. Point imputation is
forbidden.

Each summary exposes signal/control dispositions, numeric and excursion
denominators, Regime counts, event-level return metrics, session-balanced
contrast and block-bootstrap uncertainty, cost sensitivity, chronological
halves, Regime slices, and session concentration. Unavailable and unexecutable
rows remain separately counted.

## Selection

The primary horizon is three sessions. Each endpoint scenario independently
ranks all eligible combinations by:

1. greatest 90% interval lower bound of session-balanced signal-minus-control;
2. greatest mean contrast;
3. greatest numeric signal count; and
4. lexicographically smallest stable combination ID.

A lock requires the same winner in all three scenarios, all registered evidence
and Regime floors, and zero unavailable-evidence rows in any primary-horizon
signal/control cohort in the 24-member family. No development Holm adjustment
is applied; validation retains the registered full-family correction.

## Authority

The report is owner-only, immutable, self-fingerprinted Dell evidence. It reads
only the reconstructed development package and contains no validation or
holdout input. It authorizes no validation transition, performance claim,
Candidate use, publication, deployment, Production write, canonical `/data`
write, provider request, or order execution. A separate formal development
review is mandatory even when one parameter is locked.
