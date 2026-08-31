# Candidate Strategy Research Statistics V1

## Purpose

`candidate-strategy-research-statistics/1.0` fixes the synthetic-only
statistical evaluation boundary for the first Strong-Leader Pullback research
program. It does not read canonical history and cannot create a performance
claim.

## Cohort outcome

`StrongLeaderPullbackCohortOutcomeV1` binds one signal or eligible-leader
control assignment to one 1/3/5-session fixture label. Available labels require
complete underlying, benchmark-relative, MFE, MAE and source fingerprints.
Pending, unavailable and quarantined labels carry no numeric statistics.
Both label identity and complete record identity are independently hashed.

## Parameter summary

Every summary exposes:

- assigned, available, quarantined and unavailable/pending counts by cohort;
- exact coverage ratios and available signal counts by Market Regime;
- underlying mean/median, SPY-relative median, hit rate, mean MFE and mean MAE;
- session-balanced signal-minus-control mean;
- fixed five-session, 2,000-replicate bootstrap interval and one-sided
  probability when the evidence floor is met;
- validation-only Holm-adjusted probability; and
- signal SPY-relative median after 0/10/25/50 basis points per side.

Inference remains `inconclusive` below 60 signal observations, 60 control
observations or 20 comparable sessions. Descriptive coverage is not discarded.

## Stage sequence

- Development returns 24 combinations × 3 horizons and may produce one
  immutable parameter lock.
- Validation returns the same bounded family, applies Holm across all 24
  primary-horizon hypotheses, requires complete inferential and signal/control
  outcome evidence for the whole corrected family, and cannot change the lock.
- Holdout returns only the locked combination × 3 horizons and is inaccessible
  unless all validation gates pass. Its own locked contrast also requires
  complete signal/control outcome coverage.

Every report is self-fingerprinted, binds the outcome-free mechanics batch and
prior-stage report, and declares `fixture_only=true`,
`stage_transition_authorized=false`, and
`performance_claim_authorized=false`.

`holdout_consumed=true` means that one report contains holdout fixture results;
it is not durable single-use custody. The current report explicitly declares
that such custody is not implemented, so repeated fixture calls must not be
misrepresented as an untouched real holdout process.

ADR 0107 now adds a separate external custody seam that reserves the exact
validation/lock identity before invoking a holdout capability and prohibits
replay after completion, failure or ambiguous interruption. It does not change
this fixture report field or make the evaluator authoritative. A future real
adapter must route exclusively through the custody seam or a reviewed successor.

## Current boundary

Only pure Python contracts, calculations and synthetic fixtures exist. There
is no canonical reader/writer, CLI, real label panel, research result, UI,
publication, deployment or scheduler integration. The real experiment remains
31/252 `data_blocked`.
