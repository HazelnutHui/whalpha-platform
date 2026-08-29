# ADR 0073: Custody One OCI Dashboard Deployment

## Status

Accepted

## Date

2026-08-29

## Context

ADR 0072 ends the daily chain with a formally reread Dell-local Serving Bundle.
The existing OCI script performs extensive checks, but it combines remote
preflight, upload, activation, service changes, and postflight in one textual
command. The coordinator therefore cannot bind an approval to an exact remote
pre-state, independently prove the post-state, or classify an interruption
without risking a replay.

## Decision

Add one separately enabled OCI deployment transition after
`review_bundle_deployment`.

The transition requires:

- the exact Serving Bundle 1.0 path, logical fingerprint, manifest SHA-256,
  checksum-inventory SHA-256, release ID, and source revision;
- an owner-controlled external deployment config, pinned by its exact file
  SHA-256, that names Dell `hui`, `main`, the clean implementation revision,
  the fixed `whalpha-oci` alias, and the reviewed scripts;
- a fresh structured read-only remote-state report whose fingerprint and
  current release equal the explicit approval;
- a durable `oci_deployment_started` reservation before the first remote
  mutation; and
- an independent post-deployment inspection proving the exact current release,
  local/remote manifest and checksum identities, healthy Nginx and Session Auth
  services, localhost-only Auth binding, protected routes, role-free guest
  access, and absence of staging, failed-release, or unexpected-listener
  residue.

The existing deployer gains an explicit bundle path and expected-current-
release guard. It repeats that guard in the remote mutation session immediately
before creating the new release. The deployment capability remains absent by
default and executes exactly three bounded external control operations: inspect
pre-state, apply once, inspect post-state. It never accepts a password or reads
credential content.

Recovery performs one read-only remote inspection and never invokes Apply. It
records:

- recovered success only when the exact target post-state is independently
  proven;
- recovered not completed only when the exact approved pre-state remains and
  no target, staging, or failed residue exists; or
- recovery blocked for every partial, changed, unhealthy, or ambiguous state.

Scheduler enablement, automatic retry, rollback, release cleanup, public-DNS
changes, password rotation, and credential-login testing remain separate and
unauthorized.

## Consequences

- A deployment is no longer accepted merely because the deploy command exits
  zero.
- An interrupted process cannot silently redeploy or overwrite a changed
  Production state.
- Recovery needs one explicitly enabled network-reading capability, but reports
  zero remote writes and `action_replayed=false`.
- A new source commit invalidates a previously prepared external deployment
  config and requires explicit review and repinning.

## Alternatives Considered

### Parse the old deployer's human-readable output

Rejected because text output is not a stable state contract and cannot prove
what remained active after an interrupted connection.

### Retry deployment when the outcome is unknown

Rejected because the first attempt may already have switched the current
release or changed services.

### Treat the local bundle fingerprint as deployment approval

Rejected because artifact integrity neither proves remote preconditions nor
authorizes a Production mutation.
