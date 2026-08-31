# ADR 0107: Reserve Holdout Before Evaluation

## Status

Accepted

## Date

2026-08-31

## Context

The fixture statistics contract exposes only the development-locked parameter
in holdout after validation passes, but `holdout_consumed=true` exists only
inside one returned report. Repeating the process can evaluate the same fixture
again. This is explicit and harmless while no real research path exists, but it
is not adequate custody for a future untouched holdout.

## Decision

Add `candidate-strategy-holdout-custody/1.0` as an external, durable,
fail-closed seam around a future holdout evaluation capability.

The custody identity binds the experiment, mechanics batch, passed validation
report, immutable parameter lock and selected combination. Under one
owner-controlled root and nonblocking lock, custody writes an immutable
`holdout_reserved` event before invoking the capability. It may then append
exactly one `holdout_completed` or `holdout_failed` event. Events are
permission-checked, fingerprinted and chained.

Any reservation without a terminal event has an unknown outcome and is never
replayed. A recorded failure is also never replayed. A completed identity is
reread as `already_consumed` without invoking the capability. Binding drift,
invalid evidence, extra files, permission drift, symlinks and event-chain
tampering fail closed.

Custody roots may not overlap Git or `/data`. The implementation has no CLI,
default root, canonical adapter, real label input, network access or Production
writer. Fixture integration proves the one-use mechanics only. The existing
fixture evaluator remains explicitly non-authoritative; any future real
holdout path must be accessible only through this custody boundary or its
separately reviewed successor.

## Consequences

- A crash cannot silently turn an inspected holdout into another tuning set.
- A valid completed result can be identified and reread without reevaluation.
- This closes the durable reservation mechanism, not the real-data readiness,
  inferential-Oracle or research-activation gaps.
- Custody grants neither stage-transition nor performance-claim authority.

## Alternatives Considered

### Write `holdout_consumed=true` only in the result

Rejected because a crash can occur after inspection but before the result is
durably retained.

### Permit an operator to retry an interrupted evaluation

Rejected because the system cannot prove whether the holdout was already
observed before interruption.
