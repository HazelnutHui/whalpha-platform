# Candidate Strategy Evaluation V1

## Status

Repository-only typed shadow contract. No evaluation dataset has been written,
no channel formula has been selected, and no performance result exists.

## Purpose

Candidate Strategy Evaluation V1 separates information available when a
research signal is created from forward outcomes that become knowable later.
This is the core anti-look-ahead boundary for the six independent Candidate
strategy channels.

## Fixed evaluation policy

- Research evaluation requires at least 252 completed sessions.
- Stronger Regime-stratified review targets at least 504 sessions and at least
  60 observations in every reported Regime; smaller cells are inconclusive.
- The chronological split is earliest 50% development, next 25% validation,
  final 25% untouched holdout.
- Forward horizons are 1, 3, and 5 XNYS sessions.
- Entry is the next-session open and exit is the selected horizon-session
  close.
- Overlapping labels are purged and the embargo is five sessions.
- Random train/test split is prohibited.
- After parameter freeze, evaluation advances through expanding or monthly
  walk-forward windows using only the parameter version active at the time.
- Raw outcome ledgers exclude transaction costs. Reports show separate 0, 10,
  25, and 50 basis-point-per-side sensitivity.

The complete policy has one fixed logical fingerprint. A policy change
requires a new version rather than mutating an old evaluation.

## Sealed signal grain

One `candidate-strategy-signal/1.0` record represents one session, Universe,
stable `instrument_id`, and strategy channel. It binds:

- exact channel assessment and parameter fingerprints;
- Candidate, entry-geometry, and Market Regime source fingerprints;
- the ordered source sessions, none later than the signal session;
- point-in-time membership session, methodology, and fingerprint;
- the channel status, score, and same-channel rank as they existed then;
- chronological split assignment and known limitations.

The signal ID is a deterministic digest of the signal session, Universe,
stable ID, channel, and assessment fingerprint. The signal schema forbids
outcome fields and declares `sealed_without_outcomes=true`.

An `unavailable` channel result cannot enter performance evaluation. A
`current_as_of_constituent_replay` signal must be marked research-only and is
never performance-eligible. Current constituents cannot be projected backward
and presented as point-in-time evidence.

## Forward outcome grain

One `candidate-strategy-forward-outcome/1.0` record represents one sealed
signal and one 1-, 3-, or 5-session horizon. The expected ordered session path
is fixed before labels mature.

Status is one of:

- `pending`: the future path has not matured and every label remains null;
- `available`: entry/exit sessions, prices, returns, benchmark comparison,
  maximum favorable excursion, and maximum adverse excursion are complete;
- `quarantined`: a corporate-action or source-integrity review prevents the
  numeric values from feeding evaluation;
- `unavailable`: the label cannot be constructed and carries a reason.

For an available result, the contract recomputes next-open-to-horizon-close
price return and its arithmetic difference from the benchmark. Maximum
favorable excursion is non-negative and maximum adverse excursion is
non-positive. The label source session must be the horizon exit session and
strictly later than the signal.

These are underlying-stock price outcomes, not total return, alpha, or option
returns. Dividends, splits, mergers, delistings, and other corporate actions
require explicit governed treatment; affected results stay quarantined while
Corporate Action V1 has no completed canonical dataset.

## Required evaluation reports

When sufficient point-in-time history exists, report each strategy separately
by status/rank bucket, Regime, sector/industry, liquidity, volatility, and
signal age. Include count, coverage, missing/quarantined share, mean, median,
quartiles, 5th/95th percentiles, hit rate, MFE, MAE, turnover, drawdown,
rank monotonicity, and unconditional eligible-Universe base rates. Do not
publish only an average return or only favorable regimes.

## Current blockers

- Canonical history is 29 EOD sessions, below the 252-session minimum.
- Existing analytics replay current-as-of membership; implemented daily
  point-in-time Universe history is still absent.
- Corporate Action V1 has a typed source-observation boundary but no completed
  canonical dataset or adjustment reconciliation.
- Fundamental, valuation, point-in-time sector/industry, and option-chain data
  remain absent.
- No channel formula, frozen formula parameter set, signal writer, outcome
  maturer, evaluation runner, or Production consumer exists.

Dell remains the only approved compute, storage, and data-governance boundary
for future evaluation work. This contract does not authorize a `/data` write,
backfill, provider request, or Production publication.
