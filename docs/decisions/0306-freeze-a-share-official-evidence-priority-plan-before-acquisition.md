# ADR 0306: Freeze the A-share Official-Evidence Priority Plan Before Acquisition

## Status

Accepted

## Date

2026-09-18

## Context

The conservative reconstructed A-share package
`66ba3b6b552ebb3449860f841f622acb0195c026543f14068de9d42c0c7e3694`
exactly replays 109 partitions and 5,997,301 daily states. It routes 492
risk-warning candidates, 189 lifecycle candidates, and 1,046 listing-stage
candidates to missing official evidence. It also identifies 5,196 securities
and 56,112 windows with provider factor changes, but those observations do not
prove corporate-action terms.

Blindly querying five event families for all 5,409 targets would allow 27,045
requests without proving that each response serves an admission gap. The next
stage therefore needs a deterministic, immutable request plan before any
network access.

## Decision

1. Bind the plan only to the exact-reread conservative reconstruction package
   above. No population, normalized partition, provider endpoint, outcome, or
   other package may enter planning independently.
2. Route evidence in this order: risk warning, lifecycle, then listing stage.
   Deduplicate by stable source security ID within each family.
3. Freeze one risk-warning request unit per 492 securities, four separately
   purposed lifecycle units per 189 securities, and one listing-stage unit per
   1,046 securities. The maximum is therefore 2,294 request units.
4. A request unit has a content-derived stable ID, the full effective interval,
   one purpose, explicit expected fields, ordered official authority candidates,
   one total acquisition attempt, and the fail-closed disposition
   `quarantine_unchanged`. Candidate authorities are alternatives within one
   request unit; they do not multiply its request budget.
5. SSE-listed requests may route to SSE then CNINFO. SZSE-listed requests may
   route to SZSE then CNINFO. These are candidate authorities, not permission
   to access the network and not evidence that a URL or response exists.
6. Corporate-action candidates remain quarantined with zero requests. No
   request may be created from a provider factor change until a separately
   bounded corporate-action source policy is accepted.
7. Persist the plan as canonical JSON in an owner-only, atomic, closed package.
   Exact reread, forward/reverse candidate-order equality, and independent
   byte replay are required before acquisition can be considered.
8. The plan grants no network, return, Historical Coverage, Factor Discovery,
   backtest, canonical Apply, Product, publication, deployment, or trading
   authority.

## Consequences

The first eventual network batch is finite and reviewable: 492 warning-history
units, followed by 756 lifecycle-purpose units, followed by 1,046 listing-stage
units. A captured official document may be reused by later bound adjudications
when its stable security, effective interval, publication clock, raw hash, and
parsed fields satisfy those contracts; reuse never converts a failed or
ambiguous response into evidence.

Acquisition remains a later, separately authorized operation. Transport,
anti-bot, schema, missing-document, and conflicting-event failures preserve
the existing quarantine. The plan does not change any of the 5,997,301
reconstructed daily dispositions.

The logical interface is [China A-share Official-Evidence Priority Plan
V1](../data-contracts/china-a-share-official-evidence-priority-plan-v1.md).
