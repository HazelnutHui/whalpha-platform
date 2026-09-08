# ADR 0172: Stage split adjustments before dividend total return

- Status: Accepted
- Date: 2026-09-08

## Context

ADRs 0169–0171 now provide two complete same-scope Massive split/dividend
observations, exact-event-date Identity resolution, and a short-interval
zero-delta comparison. That evidence is sufficient to review adjustment
semantics, but it is not yet a canonical Corporate Action family or an
Adjustment Ledger.

Massive's current split documentation defines `historical_adjustment_factor`
as a cumulative factor relative to a later/current share basis. Its dividend
documentation likewise defines `split_adjusted_cash_amount` on a later split-
adjusted share basis. A provider cumulative factor therefore cannot be copied
into a ledger whose explicit basis session is 2026-09-04. Doing so can include
actions after that basis and create a wrong or future-dependent transformation.

The real source also contains unresolved rows, multi-event dates, non-USD
dividends, and same-date split/dividend combinations. Treating all instruments
without one resolved event as neutral would silently classify potentially
affected histories as clean.

## Decision

Proceed in two bounded stages.

1. Build and validate a split-only, outcome-reconciliation candidate before
   any dividend total-return implementation.
2. Derive each split price multiplier from the event ratio `from / to` and its
   volume multiplier from `to / from`. For a source session `s` and explicit
   basis session `B`, compose only events satisfying `s < effective_date <= B`.
3. Group all split-like events by stable `instrument_id` and effective date
   before composition. This preserves reciprocal or multiple same-date events;
   source response order is never treated as legal event order.
4. Use provider cumulative factors only as audit evidence. Never use them as
   the calculation input for a target-basis ledger.
5. Keep every stable ID that is a plausible historical match for an unresolved
   split row non-clear. Historical ticker matches may identify a conservative
   quarantine set, but they must never promote or assign the unresolved event.
6. Keep total-return adjustment unavailable until USD/currency handling,
   split-adjusted cash reconciliation, same-date ordering, special
   distributions, and dividend price continuity are separately validated.
7. Keep raw canonical EOD immutable. Any future Adjustment Ledger is a derived
   family keyed by stable ID, source session, basis session, and methodology.
8. The first implementation remains owner-only below `/tmp`, network-
   prohibited, formally reread, and explicitly non-canonical. A separate
   inventory-bound review is required before any `/data` publication.

This decision narrows the next implementation; it does not make historical
research ready and does not authorize a strategy, Snapshot, bundle, deployment,
or Production change.

## Consequences

- Split continuity can advance independently of the more ambiguous dividend
  total-return layer.
- The current-basis provider factor remains useful for diagnostics without
  contaminating the target-basis calculation.
- A conservative unresolved-impact quarantine prevents false neutral factors.
- Fixed-basis adjusted prices remain unsuitable for raw-dollar, price-floor,
  liquidity, or volume features until feature-specific leakage review is
  complete.
- Canonical Corporate Action, lifecycle, historical Membership, costs, final
  Coverage, and chronological evaluation remain separate gates.

## Execution evidence

The first real candidate completed on clean Dell main
`2e4e1f21f09c357180f3ac6f67ef82f709ed6b32`. It formally reread all 1,949
split-like observations and all 304 evidence-bound historical Resolvers. The
result contains 708 resolved stable-ID/date groups from 709 source rows, one
multiple-action date, and 43 possible-impact stable IDs derived from 41
unresolved rows with historical ticker presence. Another 1,199 unresolved rows
have no historical Identity presence; two rows have multiple historical stable-
ID candidates.

The owner-only output is one 564,826-byte file with SHA-256
`83e8a3722132bd2172e0546e3d8fb84a5a5cece6e289a2b1c3744e1e8d175618`
and logical fingerprint
`b3efa16da5570cddf41f7fc741d71a29e73e6a1f696f68828b2f5e67b596d226`.
A separate formal reread passed. The post-run context report kept `/data` and
Production unchanged, and research readiness remains `data_blocked`.

## Rejected alternatives

- **Copy the provider historical factor:** its cumulative basis can extend
  beyond the requested ledger basis.
- **Treat every unresolved row as irrelevant:** 41 unresolved split rows have
  a ticker present elsewhere in historical Identity and can plausibly affect
  43 stable IDs.
- **Implement dividend total return together with splits:** currency and
  same-date ordering ambiguities would make a simpler split result harder to
  audit.
- **Overwrite EOD with adjusted values:** destroys the received raw series and
  its provenance.
