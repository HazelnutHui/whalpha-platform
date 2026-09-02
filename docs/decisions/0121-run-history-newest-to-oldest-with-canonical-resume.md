# ADR 0121: Run History Newest-to-Oldest with Canonical Resume

## Status

Accepted; zero-retry consequence amended by
[ADR 0122](0122-bound-transient-retries-inside-historical-batches.md)

## Date

2026-09-01

## Context

The first three-session Historical Pilot completed successfully, extending
canonical EOD/Identity from 32 to 35 contiguous sessions. Manual execution
also exposed an important recovery property: applying an older date before the
date adjacent to current history temporarily creates a gap. A crash in that
state prevents the formal contiguous-history planner from resuming cleanly.

The remaining 265 sessions require a non-looping daily workflow to become one
bounded, resumable batch executor without weakening the existing fetch-only,
offline-plan, approved-Apply, immutable package, inventory fingerprint, and
formal reread boundaries.

## Decision

Add a Dell-local Historical Backfill Batch Runner that:

- always selects the single XNYS session immediately preceding the current
  canonical left boundary;
- processes Identity before unadjusted EOD for that exact session;
- shares one 15-second fixed limiter across every provider request;
- reuses a formally readable existing `/tmp` source package after interruption;
- names offline plans by the exact pre-Apply inventory fingerprint;
- applies only the exact generated plan SHA and expected inventory state;
- treats canonical Identity/EOD presence as the resume authority rather than a
  mutable progress counter;
- stops immediately on any fetch, mapping, quality, custody, inventory, Apply,
  or formal-reread failure; and
- accepts an explicit maximum session count per invocation.

The runner may continue multiple sessions after the user-authorized Pilot, but
it never computes analytics, publishes Market Intelligence or Snapshot data,
deploys OCI, or claims research readiness. Existing package and canonical
writers remain the only mutation implementations.

## Consequences

- Every completed EOD Apply extends one contiguous left boundary.
- A crash after Identity but before EOD resumes that same date and does not
  fetch or rewrite Identity again.
- A crash after a frozen package reuses its formally reread bytes.
- At this decision boundary there was no automatic retry. ADR 0122 later
  permits only two bounded transient transport retries inside the same exact
  session and invocation; every other failure remains fail-stop.
- Full-inventory hashing remains intentionally conservative and adds offline
  overhead. It may be optimized later without weakening exact pre-state binds.
