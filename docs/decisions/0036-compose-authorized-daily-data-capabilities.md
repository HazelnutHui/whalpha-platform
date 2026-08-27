# ADR 0036: Compose Authorized Daily Data Capabilities

## Status

Accepted

## Date

2026-08-27

## Context

The coordinator, standing authorization, acquisition custody, canonical-Apply
custody, and Massive fetch/apply boundaries were individually implemented, but
no executable capability composed them. Directly wiring the existing commands
would omit exact authorization evidence, interruption semantics, or actual
Identity pagination request counts.

Integration review also found three pre-activation contract conflicts: the
standing authorization used `/data` instead of the approved canonical root
`/data/trading-intelligence-platform`; Apply authorization still named a
completed acquisition event instead of the new Apply reservation; and the
coordinator treated a paginated Identity fetch as exactly one HTTP request.

## Decision

Add `daily-eod-authorized-capabilities/1.0` as an explicitly installed pair of
fetch and Apply callables. Construction performs no file, credential, network,
or canonical-data I/O. An invocation:

1. validates the exact coordinator context;
2. formally rereads the externally provisioned authorization and its external
   whole-file SHA pin;
3. preflights expiry, operation, host, provider, paths, implementation revision,
   and readiness-policy fingerprint before creating a custody start;
4. reserves the exact acquisition or canonical-Apply attempt, including the
   authorization file/content fingerprints;
5. authorizes a request bound to that new start event;
6. only then loads the Massive credential and fetches, or executes the approved
   canonical Apply; and
7. records the authorization-decision fingerprint in a formally proven terminal
   event.

The authorized-transition request advances additively to 1.1. Fetch requests
bind `acquisition_started`; Apply requests bind `canonical_apply_started` plus
the completed package hashes, approved-plan SHA, and expected-state fingerprint.
The approved data root is the project canonical root, not its `/data` parent.

The coordinator advances to 1.1. A successful Identity fetch may report 1–20
actual HTTP requests; EOD must report exactly one. The adapter wraps the
transport per invocation so successful and recognized failed requests retain
the actual count. This is an HTTP request count, not merely a logical task count.

Known 404, 429, transport, credential, and quality outcomes use the existing
bounded acquisition outcomes. Unexpected fetch exceptions leave the start
unresolved. Any Apply exception or failed formal postcondition leaves the Apply
start unresolved and requires no-write recovery; Apply is never replayed by the
adapter.

The adapters remain absent from the coordinator unless explicitly supplied.
This implementation adds no CLI, active authorization, host SHA pin, credential
read, provider request, `/data` write, publication, deployment, scheduler, or
notification delivery.

## Consequences

- Authorization, custody, execution, and formal result evidence now form one
  exact chain without moving authority into the coordinator.
- Obvious expired or mismatched grants do not consume an acquisition attempt or
  touch credentials.
- A crash after reservation remains detectable and cannot silently retry a
  provider request or canonical Apply.
- Identity pagination is no longer underreported as one external request.
- Operational installation, external authorization provisioning, alerting,
  rehearsal, and scheduler activation remain separate reviewed work.

## Alternatives Considered

### Call existing fetch/apply commands directly from the coordinator

Rejected because command success alone does not bind the standing grant,
custody event, exact request count, or interruption recovery.

### Read the credential before authorization preflight

Rejected because expired, revoked, or mismatched authority must fail without
touching credential custody.

### Report one logical fetch regardless of Identity pagination

Rejected because the field is an external HTTP request count and must remain
factually accurate.
