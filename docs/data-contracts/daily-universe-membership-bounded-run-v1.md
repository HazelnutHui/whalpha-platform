# Daily Universe Membership Bounded Run V1

## Purpose

`daily-universe-membership-bounded-run/1.0` executes only the two existing
non-canonical actions of the independent Membership research sidecar. It does
not make Membership part of the public website pipeline.

## Inputs and limits

- one exact XNYS target session and its deterministic daily workspace;
- canonical Dell data root and completed security-evidence catalog date;
- the primary Automation Plan paths, used only for read-only planning;
- an aware UTC start time;
- one or two action attempts, with a default of two; and
- an elapsed budget of at most four hours, default one hour.

The planning timestamp is fixed for the invocation. Action timestamps come
from a monotonic UTC clock. Execution requires an existing owner-only `0700`
session directory and holds an exclusive process lock on that directory.

## Executable actions

| Action | Permitted effect | Required next boundary |
| --- | --- | --- |
| `prepare_candidate` | create or formally reuse the exact session's candidate below `universe-membership-candidate` | wait for the primary pipeline, prepare the plan, or stop blocked |
| `prepare_apply_plan` | atomically create and reread `universe-membership-plan.json` against the current `/data` inventory | `review_apply` |

The runner validates target session, methodology, paths, fingerprints, record
count, point-in-time classification, and zero-authority fields returned by each
action. The post-action planner must change and must not repeat the same action.

## Stop states

| Status | Meaning |
| --- | --- |
| `review_ready` | an action is visible but `--execute` was absent |
| `boundary_reached` | canonical input/primary completion is pending, Apply review is required, or canonical Membership is already complete |
| `blocked` | formal sidecar evidence requires operator diagnosis |
| `action_failed` | one action failed; no retry or later action follows |
| `budget_exhausted` | the action/time limit was reached before another workspace action |

An action that completed but cannot be formally replanned is an unknown runner
outcome. The process fails closed; a later invocation must inspect the retained
artifacts and must not infer recovery.

## Result evidence and authority

The fingerprinted result records ordered action times, pre/post plan identities,
artifact fingerprints, final sidecar state, budgets, and stop reasons. It
always reports:

- `website_pipeline_blocked=false`;
- primary pipeline invocation count zero;
- external request and Production write counts zero;
- canonical Membership Apply not performed;
- retry, automatic recovery, Historical Coverage, research performance, and
  scheduler authority false.

The result is not a durable journal or Apply authorization.

## Entry point

`scripts/admin/run-bounded-daily-universe-membership.sh`

The command is network-prohibited and defaults to review-only. `--execute`
permits only the two workspace actions above.

## Explicit exclusions

- provider or credential access;
- canonical EOD, Identity, or Membership writes;
- Membership Apply or recovery;
- Market Intelligence, Snapshot, bundle, or OCI actions;
- invocation or blocking of the primary website pipeline;
- timer/service installation or unattended operation; and
- Historical Coverage or performance claims.
