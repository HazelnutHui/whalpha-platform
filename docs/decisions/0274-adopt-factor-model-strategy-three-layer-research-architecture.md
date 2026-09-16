# ADR 0274: Adopt a Factor–Model–Strategy Three-Layer Research Architecture

## Status

Accepted

## Date

2026-09-15

## Context

WH Alpha's first research program proved that a fully specified setup can be
implemented, reproduced, and rejected without opening Validation or Holdout.
It also exposed a structural weakness in the forward plan: several documents
treated named chart-pattern families such as Pullback, Momentum Breakout, and
Trend Continuation as a fixed model-development queue.

Those names are useful hypothesis labels, but they are not a professional
research architecture. They can prematurely determine which interactions are
tested, mix measurements with prediction rules and trading decisions, and
encourage each rejected setup to be replaced by another hand-written score.
Conversely, allowing an AI system to search unlimited factors and formulas on
shared historical outcomes would industrialize data snooping rather than
discover Alpha.

A durable architecture must remain open to evidence-led discovery over time
while keeping every individual research campaign finite, traceable, and
falsifiable.

## Decision

Adopt three separately versioned research layers:

```text
Factor Discovery
-> Model Construction
-> Strategy Expression
-> locked evaluation and prospective evidence
-> separate Product activation
```

The complete operating contract is
[Quant Research Three-Layer Architecture V1](../product/quant-research-three-layer-architecture-v1.md).

### 1. Factor Discovery

A factor is a point-in-time measurement, not a strategy and not an Alpha
claim. Every factor version binds its source fields, availability clock,
formula, transforms, missingness, eligible population, expected mechanism,
countermechanism, related-factor cluster, and reproducibility identity.

Discovery is open-ended across successive registered batches, but no batch is
unbounded. Before outcomes are read, each batch fixes its candidate
definitions, cohort, labels, trial count, related-hypothesis groups,
multiplicity method, screening criteria, and stopping rule. Outcome-blind
coverage, distribution, concentration, and redundancy diagnostics precede
development screening. Failed, duplicated, unstable, and null factors remain
in the append-only trial ledger.

A factor may be admitted as a directional candidate, conditioner, neutralizer,
risk guard, or execution/capacity input. It need not display a universal
monotonic return relationship to be useful, but its role cannot be changed
after seeing outcomes without creating a new counted trial.

### 2. Model Construction

A model combines a small admitted, non-redundant factor set into a rank,
conditional estimate, probability, distribution, or risk state. It is not an
entry order or a portfolio.

Every model version fixes its target, benchmark, feature set, transformations,
interactions, parameter and algorithm budget, regularization, calibration,
applicability, uncertainty, and comparison baseline. Transparent rules and
linear/ranking baselines come first. Additional complexity is admitted only
when it produces stable incremental out-of-sample value under the same data,
cost, and evaluation boundary.

Development access is limited to the registered development partition.
Feature selection, hyperparameter choice, and model comparison count against
one declared family budget. A selected model is locked before Validation and
cannot be repaired with Validation or Holdout evidence.

### 3. Strategy Expression

A strategy expression translates a model into a decision that could actually
be evaluated or used. It owns the point-in-time Universe, signal cutoff,
earliest execution, entry/wait/invalidation/exit rules, holding horizon,
re-entry, concurrent holdings, sizing, turnover, liquidity, costs, capacity,
portfolio risk, and monitoring rules.

Expression assumptions may be prototyped only inside a separately registered
development budget. The model and the expression that support a performance
claim are both locked before Validation. A later change to entry, exit,
portfolio construction, stock-versus-option vehicle, or cost treatment creates
a new expression version and cannot inherit the prior performance claim.

Stock and option expressions remain separate. An underlying-stock model may
inform an option hypothesis, but option returns require independent chain,
volatility, execution, event, and payoff evidence.

### Layer lineage and Product authority

Every published result must identify the exact factor versions, model version,
strategy-expression version, data cohort, label, costs, code, and evidence
stage. Quant Research Lab is the human-readable registry for all three layers.
Stock Candidates may consume only explicitly activated expressions backed by
an eligible locked model. Research existence, statistical validation, and
Product activation remain separate decisions.

There is no permanent list or count of future factor, model, or strategy
families. The visible Product may deliberately feature only a small reviewed
set at one time, but this is a presentation and operational-risk budget rather
than a fixed research taxonomy. Named concepts such as breakout, reversal,
value, defensive resilience, events, and cross-asset state are hypothesis
territories or tags until evidence produces a versioned factor/model/
expression lineage.

### Relationship to current and historical work

- The deployed Candidate score, Entry Geometry, and six Strategy Channels
  remain frozen, unvalidated Baseline V1 compatibility behavior. Their fixed
  taxonomy does not define future research.
- Strong-Leader Pullback remains a completed, rejected historical research
  program. Its contracts, audits, and retained results are not deleted or
  rewritten.
- ADR 0273's 12 price/volume definitions become the first bounded discovery
  catalog under this architecture, not the complete factor universe and not a
  commitment to Momentum Breakout.
- ADR 0191's Lab-to-Candidate activation boundary remains accepted. Its exact
  `one to three` wording is superseded by a small, explicitly reviewed active
  display/operational budget with no permanent numeric model cap.
- ADR 0192's V1 catalog limit remains valid only for that implemented contract
  version. A future three-layer catalog requires a new version rather than an
  in-place semantic change.
- ADR 0194's bounded AI Research Factory remains accepted and maps its agents
  to these three layers. Wider autonomous Factory operation remains deferred
  until at least one complete factor-to-model-to-expression path survives
  locked evaluation and prospective shadow review. ADR 0287 supersedes only
  this timing boundary for one manually supervised, outcome-blind Campaign
  Three qualification pilot; it opens no Development outcome access.

## Consequences

- Research breadth is no longer limited by a hand-written strategy queue.
- Factor evidence, model evidence, and trading-performance evidence cannot be
  silently collapsed into one score.
- Open-ended idea generation remains statistically accountable because each
  outcome-reading campaign is finite and retained.
- A useful discovery batch may produce no model, and a valid model may produce
  no cost-feasible strategy expression; both are legitimate outcomes.
- Quant Research Lab must evolve from one model card into linked factor,
  model, expression, evaluation, failure, and lifecycle records.
- Current Production and all access, data, Validation, Holdout, deployment,
  broker, and execution boundaries remain unchanged.

## Alternatives considered

### Continue a fixed sequence of named technical setups

Rejected because it narrows discovery before evidence and repeatedly mixes
feature choice, prediction, and trade construction.

### Keep one large composite Candidate score

Rejected because weights with different mechanisms and horizons are difficult
to falsify and provide weak lineage for why a security ranks highly.

### Allow unlimited automated factor and model search

Rejected because repeated access to the same outcomes makes apparent novelty
and statistical significance unreliable.

### Require a complete universal factor library before modeling

Rejected because it creates endless data and feature work. Each registered
research batch needs only the evidence required by its declared question and
must stop at its exit criterion.
