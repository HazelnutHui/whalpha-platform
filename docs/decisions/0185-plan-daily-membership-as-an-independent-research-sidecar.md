# ADR 0185: Plan Daily Membership as an Independent Research Sidecar

## Status

Accepted

## Date

2026-09-09

## Context

ADR 0154 deliberately kept prospective Universe Membership preparation outside
the public serving gate. The live 2026-09-08 run has now proved that the
candidate, near-Apply plan, canonical Apply, reread, and recovery boundaries
work from the persistent daily workspace. The remaining gap is operational
visibility: the daily wake currently reports only the primary EOD-to-website
path, so Membership readiness must still be reconstructed manually.

Membership cannot simply become another serial coordinator action. Candidate
preparation may begin after same-session EOD and Identity exist, but its
inventory-bound Apply plan is valid only after the primary canonical writes
are complete. A research-side failure must also remain unable to stop a valid
website update.

## Decision

Add a pure, read-only Membership sidecar planner and expose its result as an
optional nested status in the daily wake plan.

- The primary daily status and next action remain authoritative and unchanged.
- The sidecar consumes the exact target session, current primary automation plan,
  formal completed security-evidence catalog, deterministic daily workspace,
  candidate, Apply plan, and canonical Membership readers.
- Candidate readiness may be reported only after same-session EOD and Identity
  are complete.
- Near-Apply planning may be reported only when the primary pipeline reaches
  its final serving-review boundary, after expected canonical `/data` writes.
- A complete physical partition plus publication marker is the only completed
  state. Physical-only or marker-only state is blocked for exact recovery.
- Outcome-only candidates cannot advance to Apply planning.
- Every sidecar result keeps `website_pipeline_blocked=false` and grants no
  write, Apply, scheduler, network, deployment, Historical Coverage, or
  research-performance authority.
- The daily wake contract may carry the sidecar's status, action, fingerprint,
  and non-blocking flag, but must not use them to change its primary decision.

This decision adds the planner, CLI, administrator entry point, tests, and
documentation only. Installing or changing a timer and unattended candidate,
plan, or Apply execution require later decisions and verification.

## Consequences

- Operators can see the next primary website action and the independent
  Membership research action in one read-only report.
- Membership can progress at the correct two clocks without making the public
  product less reliable.
- Existing candidate, plan, Apply, and canonical readers remain the only
  execution and evidence boundaries; the planner does not duplicate them.
- A sidecar fault remains visible and fail-closed for research while the
  primary pipeline can continue.

## Alternatives Considered

### Add Membership as the last coordinator action

Rejected because it would turn an additive research family into a serving
dependency and would mix candidate and near-Apply clocks.

### Run Membership without reporting it in the daily wake

Rejected because invisible background work is difficult to audit and recover
after interruption.

### Let the sidecar write its candidate or plan

Rejected because planning and execution have separate authority boundaries.
