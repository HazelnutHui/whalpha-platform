# ADR 0194: Govern AI-Assisted Quant Research as a Bounded Factory

## Status

Accepted

## Date

2026-09-10

## Context

Quant Research Lab already separates registered methods, real evidence,
Candidate activation, failure, and retirement. The first research program is
still being prepared manually and one strategy at a time. The intended longer-
term capability is broader: multiple specialized AI agents may propose
hypotheses, identify required data, specify factors, implement tests, and
attack each other's conclusions.

Unbounded parallel search over shared historical outcomes would not create
independent evidence. It would amplify data snooping, duplicate similar ideas,
consume holdout information, and make a lucky backtest more likely. Agent
count, code volume, and model complexity are not measures of Alpha.

## Decision

Treat the future AI capability as a governed **AI Quant Research Factory**
inside the Quant Research Lab boundary.

The operating principle is:

```text
high-throughput hypothesis generation
+ point-in-time governed data
+ bounded registered experiment budgets
+ isolated development / validation / holdout custody
+ deterministic evaluation and automated falsification
+ prospective shadow and paper evidence
= a research system, not an Alpha guarantee
```

The factory has the following non-negotiable rules:

1. AI may generate many ideas cheaply, but only deduplicated, economically
   stated, falsifiable hypotheses receive a finite registered experiment and
   parameter budget.
2. Every attempted experiment, including rejection and failure, remains in an
   append-only registry so repeated searches cannot erase the true trial count.
3. Idea, data, implementation, statistics, cost, red-team, reproduction, and
   shadow-monitoring roles are logically separate. Multiple agents sharing the
   same priors are not treated as independent statistical confirmation.
4. Research agents may see only the data partition required by their stage.
   Development cannot read sealed validation or holdout outcomes. Holdout
   custody is deterministic and single use.
5. Numerical calculation and gate decisions come from versioned deterministic
   code on Dell. Agent narrative cannot override a failed schema, fingerprint,
   chronology, cost, multiplicity, or evidence gate.
6. Automated falsification checks leakage, survivorship, revisions, action and
   terminal handling, parameter perturbation, temporal/Regime stability,
   concentration, costs, capacity, and independent reproduction. Passing those
   checks is necessary but not sufficient.
7. A locked model advances first to prospective shadow and then, when useful,
   paper trading. New live observations update evidence; they do not silently
   rewrite the old model. Material changes create a new version and new
   untouched evidence boundary.
8. No research result automatically enters Stock Candidates, becomes an order,
   or receives capital. Candidate use still requires a separate activation
   decision with monitoring, decay, and rollback rules. Automated trading and
   order execution remain outside scope.
9. Dell remains the code, data, orchestration, and heavy-compute authority.
   Start with bounded local processes and reusable manifests; do not introduce
   microservices, a distributed cluster, or a new database without measured
   need.

Implementation proceeds incrementally. Strong-Leader Pullback must first prove
one complete, reproducible, rejection-capable research path. Only then should
that path be generalized and piloted with a small number of specialized agent
roles before wider parallelism.

This decision records direction. It does not authorize agents to access
credentials, providers, `/data`, sealed outcomes, Production, a broker, or an
execution venue, and it does not implement a long-running agent service.

## Consequences

- The platform can scale research throughput without treating repeated search
  as free statistical evidence.
- Quant Research Lab remains the human-readable authority; the factory is its
  governed backend, not a competing product workspace.
- Rejection rate, reproducibility, leakage detection, and cost-aware survival
  become primary system-quality measures alongside any reported return.
- Early implementation remains deliberately small. The project avoids a large
  orchestration platform until one real strategy exposes the reusable needs.
- The user retains final authority over research objectives, data purchases,
  risk boundaries, model activation, and any later capital decision.

## Alternatives considered

### Let many agents search the same complete history freely

Rejected because it industrializes multiple testing and holdout contamination.

### Keep every strategy as a bespoke manual pipeline

Rejected as the long-term design because it limits throughput and makes
cross-strategy governance inconsistent. It remains the correct first step for
discovering the reusable contract.

### Allow an agent consensus vote to activate models

Rejected because correlated model opinions are not independent evidence and
cannot replace deterministic gates, prospective observations, or human review.

### Build distributed infrastructure before the first real result

Rejected because Dell has sufficient local capacity and the actual bottleneck
is evidence quality and research discipline, not cluster scale.
