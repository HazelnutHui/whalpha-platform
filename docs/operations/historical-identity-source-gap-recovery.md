# Historical Identity Source Gap Recovery

## Purpose

Recover an explicit set of missing historical Massive Identity reference
packages without changing canonical data. This is a source-custody operation,
not an Identity/EOD replay.

## Guarded entrypoint

Use `scripts/admin/fetch-historical-identity-source-gaps.sh` from a clean Dell
repository revision. Supply the approved canonical root, a new or resumable
owner-only package root below `/tmp`, and each exact date with a repeated
`--session-date` argument. `--execute` is mandatory.

The command preflights the complete date set before requesting data. It then
uses one serial 15-second limiter for all reference pages and emits one safe
checkpoint after each formally reread package. An interruption can be resumed
with the same arguments and package root; exact completed packages are reread
and reused.

## Hard boundaries

- Maximum 24 unique ascending historical dates.
- Existing canonical EOD and same-day Identity are required.
- Existing canonical normalized source custody is rejected.
- Only the Massive reference Tickers endpoint is allowed.
- Package custody remains below `/tmp` with owner-only directories and
  read-only package files.
- No canonical data, normalized source custody, membership, analytics,
  publication, deployment, or scheduler state is written.
- Output is aggregate custody evidence only; source rows, response bodies,
  URLs, request identifiers, and secrets are not logged.

## Required next gates

1. Run exact reconstruction comparison under both governed profiles.
2. Require exactly one all-family match per session.
3. Bind each selected profile to package and canonical fingerprints.
4. Normalize into a separate `/tmp` candidate and formally reread it.
5. Build an incremental no-write Apply plan against the then-current canonical
   inventory.
6. Apply only the exact reviewed plan and perform a complete canonical
   postflight.

Nothing in the fetch result grants Historical Coverage, research readiness,
performance claims, or public serving authority.
