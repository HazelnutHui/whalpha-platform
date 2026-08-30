# Historical Source Package V1

## Status

Implemented with synthetic temporary-root tests. No provider request, credential
access, `/data` write, canonical Apply, publication, deployment, or scheduler
change has occurred.

## Purpose

Historical Source Package V1 is the provider-neutral custody boundary between
an explicitly authorized transport adapter and all canonical historical-data
mapping. It ensures that downloaded source evidence is first frozen and
formally reread on Dell before any family-specific parser or Apply plan can use
it.

The package does not choose a provider and does not prove that permission,
account entitlement, lifecycle coverage, or user authorization is valid. It
only binds the fingerprints of the evidence that a future transport boundary
must verify independently.

## Exact package layout

One package is an immutable directory below:

```text
/tmp/historical-research-pilot/plan=<pilot-plan-fingerprint>/
  manifests/
    inventory-source.json
    request-plan.json
    source-package.json
  staged/
    <request-family>/<exact-scope>/<sequence>.json
```

The package directory must match the exact Pilot plan fingerprint. Directories
are owner-only and completed files are read-only. Publication uses a sibling
staging directory, durable writes, atomic rename, and a complete formal reread.
Symlinks, partial targets, conflicting reruns, changed bytes, unexpected files,
noncanonical JSON, and writable completed files fail closed.

## Manifest bindings

`historical-source-package/1.0` binds:

- provider ID and exact Historical Pilot plan fingerprint;
- Source Permission review, account-entitlement evidence, lifecycle-coverage
  review, and exact user-authorization acknowledgement fingerprints;
- acquisition time, fixed serial pace, zero-retry policy, plan document, and
  inventory document;
- every logical endpoint, exact scope, request ceiling, actual request count,
  contiguous response sequence, relative file path, byte count, and SHA-256;
- total actual requests and the plan-wide ceiling; and
- explicit false values for canonical Apply, publication, deployment, and
  scheduler authority.

Every non-empty planned request scope must be present and explicitly complete.
Actual pagination may end below its ceiling, but it may not exceed it or add an
unplanned endpoint, scope, or file.

## Security boundary

The repository accepts already captured JSON objects only. It has no transport,
provider client, credential loader, CLI, default root, or `/data` path.
Credential-bearing fields and URLs are rejected before any file is written.
Response bodies are never emitted by the formal reader.

Provider-specific adapters remain responsible for preserving source meaning
while removing credentials from URLs or fields. Mapping to stable
`instrument_id`, point-in-time interpretation, action resolution, quarantine,
and corrections all occur after this package and under their separate
contracts.

## Authority boundary

A valid package proves temporary byte custody only. It is not evidence that the
source may be used and cannot grant acquisition, retention, derived-use,
display, browser delivery, canonical Apply, Historical Coverage publication,
model evaluation, or deployment authority.
