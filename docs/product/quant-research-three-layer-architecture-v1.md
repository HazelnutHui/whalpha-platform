# Quant Research Three-Layer Architecture V1

## Purpose

This is the durable research structure for WH Alpha. It separates what is
measured, what is estimated, and how an estimate becomes a tradeable decision:

```text
governed point-in-time data
        |
        v
Factor Discovery
        |
        v
Model Construction
        |
        v
Strategy Expression
        |
        v
locked Validation -> one sealed Holdout -> prospective shadow
        |
        v
separate activation -> Stock Candidates
```

The layers are linked, not interchangeable. A factor is not a model; a model
is not a strategy; a backtest is not Product authority.

## Layer 1 — Factor Discovery

### Question

Does a precisely timed measurement contain stable, incremental information, or
does it provide a useful condition, risk control, neutralizer, or execution
constraint?

### Required record

- stable factor ID, owner, version, and economic family;
- economic mechanism, expected behavior, countermechanism, and known failure
  states;
- source families/fields, point-in-time availability, signal cutoff, and
  stable-ID/Universe requirements;
- exact formula, lookback, lag, adjustment basis, transformation, unit,
  standardization, neutralization, and missingness/quarantine policy;
- related-factor cluster and expected redundancy;
- code/data fingerprint, deterministic tests, and coverage report; and
- lifecycle: proposed, registered, screened, admitted, rejected, deprecated,
  or unavailable.

### Two-stage boundary

1. **Outcome-blind qualification:** compute only values, coverage, missingness,
   ties, dispersion, outliers, concentration, correlation, and reproducibility.
2. **Registered development screening:** only after a protocol freezes cohort,
   labels, trial count, multiplicity, stability tests, costs, and stopping
   rules may development outcomes be read.

Factor screening should compare simple baselines, rank IC/decay, monotonic
buckets where appropriate, exposure-neutralized results, time/Regime/
liquidity stability, and concentration. Conditioners need a registered shape
or interaction test rather than a misleading universal monotonic claim.

An admitted factor is only eligible input to model construction. It is not a
validated strategy or Candidate ranking.

## Layer 2 — Model Construction

### Question

Can a small set of admitted measurements produce a reproducible and calibrated
ranking, conditional outcome estimate, distribution, or risk state that adds
value over a simpler baseline?

### Required record

- model ID, owner, version, research question, intended decision, and target;
- exact admitted factor versions and lineage;
- Universe, benchmark, label, horizon, and evaluation unit;
- transforms, interactions, missingness, neutralization, algorithm, objective,
  regularization, calibration, and uncertainty treatment;
- finite feature/model/hyperparameter budget and complete attempted-variant
  ledger;
- simple baseline and incremental-value test;
- chronological development, locked Validation, sealed Holdout, purge,
  embargo, multiplicity, and sensitivity design; and
- applicability, limitations, counterevidence, drift, decay, and retirement
  rules.

Complexity advances only when it earns stable incremental value. The default
ladder is transparent rules or rankings, then linear/regularized models, then
bounded nonlinear methods. A sophisticated algorithm is not evidence by
itself.

Model outputs should prefer ranks, probabilities, distributions, expected net
utility, or risk states over an unexplained 0–100 total. Every displayed score
must show its definition, calibration, factor contributions, uncertainty, and
the evidence that can invalidate it.

## Layer 3 — Strategy Expression

### Question

Can the locked model output be converted into a cost-aware, capacity-aware,
risk-bounded decision without destroying the observed edge?

### Required record

- expression ID/version and exact source model version;
- eligible point-in-time population and applicability state;
- signal cutoff, earliest execution, entry/wait/skip/invalidation/exit rules;
- holding horizon, overlapping signals, re-entry, cooldown, concurrency, cash,
  and rebalance rules;
- ranking-to-position mapping, position sizing, portfolio/risk limits, sector
  and factor exposure, and concentration;
- spread, slippage, impact, fees, borrow/financing, capacity, delay, and stress
  scenarios;
- event and data-failure behavior;
- event-study versus portfolio-simulation evidence; and
- shadow, activation, monitoring, pause, rollback, and retirement rules.

Expression variants consume a finite development budget and must lock before
Validation. A portfolio metric such as Sharpe, annualized return, or maximum
drawdown is allowed only after portfolio construction is fixed. A stock
expression cannot publish option returns; an option expression is a separate
version with historical chain and payoff evidence.

## Research lifecycle across the layers

```text
mechanism and falsifiable question
-> registered factor batch
-> outcome-blind qualification
-> registered factor screening
-> admitted small factor set or no selection
-> bounded model construction and simple-baseline comparison
-> bounded strategy-expression construction
-> lock factor/model/expression lineage
-> chronological Validation
-> single sealed Holdout
-> independent reproduction and red-team review
-> prospective shadow / paper evidence
-> separate activation
-> monitoring, decay, replacement, or retirement
```

