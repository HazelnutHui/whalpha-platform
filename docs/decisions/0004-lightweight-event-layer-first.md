# 0004: Start with a Lightweight Event Layer

## Status

Accepted

## Date

2026-08-12

## Context

The dashboard should surface important market developments, but a full Event Knowledge Base would add too much complexity before the core market dashboard exists.

## Decision

Phase 1 surfaces 3-5 evidence-backed developments. The full Event Knowledge Base is deferred. Daily dashboard usefulness has priority.

## Consequences

- Events begin as ranked findings, not a complete domain system.
- The natural-language layer must explain evidence rather than invent unsupported market narratives.
- The event model can evolve after the MVP proves useful.

## Domain Design Clarification

The confirmed long-term vocabulary distinguishes processing stages from core Domain Objects. `Subject` is a Domain Object. `Observation` may feed the processing chain but is not a core Domain Object. `Candidate` is temporary, `Event` is validated behavior, and `Knowledge` is the durable result of outcome and review. This clarification records design intent only; it does not authorize or implement the full Event Engine. `SecEvidenceSubject` is a separate SEC evidence-contract concept.

## Alternatives Considered

- Build the full Event Knowledge Base first: rejected as too much upfront complexity.
- Omit market developments entirely: rejected because the dashboard should highlight significant changes for human review.
