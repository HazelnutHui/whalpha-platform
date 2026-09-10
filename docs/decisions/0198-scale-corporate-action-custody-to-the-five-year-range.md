# ADR 0198: Scale Corporate-Action Custody to the Five-Year Range

- Status: Accepted
- Date: 2026-09-10

## Context

ADR 0169 deliberately limited each Massive split or dividend source package to
16 pages / 80,000 rows and a 15-second request interval while the account was
on the rate-limited Basic plan.  The first 15-month dividend observation used
14 pages / 68,150 rows.  A five-year request will therefore exceed the old
row/page ceiling even when pagination is healthy.

Stocks Starter is now the active provider plan.  Its observed EOD and
reference access no longer has the Basic five-calls-per-minute limit.  Keeping
the old package ceiling would force arbitrary annual source packages and a new
merge contract before exact-date identity resolution.  Raising limits without
retaining an explicit finite bound, exact pacing, or legacy read support would
weaken custody instead.

## Decision

Add source-package contract 1.1 for one exact five-year split or dividend
range while continuing to read contract 1.0 unchanged.

Contract 1.1:

- retains the existing 5,000-row page size, ascending effective-date order,
  immutable sanitized pages, exact request chain, per-page checkpoint, formal
  reread, zero automatic retry, 32 MiB page limit, and 512 MiB package limit;
- raises only the finite pagination/record ceilings to 80 pages / 400,000
  rows, based on the observed 15-month dividend density;
- accepts one explicit serial request interval from 0.25 through 15 seconds
  and persists its canonical decimal representation in the checkpoint and
  completed manifest;
- refuses a resumed partial package if the requested interval differs; and
- continues to remove request IDs, pagination URLs, credentials, and
  Authorization material from retained content.

The command defaults to a 0.25-second serial interval for the paid Starter
plan.  It does not introduce request concurrency.  Existing 1.0 packages keep
their 16-page / 80,000-row / 15-second interpretation and fingerprint.

Hitting any 1.1 ceiling remains a stop condition.  It requires a measured
review rather than another automatic increase.  The package remains source
observation only and does not authorize canonical Corporate Actions,
adjustments, total return, Historical Coverage, research, Production, or web
publication.

## Consequences

- One split package and one dividend package can represent the same exact
  five-year interval expected by the existing exact-date resolution boundary.
- Annual packages already acquired during the ceiling diagnosis remain useful
  independent overlap observations; they are not silently merged or promoted.
- Legacy real packages and their existing canonical lineage remain readable.
- Provider speed improves source acquisition, but no knowledge-time or
  lifecycle gap is reclassified by entitlement.

## Acceptance boundary

The change is complete when focused tests prove more than 16 pages, exact
interval persistence and resume refusal, a real 1.0 package rereads with its
original fingerprint, and the exact five-year 1.1 split/dividend packages
complete natural pagination below all finite ceilings.
