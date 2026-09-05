# ADR 0147: Stage inactive lifecycle source with resumable custody

- Status: Accepted
- Date: 2026-09-05

## Context

ADR 0146 proved that the inactive All Tickers source exceeds 20,000 rows and
cannot be sized responsibly by repeatedly increasing an aggregate-only census.
The source appears useful, but its rows are provider observations rather than
canonical lifecycle facts. Download time is externally rate-limited, and a
network interruption must not force already verified pages to be fetched
again.

The existing same-day Identity package assumes `active=true`, and the original
Historical Pilot package is bound to a six-page inactive ceiling. Weakening
either contract would change previously accepted semantics.

## Decision

Add a separate inactive-lifecycle source package with these boundaries:

- exactly one historical anchor and `active=false` All Tickers scope;
- at most 100 pages, 100,000 rows, 8 MiB per sanitized page, and 512 MiB of
  sanitized page content per package;
- one shared 15-second serial limiter and zero automatic retries;
- each completed page is immutable, hashed, fsynced, and recorded in an atomic
  checkpoint before the next request;
- interruption resumes only after the checkpoint and every retained page pass
  formal reread; an exact page written immediately before a checkpoint crash
  may be adopted only when its derived request binding matches;
- provider `request_id`, credentials, Authorization material, and pagination
  URLs are not retained; credential-free cursor parameters and hashes remain
  only inside the owner-only package to support resume and request-chain proof;
- the completed package is owner-only below `/tmp`, content-addressed by page
  and logical fingerprints, and fully reread before success;
- source results retain their original provider fields inside temporary source
  custody, including ticker and stable identifiers, because later mapping must
  be evidence-based rather than inferred from aggregates; and
- canonical Apply, `/data` writes, lifecycle resolution, analytics,
  publication, deployment, and scheduler transitions remain zero.

The package explicitly records `outcome_reconciliation_only`. Observation now
does not prove when the source originally published or made a historical fact
available. `delisted_utc` is an effective-date candidate, not last tradable
session, reason, successor, or terminal consideration.

## Consequences

- A long, rate-limited download can recover safely after loss of network or
  process interruption without accepting an unverified partial package.
- Full physical source coverage can be measured once instead of issuing more
  discard-only censuses.
- The next offline stage may normalize and resolve observations by stable
  identity, while quarantining duplicate tickers, missing stable identifiers,
  conflicts, and unsupported terminal facts.
- The 100-page/100,000-row limits are safety ceilings, not expected counts. A
  hit stops the operation and requires a new evidence-based review.

## Execution evidence

Clean main revision `0c957d72d599179af425be6a59a225071947dabb`
completed the `2026-07-16` anchor naturally in 24 requests / 23,260 rows. The
last page contained 260 rows. Formal reread passed for all 26 package files,
6,644,157 physical bytes, owner-only modes, zero symlinks, exact request chain,
and logical fingerprint
`5b298512378f80fc5e72eb90bf05b588feb91c1ea1caedd802c8d54ac8cee7fb`.
The package remains under `/tmp`; `/data` and Production were unchanged. A
second exact package at the latest canonical EOD anchor `2026-09-03` then
completed in 24 requests / 23,469 rows with logical fingerprint
`8ae15be74aa8c554ab83075346f93c3d966cec72811d47375f53a91a8734ff98`.
It closes the source observation window through the current price-history end
without changing either package's research eligibility.
