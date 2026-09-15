# ADR 0280: Admit Private Five-Year Split Evidence for Outcome-Blind Qualification

## Status

Accepted

## Date

2026-09-15

## Context

Factor Catalog V2 failed its first outcome-blind qualification because the
canonical split-action and sparse split-adjustment publications start on
2025-06-23, while the frozen 127-session input interval starts on 2024-12-17.
The Dell source foundation already retains a five-year split/dividend package
and a composite-Identity resolution shadow, but neither is canonical research
input. Changing V2 formulas, qualification gates, or the signal population
after seeing the coverage result would invalidate the preregistration.

## Decision

1. Preserve Factor Catalog V2, protocol 2.0.0, its 287 signal sessions, and all
   outcome-blind qualification gates unchanged.
2. Retain the five-year split candidate in a versioned, owner-only Dell custody
   boundary. It remains private outcome-reconciliation evidence and does not
   write or supersede canonical `/data`.
3. Permit that candidate to extend split evidence only for the zero-outcome V2
   qualification. The adapter must formally reread the candidate, bind its file
   hash and logical fingerprint, and continue binding the prior canonical split
   action and adjustment publications.
4. Reconcile overlapping canonical action facts by stable instrument, event
   date, action type, and exact ratio. Preserve prior and new unresolved-impact
   quarantines. Any overlapping event or adjustment disagreement becomes a
   stable-ID-specific quarantine; it is never silently selected or averaged.
5. Compose split price and volume multipliers from resolved, single-event
   groups only. Multiple same-date groups remain quarantined. Do not infer
   neutral action absence, total return, historical `as_operated` knowledge, or
   research-performance readiness.
6. Fingerprint the exact action keys, quarantine keys, projected adjustments,
   source sessions, basis session, prior canonical publications, private
   candidate, and adapter code. Require the same exact full replay as ADR 0279.
7. A successful V2 qualification may open only review of a finite Development
   outcome-screening protocol. It cannot activate a model, strategy, Candidate
   ranking, Validation, Holdout, publication, deployment, or trading.

## Consequences

The data repair can be tested without weakening preregistration or mutating the
canonical database. Its result is explicitly reconstructed latest-vintage
evidence, not a claim that five years of point-in-time Corporate Actions are
complete. A later canonical publication still requires a separate exact Plan
and Apply authorization if the project decides durable canonical promotion is
necessary.

## Rejected alternatives

- Lower the 90% availability gate or shorten the 127-session formulas.
- Treat missing actions as proof of neutral adjustment.
- Replace prior canonical evidence without overlap reconciliation.
- Publish the private candidate directly into `/data` under broad development
  authority.
