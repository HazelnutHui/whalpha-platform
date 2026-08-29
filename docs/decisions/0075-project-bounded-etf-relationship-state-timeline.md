# ADR 0075: Project a Bounded ETF Relationship State Timeline

## Status

Accepted

## Date

2026-08-29

## Context

The relationship view now reports current-state duration and one-/five-session
change facts, but a user still cannot see whether the recent path was stable or
frequently switching. Phase 2 already retains the required chronological rows.

## Decision

Project `relationship-state-timeline/1.0` from the formally bound Phase 2
history. Include at most the latest ten retained sessions for each registered
pair. Each point carries its session, frozen relationship state, confidence,
whether it changed from the prior retained session, and the already calculated
5/10/20-session relative returns.

The view reports the full retained count, first retained session, and whether
older points were compacted. It is additive to API/Snapshot presentation and
does not change the immutable Phase 2 or Market Intelligence payloads.

## Consequences

- The detail view can show recent persistence and switching without a browser
  reconstruction or a second network request.
- The selected 5/10/20-session window changes the displayed relative-return
  values but never changes the historical states.
- The timeline is bounded presentation context, not the full audit ledger and
  not evidence of causality, prediction, fund flow, or option returns.
- Publication and deployment remain separately authorized.

## Alternatives Considered

### Send the complete relationship ledger in every overview

Rejected because it would enlarge every Universe response and duplicate the
existing detail/audit history.

### Recompute historical states in the browser

Rejected because the browser must render frozen source facts rather than
reimplement analytics logic.
