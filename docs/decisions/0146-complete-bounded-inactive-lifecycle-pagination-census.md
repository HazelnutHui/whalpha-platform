# ADR 0146: Complete a bounded inactive lifecycle pagination census

- Status: Accepted
- Date: 2026-09-05

## Context

The earlier two-page probe and six-page census proved Massive account access
and useful inactive-security fields, but both stopped with another page still
available. The historical Identity history contains only active records and no
supported first-trade, last-trade, validity-end, or terminal-reason facts.
Across 298 adjacent source-session pairs it can identify 904 disappearances
and 247 ticker changes, but disappearance is not evidence of delisting and a
ticker change is not by itself a lineage conclusion.

Designing canonical lifecycle storage from a truncated sample risks an
incorrect completeness claim and unnecessary schema churn.

## Decision

Add a separate aggregate-only completion census for the exact historical
anchor `2026-07-16`. It follows natural pagination with these hard bounds:

- Massive `/v3/reference/tickers`, `market=stocks`, `active=false`;
- exact anchor, 1,000 rows per page, ticker-ascending order;
- same-host, same-path and unchanged-scope pagination validation;
- no automatic retry and at least 15 seconds between requests;
- at most 20 requests and 25,000 results;
- no response body, ticker, identifier, URL, request ID, or credential
  retention/output; and
- zero `/data`, canonical, analytics, publication, deployment, or scheduler
  writes.

The CLI requires a clean source revision and explicit `--execute`. ADR 0120's
standing Dell-local acquisition direction replaces repeated per-run chat
acknowledgements; it does not relax any technical boundary.

`completed` means only that provider pagination ended within both ceilings.
It does not prove terminal reason, last tradable session, successor identity,
point-in-time availability, canonical lifecycle coverage, or research
readiness.

## Consequences

- Exact pagination size and aggregate field coverage can guide the next source
  observation contract without retaining a partial source dataset.
- `truncated_at_ceiling` or `record_ceiling_exceeded` stops schema work pending
  a new bounded review.
- A completed census permits design work only. Source custody, stable-ID
  resolution, canonical Apply, Historical Coverage and model use remain
  separate transitions.

## Execution evidence

Clean main revision `d582c5817e44ee3dc4d9fa4ad3ece5e90d046673`
executed the aggregate-only census for `2026-07-16`. All 20 pages were full:
20,000/20,000 observations had `active=false`, 19,565 had `delisted_utc`, all
20,000 had `last_updated_utc`, and 124 ticker values were duplicated. Another
page remained, so the exact result is `truncated_at_ceiling`, not completed.
No response body or row identifier was retained and the operation wrote no
data. The next step is a separately reviewed streaming source-custody boundary,
not another arbitrary increase to an aggregate probe ceiling.
