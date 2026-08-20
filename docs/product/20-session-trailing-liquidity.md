# 20-Session Median Dollar-Volume Proxy

## Definition

For each current analysis-date candidate instrument, compute `canonical close × canonical volume` for each of the 20 completed XNYS sessions immediately before the analysis session. Sort the 20 exact Decimal values and average positions 10 and 11. The product label is **20-Session Median Dollar-Volume Proxy**.

This is not fund flow, money flow, market depth, notional, market capitalization, institutional buying, or abnormal volume.

## Gates

- previous-session close must be at least USD 5;
- 20-session median dollar-volume proxy must be at least USD 20,000,000;
- exactly 20 observations are required.

There is no float conversion, winsorization, silent rounding, forward fill, or zero fill. A missing bar is absent; a real zero-volume bar contributes zero. Fractional volume is preserved. Adjustment factors remain `adjustment_factors_unverified`.

The current analysis session never enters its own window. A 19/20 result is `insufficient_history` and has no median. Other statuses distinguish missing previous bar, price failure, liquidity failure, identity-reference failure, and material data-quality failure.

## Current State

For analysis session 2026-08-19, XNYS 4.13.2 calculates the 20-session window from 2026-07-22 through 2026-08-18. All 20 canonical partitions validate and readiness is `ready`; the 2026-08-19 bar is excluded from its own qualification window.

The versioned [shadow publication](../audits/trailing-liquidity-shadow-publication-2026-08-19.md) persists one metric fact per Candidate B instrument and separate Candidate A/B decisions. It remains shadow derived data: production Universe membership and Dashboard calculations are unchanged.
