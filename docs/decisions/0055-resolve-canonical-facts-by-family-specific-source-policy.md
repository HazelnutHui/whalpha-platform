# ADR 0055: Resolve Canonical Facts by Family-Specific Source Policy

## Status

Accepted

## Date

2026-08-28

## Context

The historical foundation will combine EOD, identity, action, lifecycle, and
open filing or identifier evidence from different sources. A global provider
priority or “first non-null” merge would silently mix unlike evidence, hide
contradictions, and let ticker reuse contaminate historical facts.

Source Permission Governance establishes whether a source may be used. It does
not decide which permitted source establishes one canonical fact when multiple
sources exist.

## Decision

Each canonical fact scope has one effective policy bound to:

- one standard data family and exact fact scope;
- ordered source bindings and their permission-review fingerprints;
- explicit authoritative, primary, corroborating, or crosswalk-only roles;
- one of single-authority, primary-with-corroboration, or unanimous-evidence
  resolution;
- the exact required matching-source count; and
- fixed fail-closed actions for missing evidence and disagreement.

Resolution joins only an exact stable subject ID and effective timestamp.
Ticker joins and first-non-null selection are structurally disabled. Rejected
or pending evidence and crosswalk-only sources cannot establish a fact. Any
usable resolving source that contradicts the anchor quarantines the decision;
majority vote and precedence do not erase disagreement. Missing required
evidence returns unavailable rather than selecting a weaker fallback.

The resolver compares immutable fact fingerprints, not untyped values. Domain
contracts retain the fact bodies and their own validation. A resolution
decision grants no request, persistence, canonical Apply, publication,
deployment, or scheduling authority.

## Consequences

- Source composition can vary by fact family without a global truth provider.
- Permission, evidence role, data quality, and canonical resolution stay
  separate and independently inspectable.
- Open identifier crosswalks may support identity linkage but cannot become
  price, lifecycle, or corporate-action facts.
- Conflicts remain visible for review and cannot be hidden by source order.
- A concrete production policy still requires selected, permission-cleared
  sources and separately reviewed fact scopes.

## Alternatives Considered

- **Global provider priority:** rejected because provider strengths and
  permissions differ by family and fact scope.
- **First non-null:** rejected because availability is not authority.
- **Majority vote:** rejected because two correlated or lower-quality sources
  do not automatically outweigh a contradictory authoritative observation.
- **Ticker-based reconciliation:** rejected because ticker is not a stable
  historical identity.
