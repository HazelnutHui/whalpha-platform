# ADR 0082: Bound Distinct Pipeline Wake Cadence

## Status

Accepted

## Date

2026-08-30

## Context

ADR 0081 can identify one data or offline transition after each fresh pipeline
observation, but it does not say when another process may observe again or how
many transition wakes one session may consume. An unbounded loop would collapse
all stages into one failure domain. An unbounded timer would instead spread the
same risk across processes and could replay a failed or unknown action.

The current session-readiness policy allows at most five provider attempts.
Canonical Apply is a separate transition, and the offline pipeline contains ten
governed actions before its manual publication/deployment boundaries. These
facts provide a conservative structural ceiling for a review candidate; they
do not prove an appropriate Production cadence.

## Decision

Add repository-only contracts for one bounded cadence plan and its prior-wake
evidence chain. Each planner invocation consumes a freshly verified Pipeline
Wake Plan 2.0 plus immutable evidence from earlier distinct process wakes. It
never loops or invokes a transition itself.

The first candidate has hard upper bounds:

- no more than 16 transition wakes for one target session;
- no more than four hours from the explicit cadence start; and
- at least five minutes from completion of one wake to start of the next.

Callers may propose stricter values but cannot widen these limits. The 16-wake
ceiling reflects five possible provider attempts, one separately governed
canonical Apply, and ten offline actions. It is a safety ceiling, not a target
or a claim that all stages normally run.

An enabled proposal requires both the cadence candidate and its exact Pipeline
Wake Plan to be enabled. Waiting produces only a future observation time.
Manual review and blocked pipeline states stop. A formally known failure stops
without retry; an unknown outcome stops without replay or recovery. A formal
`no_change` outcome may be observed again only in a later process after the
minimum interval and while both budgets remain.

Strengthen Pipeline Scheduler V2 verification at the same boundary so a
maliciously changed and re-fingerprinted plan cannot combine incompatible
status, phase, action, scope, enablement, or authority fields.

No evidence store, runtime bridge, service, timer, capability, workspace,
credential, request, `/data` write, publication, or deployment is created or
changed. The already installed read-only timer is not rebound. A natural timer
wake remains required evidence before any later installation decision.

## Consequences

- Repeated observation is finite by construction and remains one transition
  per process.
- Known failure, crash ambiguity, manual review, and blocked states cannot turn
  into automatic retry or replay.
- The candidate exposes its limits, usage, remaining budget, evidence-chain
  identity, and every zero-authority field instead of hiding them in one hash.
- Future runtime work must define owner-only evidence persistence, exact result
  adapters, overlap prevention, and systemd custody before this can run.
- Production interval and window values still require measured Dell timing and
  natural-trigger evidence; these candidate limits are not activated policy.

## Alternatives Considered

### Run the whole session pipeline in one service process

Rejected because a crash would make several transitions ambiguous and weaken
the existing per-action journal and recovery boundary.

### Retry known failures automatically

Rejected because provider and offline failures have different semantics, and a
completed side effect may not be safely replayable.

### Wake forever until manual review is reached

Rejected because an unchanged or defective state would create an unbounded
background loop.
