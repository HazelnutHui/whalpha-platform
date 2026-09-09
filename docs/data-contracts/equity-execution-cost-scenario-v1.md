# Equity Execution Cost Scenario V1

## Purpose

The `equity-execution-cost-* /1.0` contracts define deterministic,
transparent one-side equity execution-cost and capacity mechanics. They replace
an unspecified fixed-basis-point shortcut at the design boundary; they do not
claim that current costs have been observed or calibrated and they do not
authorize strategy research.

## Inputs

Every input is bound to one stable `instrument_id`, session, source EOD
fingerprint, data cutoff, and calculation time. It carries:

- order notional in USD;
- 20-session median of unadjusted close times volume as a daily-dollar-volume
  proxy; and
- 20-session daily-return volatility.

The proxy is not an intraday volume profile, executable depth, quote, or fill.
Input construction rejects binary floating-point values and future source
cutoffs.

## Assumptions and evidence

One immutable assumption record contains commission, half-spread, delay
slippage, square-root impact coefficient, and maximum participation rate. Its
evidence status is exactly one of:

- `scenario_only`: no quote or calibration fingerprint; both limitations are
  mandatory;
- `observed_spread`: a quote-evidence fingerprint exists, while impact remains
  explicitly uncalibrated; or
- `observed_spread_and_calibrated_impact`: both quote and impact-calibration
  evidence fingerprints exist.

Even the strongest state means only that the spread was observed and the
impact component was calibrated against governed evidence. It does not turn an
estimate into a realized fill.

## Calculation

For one side:

```text
participation = order_notional / median_daily_dollar_volume_20
impact_bps = impact_coefficient
             * daily_return_volatility_20
             * sqrt(participation)
             * 10,000
estimated_bps = commission_bps
                + half_spread_bps
                + delay_slippage_bps
                + impact_bps
estimated_cost_usd_per_side = order_notional * estimated_bps / 10,000
```

Decimal arithmetic, fixed rounding, normalized limitation codes, and logical
fingerprints make repeated calculations reproducible. Participation above the
declared limit is retained but marked `above_participation_limit`; it is never
silently clipped.

## Authority boundary

Every estimate declares:

- `estimated_not_realized=true`;
- `equity_execution_only=true`;
- `research_admission_authorized=false`;
- `option_execution_cost_authorized=false`; and
- `performance_claim_authorized=false`.

Borrow, financing, regulatory fees, intraday liquidity, market-condition
dependence, and options execution are outside V1. Entry and exit must be
estimated independently because notional, volatility, spread, and capacity may
differ; a caller must not blindly double one side. Real research still requires
governed point-in-time quotes or an explicit spread proxy policy, impact
calibration and stress validation, corporate-action-safe inputs, chronological
evaluation, and final Historical Coverage.
