# ADR 0179: Separate equity cost mechanics from execution evidence

- Status: Accepted
- Date: 2026-09-09

## Context

The synthetic Candidate statistics expose fixed 0/10/25/50-basis-point
scenarios. Those scenarios are useful sensitivity checks but do not respond to
order size, instrument liquidity, or volatility. The project needs an explicit
mechanical boundary before a real research panel exists, while current custody
has no point-in-time NBBO, actual fills, or impact-calibration sample.

Calling a price-volume formula a real execution model would overstate present
evidence and create another hidden score. Waiting for every external dataset
would also leave future adapters without a stable, testable interface.

## Decision

1. Implement a deterministic, one-side equity scenario with separately visible
   commission, half-spread, delay-slippage, and square-root impact components.
2. Use order notional divided by 20-session median close-times-volume only as a
   daily participation proxy. Preserve the lack of intraday volume, depth, and
   realized execution evidence as limitations.
3. Bind every assumption, input, and estimate to normalized Decimal data and a
   logical fingerprint. Reject binary floats, malformed evidence states,
   arithmetic drift, and tampering.
4. Separate `scenario_only`, `observed_spread`, and
   `observed_spread_and_calibrated_impact`. The strongest state still describes
   an estimate, not a realized fill or complete model validation.
5. Keep capacity visible as a gate, never as a score contribution. Preserve an
   above-limit estimate for audit instead of clipping it.
6. Authorize no research admission, performance claim, option-cost use,
   Historical Coverage, `/data` publication, analytics, Snapshot, bundle,
   deployment, or scheduler action.
7. Advance the read-only current-context report to 1.10. It records scenario
   mechanics as present while changing the blocker from absent mechanics to
   absent execution evidence.

## Consequences

- A future quote feed, calibrated execution sample, or IBKR fill history can
  strengthen evidence without changing the component interface.
- Costs can be inspected and stressed rather than hidden inside a candidate
  rank.
- Current research remains `data_blocked`; this ADR completes mechanics, not
  empirical calibration or research readiness.
- Options require a separate model because contract spread, Greeks, IV,
  exercise, assignment, and multi-leg execution are not equity costs.

## Rejected alternatives

- **Keep only fixed basis-point deductions:** useful as stress cases but blind
  to size, volatility, and liquidity.
- **Label the square-root formula a real calibrated model:** unsupported without
  quote and execution evidence.
- **Infer spread from daily OHLC:** conflates range with executable spread.
- **Apply one cost twice for a round trip:** entry and exit conditions can
  differ materially.
- **Blend cost into a strategy score:** hides tradability and prevents a clean
  signal-versus-execution diagnosis.
