# ADR 0272: Register One Coverage-Corrected Replacement Selection Protocol

## Status

Accepted

## Date

2026-09-15

## Context

The immutable Strong-Leader Pullback V1 development report completed its exact
24 × 3 × 3 matrix and returned `inconclusive_evidence_floor`. Twenty-three of
24 primary combinations met the general signal, control, and comparable-
session inference floors, but only one met the existing per-combination
reported-Regime floor. Nineteen combinations produced between one and 47
Defensive signals, below 60. No Validation or Holdout data was accessed.

The V1 hypothesis asks whether the setup improves the general same-session
leader/control contrast. It does not require the setup to produce an
independently estimable effect in every Regime. Treating a sparse descriptive
Regime cell as a global selection failure is therefore stricter than the
primary hypothesis. The original implementation also lets a zero-count Regime
avoid that floor while one observation triggers failure, which is not a useful
definition of overall evidence eligibility.

Editing V1 after its result would be invalid. Abandoning the whole family
without distinguishing primary evidence from a sparse subgroup would also
waste a valid development-stage diagnostic.

## Decision

Register exactly one replacement selection protocol, version 2.0.0, over the
same immutable V1 development report and unchanged 24 parameter combinations.
This is a second protocol trial, not a rewrite or successful result for V1.
Its design uses only retained coverage, disposition, and selection-state
fields; development return values were not inspected for its design.

All 24 combinations remain in the trial ledger. Eligibility becomes per
combination: at least 60 numeric signals, 60 numeric controls, 20 comparable
sessions, inference in all three terminal-endpoint scenarios, and no
unavailable evidence anywhere in the primary family. An ineligible
combination remains reported but cannot win; it no longer blocks every other
complete combination.

Regime is a prespecified stability and interaction view, not a primary
selection gate. Every Regime count and descriptive contrast remains visible,
but a Regime-specific inference or claim requires at least 60 signals. A
sparse Regime is `inconclusive`, never favorable, adverse, or silently absent.

Each endpoint scenario ranks the common eligible set using the unchanged
three-session lower-90%-bound objective and existing tiebreaks. A lock requires
the same winner in all three scenarios plus all of these prespecified
robustness gates:

- adverse-endpoint lower 90% contrast is strictly positive;
- median SPY-relative signal return after 25 bps per side is strictly positive;
- first- and second-half mean contrasts are each strictly positive;
- more than half of paired sessions have a positive contrast; and
- the largest absolute session contribution is at most 20%.

The replacement run budget is one. Failure or instability retires this
selection attempt; another rule change over the same development result is
not allowed. If it locks one combination, a separate formal review is still
required before constructing or accessing Validation labels.

To account for the original and replacement protocol trials, Validation keeps
the complete 24-member multiplicity family and tightens the family-wise alpha
from 0.10 to 0.05. Validation cannot change the lock. Holdout remains sealed,
single-use, and locked-combination-only after all Validation gates pass.

The machine policy fingerprint is
`9fa09e0b627aed2c1bb1f108eec2d73bfeb3a5407b3c0850b3605b23ef0991f9`.

## Consequences

- V1 remains permanently inconclusive and reproducible.
- The replacement is an explicitly counted adaptive development analysis,
  not an independent confirmation.
- Sparse market states cannot manufacture either a pass or a universal
  failure, and they cannot support a Regime claim.
- The rules may still reject the family before Validation; that is an expected
  result rather than a reason to create an unbounded V3.
- Validation, Holdout, Candidate activation, publication, deployment, and
  Production remain unauthorized until their later gates are satisfied.

## Alternatives Considered

### Lower the V1 Regime floor

Rejected because V1 has already read development outcomes and must remain
immutable.

### Ignore Regime evidence entirely

Rejected because market-state stability is useful evidence; sparse cells need
an explicit inconclusive status rather than deletion.

### Keep changing protocols until one parameter locks

Rejected because that would turn the development set into an unbounded search
and make later p-values and Holdout language misleading.
