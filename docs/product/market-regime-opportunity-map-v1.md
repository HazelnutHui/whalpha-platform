# Market Regime & Opportunities V1

> **Current contract and historical implementation record.** Sections that
> describe the deployed Candidate score, Entry Geometry, or Strategy Channels
> remain authoritative for **Baseline V1** behavior only. Future model research
> and Candidate promotion are governed by
> [Quant Research Lab](quant-research-lab-v1.md) and
> [ADR 0191](../decisions/0191-promote-validated-research-models-into-stock-candidates.md);
> this document does not authorize direct tuning of the baseline formulas.

User-facing Chinese name: **市场风向与机会**. Existing machine-contract IDs and
filenames retain `market-regime-opportunity-map` for compatibility.

## Status and decision boundary

Status: **Implemented and production-published through the separate immutable
Market Intelligence boundary.** Exact active session, freshness, publication,
and release identity belong in
[current context](../project/current-context.md).

Phase 1a now implements the fixed five-dimension raw-metric, normalization,
Composite, missingness, contribution, and explanation ledger for explicit
completed sessions. It writes canonical review artifacts only under `/tmp` and
has no API, frontend, snapshot, pointer, or Production publication boundary.
The Phase 1a profile deliberately keeps its original `regime_state=null` and
`state_classification_status=deferred_phase_1a` semantics. Phase 1b consumes
version-compatible Phase 1a Composites without changing their formulas or
fingerprints, and emits a separate candidate/confirmed state history under
`/tmp`. The immutable Market Intelligence publisher now validates these audit
sources, promotes a language-neutral payload to `/data`, and exposes it through
the versioned Snapshot consumer (currently Snapshot 1.11 / Dashboard 2.8). The
audit artifacts remain immutable sources;
they are not themselves Production pointers.

Phase 2 consumes the same once-loaded 26-session panel and the completed Phase
1 audit ledgers. It computes all 16 pre-registered pairs for 5, 10, and 20
XNYS-session windows, writes a separate canonical `/tmp` audit, and does not
change either regime result. It does not scan or rank unregistered pairs.

Phase 5 now implements the offline candidate score, risk-mode, and candidate-
state core: strict ledgers, the frozen seven-component parameter set, source-
bound bar coverage, price-derived registered-ETF proxy selection, missing-
component reweighting, anomaly quarantine, deterministic Conservative/
Balanced/Aggressive ranking, Watch/Prepare/Enter/invalidated replay, an
independent raw-panel Oracle, and canonical `/tmp` audit/reread. Phase 6 adds
the bounded, language-neutral Candidate publication and multilingual Stock
Candidate workspace. It was introduced with MI 1.1 / Snapshot 1.6 / Dashboard
2.3 and remains active through the current MI 1.3 / Snapshot 1.11 / Dashboard
2.8 consumer; later publications still require separate approval.

Phase 7 adds the additive entry-geometry layer without changing the deployed
Candidate score or rank. It separates “which stocks show leadership” from
“whether current price location merits technical review” and classifies
bounded breakout, breakout watch, orderly pullback, strong but extended, or no
viable setup. Candidate publication 1.1 and later Snapshot consumers now carry
this layer into the frontend.

The initial design baseline remains `as_of_session=2026-08-21`; Production
rolls the same versioned formulas and registered relationships with matching
same-day Identity and EOD sources. Baselines and active publications must never
mix Identity dates.

This specification defines a transparent decision-support page for short-horizon
equity research. It does not issue trading instructions, estimate certain
outcomes, or model option returns.

The page is intended to help answer, in order:

1. Where is market risk appetite now, and what changed?
2. Which economically registered ETF relationships are strengthening,
   weakening, diverging, or breaking?
3. Which active-Universe stocks deserve research now for a one-to-five-session
   underlying move?
4. For an existing holding, which evidence has weakened enough to require
   review?

The underlying use case may involve options with at least roughly half a month
to expiry, but V1 evaluates the underlying stock only. There is no formal
options chain, implied-volatility, Greeks, open-interest, spread, or execution
dataset. The page must say this plainly.

The machine contract is defined in
[Market Regime & Opportunity Map V1 data contract](../data-contracts/market-regime-opportunity-map-v1.md).
The implementation sequence is defined in
[Market Regime & Opportunity Map V1 architecture](../architecture/market-regime-opportunity-map-v1.md).

## Frozen source baseline

The 2026-08-21 design baseline is:

- EOD: 9,941 completed rows, content fingerprint
  `b3d4acc3184e909e233778c6009e9fb81baa5058f67ab2cdd7cef1e84ae4870f`;
- same-day Identity: 9,968 Instrument Master rows, 13,131 provider identity
  rows, 9,968 resolver rows, logical fingerprint
  `9129f3a7cc7bd3b2902471a6c76b64e6c5772cdb27cdc54fb94da5c3f20899d6`;
- Primary: 1,718 Common Shares, membership fingerprint
  `c3665203965b96528c9be07db3c49d18023104e346da16050f1170d4fe148978`;
- Secondary: 1,831 members, exactly Primary plus 113 ADRCs, membership
  fingerprint
  `2dce08e728774510878c47dc80898e10236952dacd146990ad344c4dcb75a295`;
- activation pointer fingerprint
  `dbe6056e1ed4b87ebce88b356c346831ce67431a263066cd283b9ad7e8067168`.

Formal reads found 1,716/1,718 Primary and 1,829/1,831 Secondary members with a
2026-08-21 canonical bar. Missing observations remain missing; they are not
zero-filled.

## Data feasibility inventory

This matrix records what is physically and formally available at the frozen
baseline. “History sufficient” means sufficient for the V1 formula, not for a
credible long-horizon backtest.

