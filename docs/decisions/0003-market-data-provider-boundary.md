# 0003: Introduce a Market Data Provider Boundary

## Status

Accepted

## Date

2026-08-12

## Context

Market-data vendors differ in schemas, coverage, pricing, entitlement rules, and reliability. Coupling domain calculations directly to one vendor would make replacement and testing harder.

## Decision

Analysis code consumes normalized internal interfaces. Massive is the proposed primary broad-market provider. IBKR has a separate account, portfolio, and selected-instrument role. Provider choice remains replaceable.

## Consequences

- Raw vendor data must be normalized before analysis.
- Vendor response schemas should not leak into domain calculations.
- Tests can use normalized fixtures without requiring live provider access.

## Alternatives Considered

- Directly call a single provider from calculations: rejected because it creates avoidable coupling.
- Build a large provider abstraction immediately: rejected because Phase 1 should stay minimal.
