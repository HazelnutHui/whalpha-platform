# ADR 0083: Reuse the Run Journal for Cadence Evidence

## Status

Accepted

## Date

2026-08-30

## Context

ADR 0082 defines finite distinct-wake planning, but its in-memory evidence must
survive process exit and reboot before a later wake may consume it. The project
already has an owner-only Dell run journal with a non-blocking global lock,
immutable owner-read-only event files, canonical JSON, cross-session SHA-256
chaining, symlink rejection, and unresolved-action blocking. A second cadence
database would duplicate custody and create two operational truths.

Review also found that coordinator 1.11 reported any returned provider
capability and offline executor result as `transition_executed`, even when the
formal outcome was `waiting` or `failed`. A future cadence adapter could
therefore mistake a known failure for progress.

## Decision

Reuse the existing run journal as the only durable operational evidence store.
Advance it to `daily-eod-run-journal/1.7` with one standalone
`cadence_wake_recorded` event. The event is allowed only when no data, offline,
publication, Snapshot, or deployment attempt is unresolved. Existing 1.2–1.6
events remain readable, including OCI events introduced under 1.6.

Each cadence event retains and formally rereads:

- the complete enabled Bounded Cadence Plan 1.0;
- Cadence Wake Evidence 1.2;
- the immutable cadence start and exact cadence/pipeline plan fingerprints;
- the one action, known outcome, formal result identity, completion time, and
  any formal readiness `next_check_at` boundary;
- the cadence-only sequence and the enclosing run-journal hash chain.

Retention rejects skipped or duplicate sequence/result identity, a changed
cadence start, a wake before the five-minute floor, a start outside four hours,
more than 16 wakes, a wake after known failure, an unknown outcome, plan/evidence
drift, and any append while an action is unresolved. Unknown process outcome
remains an in-memory terminal classification; it cannot be persisted as if it
were resolved.

Add result adapters for exact enabled Pipeline V2 and Bounded Cadence plans.
Coordinator `transition_executed` maps to `advanced` only with matching formal
transition evidence; `waiting` maps to `no_change`; all manual, recovery,
blocked, or other non-progress states map to terminal `failed`. Offline executor
success requires changed post-plan and succeeded journal evidence; executor
failure remains `failed`.

Advance the coordinator to 1.12. Provider capability success remains
`transition_executed`, `waiting` becomes `waiting`, and `failed` becomes
`blocked`. Offline executor failure becomes `blocked` rather than
`transition_executed`.

No second store, real directory, runtime loop, service, timer change,
credential, provider/OCI request, `/data` write, publication, or deployment is
created or performed. The installed read-only timer remains unchanged.

## Consequences

- Cadence budget and result evidence share the same serial operational truth as
  the actions they describe.
- A restart cannot reset the cadence start or silently reinterpret failure as
  progress.
- Existing journal locking continues to prevent overlap; cadence evidence does
  not introduce another lock hierarchy.
- A later runtime bridge still must compose planning, exactly one invocation,
  result adaptation, and evidence append with explicit unknown-outcome handling.
- Natural timer evidence remains a prerequisite before any installation or
  Production capability decision.

## Alternatives Considered

### Create a separate cadence journal

Rejected because it would duplicate permission, locking, hash-chain, recovery,
and retention logic while allowing two operational truths to diverge.

### Store only the cadence-plan fingerprint

Rejected because later reread could not independently verify limits,
enablement, target, or remaining budget.

### Treat any coordinator return as progress

Rejected because waiting and failed capability results do not prove a state
transition.