| Capability / metric | Current field exists | Current history sufficient | Directly computable | New derived data | New provider | V1 treatment |
|---|---:|---:|---:|---:|---:|---|
| Common Shares membership | Yes | Yes | Yes | No | No | Formal Primary only; stable `instrument_id` keys |
| ADRC membership | Yes | Yes | Yes | No | No | Formal Secondary delta of 113; selectable, not hidden |
| ETF data | Yes | 26 sessions | Yes | No | No | Formal Identity/EOD reader; separate from equity Universe |
| Index proxies | ETF proxies only | 26 sessions | Yes | Yes | No | SPY, QQQ, IWM, DIA; call them proxies, not index levels |
| Sector ETF proxies | Yes | 26 sessions | Yes | Yes | No | Eleven registered Select Sector ETFs; not stock taxonomy |
| Industry/theme ETF proxies | Yes | 26 sessions | Yes | Yes | No | SMH, XBI, KRE, IGV; curated analytical baskets only |
| OHLC | Yes | 26 sessions | Yes | No | No | Exact `decimal128(38,10)` canonical values |
| Volume | Yes | 26 sessions | Yes | No | No | Exact Decimal; participation proxy, never fund flow |
| VWAP | Nullable field; 9,941/9,941 present on baseline | 26 sessions | Yes, when present | No | No | Optional evidence; absence never becomes zero |
| Previous close | No stored field | 26 sessions | Yes | Yes | No | Join prior completed session by stable ID |
| Dollar-volume proxy | No usable stored field | 26 sessions | Yes | Yes | No | `close × volume`; stored `notional` is a zero placeholder |
| 5-session history | Yes | Yes | Yes | Yes | No | Supported with at least 6 completed sessions |
| 10-session history | Yes | Yes | Yes | Yes | No | Supported with at least 11 completed sessions |
| 20-session history | Yes | Yes | Yes | Yes | No | Supported with at least 21 completed sessions |
| 40-session history | No | No | No | Yes | No, after more EOD | Return null with `insufficient_history` |
| 60-session history | No | No | No | Yes | No, after more EOD | Needed for robust relationship standardization |
| Point-in-time sector taxonomy | Logical contract only | No | No | Yes | Likely | V1B dependency; not a V1A blocker |
| Point-in-time industry taxonomy | Logical contract only | No | No | Yes | Likely | V1B dependency; no price-based substitution |
| Market capitalization | No | No | No | No | Yes | No market-cap weighting or heatmap |
| Shares outstanding | No | No | No | No | Yes | Deferred; cannot synthesize market cap |
| Corporate actions | Contract only; factors unverified | No | No | Yes | Likely | Quarantine extreme moves for review; do not adjust manually |
| Fundamental statements | No | No | No | No | Yes | Deferred to a later module |
| Valuation metrics/models | No | No | No | Yes | Yes | Deferred; no value score in V1 |
| Options chains | No | No | No | No | Yes | No option selection or payoff simulation |
| Implied volatility | No | No | No | No | Yes | Deferred |
| Greeks | No | No | No | No | Yes | Deferred |
| Open interest | No | No | No | No | Yes | Deferred |
| True fund flows | No | No | No | No | Yes | Never infer from price or volume |

The formal read boundary contains 26 consecutive completed XNYS sessions from
2026-07-17 through 2026-08-21. It supports one current 20-return correlation
and a comparison with the window ending five sessions earlier, but it does not
support a stable 40- or 60-session empirical distribution. Historical
calculations over the current active membership are explicitly
`current_as_of_constituent_replay`, not a survivorship-free backtest.

### V1A and V1B split

- **V1A — Market Regime Core + ETF Relationship Map:** uses completed EOD,
  same-day Identity, and activated memberships. It can be implemented now.
- **V1B — Sector Breadth + Stock Opportunity Transmission:** activates only
  after an effective-dated canonical sector/industry taxonomy is completed and
  formally readable.

V1A may calculate a stock’s statistical exposure to a registered ETF from
prices. The UI and contract must label it `price-derived exposure proxy`. It is
not sector membership. Price correlation must never populate the formal
classification field.

## Shared quantitative conventions

For instrument `i` and session `t`:

```text
r(i,t,k) = close(i,t) / close(i,t-k) - 1
gap(i,t) = open(i,t) / close(i,t-1) - 1
dollar_volume_proxy(i,t) = close(i,t) × volume(i,t)
log_return(i,t) = ln(close(i,t) / close(i,t-1))
```

All session offsets use completed XNYS sessions, never calendar days. Price,
volume, ratios, and return differences are calculated without future data.
Ticker is display metadata; all joins use stable `instrument_id`.

Two fixed normalizers are used:

```text
L(x; low, high) = 100 × clip((x - low) / (high - low), 0, 1)
D(x; low, high) = 100 - L(x; low, high)
```

`L` means higher is more supportive. `D` means lower is more supportive. A
two-sided metric explicitly defines its center and tails. No threshold is
estimated from the 2026-08-21 observation.

Cross-sectional metrics use this versioned robust normalizer:

1. include only eligible observations for the selected Universe and session;
2. winsorize at the session’s 5th and 95th percentiles using inclusive linear
   interpolation (`h=(n-1)p`) under the local Decimal context;
3. compute `z = 0.67448975 × (x - median) / MAD`;
4. apply the declared direction and publish `clip(50 + 15 × z, 0, 100)`;
5. if `MAD=0`, use average-tie percentile rank; if every value is tied, emit
50 for all records and warning `zero_cross_sectional_dispersion`.

Average-tie percentile fallback uses inclusive 0–100 ranks: the first ordered
observation is 0, the last is 100, tied observations receive their average
rank, and stable ID order makes grouping deterministic. These computation-only
conventions are versioned; they were not fitted from observed outcomes.

The raw value, winsorized value, median, MAD, z-score, direction, normalized
score, configured weight, effective weight, and contribution remain visible.

