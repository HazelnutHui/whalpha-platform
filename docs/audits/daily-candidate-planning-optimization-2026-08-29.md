# Daily Candidate Planning Optimization — 2026-08-29

## Scope

This repository-only change applies ADR 0065 to the exact-session daily
planner. It changes only how an already completed Candidate audit is observed
by planner and postcondition roles. It does not recalculate or modify the real
Candidate audit, `/data`, Market Intelligence, Snapshot, Dashboard, OCI, or
the run journal.

## Preserved boundary

- all Candidate artifact files are rehashed and checked against the canonical
  completion manifest;
- owner/mode/path/symlink/file-set and parameter contracts remain enforced;
- zero Oracle mismatch and all equivalence gates remain required;
- the incremental ledger's own canonical encoding and logical fingerprint are
  checked;
- prior/current sessions, prior audit identity, validation scope/tier,
  current-session Oracle segment, and all reuse gates are checked;
- current daily output still requires explicit `validation_tier=daily`;
- Candidate calculation retains its full typed prior-audit reconstruction;
- the executor retains its locked re-plan and formal postcondition.

## Real benchmark

Input Candidate audits:

- prior 2026-08-26:
  `0e9db80894a56c0ddd3180975a99237e84159846a1ac5ff7195978d82f887a63`;
- current 2026-08-27, 422,786,554 bytes:
  `0fa85ae742ef47e7278c444c12f05f2082e38a5071068a5787655a11271eb4e4`.

The optimized formal planner completed in 9.45 seconds at 221,640 KiB maximum
RSS. It returned the unchanged plan fingerprint
`eb19d7790605fae6d2467f6996b9411fb5fc6653f28f27b6e60c9fdd6b41811f`,
status `ready_for_offline_calculation`, and sole next action
`calculate_entry_geometry`.

The first real compatibility pass failed closed in 8.67 seconds because the
verified 2026-08-26 incremental audit predates explicit validation tiers. No
state changed. The reader was corrected to preserve the full reader's accepted
`None`/`daily` historical contract; the current daily output is still rejected
by the planner unless its tier is explicitly `daily`.

The related Candidate, planner, executor, and coordinator suite passes 157
tests. The full backend suite passes 1,571 tests with the same two existing
dependency deprecation warnings. No network request, credential access,
`/data` write, analytics recalculation, publication, deployment, or scheduler
action occurred.
