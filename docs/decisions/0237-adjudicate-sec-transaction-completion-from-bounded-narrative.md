# ADR 0237: Adjudicate SEC Transaction Completion from Bounded Narrative

- Status: Accepted
- Date: 2026-09-13

## Context

ADR 0236 linked 61 sampled common-equity instruments to structured Form 8-K
covers but deliberately left narrative transaction facts unresolved. The
cover `DocumentPeriodEndDate` is not a reliable transaction date: nine frozen
documents report a completion one to four calendar days later. Full-document
date searches also encounter agreement, tender-expiry, debt, maturity,
financing, and historical-reference dates.

The prior transaction-candidate scope can include intervening sections when
an introduction precedes Item 1.01 or 1.02. That scope remains valid as an
immutable lexical candidate package, but it is too broad for selecting a
transaction-completion date.

## Decision

1. Adjudicate only the 61 registered Item 2.01 documents already matched by
   point-in-time common-equity cover identity.
2. Build a new bounded narrative scope from the introduction and Item 2.01,
   excluding every intervening item. Permit an implicit pre-item introduction
   only when one node contains both a named closing date and an explicit
   completion statement.
3. Apply four finite rules in priority order: named Closing Date, explicit
   closing-of-merger date, dated completion statement, and dated tender
   acceptance followed by an effected merger.
4. Require one unique date at the highest supported rule. Preserve multiple
   dates as ambiguous and missing evidence as unsupported; never fall through
   merely to obtain coverage.
5. Treat the cover report date as comparison-only and retain every mismatch.
   Do not equate offer expiry, issuer completion, trading cessation, exchange
   delisting, or terminal return.
6. Publish only immutable source evidence. Keep termination reason,
   consideration, parties, tradability, lifecycle, terminal, research,
   Candidate, and Production authority at zero.

## Consequences

- The frozen population can distinguish issuer transaction completion from
  cover-report timing without hand-coded case dates.
- Intervening financing and debt sections cannot contaminate the selected
  completion date.
- Listing termination and terminal-return work remains independently testable
  rather than inheriting an issuer-event date.

## Rejected alternatives

### Use `DocumentPeriodEndDate` as completion date

Rejected because it is observably earlier in nine retained cases.

### Search the entire Form 8-K and choose the nearest date

Rejected because proximity cannot distinguish agreement, offer, financing,
filing, maturity, or historical-reference dates from completed transactions.

### Hard-code the 61 observed dates

Rejected because case-specific answers are not a reproducible source rule and
cannot fail closed on future evidence.
