# ADR 0278: Register Factor Catalog V2 without Outcomes

## Status

Accepted

## Date

2026-09-15

## Context

Factor Discovery V1 closed after all five candidate-Alpha measurements failed
its preregistered Development screen. Reusing those formulas with convenient
thresholds would be outcome-guided retuning. Ending research after one finite
batch would be equally unjustified because V1 tested a narrow 0–20-session
price/path catalog rather than all distinct daily-market mechanisms.

The next campaign needs broader hypotheses that are still computable from the
governed five-year daily OHLCV, SPY, stable-Identity, reconstructed Membership,
and split-reconciliation boundary. Historical point-in-time classification,
fundamentals, quotes, spreads, options, and diverse Regime labels are not
available and cannot be inferred.

ADR 0277 records that this design is adaptive to consumed V1 Development
evidence. A new catalog therefore cannot present itself as statistically
independent merely because its formulas differ.

## Decision

Register outcome-blind Factor Catalog V2,
`whalpha.factor-catalog.daily-behavior-v2`, with logical fingerprint
`6620000334a0a8bd23103341dfc1958d57c712a063dff0a39e23ffc82d51bed5`.
It contains exactly eight definitions across six economic families and an
exact 127-session source window.

### Candidate-Alpha measurements

1. `medium_term_relative_momentum_126s_skip5`: six-month SPY-relative
   continuation excluding the latest five sessions;
2. `short_term_relative_reversal_5s`: sign-reversed five-session SPY-relative
   return;
3. `intraday_relative_pressure_reversal_5s`: sign-reversed market-adjusted
   open-to-close return over five sessions; and
4. `overnight_relative_persistence_5s`: market-adjusted close-to-open return
   over five sessions.

The two short-horizon reversal measurements share one related-factor group and
carry a fixed standard-relative-return-first redundancy priority; they cannot
later be treated as independent discoveries. The medium-horizon factor is
explicitly linked to the two failed V1 relative-return trials. The overnight
definition is linked to the failed V1 gap-risk trial. These links do not pre-
reject V2; they preserve the true search lineage.

### Non-Alpha measurements

- `down_market_relative_resilience_60s` is a setup conditioner for a future
  separately registered market-state interaction. It has no standalone Alpha
  claim and requires at least 12 benchmark-down observations.
- `amihud_illiquidity_20s` is an applicability/capacity input. It is a coarse
  daily price-impact proxy, not observed spread, impact, order flow, or fund
  flow.
- `single_index_residual_volatility_60s` and
  `relative_downside_semideviation_60s` are related risk guards with a fixed
  residual-volatility-first redundancy priority. At most one may later survive
  the shared risk group.

The definitions cite primary research lineages for medium-horizon momentum,
short-horizon reversal, intraday/overnight return decomposition, daily
illiquidity measurement, idiosyncratic volatility, and downside risk. The
citations motivate falsifiable questions; they do not certify current Alpha or
the chosen horizons.

### Calculation and authority

All inputs end at the completed signal-session close. Earliest execution is
the next session open. OHLC and volume are reconciled to the signal-session
split basis. Missing, malformed, zero-denominator, insufficient-down-market,
or zero-benchmark-variance cases are explicit unavailable states and are never
zero-filled.

The pure calculator accepts exactly 127 aligned stock and SPY sessions and has
no outcome argument. Changing a formula, role, timing rule, source field,
related group, or consumed-trial link requires a new catalog version.

This ADR authorizes only implementation, deterministic tests, and one frozen
outcome-blind qualification design. It authorizes no Development outcome read,
factor screen, factor admission, Model Construction, Strategy Expression,
Validation, Holdout, Candidate change, data acquisition, canonical-data write,
publication, deployment, broker access, or order execution.

## Consequences

- V2 explores distinct continuation, reversal, return-timing, market-state,
  liquidity, and downside-risk questions without reopening V1.
- A 126-session lookback requires the diagnostic runner to read governed EOD
  history before the reconstructed signal cohort without projecting Membership
  backward.
- Outcome-blind coverage, timing, distribution, concentration, and redundancy
  must pass a separately frozen protocol before trials are appended or returns
  are read.
- A useful conditioner or risk guard still cannot open Model Construction when
  no candidate Alpha survives.

## Alternatives considered

### Retune the five failed V1 Alpha factors

Rejected because their Development outcomes are consumed and the V1 stopping
rule prohibits changed formulas or gates.

### Add fundamentals, industry neutrality, or option factors immediately

Rejected because the required point-in-time source families are not admitted.
Those territories remain later campaigns with named data acceptance tests.

### Register dozens of technical indicators

Rejected because correlated transforms would increase search degrees of
freedom without adding distinct mechanisms.

### Treat daily volume as money flow

Rejected. OHLCV can describe trading activity and coarse liquidity proxies;
it does not reveal investor identity or signed capital flow.
