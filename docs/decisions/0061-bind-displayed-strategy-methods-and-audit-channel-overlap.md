# ADR 0061: Bind Displayed Strategy Methods and Audit Channel Overlap

## Status

Accepted

## Date

2026-08-28

## Context

The deployed Strategy Channels workspace exposes reasons, risks, and bounded
same-channel ranks, but it does not show the exact weights, entry-geometry
mapping, status gates, or contribution arithmetic. A user therefore cannot
fully reproduce why one displayed security ranks above another.

The first real cross-sectional review also requires a distinctness check. The
three technical channels answer different research questions, but their scores
must not be compared because each score has channel-specific meaning. Set
overlap among Advance and Watch members can still reveal whether a channel is
acting as a broad superset rather than an independent selection path.

## Decision

Bind the browser methodology renderer to the exact frozen strategy parameter
fingerprint. For the known parameter version, show:

- exact component weights and entry-geometry score mapping;
- exact definitions of the reused Candidate component inputs;
- the separate Advance and Watch gates;
- the deterministic rank order; and
- each displayed security's input score, weight, and weighted contribution.

The browser independently reconstructs the published channel score using
fixed-point, round-half-even arithmetic. An unknown parameter fingerprint,
missing evidence component, malformed value, or score mismatch fails closed.
The browser does not recalculate status, rank, reasons, or the underlying
Candidate and Entry Geometry facts.

Treat extension risk as a separate position/chase review dimension in the UI.
Low extension is not automatically counterevidence; high or extreme extension
may still block or defer research according to the frozen status rules. This
is a presentation correction and does not change the published evidence row,
score, contract, or calculation.

Add a deterministic Dell-side diagnostic contract for qualifying-set overlap.
It reports exact intersections, unions, exclusive members, three-way overlap,
Jaccard overlap, and subset relationships. It prohibits cross-channel score
comparison and makes no outcome or performance claim.

Do not tune current weights or thresholds from the 2026-08-26 cross-section.
The current trend-continuation baseline must be labelled as a broad provisional
trend filter until continuation-specific facts and chronological validation
support a new parameter version.

## Consequences

- A user can reproduce every displayed score and understand status gates and
  ranking without treating the result as a recommendation or expected return.
- The frontend fails closed if its frozen explanation diverges from the
  published parameter identity.
- The real overlap audit shows that every qualifying breakout and pullback
  member is also in trend continuation in both Universes. This is a model-
  design warning, not evidence that any channel predicts returns.
- A future continuation revision should add governed facts for trend
  efficiency, orderly consolidation or volatility contraction, pullback depth,
  and recovery quality, then pass chronological evaluation under a new
  parameter version.
- No Snapshot, Dashboard, publication, or strategy calculation contract changes
  in this decision. Deployment remains a separate authorized operation.

## Alternatives Considered

### Show only prose descriptions

Rejected because prose cannot reconstruct a rank or expose a parameter drift.

### Compare the three channel scores directly

Rejected because their formulas answer different research questions and the
scores have no common calibrated scale.

### Reduce overlap by tuning thresholds on one session

Rejected because it would optimize the shape of one cross-section without any
evidence about future returns, false positives, or regime stability.