## A. Market Regime Header

### Composite definition

Every dimension is 0–100, where a larger number means a more supportive risk
environment. The fixed V1 composite is:

```text
regime_score =
    0.30 × Trend
  + 0.25 × Breadth
  + 0.20 × Volatility
  + 0.15 × LiquidityParticipation
  + 0.10 × LeadershipDispersion
```

The configured weights always sum to 100%. The base score is never changed by
risk mode. If a metric is missing, its dimension requires at least 70% of its
configured internal weight; otherwise the dimension is null. Available
internal metrics are reweighted only within that dimension and both configured
and effective weights are published. A regime state is emitted only when
Trend, Breadth, and Volatility are present and at least 90 composite weight
points are available. Otherwise `regime_state=null`, freshness is not
overridden, and `regime_unavailable` is shown.

### 1. Trend — composite weight 30%

Inputs are the registered broad-market ETF proxies SPY, QQQ, IWM, and DIA.

| Metric | Formula and window | Minimum | Direction / normalization | Internal weight |
|---|---|---:|---|---:|
| Broad 20-session return | Median `r(etf,t,20)` | 4 ETFs with 21 closes | Higher; `L(-8%, +8%)` | 35% |
| Broad 5-session return | Median `r(etf,t,5)` | 4 ETFs with 6 closes | Higher; `L(-3%, +3%)` | 25% |
| Above SMA20 share | Fraction with `close(t) > mean(close[t-19:t])` | 3 of 4 ETFs, 20 closes | Higher; `L(25%, 75%)` | 20% |
| Direction agreement | Fraction whose 5-session return has the same sign as the basket median; a zero median requires zero returns | 3 of 4 ETFs | Higher; `L(25%, 75%)` | 20% |

Template: “Trend is {supportive/mixed/weak}: the broad basket median is {r5}
over 5 sessions and {r20} over 20; {n}/4 benchmarks agree.”

### 2. Breadth — composite weight 25%

Inputs are members of the selected active Universe with valid bars. Primary is
the default. Missing members are counted and excluded from metric denominators.

| Metric | Formula and window | Minimum | Direction / normalization | Internal weight |
|---|---|---:|---|---:|
| One-session advancer share | `count(r1>0) / count(valid r1)` | 80% membership coverage and 500 observations | Higher; `L(35%, 65%)` | 25% |
| Positive 5-session share | `count(r5>0) / count(valid r5)` | 80% coverage and 6 sessions | Higher; `L(35%, 65%)` | 25% |
| Above SMA20 share | `count(close>SMA20) / count(valid SMA20)` | 75% coverage and 20 sessions | Higher; `L(30%, 70%)` | 30% |
| 20-session high/low balance | `(count(close=20-session high)-count(close=20-session low))/valid` | 75% coverage and 20 sessions | Higher; `L(-10%, +10%)` | 20% |

Template: “Breadth {confirms/conflicts with} the headline: {advancer_share}
advanced, {above_sma20_share} are above SMA20, with {missing_count} missing.”

### 3. Volatility — composite weight 20%

This is an EOD realized-risk proxy, not implied volatility.

| Metric | Formula and window | Minimum | Direction / normalization | Internal weight |
|---|---|---:|---|---:|
| SPY realized volatility | Sample standard deviation of 10 daily log returns × `sqrt(252)` | 11 closes | Lower; `D(10%, 35%)` | 35% |
| Median stock realized volatility | Median annualized 10-return volatility in selected Universe | 70% coverage | Lower; `D(25%, 80%)` | 25% |
| Downside-tail frequency | Fraction of valid instrument-session returns at or below -4% in last 5 sessions | 70% coverage | Lower; `D(0%, 8%)` | 20% |
| One-session cross-sectional dispersion | `1.4826 × MAD(r1)` | 500 observations | Lower; `D(1%, 4%)` | 20% |

Template: “Realized risk is {contained/elevated}: SPY 10-session annualized
volatility is {value}; downside-tail frequency is {value}. Options IV is not
available.”

### 4. Liquidity / Participation — composite weight 15%

These metrics describe observed trading participation. They do not measure
capital flows.

| Metric | Formula and window | Minimum | Direction / normalization | Internal weight |
|---|---|---:|---|---:|
| Aggregate participation ratio | Current sum of `close×volume` divided by median of prior 20 session sums over the same eligible membership | 18 valid reference sessions and 80% daily coverage | Higher; `L(0.75, 1.25)` | 40% |
| Up-participation share | Sum `close×volume` for advancers divided by sum for all valid comparable members | 80% coverage; positive denominator | Higher; `L(35%, 65%)` | 30% |
| Above-own-volume-median share | Fraction whose current volume exceeds its own prior-20-session median | At least 15 prior observations per member and 70% aggregate coverage | Higher; `L(35%, 65%)` | 30% |

Template: “Participation is {expanding/normal/contracting}: aggregate
close-times-volume is {ratio}× its 20-session median. This is a participation
proxy, not fund flow.”

### 5. Leadership Concentration / Dispersion — composite weight 10%

| Metric | Formula and window | Minimum | Direction / normalization | Internal weight |
|---|---|---:|---|---:|
| Winner concentration | Share of total positive 5-session return magnitude contributed by the top 10% of positive-return members | 200 positive observations and 70% coverage | Lower concentration is healthier; `D(35%, 70%)` | 45% |
| Benchmark direction agreement | Fraction of SPY/QQQ/IWM/DIA with the same 5-session sign | 3 of 4 ETFs | Higher; `L(25%, 75%)` | 30% |
| Five-session return dispersion | `1.4826 × MAD(r5)` | 500 observations | Two-sided: 0 at ≤0.5% or ≥8%, 100 at 2.5%, linearly interpolated | 25% |

