# ADR 0053: Separate Historical Pilot Approval Review from Authorization

## Status

Accepted

## Date

2026-08-28

## Context

The credential-free historical pilot planner can calculate a bounded request
scope, but a mechanically valid plan does not prove provider permission,
account entitlement, current Dell inventory, or lifecycle-source adequacy.
Presenting a plan fingerprint as an authorization would collapse technical,
source, and human gates and make accidental execution more likely.

The first pilot should extend the existing contiguous history at its boundary,
not select attractive or convenient dates after seeing results.

## Decision

Adopt `historical-research-pilot-approval-review/1.1` as a pure, in-memory
review package between planning and any future authorization capability.

The review binds:

- exact implementation revision;
- exact pilot-plan and inventory fingerprints;
- Data Record Governance V1 registry and equal-capability access-policy
  fingerprints plus the Source Permission Governance V1 policy fingerprint;
- exact target sessions, endpoint classes, scopes, parameters, page limits,
  request ceiling, retry zero, and serial-only behavior;
- synthetic action-mapping and adjustment-invariant evidence;
- the required `/tmp` package and separate Apply boundary; and
- three caller-supplied external gates: live account endpoint entitlement,
  exact current inventory, and lifecycle-source coverage; and
- one mechanically derived equal-capability source-permission gate.

The source-permission gate cannot be hand-authored. It requires exact current
assessments for `eod_price_bar`, `point_in_time_identity`, and
`corporate_action_source_observation`, all bound to one source and one official
review. Each family must assess all six Source Permission Governance uses:
Dell acquisition, raw retention, derived analysis, equal-capability raw and
derived display, and machine delivery. The assessment time must equal the
approval-review time. Blocked, unresolved, stale, unsupported, partial-use,
cross-source, or cross-review input fails closed.
The approval builder revalidates the bound review and recomputes every
assessment from its six conclusions; caller-supplied cleared assessments cannot
override a blocked review even if their outer fields are forged to match.

Satisfied external evidence is effective-dated and must still be valid at
review time. Inventory and live account entitlement are bounded to at most 24
hours, lifecycle-source review to 30 days, and equal-capability source-
permission review to 90 days. Expired evidence cannot produce an
acknowledgement string.

The result has only two states:

- `blocked`, with explicit unresolved gates; or
- `ready_for_exact_user_authorization_review`.

Neither state grants acquisition, Apply, publication, deployment, or scheduler
authority. The ready state may produce one exact acknowledgement string bound
to the complete review fingerprint, but the string is only a request for a
separate user decision. There is no historical fetch or Apply capability in
this ADR.

The deterministic date selector chooses the three XNYS sessions immediately
before a verified contiguous EOD inventory. For the documented 29-session
sequence beginning 2026-07-17, the candidate dates are 2026-07-14,
2026-07-15, and 2026-07-16. With three inactive-Identity anchors and no named
Ticker Events, the exact preliminary ceiling is 75 requests. The remaining
five-request allowance is not implicitly usable; adding targeted events
requires a regenerated plan and new binding.

## Consequences

- Technical readiness cannot conceal licensing or lifecycle gaps.
- A caller cannot convert a provider permission assertion into a satisfied
  gate without exact typed assessment evidence.
- A stale inventory fingerprint invalidates the exact review boundary.
- User acknowledgement cannot silently expand dates, tickers, endpoints,
  requests, retry, writes, or downstream publication.
- The initial window tests continuity against the retained boundary and avoids
  outcome-driven date selection.
- Current evidence remains blocked; no acknowledgement string is emitted until
  every external gate is satisfied.

## Alternatives Considered

### Treat the planner output as authorization

Rejected because planning is intentionally default-deny and cannot establish
external permission or entitlement.

### Use a generic “proceed” confirmation

Rejected because it would not bind exact dates, implementation, inventory,
source policy, or request scope.

### Reserve five unspecified lifecycle requests inside an authorization

Rejected because unnamed ticker scopes are not auditable. A plan must be
regenerated after exact unresolved instruments are known.

## Non-Goals

- accessing credentials or account endpoints
- writing `/data` or `/tmp`
- executing a provider request
- creating an authorization artifact
- implementing fetch, Apply, publication, deployment, or scheduling
