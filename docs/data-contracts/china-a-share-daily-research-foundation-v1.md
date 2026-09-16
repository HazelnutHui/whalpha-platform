# China A-Share Daily Research Foundation V1

## Status

Implemented contract and offline provider-adapter tests; real persisted pilot
and five-year coverage remain absent.

## Scope

The contract represents source observations and the admission census for
`china_a_share` multi-session daily factor and strategy research. It neither
changes the U.S.-equity contracts nor grants Product or trading authority.

Public Python imports are under:

```python
from tip_api.contracts.china_ashare.v1 import ...
from tip_api.providers.china_ashare import ...
```

## Identity observation

`ChinaAshareInstrumentSourceObservationV1` keeps these concepts separate:

- provider security ID and six-digit source code;
- display ticker;
- exchange, board, and security form;
- listing status and effective dates;
- optional stable `instrument_id`;
- resolution status, source, three-time evidence, quality, and reasons.

A `resolved` observation requires a stable ID plus source-proven board and
security form. Unresolved or quarantined observations cannot carry an
`instrument_id`. Exchange/code/display combinations and CDR form/board
relationships are validated.

`ChinaAshareIdentityBindingV1` is the only provider-adapter input that can bind
a source security to a stable ID. It requires separate evidence fingerprints
and rejects unknown board or form. Provider code prefixes and names cannot
construct this binding.

## Raw daily bar

`ChinaAshareDailyBarV1` is unadjusted OHLCV at
`instrument_id x session_date`. It uses exact decimals, CNY turnover amount,
revision, source identity, availability/ingestion clocks, quality, and reason
codes. Float input, non-finite values, invalid OHLC, and negative activity are
rejected.

An absent bar does not by itself mean suspension, delisting, holiday, or
ineligibility. Those states belong to separate evidence.

## Daily trading state

`ChinaAshareDailyTradingStateV1` separates:

- trading/suspended/resumed/not-listed/unknown state;
- none, present-unspecified, detailed risk-warning, or unknown state;
- price-limit regime;
- pre-close and optional exact source-observed up/down limits; and
- board/exchange, timing, quality, and reasons.

Unknown state requires reasons. Exact limit prices require a bounded known
regime and all three price fields. Inferred limits must not be labelled source
observed.

## Adjustment observation

`ChinaAshareAdjustmentFactorObservationV1` preserves the provider factor and a
human-readable semantics declaration. `normalized_return_authorized` is fixed
to `false`. A later reconciliation contract must prove multiplier direction,
action coverage, revision behavior, and return meaning before research labels
use it.

## Effective-dated trading rule

`ChinaAshareTradingRuleV1` binds exchange, board, risk-warning state,
validity interval, T+1 settlement, daily price-limit ratio or no-limit state,
IPO no-limit count, lot/increment rules, official source, and evidence clocks.
Current rules cannot be projected backward without a matching validity range.

## Daily Universe decision

`ChinaAshareUniverseDecisionV1` records exactly one included, excluded, or
quarantined decision per evaluated instrument and session for
`china-a-share-common-stock-research-v1`. It binds methodology, cutoff,
evaluation time, fingerprints, and explicit reasons. Only included decisions
may be performance eligible.

## Provider query and batch

`ChinaAshareSourceDailyQuery` accepts canonical provider IDs and an inclusive
date range, then deduplicates and sorts them. `ChinaAshareDailySourceBatchV1`
requires:

- one source request count per requested security;
- unique bar and state business keys;
- every bar to have a matching state;
- no bar for suspended/not-listed states;
- a bar for trading/resumed states;
- one provider identity across the batch; and
- all rows inside the requested interval.

The BaoStock adapter requests daily history with `adjustflag=3`, maps a
suspended record to state-only evidence, and labels unavailable source clocks,
exact price limits, and detailed ST subtype explicitly. It neither logs in nor
opens a network connection by itself.

## Foundation census and admission

`ChinaAshareFoundationFamilyCensusV1` records coverage and evidence tier for
each required family. Counts must reconcile and absent families cannot contain
records.

`ChinaAshareDailyResearchAdmissionV1` requires all 13 families exactly once.
The deterministic builder grants `daily_research_backtest_authorized=true`
only when all required families are complete with no quarantine blockers.
These fields always remain false:

- intraday execution backtest authorization;
- live-model authorization; and
- Product publication authorization.

Production write count is fixed to zero in this contract. The logical
fingerprint excludes its own fingerprint field and covers the complete
admission payload.

## Non-authority

Passing unit tests proves contract behavior only. It does not prove source
permission, live availability, historical completeness, correct corporate-
action economics, point-in-time Universe membership, or real research
readiness.
