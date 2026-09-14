# Candidate Strategy Research Execution V1

## Purpose

This contract makes the first Quant Research Lab experiment's chronological
and anti-leakage mechanics executable without starting a real backtest.

The current execution contract is
`candidate-strategy-research-execution/1.2`. Its Strong-Leader Pullback
mechanics batch binds both the frozen experiment and
`strong-leader-pullback-method/1.0.0`; formula and parameter execution cannot
silently drift from the method displayed by Quant Research Lab.

## Records

### Chronological plan

`CandidateStrategyChronologicalPlanV1` binds the frozen experiment and policy
fingerprints to at least 252 contiguous XNYS sessions. Every session carries
its raw 50/25/25 split, explicit warm-up/purge/embargo/outcome-maturity
exclusions, usability, and latest possible five-session outcome date.

### Source-dated observation

`StrongLeaderPullbackObservationV1` 1.1 contains only information available no
later than its as-of session: point-in-time membership evidence, leadership
facts, pullback depth, recovery facts, volume ratio, and Regime. It contains no
future label. The 1.1 widening preserves Stress and permits negative pullback
depth for leaders above their prior high; positive signal bands are unchanged.

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
Its method version and immutable method fingerprint are mandatory fields.

### Forward outcomes

The existing Candidate Strategy Evaluation V1 outcome contract remains the
label authority. The execution service first creates pending 1/3/5-session
records. Only after the expected exit session is known may the exact path
produce next-session-open to horizon-session-close underlying-stock return,
SPY-relative return, MFE, and MAE. Corporate-action review yields quarantine
with no numeric result.

## Current implementation boundary

Python/Pydantic contracts and pure services are covered by synthetic and
boundary tests. ADR 0186 adds an outcome-free, fail-closed input-construction
adapter with exact feature semantics and complete-cross-section admission.
The execution service derives all 24 combinations and executable numeric
thresholds from the canonical method instead of maintaining a second
threshold table. There is no real filesystem orchestration, canonical
persistence, CLI, development selection, real report, result publication, or
deployment. The real experiment remains `preregistered_data_blocked`; this
contract grants no authority to use incomplete current history.
