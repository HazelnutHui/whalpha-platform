# ADR 0059: Authorize a Second Exact Stale Review

## Status

Accepted

## Date

2026-08-28

## Context

Snapshot 1.9 / Dashboard 2.6 and its Candidate strategy-channel workspace are
ready for Production UI review, but canonical EOD remains at 2026-08-26 while
the formal XNYS calendar expects 2026-08-27. The original
`production-review-deployment/1.0` exception is deliberately bound only to
2026-08-24 and cannot authorize this release. Replacing its constants would
also make the historical review release unreadable.

After the lag and alternatives were disclosed, the user supplied the exact
acknowledgement `I_ACKNOWLEDGE_2026_08_26_STALE_REVIEW_LAG_1` and requested the
formal deployment for visual review.

## Decision

Add `production-review-deployment/1.1` as a second, non-general authorization.
It is valid only when every field matches:

- approved analysis and actual session: `2026-08-26`;
- expected latest completed session: `2026-08-27`;
- freshness: stale by exactly one completed session; and
- the exact acknowledgement above.

Version 1.0 remains readable and unchanged. Backend payloads, manifests,
references, pointers, approval plans, Snapshot validation, and apply-time
freshness gates accept a discriminated union of only versions 1.0 and 1.1.
The browser independently accepts only the two complete version/date/token
bindings. Version mixing, unknown versions, changed dates, changed lag, changed
acknowledgement, or a freshness transition fail closed.

This authorization covers the exact MI 1.2 and Snapshot 1.9 review publication
needed for the requested deployment. It does not authorize provider fetching,
EOD/Identity mutation, formula tuning, performance claims, a generic stale
mode, or any future stale release. OCI deployment still requires its own exact
bundle and postflight checks.

## Consequences

- Production may visibly serve `stale_review` data as of 2026-08-26 for the
  requested UI review while never claiming ordinary freshness.
- The old 2026-08-24 release remains rollback-readable.
- If EOD freshness, the active data pointers, source audits, Git revision, or
  approval artifacts change during the flow, new plans are required.
- A later fresh 2026-08-27 release should replace this review release through
  the ordinary lag-zero path.

## Alternatives Considered

### Reuse or edit version 1.0

Rejected because it violates the exact authorization and breaks historical
read compatibility.

### Add a generic `allow-stale` flag

Rejected because it would silently authorize future dates and unknown lag.

### Deploy the new frontend against Snapshot 1.7

Rejected because Snapshot 1.7 has no strategy product, so the requested UI
cannot be reviewed through that bundle.
