# ADR 0102: Freeze Provider-Neutral Historical Source Packages

## Status

Accepted

## Date

2026-08-30

## Context

ADR 0101 produces an exact blocked Historical Pilot baseline. The existing
same-day Massive workflow has a provider-specific package, while the historical
Pilot plan describes multiple EOD, point-in-time Identity, and corporate-action
request families. No source-neutral physical boundary yet ensures that a future
provider adapter freezes every response before mapping or that another source
can replace or complement Massive without rewriting downstream governance.

Implementing a live adapter now would be unsafe because permission, account
entitlement, and lifecycle coverage remain unresolved. Implementing the
transport-independent custody boundary is safe and prevents those unresolved
questions from leaking into canonical schema design.

## Decision

Add `historical-source-package/1.0` as an immutable `/tmp` package contract and
formal reader. It consumes already captured, sanitized JSON objects and the
exact `historical-research-pilot-plan/1.0`; it never performs a request.

The package binds the exact plan and inventory documents, source-permission,
account-entitlement, lifecycle-review, and authorization fingerprints, every
planned non-empty endpoint/scope, actual and ceiling request counts, ordered
artifact hashes, acquisition time, serial pace, and zero-retry policy.

Every planned scope must be complete. The writer rejects unplanned scopes,
request-budget excess, credential-bearing fields or URLs, unsafe paths, and
noncanonical JSON. It publishes with owner-only directories, read-only files,
atomic rename, and a complete reread. The reader rejects changed bytes,
symlinks, extra or missing files, writable files, and plan/inventory drift.

The manifest permanently records that Apply, publication, deployment, and
scheduler authority are false. Validity is custody evidence, not permission or
execution authority.

## Consequences

- Provider transport and canonical family mapping now have a stable isolation
  seam.
- Massive, a replacement EOD source, or a hybrid source can share custody
  mechanics while retaining distinct permission and resolution policies.
- A future live Pilot still needs new written permission evidence, verified
  account entitlement, lifecycle coverage, and exact user authorization.
- No current Pilot plan, baseline, `/data` inventory, or Production state is
  changed by this fixture-only implementation.

## Alternatives Considered

### Extend the existing same-day Massive package directly

Rejected because its two package types and provider literal do not represent
the multi-family historical Pilot or a replacement source.

### Map provider responses directly into canonical Parquet

Rejected because permission, source revision, request completion, and immutable
byte custody must be independently reviewable before canonical Apply.

### Wait until a provider is selected

Rejected because the source-neutral isolation seam is already known and keeps
future provider selection additive rather than architectural.