The two-sided metric avoids treating both stagnant markets and disorderly
dispersion as healthy. Template: “Leadership is {broad/concentrated/disorderly};
the top return decile accounts for {share} of positive 5-session movement.”

The fixed V1 top-decile cardinality is `ceil(0.10 × positive_count)`. Rows are
ordered by positive return descending and stable `instrument_id` ascending, so
the cutoff is deterministic even when returns tie. Missing dimensions are not
reweighted across the Composite: a present dimension retains its configured
Composite weight, while missing metric weight may be redistributed only inside
that dimension. The available configured Composite weight and missingness
remain explicit; the Composite is null unless Trend, Breadth, and Volatility
are present and at least 90 configured weight points are available.

### Conflicting evidence

A dimension conflicts with the headline when either:

- its score is at least 20 points below the composite; or
- its fixed raw band implies the opposite side of 50 from the composite.

The header lists all such dimensions. It also shows the current score, prior
session score, five-session-ago score, their deltas, source session, parameter
set, and data-quality state.

### Regime state and hysteresis

Unhysterized bands are Risk-on `>=70`, Balanced `50–<70`, Defensive `30–<50`,
and Stress `<30`. Published state follows this deterministic transition table:

| Current state | Proposed state | Entry condition | Minimum confirmation |
|---|---|---|---:|
| Bootstrap | Any | Two consecutive raw bands agree; otherwise choose the more defensive band and mark provisional | 2 sessions |
| Balanced | Risk-on | score `>=70` | 2 consecutive sessions |
| Risk-on | Balanced | score `<65` | 2 consecutive sessions |
| Balanced | Defensive | score `<45` | 2 consecutive sessions |
| Defensive | Balanced | score `>=55` | 2 consecutive sessions |
| Defensive | Stress | score `<30` | 2 consecutive sessions |
| Any non-Stress | Stress | score `<=20` | 1-session immediate stress override |
| Stress | Defensive | score `>=35` | 3 consecutive sessions |

Normal transitions move one adjacent state at a time. The immediate stress
override is the only skip. Missing required data never changes state: it makes
the current calculation unavailable and displays the prior state as stale,
with no synthetic confirmation session.

Phase 1b freezes the remaining initialization and replay details in the
corrected state parameter set `mrom-regime-state-v1-stable-prefix-2`,
fingerprint
`cbbce1923f7993ea936d41c989cad5296883c368e98f63c731a45c9fa3d9c2d0`.
The legacy fixed-baseline-1 parameter remains readable but its rolling-window
bootstrap is not eligible for new incremental work:

- the first available candidate starts a two-session bootstrap and is never
  silently accepted as confirmed;
- if the first two candidates disagree, the more defensive one is initialized
  as provisional; one later available session matching it clears provisional;
- a missing Composite creates an explicit unavailable/stale row, holds the last
  confirmed state, and pauses rather than increments a pending counter;
- the caller supplies a complete, unique, ascending XNYS-session sequence;
  duplicates, non-XNYS dates, or an omitted expected session fail closed;
- pending confirmation reversals reset deterministically; ordinary cross-level
  changes advance only one adjacent state, while `score <=20` remains the sole
  immediate cross-level Stress override; and
- replay from the first session, daily append, and restart from a serialized
  prefix must produce the same state history fingerprint; and
- cold replay retains the first contiguous canonical session as its left
  boundary across adjacent as-of dates, while each Composite uses at most its
  exact trailing 26-session source window.

These are transparent operating rules, not fitted thresholds. They were not
selected from the frozen 2026-08-21 outcome and have not been statistically
validated as a predictive model. A parameter change requires a new version and
fingerprint.

## B. ETF Relationship Map

### Registered V1A basket

Every listed ETF was formally resolved as `instrument_type=etf` and had a valid
bar in all 26 baseline sessions.

| Basket | Registered tickers | Use |
|---|---|---|
| Broad market | SPY, QQQ, DIA | Large/broad and growth-heavy market proxies |
| Growth/value | IWF, IWD, VUG, VTV | Style comparisons; IWF/IWD is the primary registered pair |
| Size | IWM, MDY, IJR | Small-, mid-, and smaller-cap proxies relative to SPY |
| Sector | XLB, XLC, XLE, XLF, XLI, XLK, XLP, XLRE, XLU, XLV, XLY | ETF direction only; never stock sector breadth |
| Industry/theme | SMH, XBI, KRE, IGV | Curated semiconductor, biotech, regional-bank, and software proxies |
| Rates/credit | TLT, IEF, SHY, HYG, LQD | Duration and credit-risk proxies |
| Dollar/commodity/defensive | XLP, XLU only for defensive context | No approved direct dollar or commodity proxy in V1A |

GLD, USO, UUP, and DBA were not available through the formal 2026-08-21
Identity/EOD reader and are not registered. Their absence is visible rather
than replaced by a look-alike product.

### Pre-registered pair ledger

V1 permits only these 16 economically interpretable numerator/denominator
pairs:

| Pair ID | Pair | Interpretation to investigate, not assume |
|---|---|---|
| `growth_broad` | QQQ / SPY | Growth-heavy leadership versus broad large-cap market |
| `growth_value` | IWF / IWD | Growth versus value rotation |
| `small_large` | IWM / SPY | Small-cap participation versus broad large-cap market |
| `mid_large` | MDY / SPY | Mid-cap participation versus broad large-cap market |
| `consumer_risk` | XLY / XLP | Cyclical versus defensive consumer behavior |
| `technology_defensive` | XLK / XLU | Technology sensitivity versus utilities defense |
| `industrial_defensive` | XLI / XLU | Industrial cyclicality versus utilities defense |
| `financial_defensive` | XLF / XLU | Financial cyclicality versus utilities defense |
| `energy_broad` | XLE / SPY | Energy leadership versus broad equities |
| `health_broad` | XLV / SPY | Health-care relative defense/leadership |
| `semis_growth` | SMH / QQQ | Semiconductor leadership within growth exposure |
| `biotech_health` | XBI / XLV | Biotech risk appetite versus broad health care |
| `regional_financials` | KRE / XLF | Regional banks versus broad financials |
| `software_growth` | IGV / QQQ | Software relative strength within growth exposure |
| `credit_quality` | HYG / LQD | Lower-quality versus investment-grade credit proxy |
| `credit_duration` | HYG / TLT | Credit risk appetite versus long-duration defense |

