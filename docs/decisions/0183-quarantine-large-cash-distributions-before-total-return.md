# ADR 0183: Quarantine large cash distributions before total return

- Status: Accepted
- Date: 2026-09-09

## Context

The canonical source-observation publication contains 68,150 cash-dividend
rows, including 41,347 exact-event-date stable-ID resolutions. Those rows are
still a late, first-observed, bounded provider snapshot rather than canonical
Corporate Actions or point-in-time signal evidence.

The current-Secondary price-discontinuity review identified two resolved VISN
cash distributions. The 2026-04-28 USD 10 row matches OCC's ex-distribution
date and the raw price discontinuity. The 2026-08-17 USD 5 row instead uses the
record date as its ex-dividend date. The issuer states that this large
distribution's ex-dividend date was 2026-08-28, after its 2026-08-27 payment;
raw EOD also shows the cash discontinuity on August 28 rather than August 17.

The earlier VISN provider adjustment factor also composes later action state
and is not the single-event factor calculated from the same-basis pre-ex close.
This confirms that provider dates and cumulative factors cannot be copied into
an Adjustment Ledger without independent semantic validation.

## Decision

1. Add a disconnected, network-prohibited, zero-write diagnostic over the
   exact canonical corporate-action source marker and exact canonical EOD
   family evidence.
2. Group resolved dividends only by stable `instrument_id` and reported
   effective date. Never resolve an action by current ticker, name, nearby
   session, or price fit.
3. Admit only a bounded arithmetic candidate when the group is active, a
   single USD dividend, has no same-date split-like action, has both adjacent
   EOD bars, has cash below the same-basis prior close, and has no extreme
   cash-inclusive price contradiction.
4. Treat cash at or above 25% of the prior close as a review threshold, not as
   an exchange-law conclusion. Such a distribution always requires an
   independent actual-ex-date source before canonicalization. A reported
   ex-date on or before its pay date receives an additional date-order review.
5. Quarantine non-USD, multiple-dividend, same-date split/dividend, missing-
   price, non-active, malformed-date, and extreme price-continuity cases.
6. Preserve provider historical adjustment factors for audit only. Compute
   candidate arithmetic only from cash and the same-basis prior close.
7. Keep all unresolved source observations explicit. Neither a passing
   arithmetic candidate nor an absent source row authorizes a canonical
   dividend, total return, factor one, Historical Coverage, or performance.

## Consequences

- The known VISN date-semantic error becomes a deterministic regression
  boundary instead of an undocumented one-off exception.
- Ordinary USD candidates can be quantified without contaminating canonical
  actions or research inputs.
- Special distributions require a source with authoritative actual ex-date
  semantics or a separately governed evidence override.
- The existing split-only Adjustment Ledger remains unchanged and total return
  remains unavailable.

## Rejected alternatives

- **Copy the provider ex-date and factor:** the VISN counterexample proves both
  can use a wrong date or later cumulative basis.
- **Infer the date from the largest price gap:** price response is corroboration
  only and cannot establish a legal event date.
- **Drop large or unresolved rows:** that would turn missing evidence into a
  false neutral total-return factor.
