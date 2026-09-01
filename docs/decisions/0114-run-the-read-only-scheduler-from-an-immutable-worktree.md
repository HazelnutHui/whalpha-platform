# ADR 0114: Run the read-only scheduler from an immutable worktree

## Status

Accepted.

## Date

2026-09-01.

## Context

The installed read-only user service combined two valid safeguards: it ran code
from canonical `main`, and it rejected any revision other than the reviewed
commit. During active development those safeguards conflict operationally.
Every later commit advances `main`, so the next wake rejects even when the
scheduler implementation itself did not change. Rebinding the service after
every repository commit is slow and creates avoidable host-state churn.

## Decision

Use a detached Git worktree at an exact commit as the future Dell scheduler
runtime. Place it below the fixed user-owned runtime parent and name its leaf by
the full revision. Continue using the canonical project Python environment,
but resolve and bind its exact executable.

Introduce a deterministic, network- and write-free V1 plan before creating the
runtime. Runtime creation, verification, systemd candidate rendering and timer
migration each require their own reviewed boundary; this decision does not
perform or authorize any of those host changes.

## Consequences

- Ordinary `main` commits no longer invalidate an already verified runtime.
- The service can remain pinned to exact immutable code and fail closed on
  checkout mutation, dirtiness, revision mismatch or Python custody drift.
- Runtime code remains on Dell and comes from the same repository; OCI remains
  only the public serving boundary.
- The runtime adds one managed code checkout but does not duplicate canonical
  data or create a second Python environment.
- Updating scheduler code becomes an explicit runtime replacement and timer
  migration rather than an incidental consequence of every commit.

## Alternatives considered

- Keep rebinding the service to every `main` commit. Rejected because unrelated
  commits repeatedly invalidate the next wake.
- Remove exact revision checks. Rejected because it weakens review custody.
- Copy selected Python files outside Git. Rejected because provenance,
  dependency closure and cleanliness become harder to prove.
- Build a container image. Deferred as unnecessary complexity for the current
  single-workstation, read-only scheduler.
