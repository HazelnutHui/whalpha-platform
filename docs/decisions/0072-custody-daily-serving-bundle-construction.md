# ADR 0072: Custody Daily Serving-Bundle Construction

## Status

Accepted

## Date

2026-08-29

## Context

The daily control plane now prepares and separately applies the exact Market
Intelligence and Dashboard Snapshot publications. The next existing operation
is the local OCI serving-bundle builder. It produces the React snapshot build,
role-free credential/guest entry assets, and the approved Snapshot payload,
but it has remained outside the daily plan fingerprint, journal, formal reader,
and interruption-recovery boundary.

The old builder also accepts `--snapshot-release`, which resolves a legacy
repository build directory rather than the active immutable V2 Snapshot
namespace. That shortcut is unsafe for the current publication model.

## Decision

Extend the offline daily chain with exactly one `build_serving_bundle` action.
It is eligible only after the active Dashboard Snapshot pointer exactly equals
the reviewed Plan 2.4 pointer and the immutable target formally rereads.

The action:

- accepts an explicit UTC build time and a new direct child of `/tmp` as its
  candidate root;
- builds from the exact active Snapshot target and uses the Snapshot release ID
  as the bundle release ID;
- requires Dell `hui`, the source-of-truth `main` repository, a clean tree, and
  a release suffix matching the full source commit;
- records the source commit, Snapshot aggregate and manifest SHA-256 values,
  Market Intelligence identity, contracts, locale policy, role-free guest/
  credential parity, and prohibited-content flags in a deterministic manifest;
- inventories every regular file, rejects symlinks, source maps, unexpected
  top-level entries, unchecksummed files, partial staging, and changed source
  Snapshot bytes; and
- formally rereads the completed bundle before the journal can record success.

The builder's legacy `--snapshot-release` shortcut is removed. All builds must
name the exact immutable absolute `--snapshot-path`. The default manual local
bundle root remains available, while the daily action must use its explicit
`/tmp` candidate root.

After success the planner stops at `review_bundle_deployment`. Local bundle
construction is not OCI deployment and grants no upload, remote preflight,
switch, reload, rollback, credential, network, `/data`, or scheduler authority.
OCI deployment remains a later, separately authorized one-shot boundary.

## Consequences

- One daily transition can now prove the exact serving artifact without
  touching OCI.
- Build interruption is classified through the existing offline journal; an
  absent cleaned candidate can be retried explicitly, while partial or changed
  state blocks.
- A source change after Snapshot creation intentionally prevents constructing
  a differently versioned UI under the old Snapshot release identity.
- Historical bundles remain readable by the existing context report, but only
  the new contract is eligible for this daily custody step.

## Alternatives Considered

### Let deployment build the frontend remotely or immediately before upload

Rejected because construction and remote mutation would become one ambiguous
custody boundary and OCI would cease to be a lightweight serving target.

### Keep the legacy release-name shortcut

Rejected because the same release syntax can resolve two different storage
namespaces and can silently select obsolete repository output.

### Treat checksum success as deployment authorization

Rejected because artifact integrity does not authorize a network connection or
Production state change.