No stage advances merely because the previous stage produced attractive
charts. A failure at any stage is retained and ends that version. A new
mechanism, factor formula, label, model, or expression rule creates a new
counted version; it does not rewrite the old result.

## Data-access matrix

| Activity | Feature history | Development outcomes | Validation | Holdout | Product |
| --- | --- | --- | --- | --- | --- |
| Outcome-blind factor qualification | Yes | No | No | No | No |
| Registered factor screening | Yes | Registered slice only | No | No | No |
| Model/expression development | Yes | Registered slice only | No | No | No |
| Locked Validation | Frozen inputs | Frozen read only | Once per version | No | No |
| Holdout review | Frozen inputs | Frozen | Frozen | Single use | No |
| Shadow | Frozen live calculation | Historical record | Historical record | Historical record | No rank authority |
| Activated expression | Frozen live calculation | Historical record | Historical record | Historical record | Exact approved scope |

The same agent or process must not use Validation or Holdout outcomes to
generate new factor formulas, select features, tune parameters, or rewrite
expression rules. Failed and attempted variants remain in the true trial
count.

## Quant Research Lab presentation

The Lab should expose five linked views while keeping the collapsed page
readable:

1. **Factor registry:** definitions, roles, coverage, redundancy, screening,
   failures, and source lineage.
2. **Model registry:** admitted factors, complete formula/algorithm, parameters,
   baselines, uncertainty, validation, and lifecycle.
3. **Strategy-expression registry:** execution, holding, costs, portfolio,
   risk, and vehicle rules.
4. **Evidence ledger:** data cohort, split, metrics, confidence intervals,
   sensitivity, counterevidence, reproduction, and sealed-stage custody.
5. **Lineage and decisions:** which factor versions feed which model, which
   expression is shadow/active, and why it advanced, failed, paused, or retired.

Headline cards show only decision-critical state. Expanded records disclose
all material data, formulas, parameters, search budgets, results, limitations,
and fingerprints. Research-only, rejected, shadow, active, and retired states
must be unmistakable.

## Stock Candidates boundary

Stock Candidates is a downstream decision surface. It may show only separately
activated strategy expressions and must identify:

- exact model and expression versions;
- current applicability and evidence freshness;
- within-model rank or estimate with factor contributions;
- entry readiness and chase/fragility risk as separate evidence;
- supporting evidence, counterevidence, and invalidation; and
- a link to the complete Lab lineage.

There is no permanent three-model or six-channel research taxonomy. The active
Product set stays intentionally small through a reviewed display and
operational-risk budget. Different model outputs are not merged unless an
ensemble is itself registered, evaluated, and activated.

## Relationship to market context and AI research

Market Regime, sector rotation, cross-asset state, fundamentals, events, and
options may contribute factors, conditioners, risk controls, or strategy-
expression inputs. They do not automatically become hidden score adjustments.
Their information time, role, and incremental evidence must be explicit.

The AI Quant Research Factory may propose and attack work in all three layers,
but it cannot grant statistical independence, hide the number of attempts,
open sealed data, override deterministic gates, activate a model, allocate
capital, or execute an order. Dell remains the numerical, data, and evidence
authority.

## Current migration state

- Strong-Leader Pullback predates this architecture and remains preserved only
  in internal contracts and audits as rejection and anti-retesting evidence.
  It is not a current Alpha, model, strategy expression, or public Lab program.
- Quant Research Factor Catalog V1 is the first bounded discovery batch. Its
  12 factors are not the permanent feature universe or a promised model. Its
  outcome-blind value, coverage, distribution, concentration, redundancy, and
  exact-replay report is complete under ADR 0275. Its frozen Development screen
  then rejected all five candidate-Alpha factors and retained one risk guard;
  the batch is closed without a model.
- ADR 0277 binds all eight consumed V1 trials in a cumulative ledger. ADR 0278
  registered the separate eight-definition Factor Catalog V2. Its
  outcome-blind qualification passed, but its frozen Development screen closed
  without candidate Alpha: four Alpha trials failed and two risk guards
  qualified but were not selected. Ledger V3 closes all 14 consumed trials.
- Campaign Three completed outcome-blind intake and input qualification. Its
  finite Ledger V4 registers two Alpha interactions and one risk guard as
  unread trials, bringing the cumulative formal-trial count to 17 without
  admitting any model input.
- ADR 0284 makes Factor Discovery itself renewable: close and count each finite
  campaign, then return to deduplicated hypothesis intake. Model Construction
  may open only for admitted Alpha and runs independently from later discovery.
- The current six Strategy Channels and Candidate score remain frozen,
  unvalidated Baseline V1 compatibility surfaces until separately replaced.
- No three-layer model or strategy expression is active in Stock Candidates.
- Model Construction and Strategy Expression remain locked until a separately
  screened catalog admits at least one candidate Alpha.
- Validation, Holdout, publication, broker, and execution
  authority are unchanged.