Adding, deleting, or changing a pair requires a new `parameter_set_id`; V1 does
not scan all tickers for attractive historical relationships.

### Relationship statistics

For pair numerator `A`, denominator `B`:

```text
pair_spread_k = r(A,t,k) - r(B,t,k)
ratio_level_t = ln(close(A,t) / close(B,t))
corr20_t = PearsonCorr(daily log returns A,B over last 20 returns)
corr_change_5 = corr20_t - corr20_(t-5)
```

The implemented offline profile emits `k in {5,10,20}`. An `N`-session return
uses the inclusive endpoint sequence `t-N ... t` (N+1 closes); its correlation
uses the N adjacent daily log returns from the same endpoints. One missing
paired close makes that window unavailable rather than shortening or filling
it. The 20-session correlation remains the state-classification correlation.

Requirements and states:

- 5-session return needs 6 paired closes; 20-session return and `corr20` need
  21 paired closes and at least 18 valid return pairs.
- `corr_change_5` needs 26 paired closes and both windows need 18 valid pairs.
- Robust ratio z-score uses the latest ratio minus the rolling 20-session
  median divided by rolling MAD, but is emitted only after 60 ratio
  observations. A percentile requires the same minimum. At the frozen
  baseline both are null with `insufficient_history`.
- `synchronous_strengthening`: both 5-session returns are positive and
  `corr20>=0.35`.
- `synchronous_weakening`: both are negative and `corr20>=0.35`.
- `divergence`: return signs differ and `abs(pair_spread_5)>=2%`.
- `rotation_candidate`: `abs(robust_z)>=1.5`, the 5-session spread moves in
  the same direction, and the condition holds two sessions.
- `relationship_break_candidate`: prior correlation `>=0.50`, current
  correlation `<=0.10`, and `corr_change_5<=-0.30`.
- otherwise the state is `neutral`.

If more than one state qualifies, priority is relationship break, rotation,
divergence, synchronous strengthening, synchronous weakening, then neutral.
This priority is versioned and deterministic.

### Stability and confidence

Confidence describes statistical support, not outcome probability:

- `insufficient`: fewer than 21 paired closes;
- `low`: 21–59 paired closes;
- `medium`: 60–119 paired closes and the state survives 18/20/22-return
  perturbations;
- `high`: at least 120 paired closes, the perturbation check passes, and the
  same direction appears in at least two non-overlapping 20-return blocks.

The frozen baseline therefore cannot exceed `low`. If p-values are displayed,
they are descriptive and Holm-adjusted across the fixed 16-pair family. No card
is promoted solely because a p-value crosses a threshold.

The implemented parameter contract is
`mrom-etf-relationships-v1-fixed-registry-1`, fingerprint
`c84d6338412f68be44e35760de83bbad8dd306bbbd480166e874fc05eee5eca9`.
At the 26-session baseline every pair is available but confidence is `low`;
ratio z-score and percentile remain null because their 60-observation gate is
not met. This is an implementation/replay validation, not a backtest.

Each card shows the current and five-session-ago statistics, delta, economic
rationale, a plausible reverse explanation, sample size, confidence, and
invalidation. It always carries: “Statistical relationship; not evidence of
causality.”

The presentation projection additionally shows how many retained sessions the
current state has persisted and whether the rolling relative-return advantage
expanded, narrowed, reversed, newly appeared, or faded over one and five
sessions. These are descriptive changes in overlapping rolling windows—not a
new relationship score, causal attribution, or predictive signal.

Relationship detail also uses a bounded ten-point state path to distinguish a
stable condition from frequent switching. Each point shows its frozen state
and the selected-window relative return. The retained-history start/count and
any older-point compaction are explicit, so the visual cannot imply that the
displayed first point began the economic relationship.

## C. Opportunity Transmission

The intended path is:

```text
Market Regime → registered ETF or formal sector direction → active-Universe stock candidates
```

V1A stops at registered ETF direction. A stock may be associated with the
approved driver ETF having the highest positive 20-return correlation when
there are at least 18 paired returns and `correlation>=0.35`; ticker breaks
ties ascending. That association is a `price-derived exposure proxy`, is capped
in scoring, and cannot populate sector or industry fields. V1B replaces it with
effective-dated formal taxonomy while retaining the proxy as separate evidence.

Only active Primary or Secondary members may become candidates. Primary is the
default, Secondary is opt-in, and Legacy never enters ordinary results.

### Fixed base candidate score

The V1 base score is fixed and independent of risk mode:

| Component | Weight | Exact V1 content |
|---|---:|---|
| Market alignment | 12% | Current transparent regime composite; null when regime unavailable |
| ETF/sector alignment | 13% | V1A: 40% driver 5-session return relative to SPY + 35% stock-minus-driver 5-session return + 25% normalized positive 20-return correlation; capped at 70 because it is a proxy. V1B removes the cap only for formal taxonomy evidence |
| Stock relative strength | 25% | 45% robust score of `r5-stock - r5-SPY`, 35% robust score of `r20-stock - r20-SPY`, 20% within-Universe 20-session return percentile |
| Trend quality | 18% | 35% `close>SMA10`, 35% normalized `(SMA10/SMA20-1)` using `L(-3%,3%)`, 30% inverse maximum 5-session close drawdown using `D(2%,12%)` |
| Volume participation | 12% | 50% robust score of `ln(current volume / prior-20 median)`, 25% up-session participation indicator, 25% fraction of last 5 sessions above own prior-20 volume median |
| Volatility / risk | 10% | 50% inverse 10-return realized volatility, 30% inverse maximum absolute 5-session open gap, 20% inverse 5-session downside-tail frequency |
| Liquidity suitability | 10% | 70% `L(log10(median20 close×volume), log10(USD 5M), log10(USD 100M))` + 30% `L(price, USD 2, USD 20)` |

