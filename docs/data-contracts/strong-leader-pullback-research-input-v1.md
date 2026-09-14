# Strong-Leader Pullback Research Input V1

## Purpose

`strong-leader-pullback-research-input/1.0` seals one complete, outcome-free
Primary cross-section for the first preregistered Quant Research Lab study. It
is an input/admission contract, not a signal, backtest, recommendation, or
performance result.

## Admission boundary

The pure builder accepts only already-read canonical evidence and performs no
I/O. It requires:

- a formally valid `ready_for_development_review` assessment bound to the exact
  frozen experiment and a self-fingerprinted `research_ready` Historical
  Coverage manifest;
- one same-session signal-eligible canonical Membership publication, physical
  partition manifest, and complete deterministic decision rows;
- the complete set of quality-valid included Primary common stocks;
- one explicit stable `instrument_id` for SPY, with ETF/ticker checks used only
  as supporting metadata;
- exactly 21 contiguous XNYS sessions of quality-valid USD EOD bars for every
  member and SPY; and
- a clear, quality-valid split and total-return Adjustment Ledger projection
  from every source session to the signal-session basis, with its source-data
  cutoff strictly before the modeled next-session open.

Any missing, duplicate, extra, stale, quarantined, non-clear, future-dated, or
internally inconsistent required item rejects the whole batch. Partial
cross-sections are forbidden.

## Frozen feature calculation 1.0.0

All calculations use Decimal values and split-adjusted OHLCV on the
signal-session basis.

| Field | Exact calculation |
| --- | --- |
| 20-session relative leadership | Stock close return from `t-20` to `t` minus the same SPY return, then average-rank inclusive percentile across every same-session point-in-time Primary member; ties use stable-ID order and a fully tied set is 0.5000 |
| Trend quality | 35% `close > SMA10` score + 35% clipped normalization of `SMA10 / SMA20 - 1` from -3% to +3% + 30% reverse clipped normalization of absolute five-session maximum drawdown from 2% to 12% |
| ATR | Simple mean of the latest 14 true ranges |
| Pullback depth | `(highest adjusted close over t-20 through t-1 - close[t]) / ATR14` |
| Recovery | `close[t] > close[t-1]` and, separately, `close[t] > high[t-1]` |
| Pullback volume | adjusted `volume[t] / median(adjusted volume[t-20:t-1])` |
| Market Regime | same-session, non-stale, available, confirmed Primary state; Risk-on, Balanced, Defensive, and Stress remain distinct |

The feature fingerprint binds these definitions independently of whichever
Candidate or Entry Geometry version is current later.

## Output custody

The batch records source sessions, next-entry session/open, benchmark return,
all six dataset logical/physical hashes, readiness, coverage, Membership
publication/partition/knowledge-time, Market Regime, expected member count,
observations, and its own logical fingerprint. Each observation has a source
fingerprint over the exact complete-cross-section source hash, sessions, and
upstream evidence. The cross-section source hash covers every admitted member
and SPY bar and adjustment, because one peer's value can affect every rank.

The contract fixes:

- `contains_forward_outcomes=false`;
- `development_authorized=false`;
- `performance_claims_authorized=false`;
- `external_request_count=0`; and
- `production_write_count=0`.

Observation/execution contract 1.2 accepts Stress and preserves every finite
ATR pullback depth and every finite, nonnegative volume ratio. Extreme raw
observations remain valid non-signals rather than becoming missing data through
arbitrary observation bounds. The experiment's positive trigger bands remain
unchanged.

## Current status

Contracts, shared pure feature calculation, and adversarial fixtures exist.
The separate reconstructed-population diagnostic has exercised the calculation
over real Dell inputs, but that proxy population is not a research-input batch.
Real research-input construction remains blocked because Dell does not yet have
research-ready complete Membership, Corporate Action, Instrument Lifecycle,
Adjustment Ledger, and transitive Historical Coverage evidence. No real
outcome or performance batch has been created or persisted.
