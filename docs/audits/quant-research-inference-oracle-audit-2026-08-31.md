# Quant Research Inference Oracle Audit — 2026-08-31

## Scope

This repository-only audit tests the fixture inference mechanics registered for
Strong-Leader Pullback. It uses no canonical research input and creates no
performance evidence.

## Independent path

The reference implementation does not import the primary Bootstrap, quantile
or Holm helpers and does not call `random.Random`. It independently implements
the integer MT19937 state transition and seed-array initialization, circular
block-start draws, original and centered Decimal accumulation, percentile
interpolation, add-one probability and ordered Holm adjustment.

## Evidence

- Exact Bootstrap lower bound, upper bound and one-sided probability matched
  for nonconstant Decimal series with 1, 2, 5, 20, 37 and 53 observations.
- Counts 37 and 53 exercise truncated final blocks.
- All inferential fields in the stable development fixture matched across the
  complete 24-combination × 3-horizon family.
- All 24 primary-horizon validation Holm-adjusted probabilities matched.
- Sparse evidence remains inferentially unavailable in both implementations.

The complete backend suite result is recorded in the project changelog.

## Boundary

This audit establishes deterministic implementation equivalence. It does not
show that Strong-Leader Pullback works, that historical data is ready, that
Bootstrap assumptions hold in live markets, or that stock results predict
option returns. Stage-transition and performance-claim authority remain false.
