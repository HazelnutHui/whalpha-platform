# ADR 0054: Gate Data Sources by Explicit Use Permission

## Status

Accepted

## Date

2026-08-28

## Context

WH Alpha uses the Dell workstation for acquisition, retention, and computation,
then serves one shared product with identical guest and credential Sessions.
A provider endpoint can be technically available while its terms prohibit one
or more required uses. A general label such as `personal`, `non-commercial`, or
`public data` does not answer whether Dell retention, derived analysis, raw
display, derived display, and browser/API delivery are all allowed.

Record governance already separates content scope and web-serving policy, but
it cannot by itself prove that every upstream source permits the use that
produced a record.

## Decision

Every external source requires an effective-dated, evidence-fingerprinted
Source Permission Review before it can be used by an acquisition, retention,
analysis, or shared-serving transition. The review records, separately for
every use case:

- Dell acquisition;
- Dell raw retention;
- Dell derived analysis;
- equal-capability raw display;
- equal-capability derived display; and
- equal-capability machine delivery to the browser or another client.

Every conclusion is one of `cleared`, `blocked`,
`requires_separate_permission`, `unresolved`, or `not_applicable`. A separate
agreement is unresolved until its evidence is reviewed. Missing, stale,
unsupported, blocked, or unresolved use is default-deny for the requested
transition.

The standard equal-capability market-source assessment requires all six uses.
A narrower source contribution, such as SEC filing evidence used only to
derive a lifecycle fact, may declare the smaller exact use set, but it may not
claim permissions that were not assessed.

Permission eligibility is not operational authority. Passing a review does
not authorize credentials, a request, `/data` writes, canonical Apply,
publication, deployment, or a scheduler.

## Consequences

- Guest access is never restricted to accommodate an incompatible source.
- A source may be suitable for Dell-only research while blocked from the
  shared product.
- Openly reusable identifiers or filings do not become proof of market-data
  coverage, security identity, or corporate-action completeness.
- New provider adapters can reuse the canonical data families without
  replacing stable instrument identity or rewriting history.
- Reviews must be renewed when terms, products, account permissions, or
  intended uses change.
- Review evidence is persisted as immutable content-addressed packages under
  an explicit caller root. There is no implicit `/data` destination or mutable
  active pointer.

## Alternatives Considered

- **One provider-level allowed/blocked flag:** rejected because it collapses
  acquisition, retention, derived use, display, and redistribution into one
  ambiguous conclusion.
- **Treat non-commercial friend access as personal use:** rejected because
  Session protection and lack of revenue do not establish third-party display
  permission.
- **Keep the full product for credentials and reduce guests:** rejected because
  it violates the confirmed equal-capability product rule.
- **Infer permission from successful API access:** rejected because technical
  entitlement is not a license conclusion.
