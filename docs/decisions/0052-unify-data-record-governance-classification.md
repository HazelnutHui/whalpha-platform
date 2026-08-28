# ADR 0052: Unify Cross-Family Data Record Governance Classification

## Status

Accepted

## Date

2026-08-28

## Context

WH Alpha already has correct but domain-specific statuses for security
classification, Universe membership, corporate actions, adjustment
availability, Candidate quality, historical coverage, lifecycle state, and
publication. Similar words such as `valid`, `excluded`, `quarantined`,
`unavailable`, and `complete` answer different questions. Treating them as one
flat status would lose evidence and create unsafe conversions; leaving them
without a common governance layer would make future fundamentals, events,
options, and portfolio data inconsistent.

The user also reconfirmed that current shared product content must be identical
for guest and credential Sessions. Future private watchlists, holdings, and
brokerage data may be identity-isolated, but cannot be implemented by silently
turning shared market analysis into role-dependent tiers.

## Decision

Adopt Data Record Governance V1 as the cross-family classification layer. It
does not replace domain statuses. Every governed record revision is classified
along separate dimensions:

1. data layer;
2. record disposition;
3. evidence status;
4. quality status;
5. bounded coverage status;
6. point-in-time signal eligibility;
7. retention class;
8. content scope; and
9. web-serving policy.

Missing is not exclusion. Quarantine is not a neutral factor. Superseded is not
deletion. Coverage is not record quality. Provider permission is not evidence
quality. Signal eligibility is not outcome-reconciliation eligibility.

The executable `standard-data-family-registry-v1` is the single registry for
current core families. It fixes each family's layer, stable-key grain,
retention class, point-in-time requirement, and allowed content scopes. New
families must extend a reviewed registry revision rather than invent local
classification terms.

Shared product data has one access rule:

- guest and credential Sessions receive identical shared data, analysis,
  language, Universe, precision, and functionality;
- no owner-only or member-only market-analysis serving state exists;
- a source that is not cleared for equal-capability use is blocked from all
  shared web Sessions until compatible permission or a replacement source is
  documented; and
- future user-private records require a real identity boundary and remain
  separate from shared product entitlements.

Existing physical datasets are not rewritten by this decision. Their domain
contracts remain authoritative. New data families and future schema revisions
must register and map their governance dimensions; existing families can be
mapped incrementally at manifest or publication boundaries.

## Consequences

- Cross-family audits can compare consistent dimensions without erasing domain
  meaning.
- Unknown, conflicting, and insufficient evidence continues to fail closed.
- Licensing cannot be disguised as a guest-versus-login product tier.
- Point-in-time research eligibility becomes explicit and cannot be inferred
  from a generic `valid` flag.
- Canonical facts, rebuildable caches, staging, and raw response bodies retain
  distinct lifecycle policies.
- User-private portfolio work remains possible later without changing shared
  market-analysis parity.

## Alternatives Considered

### Replace every domain enum with one universal status

Rejected because quality, evidence, coverage, membership, lifecycle, and
publication are independent dimensions.

### Keep only documentation terminology

Rejected because drift would remain untestable. The registry and record
classification are immutable Pydantic contracts with fail-closed validation.

### Introduce guest and member market-data tiers

Rejected because it contradicts the confirmed product policy. Source
incompatibility must be resolved at the source/publication boundary.

## Non-Goals

- rewriting existing Parquet partitions
- creating a database or catalog service
- granting provider permission or live entitlement
- acquiring or publishing data
- implementing personal identities, holdings, or IBKR integration
