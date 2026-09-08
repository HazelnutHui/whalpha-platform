# ADR 0170: Resolve corporate actions by exact event date

- Status: Accepted
- Date: 2026-09-08

## Context

ADR 0169 completed 70,099 real split/dividend source observations over the
304-session canonical EOD interval. The source is broader than the canonical
stock Identity population: it includes 1,668 split tickers and 13,759 dividend
tickers, including securities outside current active listings and the product
Universes.

A read-only pre-mapping census found 39 observations on dates without an exact
canonical Identity session: one split and 38 dividends. On dates with exact
Identity, direct provider-ticker lookup resolves 708 split rows and 41,341
dividend rows; 1,240 split and 26,771 dividend rows have no same-day resolver
match. Using the latest resolver, a prior/later trading session, ticker name,
or current Universe to raise those ratios would introduce survivorship and
identity leakage.

The source endpoint does not expose a defensible historical publication time
or revision number. The first package is one observation baseline, not proof
that revision `1` was the provider's first historical state.

## Decision

Build a disconnected, network-prohibited, owner-only `/tmp` resolution shadow
with the following rules:

- formally reread both exact ADR 0169 packages and bind both manifest hashes
  and logical fingerprints;
- bind one already-published point-in-time Identity family-evidence manifest;
- for each event on an Identity session, verify the exact snapshot completion
  manifest plus its Resolver manifest/Parquet physical hashes against that
  family evidence, then validate the Resolver schema, content fingerprint,
  provider, date, row count, ticker uniqueness, and stable-ID types;
- resolve only by the exact event-date provider ticker;
- quarantine a date without exact Identity as
  `event_date_identity_unavailable` and a missing same-day ticker as
  `unresolved_ticker`; never substitute a nearby or latest resolver;
- fail rather than drop any source row that cannot be represented by the typed
  source-observation contract;
- preserve one output record per source row, source-page observation time, and
  deterministic provider action ID;
- use local observation revision `1` only as the baseline for this one isolated
  shadow and prohibit canonical promotion until repeat-observation diff and
  append-only revision rules exist;
- partition mapped observations by event year using the existing provider-
  neutral Parquet repository, then bind every partition in one shadow manifest;
  and
- formally reread all output files and aggregate counts before success.

The shadow records zero network requests, canonical writes, Adjustment Ledger
writes, analytics, publication, deployment, and scheduler changes. A resolved
row proves a same-date technical identity link only. It is still
`first_observed_only` and is not point-in-time signal eligible.

## Consequences

- Resolution quality is measured honestly over the provider's broad source
  population without shrinking the denominator to the current Universe.
- Every accepted stable ID is traceable to one exact Resolver snapshot and the
  published Identity family evidence.
- Non-session events and unmatched tickers remain visible quarantine rather
  than disappearing or being guessed.
- The next stage can review action semantics, cross-event conflicts, and repeat
  package revisions before proposing canonical Corporate Action.
- No Adjustment Ledger work begins until source observations, identity,
  revisions, and event ordering are separately reconciled.

## Rejected alternatives

- **Latest-ticker resolution:** creates survivorship and symbol-change leakage.
- **Nearest-session fallback:** hides the absence of exact event-date identity
  and can cross an action boundary.
- **Current-Universe filtering:** discards source evidence based on a later
  product policy rather than event-time identity.
- **Direct canonical publication:** promotes a single late observation without
  revision or availability evidence.
