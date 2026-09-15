# ADR 0273: Separate Governed Factor Discovery from Strategy Construction

## Status

Accepted

## Date

2026-09-15

## Context

Strong-Leader Pullback completed a reproducible, rejection-capable development
path and was rejected because terminal-reference endpoint worlds selected
different parameters. Editing that setup again would overfit the same outcome.
Immediately freezing another hand-built setup would also keep the research
program inside a narrow collection of chart patterns and would not establish
whether the underlying inputs carry independent information.

WH Alpha needs breadth without turning AI-assisted research into an unbounded
factor zoo. A factor, a model, and a strategy answer different questions:

- a factor is one precisely timed, reproducible measurement;
- a model combines admitted factors into a ranking or conditional estimate;
- a strategy adds population, entry, exit, cost, portfolio, risk, and lifecycle
  rules.

Existing Candidate scores and Strategy Channels mix descriptive inputs for
product triage. Their weights are not validated factor evidence and cannot be
used as the research answer.

## Decision

Insert a governed **Factor Discovery** stage inside Quant Research Lab before
freezing the next strategy model.

Register an initial outcome-blind catalog of 12 daily U.S. equity factors in
five economic families:

1. relative leadership: 20-session SPY-relative return and recent relative-
   return acceleration;
2. trend path: signed path efficiency, positive-session share, and largest-
   move concentration;
3. volatility/structure: pre-signal ATR compression, base tightness, and
   distance from a prior 20-session closing high;
4. participation/execution: dollar-volume surprise and close location; and
5. downside fragility: absolute overnight-gap size and rolling maximum
   drawdown.

The catalog contains standard baselines as well as WH Alpha-specific
compositions. Novelty alone is not evidence. Every definition binds its exact
formula, source families, lookback, signal cutoff, expected relationship,
economic rationale, countermechanism, missingness behavior, and related-factor
group.

The first stage is outcome blind. It may calculate factor values, coverage,
ties, cross-sectional dispersion, outliers, session/instrument concentration,
pairwise rank correlation, and deterministic reproducibility. It may not read
forward returns, select thresholds, publish Alpha, or change Candidate ranks.

After the coverage report is retained, a separate before-outcomes protocol
must freeze:

- the admitted session/member cohort and missingness rule;
- which factors are formal directional screens and which are conditioners or
  risk guards;
- the primary three-session next-open stock label and 1/5-session sensitivity;
- daily rank-IC, monotonic bucket, incremental-baseline, decay, cost, and
  stability statistics;
- the complete trial count, related-factor clusters, multiplicity method, and
  stopping rule; and
- the maximum number of factors allowed to enter one model-development family.

Development may explore only that registered budget. Factor discovery cannot
read Validation or Holdout. A factor that survives development is a candidate
input, not an independently validated model. Momentum Breakout remains the
leading next strategy family, but its final formula and parameter grid will be
frozen only after admitted factor evidence identifies a small, non-redundant
set. Strong-Leader Pullback outcomes cannot be used to choose those factors.

All heavy calculation and private evidence custody remain on Dell. The initial
catalog uses price, volume, stable Identity, point-in-time/reconstructed
Membership, and split-reconciliation evidence already inside the governed
research boundary. Price and volume remain trading-behavior proxies, never
fund flow. Stock labels remain stock outcomes, never option returns.

## Consequences

- Research can expand beyond one technical setup without granting unlimited
  historical search.
- Outcome-free data and redundancy defects are found before consuming a
  statistical trial.
- Standard factors provide honest baselines; project-specific factors must
  demonstrate incremental information rather than win by unfamiliar naming.
- Conditioner variables are not forced into misleading standalone monotonic
  claims.
- Every rejected factor and tested variant remains in the trial ledger.
- Validation, Holdout, Candidate activation, publication, deployment,
  Production, broker, and order-execution boundaries remain unchanged.

## Alternatives Considered

### Keep tuning Strong-Leader Pullback

Rejected because its two registered development protocols are exhausted and
the second failed endpoint stability.

### Freeze Momentum Breakout immediately from current UI thresholds

Rejected because those thresholds are descriptive Baseline V1 product rules,
not independently tested factor evidence.

### Let AI generate and test unlimited formulas

Rejected because correlated formulas and repeated outcome access inflate the
effective trial count and contaminate later evidence.

### Require every feature to be a standalone Alpha factor

Rejected because base compression, breakout distance, and liquidity/volume
state can be useful conditioners or risk controls without having a global
monotonic return relationship.

