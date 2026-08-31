# Candidate Strategy Research Execution V1

## Purpose

This contract makes the first Quant Research Lab experiment's chronological
and anti-leakage mechanics executable without starting a real backtest.

## Records

### Chronological plan

`CandidateStrategyChronologicalPlanV1` binds the frozen experiment and policy
fingerprints to at least 252 contiguous XNYS sessions. Every session carries
its raw 50/25/25 split, explicit warm-up/purge/embargo/outcome-maturity
exclusions, usability, and latest possible five-session outcome date.

### Source-dated observation

`StrongLeaderPullbackObservationV1` contains only information available no
later than its as-of session: point-in-time membership evidence, leadership
facts, pullback depth, recovery facts, volume ratio, and Regime. It contains no
future label.

### Parameter and cohort assignment

The parameter contract enumerates exactly the 24 preregistered combinations.
For each combination and observation, the cohort contract records one of:

- signal;
- same-session eligible-leader non-signal control;
- excluded chronological boundary;
- excluded membership; or
- excluded non-leader.

The mechanics batch is self-fingerprinted and must state both
`contains_forward_outcomes=false` and `performance_claim_authorized=false`.

### Forward outcomes

The existing Candidate Strategy Evaluation V1 outcome contract remains the
label authority. The execution service first creates pending 1/3/5-session
records. Only after the expected exit session is known may the exact path
produce next-session-open to horizon-session-close underlying-stock return,
SPY-relative return, MFE, and MAE. Corporate-action review yields quarantine
with no numeric result.

## Current implementation boundary

Python/Pydantic contracts and pure services are covered by synthetic tests.
There is no real input adapter, canonical persistence, CLI, development
selection, validation statistic, report, UI, publication, or deployment. The
real experiment remains `preregistered_data_blocked`; this contract grants no
authority to use incomplete current history.