Weights sum to exactly 100%. Stock-specific relative strength and trend receive
43% because the decision horizon is one to five sessions; the market and
relationship layers provide context rather than overriding stock evidence.
Price, return, volume, and liquidity inputs are visible. Volume participation
is not called buying pressure, money flow, or fund flow.

If more than 20 configured weight points are unavailable, the base score is
null. Otherwise available components are explicitly reweighted, and configured
weights, effective weights, and a missingness penalty are displayed. A
corporate-action quarantine or source-integrity failure prevents state
promotion even if the numeric score is high.

The subcomponent calculations are fixed as follows:

- **Market alignment:** the selected Universe’s regime score. There is no V1
  regime adjustment; `regime_adjustment=0` and `adjusted_score=base_score` are
  published to prevent an implicit adjustment later.
- **ETF/sector alignment:** in V1A a driver must be in the registered basket,
  have positive 5-session direction, at least 18 paired returns, and
  `correlation20>=0.35`. Choose the highest correlation, ticker ascending on a
  tie. Score `40%` robust cross-sectional driver 5-session return relative to
  SPY, `35%` robust cross-sectional stock-minus-driver 5-session return, and
  `25% L(correlation20; 0.35, 0.80)`, then cap the component at 70. No qualifying
  driver makes the component missing; it does not invent a sector.
- **Stock relative strength:** exactly the three weighted submetrics in the
  table. Each requires its named return window; the percentile uses average
  ties and stable-ID order before ranking.
- **Trend quality:** `close>SMA10` contributes 100 or 0; the SMA10/SMA20 ratio
  uses `L(-3%,+3%)`; maximum drawdown is the most negative
  `close(s)/max(close through s)-1` over six closes and uses `D(2%,12%)` on its
  absolute value.
- **Volume participation:** the log volume ratio uses the robust normalizer;
  the up-session indicator is 100 when `r1>0` and current volume is above its
  prior-20 median, 50 when exactly one condition holds, otherwise 0; five-day
  persistence is `100 × count(volume above the then-available prior-20
  median)/valid sessions`, with at least four valid sessions.
- **Volatility/risk:** annualized 10-return volatility uses `D(25%,100%)`;
  maximum absolute five-session open gap uses `D(3%,20%)`; downside-tail share
  is the fraction of the last five valid returns at or below -4% and uses
  `D(0%,40%)`.
- **Liquidity suitability:** the 20-session median needs at least 15
  observations. The log and price normalizers are exactly those in the table;
  nonpositive inputs are invalid rather than clipped.

Candidate confidence is data support, not win probability:

```text
confidence =
    0.40 × (configured component weight available / 100)
  + 0.25 × min(valid required history sessions / 21, 1)
  + 0.20 × relationship support
  + 0.15 × min(current state confirmation count / 3, 1)
```

Relationship support is 0/0.40/0.70/1.00 for
insufficient/low/medium/high. All four terms are displayed.

`current state confirmation count` is not a caller-supplied judgment. For an
as-of calculation it is the capped consecutive-session count carried by the
immediately preceding compatible candidate-state ledger row for the same
stable `instrument_id`; it is zero when no prior row exists. The score is
calculated first from that prior-state fact, then the current state transition
is evaluated. The current row never feeds back into its own confidence.

### Explanations

Every candidate emits five blocks:

- **Surfaced because:** strongest positive contributions and the state trigger;
- **Supporting evidence:** raw metrics, normalized scores, sessions, and source
  fingerprints;
- **Counterevidence:** the two strongest negative or missing contributions;
- **Invalidation:** deterministic price/trend/risk conditions that would make
  the candidate stale or invalid;
- **Data-quality caveat:** missing fields, current-constituent replay,
  unverified corporate-action status, and proxy labels.

## D. Candidate Detail Drawer

The drawer contains:

- ticker, stable instrument ID, security type, selected Universe, and latest
  source session;
- candidate/position context, current stage, raw base score, risk-adjusted rank,
  confidence, and missingness;
- all component raw values, normalized values, weights, and contributions;
- a linked market-context, registered ETF price-proxy, stock-leadership,
  entry-location, and re-underwrite path that never promotes the price proxy
  into formal sector membership;
- “why now,” supporting evidence, counterevidence, reason codes, and
  invalidation conditions;
- one-to-five-session attention window, explicitly not a holding instruction;
- median 20-session dollar-volume proxy, price, realized volatility, maximum
  five-session open-gap proxy, and downside-tail observations;
- primary registered ETF relationship and whether it is a price-derived proxy
  or formal taxonomy relationship;
- corporate-action/extreme-return quarantine status;
- next manual checks: company event, corporate action, option liquidity/IV and
  spread, news, earnings timing, position-specific risk, and execution quality.

Language such as “must buy,” “will rise,” or guaranteed return is prohibited.

## Candidate and position state machine

The common display labels are Watch, Prepare, Enter, and Exit, but the contract
also carries `decision_context=candidate|position`:

- **Watch:** worth tracking, evidence incomplete;
- **Prepare:** several conditions are improving but no trigger is confirmed;
- **Enter:** EOD conditions meet the research/execution-candidate gate; it is
  not an order instruction;
- **Exit:** for a position, momentum/risk has deteriorated and merits review;
  for a non-position, it displays as “candidate invalidated,” not a sale action.

