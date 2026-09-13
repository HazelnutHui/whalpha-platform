# ADR 0223: Freeze the First-Strategy Cross-Venue Source Sample

- Status: Accepted
- Date: 2026-09-13

## Context

ADR 0221 identifies the unresolved action and lifecycle cases that can affect
the first Strong-Leader Pullback development population. Continuing to compare
data vendors against a global unresolved universe would spend time on cases
outside the registered strategy and make provider selection subjective.

The scoped evidence contains 20 unassigned action/instrument relations across
four candidate stable IDs and 64 stable IDs whose five-session label paths
cross the last canonical observation. The two ID sets do not overlap. All 64
lifecycle cases retain a share-class FIGI, CIK, primary exchange, source type,
and one ticker locator from the inactive-source custody. Those fields can
locate records in another source, but they do not prove lifecycle or terminal
outcomes.

## Decision

1. Persist one immutable, owner-only, provider-neutral acceptance sample that
   contains every one of the 20 action relations and every one of the 64
   lifecycle crossing IDs. Do not rank, subsample, or inspect outcomes.
2. Action cases retain source action ID/revision, action type and date, source
   ticker locator, candidate stable ID, one/multiple-candidate state, existing
   inactive/FINRA leads, and affected feature/label counts. Candidate identity
   remains unassigned.
3. Lifecycle cases retain stable ID, source anchors and occurrence hashes,
   FIGI/CIK/ticker/name/exchange/type locators, canonical observed span,
   provider delisting-date candidate, and 1/3/5-session crossing counts. None
   is a canonical last-trade, delisting, successor, consideration, or terminal
   fact.
4. Bind the sample to the exact ADR 0221 blocker census and both formally
   reread inactive-lifecycle anchors. Require complete one-to-one recovery of
   source occurrences for every lifecycle case.
5. Freeze the requested action evidence fields: stable security/listing IDs,
   provider event ID and revision chain, announcement/effective/ex/record/pay
   dates as applicable, exact ratio or consideration, action status/type,
   predecessor/successor identities, source availability time, and correction
   or cancellation history.
6. Freeze the requested lifecycle evidence fields: stable security/listing
   IDs, first/last tradable dates, suspension and delisting status/effective
   dates, termination reason, predecessor/successor/acquirer, cash/stock
   consideration, bankruptcy/liquidation/OTC continuation, source availability
   time, and revision history.
7. A provider pilot must return explicit matched, absent, unsupported, and
   conflicting states. First-non-null merge, ticker-only assignment, current
   status projected backward, and silent row loss are prohibited.
8. The sample performs no provider request and stores no credential. A later
   source pilot remains a separately reviewed adapter/read-only acquisition
   step and grants no canonical write, Historical Coverage, research,
   Candidate, publication, or Production authority.

## Consequences

- Free, existing, trial, and paid sources can be compared against the same
  finite cases and field-level acceptance gates.
- Provider selection can be driven by measured strategy blockers rather than
  brand, headline coverage, or global row counts.
- A source may still fail even with a high match rate if it lacks historical
  revisions, availability timestamps, terminal consideration, or exact
  security identity.
- The sample remains safe to retain locally because it contains normalized
  evidence locators and hashes, not credentials or provider response bodies.

## Rejected alternatives

### Query every unresolved corporate action first

Rejected because most of the 112,943 global unresolved rows do not intersect a
declared first-strategy path.

### Test only a hand-picked easy subset

Rejected because post-census selection could hide the hardest lifecycle and
identity cases.

### Promote the inactive-source ticker or FIGI into a terminal fact

Rejected because those identifiers locate a candidate record but do not prove
last tradability, reason, successor, consideration, or source-time validity.
