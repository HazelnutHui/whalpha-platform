# Daily Universe Membership Sidecar Plan V1

## Purpose

`daily-universe-membership-sidecar-plan/1.0` is a deterministic, read-only
decision for one target session. It reports what the independent Universe
Membership research path can do next without changing the primary daily
website pipeline.

## Status and next-action pairs

| Status | Next action | Meaning |
| --- | --- | --- |
| `waiting` | `wait_for_canonical_input` | Same-session EOD or Identity is not complete. |
| `ready` | `prepare_candidate` | Formal inputs exist and no candidate has been retained. |
| `waiting` | `wait_for_primary_pipeline` | Candidate is eligible, but later primary `/data` writes are still expected. |
| `ready` | `prepare_apply_plan` | Candidate is eligible and the primary pipeline is at its final serving-review boundary. |
| `review_required` | `review_apply` | An exact, formally readable Apply plan exists. |
| `complete` | `none` | Physical Membership and its last publication marker formally reconcile. |
| `blocked` | `operator_diagnosis` | Input corruption, outcome-only evidence, partial publication, or contradictory custody requires review. |

No other status/action combination is valid.

## Required bindings

The plan binds:

- checked time and target session;
- primary automation contract, status, action, and fingerprint;
- completed security-evidence catalog date;
- deterministic candidate and Apply-plan paths;
- candidate status, record count, logical fingerprint, and point-in-time
  eligibility when present;
- Apply-plan fingerprint when present;
- canonical publication fingerprint when complete; and
- a self-validating logical content fingerprint.

All paths must use the target session's owner-only persistent daily workspace.
The candidate and Apply plan remain outside Git and `/data`.

## Authority and isolation

Every valid plan sets:

- `website_pipeline_blocked=false`;
- `apply_authorized=false`;
- `historical_coverage_authorized=false`;
- `research_performance_authorized=false`;
- `scheduler_enabled=false`;
- `external_request_count=0`; and
- `production_write_count=0`.

The planner may formally read existing evidence. It may not fetch, prepare,
write, Apply, publish, deploy, install, schedule, or infer missing Membership.

## Administrator entry point

`scripts/admin/plan-daily-universe-membership-sidecar.sh`

## Daily wake projection

Daily EOD Pipeline Wake Plan 2.1 may optionally project only the sidecar
status, next action, plan fingerprint, and `website_pipeline_blocked` flag.
That projection is informational and must never alter the primary wake status,
action, authority, or fingerprinted source decision.
