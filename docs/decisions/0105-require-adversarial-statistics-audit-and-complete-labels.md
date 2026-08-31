# ADR 0105: Require Adversarial Statistics Audit and Complete Labels

## Status

Accepted

## Date

2026-08-31

## Context

ADR 0104 freezes the first fixture-only statistical plan before real labels
exist. Passing a favorable synthetic example is insufficient evidence that the
implementation fails safely under no effect, regime reversal, clustered
crowding, outliers or selective missingness.

The first adversarial pass exposed one concrete weakness: incomplete labels
were visible in coverage fields, but a large enough favorable remainder could
still pass the registered return gates. Every fixture report denied authority,
so no real transition was possible, but the future activation boundary should
not rely on that final disclaimer alone.

## Decision

Add an independent descriptive Oracle that imports the public contracts but
does not call the primary statistics evaluator or its private helpers. It
recalculates, for all parameter/horizon summaries:

- signal/control assignment and disposition counts;
- coverage;
- paired-session count;
- Market Regime counts;
- evidence-floor status;
- mean, median, SPY-relative median, hit rate, MFE and MAE; and
- the session-balanced signal-minus-control mean.

Keep bootstrap verification structurally separate: analytically check constant
contrast cases with exact expected interval/probability, then use behavioral
adversarial cases rather than copying the same pseudorandom implementation
into the Oracle.

Add independent data-quality gates in validation and holdout. Validation
requires inferentially complete three-session evidence and `1.0000` available
signal/control coverage for every member of the 24-combination family used by
Holm correction. Holdout requires `1.0000` available coverage for the locked
signal/control contrast. A missing, pending, unavailable or quarantined label
makes the stage fail even if every registered return gate passes. A future
policy that permits incomplete coverage requires a new version with an
explicit missingness mechanism and sensitivity analysis.

The synthetic adversarial suite must cover at least:

- stable positive effect;
- null effect;
- validation-period reversal;
- one-session crowding;
- one-session extreme positive outlier;
- differential missingness;
- cross-split leakage;
- unlocked holdout access; and
- failed-validation holdout access.

## Consequences

- Descriptive calculations now have an independently implemented reference.
- A favorable remainder cannot hide missing or quarantined cohort labels at a
  validation or holdout transition.
- Cross-sectional volume on one day cannot satisfy the 20-session evidence
  floor.
- One extreme day cannot rescue a non-positive median after the fixed cost
  scenario.
- The Oracle does not independently prove the moving-block bootstrap algorithm
  for every arbitrary series. That limitation is explicit; a future formal
  inferential Oracle may be added before real development activation.
- No real data, stage transition or performance claim is created.

## Alternatives Considered

### Accept any coverage above the 60-observation floor

Rejected because selective missingness can bias results even when the remaining
sample is large.

### Add a 90% or 95% coverage threshold

Rejected for V1 because either threshold is arbitrary without a modeled
missingness mechanism. Complete coverage is the clearer fail-closed boundary.

### Duplicate the bootstrap implementation line for line in the Oracle

Rejected because two copies of the same algorithm can reproduce the same bug.
