# ADR 0262: Bind Corrected-Terminal Listed Reference through Stable-Security Evidence

## Status

Accepted.

## Context

ADR 0261 retained three SCS consideration alternatives and the contractual
mixed default, but HNI remained a source-local locator. A ticker match or the
source calculation reference price cannot assign the listed consideration
security or value a later daily reference.

## Decision

1. Bind the SCS source definition of HNI Corporation and HNI common stock to
   the official SEC Submissions root for CIK `0000048287`, ticker `HNI`, and
   NYSE, including the exact event-day HNI filing row.
2. Assign the HNI consideration security only when the same CIK, ticker,
   exchange, common-stock form, currency, valid quality state, and stable
   `instrument_id` agree in the 2025-12-10 historical Instrument Master.
3. Formally reread the same-session canonical EOD partition and require one
   valid latest-revision USD HNI row. Use its unadjusted close as the daily
   reference boundary for all three alternatives.
4. Use the mixed alternative as the primary no-action research reference and
   retain cash and stock alternatives as sensitivity. Do not infer the actual
   holder election, adjustment mechanics, execution price, settlement amount,
   strategy return, or canonical terminal outcome.
5. Keep the SEC snapshot and canonical partition custody times explicit. They
   are reconstruction and label evidence, never historical signal knowledge.
6. Write one immutable owner-only evidence package. Do not write `/data`,
   Historical Coverage, research admission, Candidate, publication,
   deployment, or scheduler state.

## Consequences

SCS gains one strict listed-security assignment and three gross daily
reference values without weakening the outcome boundary. The next terminal-gap
census must consume this package as a versioned extension; it may not rewrite
the prior V2 report or count the three alternatives as three securities.
