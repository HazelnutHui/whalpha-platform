# ADR 0045: Retain Safe Provider Failure Evidence

## Status

Accepted

## Date

2026-08-27

## Context

The first controlled 2026-08-27 EOD fetch made exactly one provider request
and received a non-404/non-429 HTTP failure. The authorized capability mapped
that response to `permanent_failure`, but acquisition custody retained neither
the safe numeric HTTP status nor the request count for a failed package. Raw
response bodies are deliberately discarded, so the exact cause could not be
reconciled without an unauthorized repeat request.

Massive's current public plan information describes Stocks Basic as end-of-day
and paid Stocks tiers as 15-minute delayed or real-time. Therefore the
provisional 30-minute post-close boundary is only a first review time; it is
not evidence that current-session EOD is entitled or complete for the active
plan.

## Decision

Advance acquisition custody to `daily-eod-acquisition-custody/1.1` and allow
authorized capabilities to retain two bounded, non-sensitive failure fields:

- the exact request count already enforced by the operation limit; and
- the numeric HTTP status for redirect/client-response failures.

The custody boundary validates that the request count fits the exact Identity
or EOD scope and that HTTP 404, 429, or other 3xx/4xx status agrees with the
formal `not_ready`, `rate_limited`, or `permanent_failure` outcome. It never
stores the response body, request URL, headers, request ID, credential details,
or provider message.

This change is observational only. It does not reclassify 403 or another
client response as retryable, change the readiness window, authorize a retry,
or infer the user's plan entitlement. A permanent failure still blocks and
requires operator diagnosis.

## Consequences

- Future provider failures can be distinguished without replaying a request.
- Request-count custody remains complete even when no package is produced.
- The 2026-08-27 failure remains status-unknown; it must not be retroactively
  labeled from later evidence.
- A separate decision is required before making readiness plan-tier-aware or
  authorizing another EOD attempt.

## Alternatives Considered

### Retain the response body

Rejected because it may contain provider-specific or sensitive information and
is unnecessary for first-line diagnosis.

### Treat every same-day 403 as not ready

Rejected because 403 may also mean invalid entitlement or another permanent
authorization problem.

### Repeat the failed request only to observe the status

Rejected because the existing terminal explicitly requires diagnosis and the
original request is not safely replayable.
