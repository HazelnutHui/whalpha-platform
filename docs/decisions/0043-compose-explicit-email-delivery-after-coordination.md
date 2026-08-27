# ADR 0043: Compose Explicit Email Delivery After Coordination

## Status

Accepted

## Date

2026-08-27

## Context

ADR 0039 can emit an alert intent, ADR 0040 can custody one attempt, and ADR
0041 can deliver through SMTP, but these boundaries were available only as
libraries. A future one-transition runner needs an explicit composition point
without making email implicit, weakening the coordinator's network guard, or
claiming that a normal no-alert state delivered anything.

## Decision

Extend the existing one-transition CLI with `--deliver-alert-email`. The flag
is invalid unless `--emit-alert-intent` is also present and exact whole-file
SHA pins are supplied for absolute external Host Runtime and email config
paths. Host and email config directories, and provider and SMTP credential
directories, must be separate and non-overlapping. The email config must be
enabled and match the verified Dell host, clean source revision, repository,
canonical data root, daily run root, and configured alert root.

Loading the delivery capability performs no credential access or network
operation. The coordinator still runs inside its existing network boundary:
without explicitly enabled data capabilities, sockets remain prohibited even
when email delivery was requested. Only after the coordinator returns a formal
result does the CLI create the deterministic ADR 0039 intent. If the intent is
non-null, it calls ADR 0040 custody with the ADR 0041 capability outside that
coordinator network boundary.

A normal state returns `alert_intent=null` and `alert_delivery=null`; it does
not load SMTP credentials, create an alert journal, or send. A delivered or
already-delivered result is included as `alert_delivery`. A known pre-request
failure is included as `failed` and makes the command exit nonzero. An SMTP
exception after `delivery_started` returns a redacted rejected envelope with
`alert_delivery_outcome_formally_known=false` while retaining the already-known
coordinator status and request/write counts; the immutable journal then
prohibits automatic replay.

This explicit composition does not grant scheduler, publication, Snapshot,
bundle, deployment, provider, canonical-write, or retry authority. Repository
tests use a temporary owner-only alert root, synthetic credentials in memory,
and a fake sender. No external config, credential, real email, service, timer,
or scheduler is created or invoked by this decision.

## Consequences

- The existing one-transition command now has a complete but default-off path
  from coordinator evidence to an at-most-once email attempt.
- Email cannot run merely because config exists; invocation must opt in with
  both exact external SHA pins and intent emission.
- Data coordination remains socket-guarded independently from the later SMTP
  boundary.
- A normal session has zero SMTP credential access and zero alert-journal
  writes even when delivery was explicitly requested.
- Pre-coordinator CLI exceptions still lack a formal alert intent; watchdog
  coverage remains separate work before unattended scheduling.

## Alternatives Considered

### Send from inside the coordinator

Rejected because notification is not a data transition and would mix network,
retry, and alert custody with provider/Apply/offline action state.

### Enable email whenever an email config exists

Rejected because existence is not operational authorization and would break
the default-deny command contract.

### Run SMTP inside the coordinator socket boundary

Rejected because enabling email would either block the intended SMTP call or
unnecessarily permit networking throughout otherwise network-free planning.

### Retry a failed or ambiguous email automatically

Rejected by ADR 0040's at-most-once policy.
