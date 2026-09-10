# ADR 0195: Require Complete Session Cross-Sections for Reconstructed Development

## Status

Accepted

## Date

2026-09-10

## Context

ADR 0193 required an outcome-blind census before selecting a development
cohort from latest-vintage reconstructed history. The completed census found
437,402 raw-feature-complete Primary paths, but zero paths with every mandatory
evidence family complete. Choosing instruments with better coverage or a
permissive aggregate percentage would create coverage-based survivorship and
let the observed missingness pattern influence the research population.

The frozen V1 experiment already requires at least 252 research sessions and
uses same-session eligible leaders as its primary contrast. Its development
population therefore needs complete cross-sectional comparability at the
session level rather than a hand-picked static stock cohort.

## Decision

The latest-vintage reconstruction uses the complete Primary session
cross-section as its indivisible development-admission unit:

1. A candidate session must contain at least one included Primary path.
2. Every included Primary path in the session must have all mandatory evidence
   complete. The threshold is exactly 10,000 basis points, or 100%.
3. One incomplete or quarantined included path rejects the entire session.
4. Missing, excluded, and quarantined records stay in the census and its
   denominators. Coverage quality may not select stable IDs or create a static
   survivor cohort.
5. At least 252 complete candidate sessions are required, inheriting the
   preregistered V1 history floor rather than choosing a new threshold after
   seeing outcomes.
6. A zero-included session is not admitted and does not satisfy the 252-session
   floor.
7. The decision is made from missingness and evidence status only. Strategy
   triggers, forward outcomes, performance metrics, parameters, validation,
   holdout, and Candidate activation remain inaccessible.

Under the current census, zero sessions satisfy the complete-cross-section
rule. The current evidence is therefore rejected and no cohort or development
authority exists. A later, versioned census may be reviewed only after the
mandatory evidence families are repaired; an admission would require a new
contract version and immutable decision.

## Consequences

- The rule protects the same-session comparison from coverage-based stock
  selection and keeps entrants, exits, and quarantines visible.
- A single unresolved included path is intentionally expensive: it removes a
  session rather than silently changing that session's cross-section.
- The project does not need to invent a 90% or 95% completeness threshold.
- The rule may yield no usable cohort. That is an acceptable falsification of
  the reconstructed development route.
- This decision does not weaken the stronger source-time requirements for
  validation, holdout, model activation, or Production.

## Alternatives considered

### Admit instruments above a coverage percentage

Rejected because coverage-based stable-ID selection creates a survivor-like
population and changes the intended cross-sectional comparison.

### Admit sessions above a lower completeness threshold

Rejected because the threshold would be arbitrary and unresolved records
could systematically cluster around corporate events and terminal outcomes.

### Open outcomes before setting the rule

Rejected because attractive returns could influence which missingness rule is
chosen.
