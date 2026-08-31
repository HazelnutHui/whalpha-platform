# ADR 0108: Independently Reproduce Research Inference

## Status

Accepted

## Date

2026-08-31

## Context

ADR 0105 independently reproduces descriptive statistics but deliberately does
not duplicate the pseudorandom moving-block Bootstrap. Constant-effect cases
prove useful invariants, yet they cannot detect wrong block sampling, quantile
interpolation, centered-null exceedance counting or Holm ordering on an
arbitrary nonconstant series.

## Decision

Extend the independent statistics Oracle to reproduce the registered
five-session circular moving-block inference without importing or calling the
primary evaluator, its private helpers or Python's `random.Random`.

The Oracle implements an independent integer MT19937 state machine compatible
with the frozen current seed boundary. It derives the registered seed, draws
block starts, directly accumulates original and centered sample sums, sorts the
2,000 replicate means, independently interpolates the 5th and 95th
percentiles, and calculates the add-one one-sided centered-null probability.
It separately implements monotone Holm-Bonferroni adjustment across the fixed
family.

The adversarial audit compares exact unrounded Decimal outputs for
nonconstant series of 1, 2, 5, 20, 37 and 53 observations. It also compares
every inferential field exposed by the stable research fixture and all 24
validation-family Holm values. Tests intentionally include counts not divisible
by the five-session block length.

This verifies implementation equivalence, not the economic validity of the
hypothesis, market stationarity, optimality of a block Bootstrap, or future
performance. Both implementations remain fixture-only and non-authoritative.

## Consequences

- Random-state, circular wrapping, final partial-block, Decimal-centering,
  quantile, probability and Holm defects now have an independent exact check.
- Python RNG or arithmetic behavior drift will fail regression rather than
  silently alter the registered analysis.
- Real research remains blocked by historical readiness and separate
  development activation.
- The Oracle does not make 2,000 replicates universally sufficient or prove
  that the five-session block length fits every future market regime.

## Alternatives Considered

### Call the primary private Bootstrap helper from the Oracle

Rejected because it cannot detect a defect shared with that helper.

### Use a second random seed and compare approximate intervals

Rejected because tolerance choices can conceal implementation defects and make
regression evidence weaker.

### Validate only constant-effect series

Rejected because every resample of a constant series is identical and cannot
exercise the actual sampling path.
