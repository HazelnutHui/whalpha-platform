# Candidate Strategy Research Experiment V1

## Purpose

`candidate-strategy-research-experiment/1.0` freezes a personal quantitative
research hypothesis before historical outcomes can influence its design. It is
a repository-only preregistration contract, not a signal, backtest result,
recommendation, or Production model.

## Identity and immutability

The first registration is `strong-stock-pullback-research/1.0`:

- experiment ID:
  `3ab7175302bbcfb6894233d1db05534aa69bbab83935fa5d31dc9a916002b5d0`;
- logical fingerprint:
  `afc9b38f435484996e614f956b541c20f71b2506f7cff6252042af4da7211a41`;
- evaluation-policy fingerprint:
  `982929516dac7f963b1113c871ee63c78f440d39922561c8654cc4165865563a`.

The experiment ID binds the research version, registration date, and existing
evaluation policy. The logical fingerprint additionally binds every default
safety field, feature definition, parameter candidate, decision gate, blocker,
ownership label, and risk disclosure. Extra fields are forbidden and models
are frozen after validation.

## Research design

- Channel: `strong_stock_pullback`.
- Primary Universe: `primary`; `secondary` is sensitivity-only.
- Signal cutoff: session close.
- Entry basis: next session open.
- Primary horizon: three sessions; one and five sessions are secondary.
- Market benchmark: SPY price return.
- Primary contrast: same-session, point-in-time eligible leaders that did not
  trigger the pullback setup.
- Outcomes inherit Candidate Strategy Evaluation V1 and remain underlying-
  stock price outcomes, never option returns.

Eight source-bound requirements cover point-in-time population, adjusted
OHLCV, relative leadership, trend quality, ATR pullback depth, volume
contraction, recovery trigger, and Regime stratification.

## Bounded parameter selection

The Cartesian grid is exactly 24 combinations: 2 leadership gates × 3
pullback-depth bands × 2 recovery triggers × 2 volume caps. Every dimension is
`development_only`; exceeding 24 combinations is invalid. Validation and
holdout cannot select parameters.

The registered gates require:

- validation block-bootstrap p-values with Holm-Bonferroni family-wise
  adjustment at or below 0.10;
- a positive lower bound of the holdout block-bootstrap 90% interval for the
  primary three-session leader-control contrast;
- positive median three-session SPY-relative return after 25 bps per side in
  validation and holdout; and
- at least 60 observations for each separately reported Regime.

These gates are necessary, not sufficient, for later activation. Failure is a
valid research outcome and must not be repaired by editing V1.

## Current blocking state

The fixed stage is `preregistered_data_blocked`, with explicit blockers for:

- 252-session canonical history;
- daily point-in-time membership;
- corporate-action coverage;
- instrument lifecycle/terminal coverage; and
- a research-ready adjustment ledger.

Moving into an active research stage while retaining any blocker is invalid.
The contract performs no provider request, `/data` write, formula execution,
outcome maturation, publication, Snapshot change, frontend change, deployment,
or scheduler transition.
