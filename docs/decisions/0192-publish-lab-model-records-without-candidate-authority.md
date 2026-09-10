# ADR 0192: Publish Lab Model Records Without Candidate Authority

## Status

Accepted

## Date

2026-09-10

## Context

ADR 0191 makes Quant Research Lab the authority for model identity, method,
evidence, and lifecycle, while Stock Candidates may consume only separately
activated models. The current Lab page explains the first preregistered study,
but its content is hand-written interface copy rather than a typed, auditable
model record. The existing fixture statistics contracts also prove mechanics
only and must never be mistaken for real performance.

The system needs one durable boundary that permits full method transparency
now without implying that a backtest exists, that a model is valid, or that a
Candidate ranking may use it.

## Decision

Add three separate contracts:

1. a **model record** for immutable identity, ownership, hypothesis, inputs,
   exact feature formulas, parameters, evaluation design, limitations,
   blockers, and reproduction bindings;
2. a **research result publication** whose evidence scope is explicitly
   `method_only`, `fixture_only`, `signal_event_study`, or
   `portfolio_simulation`; and
3. a **catalog** that may list models but may name at most three Candidate
   models, each of which must already be in `active` lifecycle state and carry
   a separate activation fingerprint.

The first checked-in record projects the frozen Strong-Leader Pullback V1
method. It is `preregistered_data_blocked`, has no performance metrics, and has
no Candidate authority. The browser reads the same checked-in projection that
the Python contract test validates against the canonical builder.

Result semantics are fail-closed:

- method-only publications contain no observations, periods, metrics, or
  performance claim;
- fixture-only publications are permanently non-authoritative;
- signal/event studies cannot publish portfolio annualized return, Sharpe,
  drawdown, or other portfolio-only metrics; and
- portfolio metrics require a frozen portfolio-construction fingerprint.

A result publication never grants Candidate authority. Activation remains a
separate reviewed artifact and catalog binding. Guest and credential Sessions
receive the same record.

## Consequences

- The Lab can expose a complete research method before real data is ready.
- Interface copy can no longer drift independently from the registered model
  identity and formulas.
- Fixture-tested code cannot accidentally acquire a public performance claim.
- Event-level evidence and portfolio-backtest evidence remain semantically
  distinct.
- A future active Candidate model requires both lifecycle advancement and a
  separately fingerprinted activation decision.

## Alternatives considered

### Keep the Lab page as hand-written copy

Rejected because method facts and blockers could drift from the contracts.

### Put method and performance in one permissive JSON object

Rejected because missing fields and fixture metrics could look like real
validated results.

### Let a validated result automatically feed Stock Candidates

Rejected because statistical validation does not establish operational fit,
current-market applicability, monitoring, or rollback readiness.
