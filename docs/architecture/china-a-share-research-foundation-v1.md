# China A-Share Research Foundation V1

## Purpose and current boundary

This design defines an isolated workstation foundation for five-year A-share
daily research. It is not a statement that real coverage is complete and does
not authorize a live acquisition, `/data` write, research outcome read,
Candidate activation, website publication, or deployment.

The implementation contains provider-neutral contracts, BaoStock and
AKShare-mediated adapters, and an owner-only temporary normalized-reference
pilot that rereads exactly. That package is not a raw provider archive,
canonical dataset, or completed historical pilot.

## Logical layers

```text
source snapshots
  -> normalized source observations
  -> reconciliation and quarantine
  -> canonical point-in-time families
  -> immutable research panel
  -> research admission
  -> Factor Discovery
```

Each arrow is a separate, fingerprinted decision. A later layer may reference
earlier bytes but does not mutate them.

### Source snapshots

Retain exact provider payload identity, request interval, retrieval time,
provider/version, declared permission, content hash, and request outcome. A
failed or partial response is evidence of failure, not an empty market day.

The current temporary reference package explicitly declares
`normalized_library_observations` and `raw_upstream_payload_retained=false`.
It qualifies adapter semantics only and cannot satisfy the later raw-source
archive requirement by itself.

### Normalized observations

Normalize provider fields into typed observations while preserving source
identity and uncertainty. BaoStock emits unadjusted daily bars, daily trading
state, instrument snapshots, and adjustment-factor observations. It does not
resolve stable identity from a code or name.

Provider-keyed snapshot trading state is retained even before stable identity
exists. Lifecycle observations distinguish listed-security codes from issuer
codes. The SSE delisting interface currently exposes company codes and a
pause/termination-conflated status, so those rows cannot claim a listed-
security identity or a definitive termination without adjudication.

### Reconciliation and quarantine

Reconciliation compares business keys and values across sources. It records
agreement, tolerance-qualified differences, hard conflicts, source absence,
and semantic mismatch. There is no generic first-non-null or last-writer-wins
rule.

### Canonical families

Canonical rows require a versioned resolution rule and retain all input
fingerprints. Missing critical evidence is represented as quarantine, not
silently dropped or filled from today's state.

### Research panels

Research panels are immutable derivatives built only from admitted canonical
families. Factor inputs and future labels remain separately materialized and
access-controlled under the existing three-layer research governance.

## Market isolation

The `market_id` is `china_a_share`. Its contracts, persistence paths,
manifests, calendars, stable-ID namespace, Universe, actions, rules, costs,
research panels, and admission report are distinct from U.S. equities.

Shared utilities may provide hashing, immutable manifests, exact decimals,
atomic publication, and statistical methods. Shared utilities must not embed
U.S.-specific exchange, symbol, settlement, adjustment, or eligibility rules.

## Source roles

| Source role | Initial route | Permitted use | Not sufficient for |
| --- | --- | --- | --- |
| Primary daily observations | BaoStock | unadjusted OHLCV, trade state, coarse ST state, adjustment observations | stable identity, exact limit rules, complete lifecycle, return authority |
| Independent cross-check | AKShare-mediated public endpoints | exchange lists, histories, name/lifecycle/action corroboration | silent replacement or automatic canonical promotion |
| Rule and disclosure authority | SSE, SZSE, BSE, CNINFO | effective-dated rules, official notices and disclosed events | proof that every historical record was known at an earlier cutoff |
| Optional extension | Tushare or paid vendor | close declared coverage or timestamp gaps after review | retroactive authority over prior incomplete evidence |

Every source has its own adapter and source package. A library that proxies a
public endpoint is recorded separately from the underlying publisher.

## Stable identity

`instrument_id` is generated only after independently evidenced identity,
board, and security form are bound. Source codes use provider-native
`sh.######`, `sz.######`, or `bj.######`; display tickers use `######.SH`,
`######.SZ`, or `######.BJ`. Neither representation is a permanent identity.

Ticker changes generally preserve an instrument; reorganizations, new share
classes, or successor securities may require distinct instruments and explicit
relationships. Ambiguous cases remain quarantined.

The first live reference pilot also demonstrated why this boundary is needed:
the current BSE code namespace uses `920xxx`, while an earlier assumed `430xxx`
anchor was absent from the current official list. The obsolete assumption was
replaced in the plan, not silently joined across time.

## Required foundation families

Daily research admission covers exactly these families:

1. instrument identity;
2. trading calendar;
3. raw unadjusted EOD price;
4. daily price limits;
5. suspension state;
6. risk-warning state;
7. adjustment factors;
8. corporate actions;
9. instrument lifecycle;
10. daily Universe membership;
11. effective-dated trading rules;
12. effective-dated fees; and
13. historical coverage.

Completeness is measured over the exact target sessions and evaluated
population. A price row without a stable ID or tradability state is not a
complete research observation.

## A-share execution facts

The foundation must preserve, by effective date and board where relevant:

- T+1 share-sale restriction;
- board- and state-specific price-limit regime, including no-limit sessions;
- exact source-observed limit prices when available;
- suspension/resumption and absent-bar semantics;
- ST/risk-warning subtype and its historical validity;
- minimum order and share increments;
- commissions, transfer fees, and stamp duty; and
- earliest feasible execution relative to the signal cutoff.

Daily research may use conservative close-to-next-session assumptions only
when those assumptions are registered and the security was executable. It may
not claim intraday limit-board fills, queue priority, or realistic high-
frequency execution from EOD data.

## Five-year build sequence

1. Qualify a small, deliberately varied pilot containing each exchange, major
   boards, an ST observation, a suspension, a corporate action, and a lifecycle
   edge case.
2. Run exact replay and source-repeat comparison before expansion.
3. Materialize source packages and normalized observations by bounded session
   partitions.
4. Cross-check identities, prices, calendars, states, and events without
   overwriting disagreements.
5. Resolve effective-dated rules, actions, and lifecycle evidence.
6. Build daily Universe decisions with one disposition per evaluated
   instrument.
7. Publish a coverage census and admission decision.
8. Open Factor Discovery only for the exact admitted interval and population.

Expansion stops on systemic schema drift, unexplained coverage loss,
unbounded rate failure, fingerprint mismatch, or a critical family with no
defensible source. Isolated record conflicts are quarantined and do not force
unrelated partitions into an infinite repair loop.

## Performance and storage design

- Network acquisition is I/O-bound and uses bounded concurrency plus source-
  compliant pacing; CPU parallelism does not defeat provider limits.
- Normalization, reconciliation, feature materialization, and reporting may
  use workstation cores on immutable partitions.
- Parquet and small manifests remain the default research store. A service
  database is introduced only if measured query/concurrency needs justify it.
- Raw snapshots are append-only; canonical corrections create new revisions.
- Reusable panels are content-addressed and cannot mix factor and future-label
  custody.

## Admission states

- `source_incomplete`: one or more required families are absent or partial;
- `quarantined`: apparent coverage exists but critical conflicts or unresolved
  evidence remain; and
- `research_backtest_ready`: every required family is complete for the exact
  declared scope.

Even the final state authorizes only daily research backtesting. Intraday,
live-model, Product publication, deployment, and trading authority remain
false unless separately approved.
