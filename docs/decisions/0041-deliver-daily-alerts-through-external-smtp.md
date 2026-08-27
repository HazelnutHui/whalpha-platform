# ADR 0041: Deliver Daily Alerts Through External SMTP

## Status

Accepted

## Date

2026-08-27

## Context

ADR 0039 defines deterministic alert content and ADR 0040 owns at-most-once
delivery custody, but neither decision provides a channel. Email is sufficient
for the first personal operational alert and avoids introducing a notification
vendor SDK. SMTP nevertheless crosses a credential and network boundary: a
connection may fail after the server has accepted some or all recipients, and
configuration must not silently install a sender or broaden daily automation.

## Decision

Add `daily-eod-email-transport-config/1.0` and one SMTP capability behind ADR
0040. The external canonical JSON configuration is whole-file SHA-pinned,
owner-read-only `0400`, beneath an owner-only `0700` directory outside Git and
canonical `/data`. Absence or `enabled=false` means no delivery. Configuration
binds the exact Dell host, clean verified source revision, repository, data,
run and alert roots, sender, one to five recipients, SMTP endpoint, credential
path, timeout, and channel. It grants no scheduling, publication, or deployment
authority.

Only verified TLS modes are accepted: implicit TLS on port 465 or STARTTLS on
port 587. The separate credential file contains exactly
`TIP_SMTP_USERNAME` and `TIP_SMTP_PASSWORD`, is owner-read-only beneath an
owner-only directory, and is loaded only during an explicitly custodied
delivery attempt. Config review does not read or inspect that file. Secrets do
not enter message content, object representation, evidence, journal events, or
error text.

The adapter renders one deterministic bilingual operational message from the
formal intent. It includes session, severity, category, coordinator status,
next action, reason codes and deduplication key, plus an explicit statement
that it is not a trading recommendation. A stable Message-ID and exact
deduplication header support human/provider investigation. From/To headers are
added only from the validated external config, and Date records the actual
UTC delivery-attempt time rather than altering logical alert identity.

Credential/configuration rejection before an SMTP call returns known failure
with zero external requests. Once the SMTP sender is invoked, any exception or
partial recipient acceptance is an unknown outcome: it propagates so ADR 0040
keeps only `delivery_started` and prohibits automatic replay. Complete SMTP
acceptance returns one logical external delivery transaction and a SHA-256
fingerprint of the stable Message-ID; no raw SMTP receipt is persisted.

This decision installs only repository code and synthetic tests. It creates no
external config, credential, alert root, command, service, timer, network
request, or real email.

## Consequences

- Email can later be enabled without committing credentials or changing the
  channel-neutral alert contract.
- Runtime, path, TLS, recipient and revision drift fail closed before sending.
- SMTP does not provide a portable provider idempotency API; ADR 0040 therefore
  retains conservative at-most-once behavior after ambiguous results.
- A known pre-request failure also requires operator review because custody
  deliberately has no automatic retry policy.
- Provisioning, a controlled rehearsal, scheduler integration and any
  escalation channel remain separate decisions and authorizations.

## Alternatives Considered

### Store SMTP settings or credentials in Git

Rejected because it would expose secrets and let a repository change silently
alter a live notification destination.

### Treat all SMTP exceptions as safe to retry

Rejected because a disconnect can occur after message or partial-recipient
acceptance.

### Use a provider-specific email API first

Deferred because it would add a vendor contract without improving the current
single-user requirement. A future provider with status lookup or native
idempotency may be added behind the same custody port.

### Enable a scheduler with the adapter

Rejected because notification transport, real one-transition rehearsal,
publication/deployment authority, and unattended scheduling require separate
review.
