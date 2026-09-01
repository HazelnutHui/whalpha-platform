# Daily EOD Scheduler Runtime Plan V1

## Purpose

`daily-eod-scheduler-runtime-plan/1.0` describes one exact, immutable Dell
runtime checkout for the read-only daily wake. It separates the scheduler's
executable code from the moving `main` checkout without weakening revision or
cleanliness checks.

The plan is review evidence only. Producing it does not create a directory,
add a Git worktree, read data or credentials, change systemd, invoke the daily
coordinator, or authorize installation.

## Fixed custody

- Host/user: `dell5820` / `hui`.
- Source repository:
  `/home/hui/projects/trading-intelligence-platform`.
- Checkout mode: detached Git worktree.
- Runtime parent:
  `/home/hui/.local/share/trading-intelligence-platform/daily-eod-scheduler-runtime`.
- Runtime leaf: `revision=<exact 40-character commit>`.
- Python environment: the canonical source repository `.venv`, resolved to an
  exact executable.

The runtime contains code only. Canonical market data stays under `/data`; the
plan does not read or write it.

## Required post-creation verification

Before a separately authorized timer migration, a future installer must prove:

1. the exact runtime root is a non-symlink directory;
2. `HEAD` equals the planned revision and the checkout is detached;
3. the worktree is clean;
4. the planned scheduler entrypoint is a regular executable file;
5. the canonical Python launcher resolves to the planned executable;
6. imports resolve from the runtime worktree rather than moving `main`; and
7. the scheduler's Dell runtime verification passes the exact revision.

Creation, post-creation verification, systemd candidate rendering and timer
migration remain separate custody transitions. The current V1 planner performs
none of them.

## Why the runtime is immutable

The previous service pointed at `main` and required its exact revision. Any
subsequent documentation or development commit made the installed service
stale before its next wake. A detached exact-commit runtime preserves the
fail-closed revision guarantee while allowing `main` to advance normally.

## Fingerprint

`logical_content_fingerprint` is SHA-256 over deterministic JSON for every plan
field except the fingerprint itself. Any path, revision, Python executable,
check, proposed command or authority change invalidates the plan.
