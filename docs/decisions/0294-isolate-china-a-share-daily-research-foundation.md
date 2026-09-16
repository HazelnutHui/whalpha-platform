# ADR 0294: Isolate a China A-Share Daily Research Foundation

## Status

Accepted

## Date

2026-09-16

## Context

WH Alpha intends to research China A-shares alongside U.S. equities. The two
markets can share the same governed Factor Discovery -> Model Construction ->
Strategy Expression method, but they cannot share market assumptions or
silently merge data. A-shares have different calendars, settlement, price
limits, risk-warning states, suspensions, boards, listing lifecycles, corporate
actions, identifiers, costs, and source semantics.

The first intended use is daily, multi-session factor and swing-strategy
research, not intraday execution simulation. Free sources can support a useful
foundation, but no individual free API proves every point-in-time identity,
tradability, lifecycle, adjustment, or availability fact. Treating a convenient
adjusted-price endpoint as a complete backtest database would create hidden
survivorship, look-ahead, and executability errors.

## Decision

Build a separately governed `china_a_share` research foundation on the
workstation with these boundaries:

1. U.S. and A-share raw, normalized, canonical, research, and serving assets
   use distinct namespaces, manifests, stable IDs, calendars, rules, and
   admission decisions. No cross-market union is implicit.
2. The initial target is five years of daily evidence for multi-session
   research. This horizon is a scope boundary, not a claim that every factor
   should use the same lookback or that five years covers every regime.
3. Raw daily prices remain unadjusted. Provider adjustment factors are retained
   as source observations and cannot authorize returns until their direction,
   corporate-action coverage, and revision semantics are reconciled.
4. Stable `instrument_id` is the research join key. Codes, names, prefixes, and
   current listings may generate review candidates but may not prove board,
   security form, historical existence, or eligibility.
5. The first source composition is:
   - BaoStock for primary free daily source observations;
   - AKShare-mediated public datasets for independent cross-check and source
     discovery, never silent first-non-null fallback;
   - exchange and CNINFO publications for authoritative rules, disclosures,
     and lifecycle/corporate-action evidence when available;
   - optional Tushare or paid sources only as later evidence extensions, not as
     prerequisites for starting the free pilot.
6. Every conflict remains explicit. A secondary source may corroborate or
   challenge a primary observation but cannot overwrite it. Unknown,
   unavailable, ambiguous, or heuristic-only records remain quarantined.
7. Daily research admission requires all 13 declared foundation families to be
   complete for the exact target interval and population. Source acquisition,
   a successful pilot, or a complete price file alone grants no backtest,
   model, Candidate, publication, deployment, or trading authority.
8. Exact limit-up/limit-down behavior, ST subtype, suspension state, lot size,
   fees, and T+1 rules are effective-dated data. They are not inferred from
   today's rules or names.
9. The adapter layer performs no implicit login, network startup, canonical
   write, or Product publication. Live acquisition and persistence require a
   separately bounded operation and report.
10. Research involving cross-market factors may later consume separately
    admitted artifacts from both markets, but it must preserve each market's
    cutoff, calendar, currency, and source lineage.

The exact contract is [China A-Share Daily Research Foundation V1](../data-contracts/china-a-share-daily-research-foundation-v1.md),
and the physical design is [China A-Share Research Foundation V1](../architecture/china-a-share-research-foundation-v1.md).

## Consequences

- A useful free-data pilot can start without claiming the five-year database is
  already complete.
- Existing U.S. Production, Candidate data, research ledgers, and `/data`
  publications remain unchanged.
- Provider limitations become visible admission blockers instead of hidden
  imputations.
- Initial implementation is slower than downloading one adjusted-price table,
  but later factors share a reproducible, point-in-time-aware base.
- Intraday queue position, order-book fills, and limit-board microstructure are
  outside the admitted scope until separate evidence exists.

## Alternatives considered

### Reuse the U.S. schema and append an exchange column

Rejected because shared field names would conceal materially different
tradability, lifecycle, rule, and adjustment semantics.

### Use one free API as canonical truth

Rejected because free APIs have different coverage, revisions, failure modes,
and authority. Convenience does not establish completeness.

### Delay all A-share work until a paid institutional source is available

Rejected because the daily research architecture, source observations,
quarantine rules, and bounded pilot can be built and tested professionally
with free evidence. Paid data should extend an explicit gap, not replace the
architecture.
