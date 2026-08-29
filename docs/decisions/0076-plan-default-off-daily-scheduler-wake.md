# ADR 0076: Plan a Default-Off Daily Scheduler Wake

## Status

Accepted

## Date

2026-08-29

## Context

The controlled daily chain now reaches one-shot OCI deployment and has passed
one real end-to-end publication/deployment round. The remaining scheduler gap
must not be filled by a timer that guesses a date or chains administrator
commands. A wake-up first needs a deterministic, credential-free answer to:
whether canonical EOD is current, which oldest XNYS session is missing, and
when the existing one-transition coordinator may next be reviewed.

## Decision

Add `daily-eod-scheduler-wake-plan/1.0` as a read-only plan derived from a
small completion-manifest index, a full formal reread of its latest EOD
Parquet/Identity binding, the offline XNYS calendar, the current UTC
observation time, and the existing readiness-policy stabilization delay.

The plan:

- rejects an empty, non-XNYS, non-contiguous, or future-ahead canonical
  session sequence;
- selects only the XNYS session immediately after the latest canonical session
  when one or more completed sessions are missing;
- waits until the current target's close plus the existing stabilization delay,
  while allowing an older missed session to enter review immediately;
- reports the next session close-plus-stabilization wake when canonical EOD is
  current; and
- limits any future scheduler wake to one invocation of the existing
  coordinator, which retains all retry, recovery, authorization, publication,
  deployment, and alert semantics.

The default candidate is disabled. An explicit enabled-candidate review only
changes the proposed next action from review to `invoke_one_transition`; it
does not invoke the coordinator, install or enable a timer, read a credential
or external control file, access a network, write a journal/artifact, authorize
publication/deployment, or make a Production write.

## Consequences

- Session/date selection and wake timing become testable business state rather
  than timer-shell behavior.
- Frequent wake planning reads every small completion manifest but fully
  reopens only the latest EOD partition. Periodic/full-source audit remains
  responsible for revalidating all historical Parquet bytes.
- Weekend, holiday, early-close, current-session stabilization, and oldest-gap
  behavior use the same offline exchange calendar as freshness/readiness.
- Retry and interruption recovery remain owned by the coordinator and durable
  journal; the scheduler cannot replay an unresolved action.
- A later systemd candidate still needs exact runtime/config custody, repeated
  distinct-wake rehearsal, and separate installation/enablement authorization.
- The current Basic EOD initial-availability operator-review gate remains
  unchanged; scheduler planning does not assert provider completeness.

## Alternatives Considered

### Schedule one large shell pipeline after market close

Rejected because one timer command would silently combine date selection,
provider readiness, retries, heavy calculations, publication, and deployment.

### Let the timer use the wall-clock date

Rejected because weekends, holidays, early closes, missed sessions, and an
unfinished prior day would select the wrong target.

### Enable the real timer with the first planning implementation

Rejected because a reviewed plan contract is not host installation authority
and has not yet passed repeated real-session wake rehearsal.
