# ADR 0169: Stage corporate-action source before adjustment

- Status: Accepted
- Date: 2026-09-08

## Context

The historical research foundation has complete current EOD and same-date
Identity evidence, but it does not yet have real corporate-action observations
or an Adjustment Ledger. The existing network-free Massive fixture mapper and
Decimal adjustment invariants prove only the typed mapping and arithmetic
boundaries. They do not prove current endpoint access, complete pagination,
source field stability, event coverage, point-in-time identity, or revision
history.

Massive now exposes dedicated `/stocks/v1/splits` and
`/stocks/v1/dividends` endpoints. The earlier entitlement probe reached the
deprecated V3 endpoints with `limit=1`; that evidence must not be treated as a
successful V1 acquisition. Download, stable-ID resolution, canonical event
construction, and adjustment calculation therefore need separate gates.

The generic Historical Pilot package and inactive-lifecycle source package
have different frozen scopes and ceilings. Weakening either accepted contract
would obscure their evidence.

## Decision

Add one focused, reusable source-custody implementation with two explicitly
separate package kinds: `split` and `dividend`.

Each package:

- covers one inclusive historical date range using `execution_date` or
  `ex_dividend_date` as the provider filter;
- uses the documented V1 endpoint, 5,000-row page limit, ascending effective-
  date order, at most 16 pages / 80,000 rows, 32 MiB per page, and 512 MiB per
  package;
- performs serial requests with at least 15 seconds between calls and no
  automatic retry;
- stores each sanitized page immutably below `/tmp`, then atomically advances
  an owner-only checkpoint;
- resumes only after formal reread of the checkpoint and every retained page;
- may adopt exactly one orphan page only if its content and request binding
  match the expected next request;
- removes provider request IDs and pagination URLs, rejects credentials or
  Authorization material recursively, and retains only credential-free cursor
  parameters and hashes required for recovery and request-chain proof;
- rejects host, endpoint, filter, limit, sort, valid-date range, or page-order
  drift;
- preserves provider result fields as source evidence and counts unexpected
  fields instead of silently erasing future schema additions; and
- supports a naturally complete zero-row result without inventing an event.

Split and dividend packages remain separate so either source can be recovered,
reviewed, or rejected independently. A later adapter must formally read both
packages, resolve tickers against the exact event-date Identity view, preserve
unresolved or ambiguous rows as quarantine, and represent repeated provider
observations as append-only revisions.

The implementation records zero canonical writes, Adjustment Ledger writes,
analytics, publication, deployment, and scheduler changes. It is not a
corporate-action coverage claim. Absence of a provider row is not proof of no
event until separate range/source completeness and revision policy pass.

## Consequences

- The first real V1 sample can verify entitlement, fields, pagination, counts,
  date scope, and source custody without contaminating `/data`.
- Network interruption does not require already verified pages to be fetched
  again.
- Provider cumulative adjustment factors remain source evidence. They cannot
  be copied into the WH Alpha Adjustment Ledger without event ordering,
  comparison-basis, and independent Decimal reconciliation.
- Symbol changes, mergers, spinoffs, delistings, successor identity, and
  terminal consideration remain outside these two endpoints and continue to
  block complete lifecycle/research readiness.
- Hitting any ceiling is a stop condition requiring evidence-based review; it
  is not permission to increase the limit automatically.

## Rejected alternatives

- **Map live responses directly into canonical rows:** loses recoverable source
  custody and mixes provider observation with stable-ID decisions.
- **Use adjusted provider bars as the ledger:** hides event ordering and makes
  independent arithmetic/revision verification impossible.
- **Expand the frozen Historical Pilot package:** changes evidence already
  accepted for a different bounded purpose.
- **Treat the old V3 limit-one probe as V1 proof:** confuses endpoint generation,
  full pagination, and body-shape evidence.