### Deterministic transitions

| Transition | Rule | Confirmation |
|---|---|---:|
| Not listed → Watch | base score `>=50`, confidence `>=0.40`, price `>=USD 2`, median dollar-volume proxy `>=USD 5M` | 1 session |
| Watch → Prepare | base score `>=65`, regime not Stress, relative-strength and trend components each `>=55` | 2 consecutive sessions |
| Prepare → Enter | base score `>=75`, fixed state liquidity gates pass, and no quarantine | 2 consecutive sessions |
| Prepare → Enter trigger | prior state Prepare, current close exceeds the maximum close of the five completed sessions immediately before the current session, volume ratio `>=1.20`, base score `>=70`, regime not Stress | 1 session |
| Enter → Prepare | score `<68` or trend component `<50` | 2 consecutive sessions |
| Prepare → Watch | score `<58` or market alignment `<40` | 2 consecutive sessions |
| Any active stage → Exit/invalidated | score `<45`, fixed price/liquidity floor fails, or a declared invalidation condition fires | 1 session |
| Exit/invalidated → Watch | score `>=55`, anomaly cleared, liquidity gates pass | 3 consecutive sessions |

Hysteresis counters use completed sessions only. A missing required observation
does not increment a counter and holds the prior display state for at most one
session with `stale_state=true`; thereafter `opportunity_stage=null` and manual
review is required. It does not synthesize Exit.

An absolute close-to-close return of at least 50%, an absolute open gap of at
least 30%, a non-unit adjustment factor, a non-valid source quality status, or
an unknown source quality flag creates `corporate_action_review_required`.
The fixed source-level flags `adjustment_factors_unverified`, `missing_vwap`,
`missing_trade_count`, and `zero_volume` remain visible degraded evidence but
do not by themselves assert a security-specific corporate action: candidate
formulas either do not consume those fields or already expose the zero-volume
fact. Until a blocking review is cleared, the candidate cannot promote to
Prepare or Enter. Raw provider values are never manually altered.

All transitions emit stable reason codes, including
`score_prepare_confirmed`, `breakout_participation_trigger`,
`trend_deterioration`, `risk_gate_failed`, `candidate_invalidated`,
`missing_required_history`, and `corporate_action_review_required`.

## Risk modes

Risk mode does not change source facts, component values, the 0–100 base score,
or explanations. It changes eligibility, ordering, and concentration limits,
and publishes a separate `risk_adjusted_rank`.

| Parameter | Conservative | Balanced | Aggressive |
|---|---:|---:|---:|
| Minimum median 20-session dollar-volume proxy | USD 50M | USD 20M | USD 5M |
| Maximum annualized 10-return volatility | 45% | 65% | 100% |
| Maximum absolute five-session open gap | 8% | 12% | 20% |
| Minimum latest price | USD 10 | USD 5 | USD 2 |
| Minimum confidence | 0.75 | 0.60 | 0.45 |
| ADRC permitted | No | Yes, Secondary only | Yes, Secondary only |
| Candidate display cap | 25 | 50 | 100 |
| One formal sector / registered ETF proxy cap | 20% | 25% | 35% |

Until V1B, the concentration key is the registered ETF proxy and is labelled as
such. A candidate without a qualifying proxy is grouped under `unclassified`,
not assigned a guessed sector. Ranking sorts eligible records by base score
descending, confidence descending, liquidity descending, then ticker
ascending; a deterministic concentration pass removes excess rows. This is
the risk-adjusted rank. No personalized position amount is produced.

## Additive entry geometry and chase-risk boundary

Candidate leadership quality and entry location are two independent axes. A
high-ranked stock can be a valid research priority and simultaneously be too
extended for immediate technical review. The original base score, state, and
risk rank remain immutable inputs; entry geometry never applies a hidden
penalty to them.

The fixed V1 shadow layer publishes SMA10/SMA20 and ATR14 location, three- and
five-session movement, a volatility-scaled five-session move, trailing up
sessions, current gap/range/close location, volume ratio, prior-five-session
close high/low, and a labelled reference-support distance. It emits low,
moderate, high, or extreme extension plus one technical structure and review
posture. High or extreme extension always prevents `technical_review_ready`.

The human presentation target is a two-axis board with distinct lanes:

- **Technical review ready:** bounded breakout or orderly pullback; still
  requires event, thesis, options, position-risk, and execution checks.
- **Monitor for trigger:** near-breakout or otherwise incomplete structure.
- **Wait for reset:** leadership remains strong but price is high/extreme
  extension.
- **Deprioritized / not assessable:** score, state, source, or history gates do
  not support technical review.

Reference support is not a stop price, the volume/range climax flag is not a
reversal forecast, and no posture is an order instruction. Exact fields and
thresholds are authoritative in the
[Candidate Entry Geometry V1 contract](../data-contracts/candidate-entry-geometry-v1.md).

## Cross-workspace market-to-candidate decision chain

The Sector Rotation workspace may join three already published, same-session
views into one concise decision aid: the selected Universe's confirmed Market
Regime and score, the top five fixed-registry sector ETF price proxies for the
selected 5/10/20-session window, and the first eight published Balanced-risk
Candidate priorities. The browser must fail this joined view closed when the
session, Market Intelligence publication, or Universe bindings differ. The
underlying Sector Rotation workspace remains available when only the joined
view fails.

This is an information-flow visualization, not a new analytics product. It
does not calculate a combined score, reorder source Candidate ranks, infer
formal sector membership, or draw a security-level causal link from an ETF to
a Candidate. The ETF column is market-wide price evidence; the Candidate
column is an independent Universe-specific research rank. Exact registered
ETF proxy correlation, evidence, counterevidence, entry geometry, and
invalidation remain in the full Candidate review. The Candidate summary is
loaded after the small Sector Rotation resource, and no detail shard is read
to populate the concise view.

