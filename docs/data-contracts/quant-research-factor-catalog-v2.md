# Quant Research Factor Catalog V2

## Purpose

Factor Catalog V2 is a finite, outcome-blind registry of daily behavior,
applicability, and risk measurements. It broadens Factor Discovery after V1
closed without candidate Alpha while retaining V1 trial lineage.

The typed contract is `quant-research-factor-catalog/2.0`; its catalog ID is
`whalpha.factor-catalog.daily-behavior-v2` and its logical fingerprint is
`077ebe1b0c57b2093380c2a0dc87c9a0a0581b895c4433faacdf7ecc401c9647`.

## Definitions

| Factor | Role | Exact measurement | Expected screen direction |
| --- | --- | --- | --- |
| `medium_term_relative_momentum_126s_skip5` | candidate Alpha | `ln(C[t-5]/C[t-126]) - ln(B[t-5]/B[t-126])` | positive |
| `short_term_relative_reversal_5s` | candidate Alpha | `-[ln(C[t]/C[t-5]) - ln(B[t]/B[t-5])]` | positive |
| `intraday_relative_pressure_reversal_5s` | candidate Alpha | negative five-session sum of stock-minus-SPY log open-to-close returns | positive |
| `overnight_relative_persistence_5s` | candidate Alpha | five-session sum of stock-minus-SPY log prior-close-to-open returns | positive |
| `down_market_relative_resilience_60s` | setup conditioner | mean stock-minus-SPY daily log return on SPY-down sessions; minimum 12 | no standalone claim |
| `amihud_illiquidity_20s` | applicability input | one-million-scaled mean absolute log return per dollar volume | no standalone claim |
| `single_index_residual_volatility_60s` | risk guard | annualized OLS-with-intercept stock-on-SPY residual standard deviation | negative |
| `relative_downside_semideviation_60s` | risk guard | annualized downside semideviation of daily stock-minus-SPY log return | negative |

`C`, `O`, and `V` are the stock close, open, and volume. `B`, `Bc`, and `Bo`
are corresponding SPY observations. All fields are split-reconciled to the
signal-session basis.

## Source and timing boundary

- exact input: 127 aligned sessions from `t-126` through `t`;
- signal cutoff: completed session close;
- earliest execution: next session open;
- Membership: reconstructed latest-vintage research only at the signal
  session; no backward Membership projection is permitted;
- stable `instrument_id` is authoritative and ticker is display only;
- source families: governed historical EOD and research adjustment ledger;
- every missing or invalid case is explicit unavailable and never zero-filled.

## Search-history boundary

The catalog binds prior cumulative discovery-ledger fingerprint
`502834abe5bfc171f80206138b36c8bf973c9fcc84078592b8dc92ccd5bee368`.
Each definition states whether it extends, opposes, decomposes, or is merely
related to a consumed V1 trial. The catalog is adaptive Development research,
not a statistically independent first attempt.

## Outcome-blind boundary

The implementation calculates factor values only. It has no label or outcome
input and grants no screening or selection authority. Before any real forward
return is read, a separate sequence must:

1. freeze coverage, timing, missingness, distribution, concentration,
   redundancy, and exact-replay rules;
2. run and retain one outcome-free report plus exact replay;
3. decide which definitions are eligible for formal outcome trials;
4. append those trials to a new cumulative ledger version; and
5. freeze cohort, labels, multiplicity, stability, cost, selection, and stop
   rules.

## Interpretation limits

Research citations motivate the mechanisms but do not validate these exact
definitions or horizons. Daily volume and Amihud illiquidity are behavior and
coarse price-impact proxies, not signed flow or executable spread. Stock
labels, if later authorized, remain underlying-stock outcomes and never option
returns.
