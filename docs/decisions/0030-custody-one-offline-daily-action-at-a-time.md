# ADR 0030: Custody One Offline Daily Action at a Time

## Status

Accepted

## Date

2026-08-27

## Context

ADR 0029 established an exact-session, read-only planner, but a plan is not an
execution authorization or a durable record of what ran. A safe Dell executor
must reject stale plans, prevent concurrent transitions, survive interruption,
and distinguish a completed immutable artifact from an action that is safe to
retry. It must not collapse provider acquisition, analytics, publication, or
deployment into one unattended command.

## Decision

Add contract `daily-eod-single-action-executor/1.0` for exactly four existing
offline analytics actions: Phase 1a, verified-prior Phase 1b, daily
verified-prior Candidate, and Candidate entry geometry.

Each invocation must:

1. receive the exact target session, explicit artifact paths, the expected
   planner fingerprint, and the expected action;
2. acquire one non-blocking, workstation-wide exclusive lock;
3. formally re-plan under that lock and reject a stale fingerprint, changed
   action, blocked state, or unresolved prior attempt before calculation;
4. append an immutable `action_started` event before calling exactly one
   existing socket-guarded administrator entry;
5. validate the returned action, output path, summary hash, and summary size;
6. formally re-plan after the call and record success only when the named stage
   is complete and the plan has advanced; and
7. release the lock without authorizing another action.

Run custody originally introduced `daily-eod-run-journal/1.0`, extended by ADR
0032 to `daily-eod-run-journal/1.1` for disjoint acquisition events, in an
explicitly pre-provisioned owner-only Dell directory outside Git and outside
`/data`.
Events are canonical JSON, immutable owner-read-only files in a monotonically
numbered, cross-session SHA-256 chain. The root, lock, session directories,
event sequence, permissions, symlink boundary, event schema, fingerprints, and
prior-session terminal state all fail closed. The journal contains operational
evidence only; it is not an analytics or publication data source.

An abrupt interruption deliberately leaves `action_started` unresolved.
Recovery never executes an action. It formally re-plans with the exact started
inputs and records one of three terminal classifications: completed artifact
proven, no completed artifact detected and therefore eligible for a separately
requested retry, or blocked because current state is ambiguous. Earlier
unresolved sessions block later sessions.

The Candidate daily action uses its resumable owner-controlled work directory
and one effective worker. Phase 1a and Candidate may use an explicit immutable
panel cache outside `/data`. These locations are execution inputs and are bound
into the recovery fingerprint.

Provider acquisition and canonical `/data` apply, publication, Snapshot,
bundle, OCI deployment, and scheduler activation remain excluded and require
separate decisions. Implementing this executor does not activate or run it
against real daily state.

## Consequences

- A caller can advance at most one already reviewed offline transition.
- Concurrency, stale intent, journal tampering, unsafe custody, ambiguous crash
  state, and false-success evidence stop the run.
- A successful process exit is insufficient; immutable formal output and a
  changed plan are both required.
- Retry is an explicit new invocation after terminal recovery or failure, not
  an automatic side effect.
- The journal remains small and auditable but must be retained and backed up as
  operational evidence.
- Unattended operation still requires session-readiness/retry policy, standing
  authorization for provider acquisition and canonical apply, alerting, and a
  separate scheduler activation decision.

## Alternatives Considered

### Execute every ready offline stage in one command

Rejected because it removes the human checkpoint and exact-plan binding
between state transitions.

### Rewrite one mutable run-state file

Rejected because overwrite cannot provide immutable interruption and tamper
evidence.

### Automatically retry after process interruption

Rejected because process state cannot prove whether an immutable output was
published immediately before interruption.

### Store the run journal under `/data`

Rejected because operational custody must not become part of the canonical
analytics data surface or share its write authorization.
