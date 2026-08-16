# Event Layer

## Confirmed Phase 1 Positioning

The Event Layer is currently a lightweight internal layer. It organizes important market changes and surfaces evidence-backed developments. It is not yet a large Event Knowledge Base.

Phase 1 includes only the lightweight detection and presentation slice.

## Long-Term Concept Direction

```text
Observation
-> Trigger
-> Candidate
-> Event
-> Active / Resolved
-> Outcome
-> Review
-> Knowledge
```

## Confirmed Domain Design History

The Event Engine vocabulary has the following confirmed intent:

- `Subject` is a Domain Object representing the entity or market relationship being evaluated.
- `Observation` may appear in the processing chain as source evidence or an intermediate result, but it is not a core Event Engine Domain Object.
- `Candidate` is a temporary validation stage and is not a durable confirmed event.
- `Event` represents behavior that has passed the required validation boundary.
- `Knowledge` represents durable learning retained after outcome and review.

The chain above is a processing direction, not a declaration that every named stage is a core Domain Object. Event Engine `Subject` is unrelated to `SecEvidenceSubject`, which belongs to the SEC evidence contract.

## Deferred

The detailed domain model, persistence model, state transitions, and Knowledge Base remain deferred. Website usefulness has higher priority than complete Event Engine implementation.
