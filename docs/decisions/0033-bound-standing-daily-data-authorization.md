# ADR 0033: Bound Standing Daily Data Authorization

## Status

Accepted

## Date

2026-08-27

## Context

The daily planner, provider-attempt custody, and single-action offline executor
can prove one safe transition, but they deliberately do not authorize a Massive
request or a canonical `/data` apply. Requiring a new chat approval for every
normal session would prevent the desired unattended post-close update. Giving a
timer a broad shell or data-write permission would erase the existing safety
boundaries.

A durable authorization must also remain separate from code. A repository
change must not be able to silently grant itself provider or canonical-write
authority.

## Decision

Add contract `daily-eod-standing-authorization/1.0` for a reviewed canonical
authorization artifact. The artifact is not active by existence alone. Runtime
use must also receive its exact whole-file SHA-256 from separately activated
host configuration. The artifact is an owner-only immutable file in a
pre-provisioned directory outside Git and `/data`; neither the repository nor a
future coordinator may create or alter the active copy.

The first contract is limited to four operations:

1. exact-session Massive Identity fetch;
2. exact-session approved Identity canonical apply;
3. exact-session Massive grouped-daily fetch; and
4. exact-session approved EOD canonical apply.

It binds the Dell host, Massive provider, canonical data root, run-journal root,
exact implementation revision, ADR 0031 readiness-policy fingerprint, approval
time, effective interval, and a maximum validity of 90 days. Every runtime
transition additionally binds the oldest missing session, acquisition action,
custody attempt/event fingerprints, direct non-hidden `/tmp` package, and the
exact operation-specific evidence. Fetch requires an unresolved
`acquisition_started` reservation. Apply requires completed package hashes plus
the existing frozen approval-plan SHA and expected-current-state fingerprint.

The authorization always retains:

- one transition per invocation;
- no overwrite or skip-forward behavior;
- formal package custody and approved-plan checks;
- bounded provider attempts from the separately fingerprinted readiness policy;
- fail-closed expiry, revision, path, host, provider, scope, and hash checks; and
- a separately controlled revocation/stop boundary in the future coordinator.

Publication, Market Intelligence activation, Dashboard Snapshot, bundle,
deployment, rollback, Universe activation, SEC, intraday/options acquisition,
order execution, notification delivery, and scheduler activation are not in
this authorization. Offline analytics retain ADR 0030's already bounded
single-action executor and do not inherit provider or canonical-write access.

The repository implementation may build in-memory candidates and validate test
fixtures, but this decision does not create a real authorization directory,
authorization artifact, host SHA pin, provider request, canonical write, or
scheduler.

## Consequences

- Normal Identity/EOD acquisition and canonical apply can later run unattended
  without broadening authority to public-serving or trading operations.
- Authorization expires and any implementation change requires a newly reviewed
  artifact and host pin.
- Copying or editing an authorization file, or changing only its configured
  path, cannot satisfy the exact SHA and canonical-content checks.
- A future coordinator must derive requests from the formal journal and frozen
  package/plan readers; it cannot authorize arbitrary command arguments.
- Ninety days is a provisional maximum. A shorter first activation is allowed
  and operational evidence should inform later renewal policy.

## Alternatives Considered

### Treat scheduler activation as permission for every daily command

Rejected because waking a state machine is not authority to access a provider,
write canonical data, publish, or deploy.

### Commit an enabled authorization file to Git

Rejected because code changes would then control their own operational
authority and every checkout would inherit it.

### Use an indefinite authorization

Rejected because code, provider behavior, data contracts, and operating
assumptions can change without a forced review checkpoint.

### Require a manual approval for every normal session forever

Rejected as the target operating model, while remaining the default until an
external authorization artifact and host SHA pin are explicitly activated.
