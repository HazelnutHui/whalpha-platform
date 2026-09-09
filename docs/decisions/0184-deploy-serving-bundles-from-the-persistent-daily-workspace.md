# ADR 0184: Deploy Serving Bundles from the Persistent Daily Workspace

## Status

Accepted

## Date

2026-09-09

## Context

ADR 0180 introduced a bounded offline runner and ADR 0181 retained daily data
custody below the owner-only persistent session workspace. The same workspace
also assigns an exact `serving-bundle/<release>` path. Bundle construction and
the daily planner accepted that path, but the OCI deployment capability and
deployment custody still required the historical `/tmp/<bundle-root>/<release>`
layout. A completed persistent bundle therefore stopped before remote
reservation even though its manifest, checksums, source revision, Snapshot,
and automation-plan bindings were valid.

## Decision

OCI deployment approval and custody accept exactly two Serving Bundle modes:

- the existing direct `/tmp/<bundle-root>/<release>` layout for controlled
  legacy compatibility; or
- one exact release below the owner-only persistent
  `daily-eod/sessions/session_date=YYYY-MM-DD/serving-bundle` root.

The persistent path must match the coordinator target session, remain outside
Git, `/tmp`, and `/data`, have an owner-controlled `0700` workspace/session and
Serving Bundle root, and contain no symlink component. The existing formal
Serving Bundle reader still verifies the release manifest, checksums, logical
fingerprint, source revision, contracts, locales, guest/credential parity, and
prohibited-content flags before any remote inspection or reservation.

The deployment capability, custody layer, and reviewed shell entrypoint use one
shared path validator.
Remote-state CAS, exact current release, immutable deployment reservation,
no-replay recovery, one-shot runtime configuration, and independent postflight
are unchanged. This decision grants no deployment, rollback, scheduler,
credential, or unrelated filesystem authority.

## Consequences

- A daily run can retain its final bundle through restart and deploy it without
  copying governed evidence back into `/tmp`.
- The deployment event remains in the same persistent session journal as the
  preceding analytics and bundle actions.
- Historical `/tmp` deployment evidence and controlled one-shot workflows stay
  compatible.
- Arbitrary persistent paths, cross-session bundles, custody drift, symlinks,
  Git paths, and `/data` paths continue to fail closed.

## Alternatives Considered

### Copy the bundle into `/tmp` before every deployment

Rejected because it duplicates a large immutable artifact, creates another
recovery identity, and loses the restart-safety gained by the persistent
workspace.

### Deploy directly without deployment custody

Rejected because it would discard exact remote-state CAS, durable reservation,
and no-replay recovery at the only remote write boundary.
