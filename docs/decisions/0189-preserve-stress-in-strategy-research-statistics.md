# ADR 0189: Preserve Stress in Strategy Research Statistics

## Status

Accepted

## Date

2026-09-09

## Context

ADR 0186 widened the outcome-free Strong-Leader Pullback observation and
execution contracts before real evaluation so all four Market Regime states,
including Stress, remain distinct. The existing fixture statistics contract
and its independent Oracle still initialized and validated only Risk-on,
Balanced, and Defensive counts. A valid Stress observation would therefore
fail during summary construction or contract validation.

No real research input, outcome, parameter result, or holdout has been created,
so this inconsistency can be corrected without interpreting or selecting from
observed market outcomes.

## Decision

Advance the fixture-only statistics contract to
`candidate-strategy-research-statistics/1.1` and require exactly four Regime
count keys: Risk-on, Balanced, Defensive, and Stress. Apply the same state space
to the primary evaluator and the separately implemented descriptive Oracle.

Add an end-to-end synthetic Stress fixture that rebuilds the outcome-free
observations and mechanics, evaluates all 24 registered combinations, and
requires exact evaluator/Oracle agreement. Do not change the experiment,
parameter grid, thresholds, chronological boundaries, selection rule,
multiplicity correction, holdout policy, or any Production path.

## Consequences

- Valid Stress sessions no longer crash or disappear from later research
  stratification.
- The statistics contract version changes because its accepted state space and
  report fingerprints change.
- Existing fixture expectations gain an explicit zero-valued Stress bucket.
- Formal readiness remains `data_blocked`; no real backtest, performance claim,
  filesystem writer, publication, deployment, or scheduler authority is added.

## Alternatives Considered

### Map Stress to Defensive

Rejected because it destroys an observed state and conflicts with the input
contract and Market Regime state machine.

### Drop Stress sessions from statistical summaries

Rejected because it creates state-dependent selection and makes Regime counts
fail to reconcile with available signals.

### Delay the repair until real evaluation

Rejected because a known contract mismatch is safer to fix and test before any
real outcome can influence implementation choices.
