# ADR 0122: Bound Transient Retries Inside Historical Batches

## Status

Accepted

## Date

2026-09-02

## Context

ADR 0121 made each Historical Backfill invocation finite, newest-to-oldest,
and resumable from canonical state, but required every provider failure to stop
without retry. A real batch subsequently completed 17 sessions and then
stopped on a single transport timeout. Canonical state and temporary-package
custody remained valid, but continuing required a new process even though the
failure class was transient and the exact authorized batch still had unused
session capacity.

Retries must not hide permanent provider responses, weaken request accounting,
repeat an uncertain Apply, or turn a bounded user-started batch into an
unattended scheduler.

## Decision

Amend only ADR 0121's zero-retry consequence. Within one already-started,
explicitly bounded Historical Backfill invocation:

- retry only `MassiveTransportTimeoutError` and
  `MassiveTransportUnavailableError`;
- allow no more than two retries for the same exact session, after delays of
  30 and 90 seconds by default;
- retain one shared 15-second provider limiter across the original attempt and
  retries;
- restart the exact session workflow and let formally readable canonical state
  and immutable source packages decide what is reused;
- count every provider-call attempt, including calls that raised a transient
  transport error;
- record the safe failure class and retry count without emitting exception
  text, response bodies, request URLs, headers, or credentials; and
- stop nonzero with completed-session evidence and the exact failed session
  when the retry budget is exhausted.

HTTP response errors, including 429, malformed data, pagination/custody/quality
failures, inventory conflicts, plan failures, Apply failures, and formal-reread
failures remain immediate stops with no retry. Retry settings are code-bounded
to at most two positive delays, each no longer than five minutes.

This policy grants no scheduler, analytics, Market Intelligence, Snapshot,
bundle, deployment, or publication authority.

## Consequences

- One short network interruption no longer discards the remaining capacity of
  an otherwise healthy batch.
- A timeout during Identity pagination may repeat provider reads for the same
  date, but cannot expose or publish a partial source package because package
  publication begins only after all pages are collected.
- A timeout after canonical Identity Apply resumes the same date and reuses the
  formally readable Identity snapshot before attempting EOD again.
- A frozen package or completed canonical partition continues to be the resume
  authority; no mutable progress counter is introduced.
- Exhaustion remains fail-stop and manually resumable from canonical state.
- The result contract advances from
  `historical-research-backfill-batch-result/1.0` to `1.1` to expose provider
  attempt counts, retry counts, failure codes, and the configured delay policy.
- The already-running service started from an earlier clean `main` revision is
  not altered in place and retains ADR 0121's zero-retry behavior until a later
  reviewed runtime transition.
