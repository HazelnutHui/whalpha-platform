# Daily EOD Bounded Offline Run V1

## Purpose

`daily-eod-bounded-offline-run/1.0` joins consecutive, already-governed
Dell-local offline actions without removing their individual journal,
postcondition, or recovery boundaries. It is not a provider, publication,
deployment, or scheduler contract.

## Inputs

- one exact target XNYS session;
- the complete explicit `DailyEodAutomationPaths` set;
- the existing owner-only daily run root;
- the shared panel-cache and Candidate work paths when required;
- an aware UTC run start;
- at most eleven action attempts and at most four elapsed hours; and
- optionally, the exact current-state fingerprint required only if Market
  Intelligence plan preparation is reached.

Default limits are eleven action attempts and two elapsed hours. The CLI is
review-only unless `--execute` is explicit. The elapsed-time budget is checked
before starting each action; it never kills an already-running governed action.

## Progress rule

Before every action, the runner obtains and verifies a fresh Automation Plan
1.8. It may execute only when the plan is
`ready_for_offline_calculation` and its action belongs to the existing
`OFFLINE_ACTIONS` set. The exact plan fingerprint is supplied to the unchanged
single-action executor.

A later action is permitted only after the executor returns formal journal
evidence and stage evidence for `succeeded`, supplies a different completed
post-plan, and a fresh planner read reproduces that post-plan. Repeated
successful plan identities, malformed events, mismatched target/action,
missing stage evidence or post-plans, or clock regression fail closed.

## Stop states

| Status | Meaning |
| --- | --- |
| `review_ready` | The next offline action is visible, but execution was not enabled. |
| `boundary_reached` | Data input, MI/Snapshot publication, deployment review, or the explicit MI current-state input is required. |
| `blocked` | The formal Automation Plan is blocked. |
| `action_failed` | One action returned a known failure; no retry follows. |
| `budget_exhausted` | The action or elapsed-time budget was reached before another action. |

An exception without a formal executor result stops the process as an unknown
runner outcome. Existing action custody determines whether recovery is needed;
the runner never infers or performs recovery.

## Result evidence

The fingerprinted result contains:

- target, start, completion, and exact budgets;
- ordered action, timing, outcome, pre/post plan, and journal-event identities;
- final formal plan status, action, and fingerprint;
- explicit execution enablement and stop reasons; and
- zero external request and Production-write counts, with publication,
  deployment, retry, recovery, and scheduler authority all false.

The result is an invocation summary, not a second durable operational store.
The existing action journal remains authoritative for resume and recovery.

## CLI boundary

`scripts/admin/run-bounded-daily-eod-offline.sh` derives the exact persistent
workspace layout. Execution additionally requires the workspace, sessions,
target/prior session, journal, and panel-cache directories to be pre-provisioned,
owned by the executing user, mode `0700`, and free of symlink substitution. A
socket guard remains active throughout planning and execution.

## Explicit exclusions

- provider or credential access;
- Identity/EOD fetch or canonical Apply;
- automatic retry, polling, sleeping, or recovery;
- MI or Snapshot Apply;
- OCI request or deployment;
- runtime checkout, service, or timer installation; and
- automated trading or order execution.
