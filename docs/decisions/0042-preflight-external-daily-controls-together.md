# ADR 0042: Preflight External Daily Controls Together

## Status

Accepted

## Date

2026-08-27

## Context

The daily control plane now has three separately governed external artifacts:
the ADR 0037 host-runtime config, ADR 0033 standing data authorization, and ADR
0041 email config. Each contract fails closed independently, but reviewing them
one at a time could miss a cross-artifact revision, path, policy, SHA, or
credential-custody mismatch. Attempting the first provider request or email is
too late to discover such installation drift.

## Decision

Add `daily-eod-external-control-preflight/1.0` and a read-only administrator
entry point. It reads the three canonical owner-only config artifacts only when
their exact whole-file SHA-256 values are supplied independently. It verifies
the actual Dell hostname, executing source checkout, clean Git revision, and
readiness-policy fingerprint through the existing host-runtime boundary.

The preflight then requires:

- the same Dell host, implementation revision, repository, canonical data root,
  daily run root, and readiness policy across all applicable artifacts;
- the host config's authorization path and SHA to exactly match the separately
  supplied authorization artifact;
- all four bounded Identity/EOD fetch/apply operations to be currently active;
- host capabilities and email transport to be explicitly enabled in the
  reviewed artifacts;
- distinct, non-nested control-artifact directories outside repository, data,
  run, and alert roots; and
- distinct, non-overlapping Massive and SMTP credential directories, also
  separated from every protected/config root.

The command installs a socket guard for its complete lifetime. It does not
read, stat, hash, or print either credential file; does not require the run or
alert root to exist; verifies Git with optional locking disabled; and performs
no filesystem or Production write. Its
successful status is only `configuration_consistent`. The result explicitly
records zero credential-file accesses, network requests, filesystem writes,
and Production writes, while keeping controlled rehearsal, publication,
deployment, and scheduler authorization false.

This repository slice creates no external artifact, credential, directory,
provider request, email, transition, service, timer, or scheduler state.

## Consequences

- Cross-artifact drift is detected before any side-effecting capability is
  installed or called.
- Operators can review a bounded, non-secret report without exposing SMTP or
  Massive credential paths or values.
- A successful preflight is necessary but not sufficient for a controlled
  rehearsal; explicit rehearsal authority and exact transition inputs remain
  separate.
- Because implementation revision is exact, every subsequent code commit
  requires regenerated and re-reviewed external artifacts before preflight can
  succeed.
- Filesystem custody of future real run/alert roots and actual credential
  availability remain later provisioning checks, not claims of this config-
  only command.

## Alternatives Considered

### Validate each artifact only when its capability runs

Rejected because a mismatch would be discovered after custody reservation and,
for transport failures, could leave an ambiguous attempt.

### Include credential metadata in preflight

Rejected because config reconciliation does not need secret-file access. That
access should occur only at the separately authorized capability boundary.

### Treat successful preflight as scheduler authorization

Rejected because proving configuration consistency does not authorize a
provider request, canonical write, notification, publication, deployment, or
unattended wake-up.
