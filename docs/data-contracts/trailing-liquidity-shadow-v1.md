# Trailing Liquidity Shadow Publication V1

## Scope

This contract persists the existing **20-Session Median Dollar-Volume Proxy** for Provider-Classified shadow candidates. It does not define a production Universe and is not an API or Dashboard contract.

## Metric fact

`TrailingLiquidityMetricV1` has one row per stable `instrument_id` in the Candidate B union. It records the analysis session, exact prior-20-session window, display-only ticker, provider security-form code, observation count, previous close, median proxy when the audited policy permits it, metric status, quality flags, source-window fingerprint, and UTC calculation time.

`instrument_id` is the join key. Ticker changes do not split a series and ticker reuse cannot merge instruments.

## Shadow decision

`TrailingLiquidityShadowDecisionV1` has one row per `(universe_id, instrument_id)`. Primary status is mutually exclusive and reconciles to exactly one of:

- `passed`;
- `missing_previous_bar`;
- `insufficient_history`;
- `below_price`;
- `below_liquidity`;
- `quarantined_or_invalid_input`.

`included=true` is equivalent to `passed`. Candidate A permits only `CS`; Candidate B permits only `CS` and `ADRC`.

## Decimal and missing-data policy

- daily proxy: canonical close multiplied by canonical volume;
- exact Decimal arithmetic, with no float conversion;
- physical fields: `decimal128(38, 10)`;
- values requiring rounding or exceeding precision fail closed;
- exactly 20 observations are required for the median;
- no forward fill, zero fill, winsorization, or silent rounding;
- a real zero-volume bar contributes zero;
- adjustment factors remain unverified.

The previous close gate is USD 5 and the median proxy gate is USD 20,000,000. The analysis session never enters its own window.

## Completion boundary

The logical manifest references the exact EOD component paths, row counts, EOD and identity fingerprints, membership evidence and as-of date, metric and decision Parquet hashes/fingerprints, Candidate A/B reconciliations, thresholds, policy version, and Decimal policy. It is published only after both Parquet components pass full staging reread.
