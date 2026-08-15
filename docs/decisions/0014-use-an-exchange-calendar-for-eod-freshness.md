# ADR 0014: Use an Exchange Calendar for EOD Freshness

## Status

Accepted

## Date

2026-08-15

## Context

Completed files can be internally valid while still lagging the latest completed market session. Weekday arithmetic and a hand-maintained holiday list cannot reliably distinguish weekends, exchange holidays, early closes, or the close boundary in New York time.

## Decision

Use `exchange-calendars` 4.13.x with calendar ID `XNYS` as the offline V1 calendar for U.S. cash-equity EOD freshness. Market schedule semantics use `America/New_York`; stored and machine-facing timestamps remain timezone-aware UTC.

The provider-neutral calendar boundary supplies session membership, previous session, latest completed session at an injected time, and session lag. Calendar freshness is evaluated separately from dataset availability and file/schema/count/fingerprint validation.

Freshness statuses are:

- `fresh`: actual latest completed data session equals the calendar's expected latest completed session;
- `stale`: actual data session precedes the expected session, with an explicit session lag;
- `unavailable`: the calendar cannot be loaded, evaluated, or reconciled safely.

Runtime calendar evaluation is offline and makes no network request. The V1 calendar identifies XNYS sessions and closes; it does not assert provider publication availability or validate corporate actions.

## Consequences

- Weekend, exchange holiday, early-close, DST, and before/after-close behavior become deterministic and testable with an injected clock.
- A completed manifest no longer implies freshness.
- Calendar failure degrades to `unavailable`; the system does not guess.
- `exchange-calendars>=4.13,<5.0` becomes an API package dependency.

## Alternatives Considered

- Weekday-only arithmetic: rejected because it mishandles holidays and early closes.
- A project-maintained holiday table: rejected because it creates an unverified calendar authority and maintenance burden.
- Runtime provider or internet calendar queries: rejected because freshness must work offline and remain provider-neutral.
