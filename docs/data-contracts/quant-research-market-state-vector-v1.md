# Quant Research Market-State Vector V1

## Purpose

`quant-research-market-state-vector/1.0` defines the outcome-blind market-state
input that must be qualified before the third finite Factor Discovery campaign
is registered. It is a research input, not the Product Market Regime and not a
forecast.

## Benchmark-exact block

All benchmark metrics require exact stable identities and 21 aligned sessions
ending at `t`:

- SPY 20-session log return;
- SPY 20-session annualized realized volatility;
- QQQ minus SPY 20-session log return;
- IWM minus SPY 20-session log return;
- DIA minus SPY 20-session log return; and
- share of SPY, QQQ, IWM, and DIA closing above their own 20-session mean.

## Reconstructed cross-sectional block

The effective-dated reconstructed membership at `t` supplies complete 21-
session member series. The vector records declared and complete member counts
and never fills missing members with zero. Cross-sectional metrics are
unavailable unless at least 500 members and 75% of declared membership have
complete inputs:

- share with positive five-session log return;
- share above the member's own 20-session mean;
- robust five-session return dispersion (`1.4826 × MAD`); and
- robust 20-session return dispersion (`1.4826 × MAD`).

This block is `reconstructed_research_only`, not `as_operated`.

## Timing and custody

Every value uses data complete at session close `t`; the earliest execution is
the next session open. Split reconciliation is bounded to the signal session.
The contract accepts no forward return or outcome label. It produces an
outcome-blind reusable market-state artifact whose exact identity includes
source, membership, session partition, code, parameter, and upstream artifact
fingerprints.

## Current state

The immutable definition and pure calculator are implemented. No real panel is
materialized yet, no state threshold or interaction is selected, Campaign
Three is not registered, and Development outcomes remain inaccessible. The
next step is one outcome-blind real-data qualification and exact replay.
