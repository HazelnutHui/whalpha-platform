# ADR 0031: Separate Market Close from Provider Readiness

## Status

Accepted

## Date

2026-08-27

## Context

The XNYS calendar proves when a cash-equity session closed, including early
closes and daylight-saving changes. It does not prove when a provider's
whole-market EOD response is available or final. Massive documents Stocks
Basic as end-of-day and includes [Daily Market Summary](https://massive.com/docs/rest/stocks/aggregates/daily-market-summary)
in all Stocks plans, but does not publish a guaranteed minute at which Grouped
Daily becomes stable. Its explanation of [late aggregate bars](https://massive.com/knowledge-base/article/why-am-i-receiving-a-late-aggregate-bar-through-massives-websockets)
also says late trades can continue to update daily aggregates.

Treating the exchange close as provider readiness would create false
completeness. Unlimited polling would create a different failure: silent
provider pressure, unbounded retries, and no missed-session escalation.

## Decision

Add the credential-free contract `daily-eod-readiness-plan/1.0`. It is a pure
decision layer and makes zero external requests and zero Production writes.
It accepts one exact target, the latest canonical session, one acquisition
preparation action, a timezone-aware observation time, and explicit prior
attempt outcomes.

The target must be the oldest missing XNYS session. The policy uses the
exchange's actual UTC close and applies:

- a provisional 30-minute post-close stabilization window before the first
  fetch-authorization review;
- at most five attempts;
- retry delays of 15, 30, 60, and 120 minutes;
- a six-hour same-day deadline;
- a bounded provider `Retry-After` override of at most four hours; and
- immediate diagnosis for permanent, schema/quality, malformed-history, or
  exhausted-attempt failures.

Thirty minutes is an operational first-review point, not a provider
completeness guarantee. Every plan therefore records
`provider_completeness_asserted=false`.

`not_ready`, rate-limit, and transient outcomes may produce a future review
time. A completed fetch package advances only to separate canonical-apply
review. The plan never fetches, applies, calculates, publishes, deploys, sends
an alert, or enables a scheduler. A passed same-day deadline produces a
visible missed-session recovery state and retains oldest-session-first order.

Attempt evidence must be chronological, start after the stabilization window,
respect prior backoff, contain bounded `Retry-After` only for rate limits, and
stop after a terminal outcome. The policy and decision each have deterministic
fingerprints.

## Consequences

- Early closes and daylight-saving changes come from the XNYS schedule rather
  than fixed UTC assumptions.
- A timer can later wake this planner without inheriting authorization to call
  the provider.
- A delayed or revising provider response becomes a bounded operational state,
  not a claim that the market session was incomplete.
- Multiple missing sessions are repaired chronologically so verified-prior
  analytics cannot skip a state transition.
- The 30-minute and retry schedule are explicit provisional parameters that
  should be recalibrated from real non-sensitive operation timing evidence.
- Durable acquisition-attempt custody, actual alert delivery, provider fetch
  and canonical-apply standing authorization, and scheduler activation remain
  separate work.

## Alternatives Considered

### Fetch exactly at the exchange close

Rejected because exchange close does not prove provider EOD readiness or
stability.

### Wait until a fixed late-night time

Rejected because it adds avoidable latency and still does not prove provider
completeness.

### Retry indefinitely until data appears

Rejected because it hides incidents and creates an unbounded external-request
policy.

### Skip an older missing session and process the newest date

Rejected because Phase 1b and Candidate require verified-prior chronological
state.
