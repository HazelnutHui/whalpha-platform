# ADR 0286: Separate Point-in-Time Market-State Inputs Before Campaign Three

## Status

Accepted

## Date

2026-09-15

## Context

Factor Discovery V1 and V2 are closed with no admitted Alpha. The next finite
campaign is intended to study whether factor applicability changes with the
market environment. Reusing the current Product Regime score would be unsafe:
it is a presentation composite, it replays current constituents, and it would
collapse benchmark evidence and reconstructed cross-sectional evidence into a
single label before their historical limitations are reviewed.

The third campaign therefore needs an outcome-blind market-state input whose
raw components, evidence tier, timing, coverage, and missingness remain
inspectable before any interaction or Development outcome is registered.

## Decision

1. Define a separate `quant-research-market-state-vector/1.0` contract before
   registering Campaign Three.
2. Keep six exact benchmark metrics based on SPY, QQQ, IWM, and DIA separate
   from four reconstructed cross-sectional metrics.
3. Use only information complete at session close `t`; the earliest allowed
   execution is the next session open. No forward return, label, model output,
   or current Product Regime score is an input.
4. Historical membership is effective-dated by stable `instrument_id` for the
   requested session. Its reconstructed status remains explicit and never
   becomes `as_operated` by implication.
5. Emit continuous raw metrics and coverage first. Do not choose regime labels,
   state thresholds, interactions, horizons, or parameter grids until an
   outcome-blind qualification reports coverage and state diversity.
6. The vector is a reusable outcome-blind market-state artifact under ADR 0283.
   Any source, membership, code, parameter, session partition, or upstream
   fingerprint change creates a new immutable version.
7. This decision does not register Campaign Three, authorize outcome access,
   materialize `/data`, open Model Construction, or grant Product authority.

## Consequences

The next campaign can ask a falsifiable conditional-applicability question
without hiding reconstructed evidence inside a composite label. A failed data
qualification stops or revises the vector while outcomes remain closed. A
passed qualification only permits a finite campaign protocol to be designed;
it does not establish Alpha.

## Rejected alternatives

- reuse the current Product Regime score as historical truth;
- infer historical sectors from today's classification;
- tune state thresholds after reading factor returns;
- use one opaque market-state label without raw components; or
- treat reconstructed membership as an as-operated constituent record.
