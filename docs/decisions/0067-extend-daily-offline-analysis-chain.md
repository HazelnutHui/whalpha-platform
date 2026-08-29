# ADR 0067: Extend the Daily Offline Analysis Chain

## Status

Accepted

## Date

2026-08-29

## Context

The daily planner, executor, and one-transition coordinator formally governed
Phase 1a, incremental Phase 1b, Candidate, and Entry Geometry. The production
publication also depends on three same-session offline artifacts: the
preregistered ETF Relationship audit (Phase 2), Market Regime preview bundle,
and Candidate Strategy Channel audit. Operators had to create those artifacts
outside daily run custody before publication review.

Stopping at Entry Geometry therefore allowed `analytics_ready` to describe an
incomplete publication input chain. It also left the latter three calculations
without the coordinator's immutable start/terminal journal, locked plan
identity, single-action postcondition, and interruption-recovery semantics.

## Decision

Extend the fixed offline order to:

```text
Phase 1a -> Phase 1b -> Candidate -> Entry Geometry
-> ETF Relationships -> Market Preview -> Strategy Channels
-> publication review
```

The planner formally rereads every new artifact and requires:

- the exact target session at each stage;
- Phase 2 lineage to the exact Phase 1a and Phase 1b logical fingerprints;
- Market Preview lineage to the exact Phase 1a, Phase 1b, and Phase 2 logical
  fingerprints; and
- Strategy Channel lineage to the exact Candidate and Entry Geometry logical
  fingerprints.

A missing artifact selects exactly one new offline action:
`calculate_etf_relationships`, `build_market_preview`, or
`calculate_strategy_channels`. An invalid artifact, session mismatch, lineage
mismatch, or downstream artifact without its verified prerequisite blocks and
requires operator diagnosis.

The executor delegates each action to its existing offline administrator,
writes only to an explicit direct child of `/tmp`, records the action in the
shared Dell journal, and formally re-plans before success. The coordinator
still performs at most one transition per invocation and never loops.

`analytics_ready` now means all seven governed offline artifacts are complete.
It still grants no permission to publish Market Intelligence, apply a
Snapshot, build or deploy an OCI bundle, access credentials, update `/data`,
or enable a scheduler. Those remain separate review and authorization
boundaries.

ADR 0068 later adds the no-Production-write Market Intelligence Plan as an
eighth custody-tracked preparation action. It does not change this ADR's seven
analytics stages or authorize publication.

## Consequences

- A daily run can advance through every offline input needed by publication
  review under one consistent custody and recovery model.
- Publication review no longer needs to discover missing Phase 2, preview, or
  Strategy Channel artifacts after the planner reported analytics readiness.
- Existing explicit offline CLIs remain independently usable for supervised
  diagnosis.
- A scheduler is still not enabled, and one wake-up still cannot run the
  entire pipeline.
- Publication, Snapshot, bundle, deployment, and notification orchestration
  remain future, separately authorized work.

## Alternatives Considered

### Loop through all missing offline stages

Rejected because it would weaken ADR 0034's one-transition failure and review
boundary and make resource-heavy work harder to recover safely.

### Treat the three artifacts as publication-time implementation details

Rejected because they are independently versioned, formally auditable
analytics with meaningful session and lineage requirements.

### Add publication and deployment to the same executor

Rejected because offline `/tmp` calculation custody must not imply Production
write or public deployment authority.
