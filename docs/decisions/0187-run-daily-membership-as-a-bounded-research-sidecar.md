# ADR 0187: Run Daily Membership as a Bounded Research Sidecar

## Status

Accepted

## Date

2026-09-09

## Context

ADR 0185 made the daily Universe Membership state visible without execution.
The candidate and near-Apply plan still required separate manual commands even
though both already had deterministic, network-prohibited, formally reread
boundaries. Leaving those two non-canonical actions uncomposed increases the
chance of a missed prospective session without adding an evidence gate.

Membership must remain independent from the website pipeline. Candidate
preparation and near-Apply planning also run at different clocks: the first may
start once same-session EOD and Identity are complete, while the second must
wait until the primary pipeline reaches its final serving-review boundary.
Canonical Membership Apply remains a separate mutation and recovery boundary.

## Decision

Add `daily-universe-membership-bounded-run/1.0`, a finite Dell-local controller
over the existing read-only sidecar planner and existing action functions.

One invocation:

- replans before and after each workspace action;
- may execute only `prepare_candidate` and `prepare_apply_plan`;
- runs at most two actions and defaults to a one-hour elapsed budget;
- uses one fixed planning time so a fingerprint changes only when evidence or
  primary state changes;
- holds a non-persistent exclusive lock on the exact owner-only session
  directory while execution is enabled;
- validates the returned candidate or Apply-plan identity and authority before
  continuing;
- stops on waiting, Apply review, canonical completion, blocked state, action
  failure, or budget exhaustion;
- never retries or recovers automatically; and
- never invokes the primary pipeline, Membership Apply, provider access,
  publication, deployment, or a scheduler.

The CLI remains review-only unless `--execute` is explicit. Candidate and plan
writes stay in the existing persistent daily workspace. Restart recovery is a
fresh planner read of those immutable/atomic artifacts; an invalid or partial
state stops for operator diagnosis rather than being deleted or inferred.

The result is a fingerprinted invocation summary, not a second durable journal.
The candidate, Apply plan, canonical Membership reader, and existing exact-Apply
custody remain authoritative.

No service, timer, standing authorization, canonical Apply, `/data` write, or
Production invocation is installed or changed by this decision.

## Consequences

- A healthy prospective session can retain its candidate and, if the primary
  pipeline is already final, its near-Apply plan in one bounded command.
- A research failure stays visible and cannot stop or invoke the website chain.
- Apply remains an explicit separate review and mutation boundary.
- The next live eligible session must prove candidate timing, waiting behavior,
  near-Apply inventory binding, and failure reporting before unattended
  execution is considered.

## Alternatives Considered

### Add Membership actions to the primary offline runner

Rejected because it would couple research continuity to website delivery and
cannot represent the candidate and near-Apply clocks cleanly.

### Automatically Apply after plan creation

Rejected because plan evidence does not grant mutation authority and exact
Apply/recovery already has a separate canonical custody contract.

### Add another persistent execution journal

Rejected because the two artifact states are already formally readable and
the runner neither retries nor crosses an ambiguous external boundary. A new
journal would duplicate authority without improving safe restart behavior.
