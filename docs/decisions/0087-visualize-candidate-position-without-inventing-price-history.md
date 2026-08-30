# ADR 0087: Visualize Candidate Position Without Inventing Price History

## Status

Accepted

## Date

2026-08-30

## Context

The Candidate detail already publishes the current close, SMA10, SMA20, prior
five-session close high and low, selected reference support, ATR-normalized
distances, and Candidate-state confirmation counts. These facts were presented
as separate numbers, which made the current entry/chase-risk geometry slower to
read. The publication does not contain a daily price series, however. Drawing a
historical line from these summary levels would fabricate a path that the
contract does not support.

## Decision

Add an explanatory Candidate position map to the existing lazy detail drawer.
It places only the published current reference levels on one shared price
scale, then separately shows distance from the prior high, distance above the
selected reference support, distance from SMA20, and current Candidate-state
confirmation count versus its fixed requirement.

The browser does not recompute a score, rank, lane, technical setup, or state.
The view labels itself a reference-level map rather than a historical chart.
Candidate-state confirmation is not called signal age; selected reference
support is not called a stop; and ATR-normalized location is not presented as a
return forecast. Missing or invalid published geometry fails closed.

A future real 20-session price path requires a separate source-bound visual
context contract derived from the formal Dell panel. It must carry exact
sessions and lineage and remain separate from strategy scoring. It is not
inferred from the present summary contract.

## Consequences

- Current position and chase risk become visually comparable without changing
  any analytical result or payload contract.
- The implementation remains bilingual, accessible in text, and inside the
  existing on-demand Candidate detail boundary.
- Production remains unchanged until a separate reviewed deployment is
  authorized.
- True path, support/resistance history, and Candidate-state age remain future
  work rather than reconstructed approximations.

## Alternatives Considered

### Draw an approximate price line from SMA and high/low facts

Rejected because the points are different statistics, not chronological closes.

### Add a charting dependency for the first reference-level view

Rejected because a small shared-scale HTML/CSS map is sufficient, lighter, and
keeps every value available to assistive technology.
