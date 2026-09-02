# ADR 0123: Chain Bounded History Batches to a Finite Target

## Status

Accepted

## Date

2026-09-02

## Context

ADR 0121 limited one Historical Backfill process to 20 sessions so early live
execution could stop at a small, reviewable boundary. After multiple successful
batches, the limit became an operational interruption rather than a data-safety
control: the process exited successfully every 20 dates and required another
manual start even though the next date, target and resume state were fully
deterministic.

The 20-session evidence boundary remains useful, but it does not require the
external process to exit. The user has directed the remaining 300-session
foundation to run continuously without manual starts between healthy batches.

## Decision

Add one Dell-local finite continuous controller above the unchanged bounded
batch runner:

- one explicit process targets an exact session count between the existing
  planner bounds;
- each internal batch remains limited to at most 20 sessions;
- one provider transport and one 15-second serial limiter are shared across all
  internal batches;
- every completed batch emits and flushes its full result as a separate
  revision-bound checkpoint before the next batch begins;
- canonical state and formally readable packages remain the resume authority;
- the controller stops successfully only when the batch runner reports the
  exact target complete;
- a zero-progress or unknown batch result stops immediately;
- ADR 0122's same-session transient retries remain the only automatic retry;
  retry exhaustion or any non-retryable failure ends the continuous process;
  and
- the loop has a fixed progress bound derived from the requested target, so it
  cannot become an unbounded daemon.

The controller may remove manual starts between healthy batches. It does not
automatically restart itself after a true stop and grants no general scheduler,
analytics, Market Intelligence, Snapshot, bundle, deployment or publication
authority.

## Consequences

- The remaining history can be initiated once while preserving 20-session
  operational checkpoints.
- A successful checkpoint survives a later batch failure in the process log;
  a partial failing batch returns its completed-session evidence when the
  transient retry budget is exhausted.
- Provider calls remain serial. No attempt is made to parallelize a
  rate-limited external API.
- Identity and EOD still apply one exact date at a time, so process duration
  does not enlarge the atomic write boundary.
- Normal completion may take many hours, but progress no longer depends on a
  person restarting a successful process every 20 sessions.
