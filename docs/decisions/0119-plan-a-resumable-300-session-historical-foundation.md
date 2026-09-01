# ADR 0119: Plan a Resumable 300-Session Historical Foundation

## Status

Accepted

## Date

2026-09-01

## Context

The canonical Dell history contains 32 contiguous XNYS sessions through
2026-08-31. Research readiness requires at least 252 sessions and the user has
chosen an initial 300-session foundation so feature warm-up and outcome
maturity do not consume the entire minimum interval. Waiting for daily append
would delay research by many months.

The repository already has a three-session Historical Pilot plan, immutable
source-package custody, provider-neutral family contracts, and transitive
coverage validation. It does not have a bulk plan that fixes the complete date
range, partitions the work into resumable batches, or projects request, time,
and storage bounds. A shell loop around the daily workflow would bypass those
controls.

Massive endpoint access has been technically probed, but equal-capability data
permission and complete lifecycle/terminal coverage remain unresolved. The
inactive-security census also exceeded its six-page ceiling. A bulk plan must
not convert accessibility into acquisition authority or incomplete lifecycle
evidence into research readiness.

## Decision

Add a credential-free `historical-research-backfill-plan/1.0` boundary. It:

- requires a contiguous, formally supplied current EOD/Identity inventory;
- selects exactly 252 through 504 XNYS sessions ending at the current latest
  completed session, with 300 as the first operational target;
- subtracts existing sessions and divides the missing prefix into deterministic
  batches of at most three sessions;
- orders execution from the batch adjacent to current history backward so each
  completed Apply can extend one contiguous boundary;
- orders sessions inside each batch from newest to oldest for the same reason;
- identifies the first batch as the representative Pilot and keeps every later
  batch dependent on its formal completion;
- separately projects Grouped Daily calls and observed/ceiling active-Identity
  pagination, fixed serial transport time, and bounded canonical/staging bytes;
- carries unresolved source-permission, lifecycle/terminal, corporate-action,
  membership, adjustment, and Historical Coverage gates explicitly; and
- always reports acquisition, Apply, publication, deployment, scheduling, and
  performance authority as false.

Add a socket-guarded Dell CLI that formally rereads current canonical
EOD/Identity evidence and emits the exact 300-session plan without writing a
file. The plan is review evidence only. A later real adapter must still freeze
each authorized response into the existing provider-neutral source-package
boundary before any separate canonical Apply.

Provider requests remain serial at no faster than 15 seconds. Dell may use
bounded CPU parallelism only after immutable source packages exist. Backfilled
history is not published to OCI session by session.

## Consequences

- The first target is fixed at 300 sessions from 2025-06-23 through
  2026-08-31 when evaluated against the current 32-session inventory.
- The missing 268 sessions become deterministic, resumable batches rather than
  an unreviewed long-running loop.
- Request and duration estimates remain projections, not promises or provider
  completeness claims.
- No real request or `/data` write can occur through this planning boundary.
- The existing three-session Pilot remains the only eligible first live step,
  and it remains blocked until its external gates are resolved and separately
  authorized.
- Reaching 300 EOD/Identity sessions alone will not satisfy research readiness;
  daily membership, canonical actions, lifecycle, adjustment reconciliation,
  and a transitive Historical Coverage publication remain mandatory.

## Alternatives Considered

### Reuse the daily scheduler for historical dates

Rejected because the daily path is designed for the oldest missing current
session, not long-range source custody, lifecycle baselines, or resumable bulk
evidence.

### Download 268 EOD dates first and repair Identity later

Rejected because it would create a tempting but survivorship-unsafe research
panel and violate the accepted point-in-time foundation.

### Target exactly 252 sessions

Rejected for the first operating target because warm-up and forward outcomes
would leave too little margin. The contract minimum remains 252 and the
preferred later extension remains 504.
