# ADR 0074: Project Descriptive ETF Relationship Change

## Status

Accepted

## Date

2026-08-29

## Context

Phase 2 retains chronological history for all 16 preregistered ETF pairs, but
the production overview exposes only the current record and previous state.
It cannot show how long a state persisted or whether the selected rolling
relative-return advantage expanded or narrowed.

## Decision

Add a compact `relationship-change-summary/1.0` API/Snapshot projection derived
only from the already bound Phase 2 history. It reports the current consecutive
state run, its retained-history boundary, one- and five-session changes in each
rolling 5/10/20-session relative return, and threshold-free descriptive labels
for strengthening, weakening, reversal, new leadership, fading, or no change.

The immutable Phase 2 and Market Intelligence payloads remain unchanged. The
read service creates the summary for overview/detail responses, and old
Snapshot responses without it remain frontend-compatible. No label, score,
threshold, priority, highlight selection, or market-state result consumes it.

## Consequences

- The interface distinguishes persistence from acceleration without claiming
  causality or predictive power.
- A five-session delta compares two rolling-window observations; it is not a
  forward return or an option return.
- Reaching the first retained record is explicit and is not presented as the
  true beginning of the economic relationship.
- Publication and deployment remain separately authorized.

## Alternatives Considered

### Reclassify relationships from the new changes

Rejected because that would silently tune the frozen V1 state rules.

### Ship the complete history in every overview

Rejected because compact facts support the first view without duplicating the
full audit ledger in each Universe response.
