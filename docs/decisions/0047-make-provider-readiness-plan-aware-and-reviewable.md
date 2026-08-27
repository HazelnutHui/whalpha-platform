# ADR 0047: Make Provider Readiness Plan-Aware and Reviewable

## Status

Accepted

## Date

2026-08-27

## Context

The first controlled 2026-08-27 Identity acquisition succeeded, while the
subsequent EOD request failed permanently. The numeric response status was not
retained by the then-active code. ADR 0045 preserves that safe evidence for
future failures, but it deliberately did not change retry policy.

The existing readiness policy used one provisional 30-minute post-close
review point for both reference Identity and Grouped Daily EOD. Massive
describes Stocks Basic as end-of-day, while higher tiers have delayed or
real-time recency. The provider does not document one guaranteed same-day
minute at which the Basic whole-market EOD response is available and final.
Consequently, a market-close delay alone cannot authorize a Basic EOD request.

The immutable journal also had no safe way to represent an operator's later
diagnosis. A permanent or quality failure therefore blocked forever unless
history was removed or code was bypassed, neither of which is acceptable.

## Decision

Advance readiness to `daily-eod-readiness-plan/1.1` and make the provider
recency profile explicit. The current default is
`massive_stocks_basic_end_of_day`. Identity keeps the provisional 30-minute
first-review boundary. A first current-session EOD request on the Basic profile
requires a separate immutable operator review with an explicit `not_before`
time; readiness does not invent a release minute or claim completeness.

Add `daily-eod-acquisition-operator-review/1.0`, advance acquisition custody to
`daily-eod-acquisition-custody/1.2`, and advance the shared journal to
`daily-eod-run-journal/1.3`. The reader remains compatible with immutable 1.2
events. A review is a standalone hash-chained event, not a replacement for the
failed attempt. It records only:

- the exact session and acquisition action;
- either initial Basic EOD availability review or one terminal-failure review;
- an allow-once-after or keep-blocked disposition;
- a bounded `not_before` time;
- a controlled diagnosis/evidence code;
- for terminal recovery, the exact failed terminal-event fingerprint; and
- zero request/write/scheduler/publication/deployment authority.

An allow-once review can release exactly the next bounded fetch-authorization
review. It does not itself load credentials, call the provider, reserve a
fetch, Apply data, or enable unattended execution. Standard attempt limits and
backoff remain in force. Package-ready outcomes can never be reopened. A
terminal failure without an exact review remains blocked.

The 2026-08-27 status-unknown EOD failure is not retroactively diagnosed. This
repository change invalidates the old exact-revision Host Runtime and standing
authorization. No review event is appended and no retry is authorized by this
decision.

## Consequences

- Plan/tier assumptions are visible in every readiness result and policy
  fingerprint.
- Stocks Basic current-session EOD fails closed until a human supplies a
  bounded review time; the code no longer treats 30 minutes as sufficient.
- Permanent history remains immutable while an independently auditable,
  single-use recovery decision becomes possible.
- Existing journal 1.2 evidence remains readable and hash-valid.
- A later scheduler can use the same state machine but cannot manufacture an
  operator review.
- Real retry, new external controls, scheduler installation, publication, and
  deployment remain separate approvals.

## Alternatives Considered

### Hard-code a later Basic release minute

Rejected because no provider guarantee supports one exact minute and a later
guess would still be a guess.

### Reclassify the old permanent failure as not ready

Rejected because its numeric status is unknown and later code cannot recreate
the original response.

### Delete the terminal journal event and start again

Rejected because it destroys the evidence needed to prevent duplicate or
unexplained provider requests.

### Let a retry flag bypass readiness

Rejected because an unbound flag is not durable, single-use, or tied to the
exact failed event.
