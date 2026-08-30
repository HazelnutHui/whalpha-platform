# ADR 0081: Make Scheduler Wakes Pipeline-Aware

## Status

Accepted

## Date

2026-08-30

## Context

The installed ADR 0079 timer safely runs scheduler plan 1.1, but that plan
observes only canonical EOD completion. After canonical Apply advances EOD, it
returns `up_to_date` even when Phase 1a, Phase 1b, Candidate, Entry Geometry,
ETF Relationships, Market Preview, Strategy Channels, or a later review plan
is still missing. Connecting that plan directly to the coordinator would
therefore stop the same-day pipeline immediately after EOD became current.

The existing one-transition custody is intentionally process-bounded. Its
artifacts were originally direct `/tmp` children for reviewed one-shot runs.
Unattended distinct wakes require stable per-session paths that survive process
exit and reboot without turning canonical `/data` into a work directory.

## Decision

Add two repository-only contracts without changing the installed timer:

- `daily-eod-workspace-layout/1.0` derives one deterministic Dell-local,
  per-session workspace and the immediately prior Phase 1b/Candidate paths;
- `daily-eod-pipeline-wake-plan/2.0` combines the existing XNYS/EOD wake plan
  with one formally fingerprinted `daily-eod-automation-plan/1.4` for the
  latest canonical session.

The workspace root must be absolute, outside the repository, outside canonical
`/data`, and outside `/tmp`. Session artifacts are direct children of
`sessions/session_date=YYYY-MM-DD`; shared journal and cache roots remain
separate. Existing direct-child `/tmp` plans remain readable for historical
recovery and backward-compatible tests.

Pipeline-aware wake planning has four bounded outcomes:

1. wait for the next session or stabilization boundary;
2. review or propose one data transition while canonical EOD is missing;
3. review or propose one offline transition when canonical data is current but
   the local pipeline is incomplete; or
4. stop at a manual publication, Snapshot, deployment, blocked, or recovery
   boundary.

The new plan recomputes both input-plan fingerprints. It does not invoke the
coordinator, create a workspace, read a credential, access a network, write a
journal, publish, deploy, or install/modify a timer. Publication and deployment
completion are deliberately not inferred from a local offline plan.

## Consequences

- Canonical EOD becoming current no longer hides unfinished same-session
  analytics.
- Distinct future wakes can share deterministic paths without relying on
  ephemeral `/tmp` names.
- The first automation rollout may advance data and offline calculations but
  must stop for human publication/deployment review.
- A later ADR must define bounded repeated calendar cadence, installed runtime
  custody, successful natural-trigger evidence, and any standing capability.
- Automatic stale-review publication remains prohibited.

## Alternatives Considered

### Connect scheduler plan 1.1 directly to the coordinator

Rejected because it would stop after canonical EOD Apply and leave downstream
analytics stale while reporting the data layer current.

### Execute the whole pipeline in one service process

Rejected because it would collapse per-transition reservation, recovery, and
unknown-outcome boundaries into one long failure domain.

### Keep durable automation artifacts under `/tmp`

Rejected because cleanup or reboot can remove evidence between distinct wakes.

### Store the automation workspace under canonical `/data`

Rejected because temporary execution state would perturb the protected
Production inventory used by publication approval.
