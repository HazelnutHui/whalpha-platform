# ADR 0154: Prepare Daily Membership Outside the Serving Gate

## Status

Accepted

## Date

2026-09-07

## Context

ADR 0153 published the first canonical, signal-eligible Membership partition
for 2026-09-04. Its component services were safe but still required a
one-off temporary candidate workflow. Repeating that shape manually would risk
missing prospective sessions, losing interruption evidence, or accidentally
making research-data completion a prerequisite for the existing public
Dashboard.

The Membership Apply plan binds the complete `/data` inventory. Creating that
plan before later MI or Snapshot publication would make it stale when those
separate canonical writes complete. Candidate evaluation and canonical Apply
planning therefore have different operational clocks.

## Decision

Add a prospective daily Membership preparation boundary with these rules:

- it consumes only the exact same-session canonical EOD, canonical Identity,
  and directly observed normalized Identity source created by Daily Identity
  Plan 1.1;
- it keeps the V3 provider-form complete-base methodology unchanged;
- it writes only an immutable candidate below the exact owner-only daily
  workspace name `universe-membership-candidate`;
- it accepts explicit UTC evaluation and assessment times and immediately
  classifies next-open eligibility without a network request;
- it reuses an exact completed candidate and an exact canonical publication;
- it rejects physical-only or marker-only canonical state and directs it to
  ADR 0153's exact-plan recovery rather than rebuilding or deleting evidence;
- an outcome-only candidate remains retained evidence and cannot receive an
  Apply plan;
- canonical Apply planning remains a separate, near-Apply step after other
  expected `/data` writes are complete, so its inventory comparison is not
  knowingly invalidated by the serving chain.

The existing Membership plan path may now use the exact persistent daily
workspace name `universe-membership-plan.json` as well as governed temporary
custody. Persistent plan creation uses a fsynced staging file and atomic rename.

The preparation boundary is additive and reports
`website_pipeline_blocked=false`. It is not yet installed as a coordinator or
scheduler action. Live-session observation and explicit integration review
must occur before unattended execution. Canonical publication still uses the
separate ADR 0152/0153 plan, Apply, marker, reread, and recovery boundaries.

## Consequences

- A new daily session can preserve a contemporaneous candidate immediately
  after Identity and EOD are complete without changing `/data` or OCI.
- The current website can continue when the research sidecar is unavailable;
  the missing research session must remain visible rather than being inferred.
- Repeated preparation is idempotent for an exact candidate or completed
  canonical publication.
- Apply plans should be created close to their separately reviewed Apply, not
  parked across unrelated canonical writes.
- This decision creates no Historical Coverage, research-performance,
  Production signal, deployment, or scheduler authority.

## Alternatives Considered

### Make Membership a hard gate before Phase 1a

Rejected for the initial rollout because a new research family must not stop
the already stable public serving chain before live recovery behavior is
observed.

### Prepare the inventory-bound Apply plan immediately after EOD

Rejected because later MI or Snapshot publication changes `/data` and would
invalidate the plan's compare-and-swap pre-state.

### Keep every candidate and plan under ad hoc `/tmp` paths

Rejected because routine daily interruption recovery needs deterministic,
owner-only session custody outside the repository and canonical data root.
