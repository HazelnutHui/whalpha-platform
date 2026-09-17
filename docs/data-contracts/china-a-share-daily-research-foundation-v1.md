# China A-Share Daily Research Foundation V1

## Status

Implemented contracts, provider adapters, an exactly reread temporary
normalized-reference package, and a linked five-year daily pilot package for
six SSE/SZSE securities. An exact same-scope source-repeat comparison also
passes with zero economic deltas. A separate exact-byte SSE/SZSE annual-notice
package now reconciles the pilot calendar. Canonical pilot data and admitted
historical coverage remain absent.

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

`ChinaAshareSourceSecuritySnapshotStateV1` preserves provider-keyed trading
state before an `instrument_id` exists. It prevents a suspension observation
from being discarded merely because identity adjudication has not completed.

`ChinaAshareLifecycleSourceObservationV1` separates issuer codes from listed-
security codes. SSE company-code rows carry no `source_security_id` and require
both issuer/security-identity and pause/termination ambiguity warnings. SZSE
security-code rows may retain a provider security ID but still do not resolve a
stable local identity.

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

`ChinaAshareAdjustmentFactorObservationV1` separately preserves BaoStock's
`adjustFactor`, `foreAdjustFactor`, and `backAdjustFactor` fields plus a human-
readable semantics declaration. `normalized_return_authorized` is fixed to
`false`. A later reconciliation contract must prove multiplier direction,
action coverage, revision behavior, and return meaning before research labels
use any of them.

## Effective-dated trading rule

`ChinaAshareTradingRuleV1` binds exchange, board, risk-warning state,
validity interval, T+1 settlement, daily price-limit ratio or no-limit state,
IPO no-limit count, lot/increment rules, official source, and evidence clocks.
Current rules cannot be projected backward without a matching validity range.

`ChinaAshareOfficialSourceReferenceV1` records each approved official URL,
publisher, publication/retrieval date, final URL, content type, exact byte
count, and physical SHA-256. `ChinaAshareFeeRuleV1` keeps buy/sell rates by
exchange, fee family, and effective interval. `ChinaAshareAccountCostScenarioV1`
keeps broker/channel, commission basis, rate, minimum, slippage, effective
date, reason codes, and a logical fingerprint; user-reported account terms are
assumptions rather than official broker evidence.

`ChinaAsharePilotPriceLimitDecisionV1` binds each pilot instrument/session to
one effective rule and stores previous close, half-up CNY 0.01 theoretical
limits, observed bar bounds, and explicit quality. Theoretical limits cannot
be represented as source-observed exchange limit prices.

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

## Temporary pilot package

`ChinaAsharePilotPlanV1` fixes seven varied exchange/board/state anchors, two
lifecycle subject keys, separate official-reference and BaoStock-snapshot
dates, a five-year target interval, provider identities, and a request
ceiling. The temporary publisher stores only typed normalized observations
below a dedicated `/tmp` boundary, uses canonical JSON, owner-only file modes,
atomic rename, physical hashes, logical fingerprints, and a complete exact
reread.

The reference quality report exposes missing official, BaoStock, and lifecycle
keys. `ChinaAsharePilotIdentityDecisionV1` either creates a deterministic
pilot-only join identity or retains a quarantined decision with reasons; it
cannot create canonical identity authority. The linked daily package contains
those decisions, typed daily source batches, and
`ChinaAsharePilotDailyQualityReportV1`. Raw upstream retention, canonical
stable identity, adjustment semantics, canonical Apply, backtesting, Product
publication, and deployment all remain explicitly false.

## Source-repeat comparison

`china-ashare-pilot-source-repeat/1.0` compares two distinct, ordered daily
packages bound to the same plan, reference evidence, provider, query, and
interval. It compares bars, daily state, and adjustment observations by stable
pilot instrument/date business key. Only the local `ingested_at` field is
ignored; source availability and every economic or quality field remain in the
comparison.

The owner-only report and change artifact are atomically published below the
same temporary plan boundary and exactly reread. A zero-delta report grants
only bounded source-repeat qualification. Canonical identity, Apply, backtest,
Product, publication, and deployment authority remain false.

## Calendar coverage diagnostic

`ChinaAsharePilotCalendarCoverageReportV1` compares the exact date set from an
offline `XSHG` calendar in `Asia/Shanghai` with both the source-state union and
every bound pilot instrument. It reports missing and unexpected dates rather
than treating either as a suspension. The expected-session set is fingerprinted
and every instrument count must reconcile.

The original library/source diagnostic cannot set `calendar_reconciled=true`
by itself. The separate `china-ashare-calendar-evidence-package/1.0` contract
retains the exact 2021–2026 SSE/SZSE notice bytes, their physical hashes,
parsed closure ranges, and a deterministic reconciliation report. It compares
all weekday closures between both exchanges and `XSHG`, then binds that result
to the daily package's source-state alignment. The real pilot result reconciles
94 weekday closures and 1,211 sessions with zero differences. BSE remains
excluded while its daily anchor is quarantined.

## Market-mechanics evidence package

`china-ashare-market-mechanics-package/1.0` binds one exact daily package and
one reconciled official-calendar package to exact official bytes, normalized
source references, trading and fee rules, an account-cost scenario, every
pilot price-limit decision, and one fail-closed report.

The package uses canonical JSON, owner-only file modes, atomic rename,
per-artifact physical hashes, logical fingerprints, a closed file set, and a
complete formal reread. Its manifest requires all seven artifact families,
retains raw official source payloads, and fixes research, canonical Apply,
Product publication, and deployment authority to false.

The real pilot package contains 13 official sources, 10 trading rules, 14 fee
rules, and 7,266 price-limit decisions. It reports zero observed-bar
violations and zero unresolved rules. This is sufficient for the bounded
SSE/SZSE pilot mechanics gate only; adjustment semantics, corporate actions,
lifecycle, historical Universe, and full admission remain independent.

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
