# Historical Inactive Lifecycle Corroboration Plan V1

Contract: `historical-inactive-lifecycle-corroboration-plan/1.0`.

This is a temporary, owner-only work plan for the complete
`review_candidate` subset of one formally validated inactive-lifecycle
resolution shadow. It is not Instrument Lifecycle, Corporate Action, or
Historical Coverage data.

## Inputs and identity

- one exact shadow anchor, manifest SHA-256, and logical fingerprint;
- one source-observation fingerprint and one full shadow-decision fingerprint
  per candidate; and
- canonical `instrument_id` as the only positive subject identity.

Ticker, name, and provider stable-ID values are not copied into the plan.
Provider primary exchange is retained only to route later source review and
cannot establish lifecycle eligibility.

## Required evidence

Every work item requires all five scopes:

1. effective-date corroboration;
2. last tradable session;
3. source-availability semantics;
4. successor and consideration applicability; and
5. terminal classification.

The existing canonical EOD terminal path is an explicit future cross-check.
The last observed bar must not automatically be labelled the last tradable
session.

XNAS candidates use `nasdaq_daily_list_pilot_required`. This means only that a
documented source candidate exists and needs a bounded representative pilot;
it is not a source selection or sufficiency conclusion. ARCX, BATS, XASE, and
XNYS candidates use `all_exchange_source_selection_required` until an exact
composition is reviewed.

## Knowledge-time boundary

All current work items are `first_observed_only`; `source_available_at` is
null and point-in-time eligibility is false. Presence of provider
`last_updated_utc` is retained as a Boolean only, under
`unverified_not_source_availability` semantics. It cannot be used as a signal
cutoff until the source documents and a review validates its meaning.

## Physical and authority boundary

- one canonical JSON document below `/tmp`;
- owner-owned file mode `0400`;
- atomic no-clobber creation and formal reread by SHA-256 plus logical
  fingerprint;
- no source requests, `/data` writes, analytics, publication, deployment, or
  scheduler changes; and
- no acquisition, canonical lifecycle, Historical Coverage, or performance
  authority.

See [ADR 0167](../decisions/0167-plan-inactive-lifecycle-corroboration-without-promotion.md).