## Cross-channel decision desk and complete candidate review

The Strategy Channels view may summarize the first displayed record from each
currently available channel in one decision desk. This is a navigation and
review aid, not a new cross-channel ranking:

- each card remains explicitly labelled as that channel's own rank, score,
  status, extension risk, first supporting reason, and first rejection risk;
- cards retain the published channel order and are never sorted by score across
  strategies;
- unavailable channels remain visibly unavailable in the channel selector and
  are not filled with proxy candidates; and
- the desk does not calculate a combined score, preferred strategy, return
  estimate, or trade instruction in the browser.

Opening a strategy candidate must join the exact strategy assessment to the
same-instrument Candidate detail from the same active Snapshot. The combined
review shows the channel score ledger first, then the existing market-to-entry
decision chain, price path, descriptive support/breakout levels, chase risk,
base-score contribution ledger, counterevidence, and invalidation. If the
stable `instrument_id` is absent from the Candidate summary, or its bound detail
cannot be read and validated, the combined review fails closed rather than
showing a partial or inferred match. Ticker is presentation only and is never
used for the join.

## Evaluation and anti-overfitting contract

The original 26-session implementation history was sufficient for a
deterministic development preview, not for performance claims. Exact current
price depth belongs in
[current context](../project/current-context.md), and price depth alone does
not establish research readiness. Production research evaluation begins
only after at least 252 completed sessions; a stronger regime-stratified review
targets at least 504 sessions and at least 60 observations in each reported
regime, or labels that regime inconclusive.

Chronological evaluation is fixed before results are reviewed:

1. earliest 50%: parameter-development and data-quality calibration;
2. next 25%: validation, with at most one documented parameter-set revision;
3. final 25%: untouched holdout;
4. after freeze: monthly walk-forward scoring using only data available at each
   session and the parameter version already active then.

For shorter initial history, use expanding windows with a minimum 126-session
warm-up and 21-session evaluation blocks; do not relabel them holdout.

Report by score quintile, state, risk mode, and regime:

- 1-, 3-, and 5-session forward underlying returns;
- maximum favorable and adverse excursion from next-session open through the
  horizon when OHLC is available;
- hit rate and unconditional/eligible-Universe base rate;
- rank monotonicity and rank correlation;
- candidate turnover and state persistence;
- calibration of score bands against empirical outcome distributions;
- coverage, missingness, and excluded/quarantined counts;
- parameter and 18/20/22-window sensitivity;
- Universe stability and results both with point-in-time membership and the
  explicitly limited current-constituent replay;
- corporate-action-isolated and unisolated results;
- transaction-cost sensitivity at 0, 10, 25, and 50 basis points per side.

Do not report only mean return. Include median, quartiles, 5th/95th
percentiles, drawdowns, worst regimes, and failure cases. Options payoff is not
simulated; forward stock return is only a proxy for underlying opportunity
quality.

Minimum integration gates are reproducibility 100%, zero look-ahead/source
mismatch, at least 90% score coverage in both public Universes, deterministic
state transitions, no sign reversal of median rank monotonicity between
validation and holdout, and no material collapse versus the eligible-Universe
base rate across both validation and holdout. These are research-quality gates,
not promises of profit.

## Desktop-first information architecture

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ Market Regime & Opportunities     As of 2026-08-21   Freshness / sources   │
│ Universe: [Common Shares ▼]       Risk mode: [Balanced ▼]   Methodology     │
├───────────────────────────────┬──────────────────────────────────────────────┤
│ Regime: BALANCED  58 / 100    │ What changed                               │
│ Δ1 session / Δ5 sessions      │ Dimension, relationship, candidate changes │
│ supporting + conflicting dims │ with explicit source sessions              │
├───────────────────────────────┴──────────────────────────────────────────────┤
│ Five-dimension contribution bar: Trend | Breadth | Vol | Participation | L │
│ Click any segment → raw value, formula, normalizer, weight, caveat           │
├──────────────────────────────────────────────────────────────────────────────┤
│ ETF Relationship Map: 16 registered pairs; state, Δ, confidence, caveat     │
│ Filters: strengthening / weakening / divergence / rotation / break           │
├───────────────────────────────┬──────────────────────────────────────────────┤
│ Opportunity directions       │ Candidate table                              │
│ ETF-first in V1A             │ Stage, score, Δ, driver, liquidity, risk     │
│ taxonomy status visible      │ deterministic sort and missing-data badges   │
├───────────────────────────────┴──────────────────────────────────────────────┤
│ Data-quality warnings and methodology/version/source-fingerprint drawer      │
└──────────────────────────────────────────────────────────────────────────────┘
                                             Candidate detail drawer →
```

The first screen contains the headline, changes, contribution decomposition,
and highest-priority opportunity directions. It avoids dozens of decorative
cards. Muted sequential colors communicate magnitude; no saturated red/green
or celebratory treatment implies certainty. Every conclusion opens its formula
and source lineage.

On mobile, the header, What Changed, and top opportunity directions remain
first. The five-dimension decomposition becomes a vertical ledger; relationship
cards become a sortable list; the candidate table shows ticker, stage, score,
change, and risk only; detail opens full screen. Methodology and warnings are
never removed, and mobile receives identical data and freshness.

## Product language rules

- Fact: “SPY 5-session return is …”
- Proxy: “close-times-volume participation proxy increased …”
- Statistical inference: “the registered pair is diverging under V1 rules …”
- Hypothesis: “this may be consistent with rotation; a reverse explanation is
  …”

Correlation is never causality. Volume is never true flow. ETF exposure is
never formal sector membership. A candidate score is never a probability of
profit. Guest and authenticated users receive identical information,
functionality, precision, and timeliness unless the product requirement is
explicitly changed later.
