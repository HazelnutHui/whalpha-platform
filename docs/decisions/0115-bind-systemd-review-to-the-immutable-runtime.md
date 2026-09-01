# ADR 0115: Bind systemd review to the immutable runtime

## Status

Accepted.

## Date

2026-09-01.

## Context

ADR 0114 defined the immutable detached-worktree plan, but the scheduler
runtime verifier and user-systemd candidate still required branch `main` and a
Python launcher inside that checkout. Creating the planned worktree without
closing those two checks would not produce an installable, fail-closed service.

## Decision

Extend runtime verification with an explicit expected checkout mode. `main`
remains the default for compatibility. `detached` additionally requires the
exact fixed runtime parent and `revision=<full commit>` leaf, an empty current
branch, the exact revision and a clean worktree.

Advance the systemd candidate contract to 1.1. Its detached mode uses the
runtime worktree for code and the canonical source repository's Python
launcher, resolved to the same exact interpreter. Render the expected checkout
mode into `ExecStart`; do not infer it at service execution time.

Candidate review remains network- and write-free. It does not create the
runtime, install or enable units, start the service, invoke the coordinator,
read credentials, or authorize data and Production changes.

## Consequences

- A created immutable runtime can now be independently reviewed and rendered
  as exact service bytes.
- Existing `main` execution remains accepted only when explicitly or
  compatibly expected as `main`.
- A detached checkout outside the fixed revision-derived path fails closed.
- A branch-attached checkout cannot masquerade as detached even at the same
  commit.
- The installed V1 service is not silently upgraded; migration remains a
  separate exact host-state action.

## Alternatives considered

- Treat an empty branch as sufficient evidence. Rejected because any detached
  checkout path could then be substituted.
- Copy the virtual environment into every runtime. Rejected because it adds
  duplication and a second dependency-custody problem.
- Reuse the 1.0 candidate label. Rejected because rendered service semantics
  and candidate fields now support a new checkout mode.
