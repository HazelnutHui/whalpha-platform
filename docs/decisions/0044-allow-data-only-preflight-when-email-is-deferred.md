# ADR 0044: Allow Data-Only Preflight When Email Is Deferred

## Status

Accepted

## Date

2026-08-27

## Context

ADR 0042 originally required Host Runtime, standing data authorization, and
email config together. The user has explicitly deferred SMTP setup. Requiring
an enabled email artifact would now block a supervised, no-email rehearsal of
the independent Identity/EOD data path, while silently treating a missing
email argument as optional would make preflight scope ambiguous.

## Decision

Advance the external-control preflight contract to
`daily-eod-external-control-preflight/1.1` and add one explicit CLI mode:
`--without-email`.

The default joint mode is unchanged and still requires exact email config and
SHA inputs. Data-only mode rejects all email arguments, never calls the email
config reader, and reports:

- `preflight_mode=daily_data_only`;
- null email config, email SHA, and alert-root fields;
- `email_transport_enabled=false`; and
- zero credential-file accesses, network requests, filesystem writes, and
  Production writes.

Data-only mode does not weaken the daily data boundary. It still requires an
enabled Host Runtime, all four exact Identity/EOD fetch/apply operations, an
active standing authorization, independently pinned canonical artifacts,
verified clean Dell revision and readiness policy, separated config/credential
custody, and matching repository/data/run roots.

As with joint mode, successful preflight grants no controlled rehearsal,
provider request, canonical write, publication, deployment, or scheduler
authority. Email can later be added only by returning to the explicit joint
mode; it cannot be inferred from a file appearing on disk.

## Consequences

- SMTP setup can remain deferred without blocking supervised validation of the
  data automation controls.
- Reports clearly distinguish data-only from data-and-email evidence.
- A scheduler cannot interpret data-only success as proof of an alert channel.
- Any future controlled Identity/EOD rehearsal still requires separately
  reviewed external artifacts, root provisioning, and explicit operational
  authorization.

## Alternatives Considered

### Keep email mandatory

Rejected because it couples an optional notification channel to the core data
path and contradicts the user's explicit deferral.

### Silently omit email when arguments are missing

Rejected because a typo or incomplete installation would appear as an
intentional data-only review.

### Disable all automation work until SMTP is configured

Rejected because supervised data rehearsal can safely produce useful evidence
without unattended scheduling or notification claims.
