# ADR 0093: Integrate Candidate Visual Context into Daily Planning

## Status

Accepted

## Date

2026-08-30

## Context

Snapshot 1.11 preserves Candidate Visual Context from Snapshot 1.10 and adds
Sector ETF Rotation. The daily executor already calculated Candidate, Entry
Geometry, and Strategy Channels, but it did not calculate Visual Context or
pass its audit to Snapshot planning. Activating MI 1.3 in that state would
leave the chain unable to prepare the complete Snapshot 1.11.

The repository also has a persistent per-session workspace design for future
distinct unattended wakes. Several older analytics audit writers and readers
still enforce direct-child `/tmp` custody, so persistent-workspace execution
has not yet been demonstrated by their real CLIs. Planner and mocked executor
tests do not prove that runtime compatibility.

## Decision

Add Candidate Visual Context as a distinct governed offline stage after
Strategy Channels and before Market Intelligence plan preparation:

1. Daily Automation Plan 1.6 observes the formally reread Visual Context audit
   and selects only `calculate_candidate_visual_context` when it is absent.
2. The audit must bind the exact same-session Candidate and Entry Geometry
   fingerprints, ordered Universes, Phase 1a history fingerprint, panel cache,
   and zero-mismatch Oracle.
3. Single-action Executor 1.5 invokes the existing socket-guarded CLI only when
   the exact panel-cache root is supplied. It writes no `/data` and grants no
   publication or deployment authority.
4. Snapshot planning receives the exact Visual Context audit path. Automation
   rechecks that Plan 2.6 binds the same audit fingerprint before advancing to
   Snapshot publication review.
5. The new stage is proven first in the established direct-child `/tmp`
   boundary. Persistent-workspace execution remains blocked until all affected
   audit custody contracts share and test one safe persistent path policy.

No installed timer, standing authorization, publication Apply, Snapshot Apply,
bundle, deployment, or network access follows from this decision.

## Consequences

- A new daily session cannot silently lose Candidate price paths or observed
  state age when it advances to Snapshot 1.11.
- The independent Visual Context calculation remains explanatory and does not
  alter Candidate scores, states, ranks, or Strategy Channels.
- The direct `/tmp` stage is real and reviewable, but the overall unattended
  chain must not be called complete while persistent-workspace CLI custody is
  unresolved.
- The next reliability slice is a shared, exact, non-symlink, owner-controlled
  persistent session-artifact boundary with real end-to-end CLI tests.

## Alternatives Considered

### Drop Visual Context from Snapshot 1.11

Rejected because a newer Snapshot cannot regress a deployed explanatory
product to make automation appear complete.

### Generate Visual Context during Snapshot construction

Rejected because Snapshot publication must consume reviewed immutable
analytics rather than scan Dell history or perform hidden calculations.

### Treat planner and mocked executor tests as persistent-runtime proof

Rejected because the underlying audit CLIs still reject those paths.
