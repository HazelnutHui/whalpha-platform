# Market Regime & Opportunity Map V1 Data Contract

## Status

Status: **Proposed V1 contract; Phase 1a offline profile implemented; no
production dataset or API is active**.

The implemented Phase 1a profile is a reversible `/tmp` audit boundary. It
emits both public Universes in catalog order, five dimension ledgers, 18 metric
ledgers per Universe, the Composite, missingness, explanations, and an
independent-oracle report. It does not emit relationship, opportunity,
candidate, risk-mode, state-transition, or Production publication records.
`regime_state` is therefore null and
`state_classification_status=deferred_phase_1a`; this is a scoped implementation
state, not missing market data.

The checked-in parameter artifact is
`parameter_set_id=mrom-v1-fixed-baseline-1`, fingerprint
`69f9cb4744f4d133c72ba872588a87821b3445cabdd6fc129785f06232407759`.
The offline artifact set is exactly `input-manifest.json`, `raw-metrics.json`,
`normalized-metrics.json`, `composite.json`, `missingness.json`,
`explanation-ledger.json`, `oracle-report.json`, and a last-written
`calculation-manifest.json`. Every JSON file is canonical and hash-bound; only
physical audit metadata (`generated_at`, elapsed time, and peak memory) is
excluded from the aggregate logical fingerprint.

This contract freezes the machine-readable boundary for the product described
in [Market Regime & Opportunity Map V1](../product/market-regime-opportunity-map-v1.md).
It does not amend any existing Production market-data, Identity, Activation, or
Dashboard contract.

Initial identifiers:

- `contract_version=market-regime-opportunity-map/1.0`
- `calculation_version=market-regime-opportunity-map-v1.0.0`
- `parameter_set_id=mrom-v1-fixed-baseline-1`
- `history_membership_mode=current_as_of_constituent_replay`

Any formula, threshold, weight, pair, ordering, normalization, or state-machine
change requires a new calculation version and parameter set. Schema-compatible
additions require a contract minor version; incompatible changes require a
major version.

## Logical publication

One logical snapshot represents one completed `as_of_session`, one source
Activation pointer, both public Universes, one calculation version, and one
parameter set. It comprises:

1. snapshot header and source ledger;
2. one regime header per public Universe;
3. five dimension records per public Universe;
4. the fixed ETF basket and up to 16 relationship records;
5. opportunity-direction records;
6. candidate records per public Universe;
7. reason/evidence records;
8. quality-gate and warning records;
9. a last-written logical manifest.

The implementation may persist these as several Parquet artifacts or a
canonical JSON snapshot, but the logical grains and fingerprints are the same.
No active pointer or Production path is authorized by this design.

## Source binding

The header must contain exact, formal-reader-validated references:

| Field | Type | Nullable | Rule |
|---|---|---:|---|
| `contract_version` | string | No | Exact supported contract identifier |
| `calculation_version` | string | No | Semantic calculation version |
| `parameter_set_id` | string | No | Immutable formula/weight/pair set |
| `snapshot_id` | UUID string | No | Deterministic UUIDv5 over calculation identity |
| `generated_at` | UTC timestamp | No | Actual generation time; not a market timestamp |
| `as_of_session` | date | No | Latest completed EOD used for all latest metrics |
| `expected_session` | date | Yes | Offline XNYS calendar result at generation time |
| `freshness` | object | No | Actual, expected, lag, status, calendar ID, checked-at |
| `source_datasets` | ordered array | No | Exact logical paths, roles, sessions, and fingerprints |
| `activation_pointer_fingerprint` | SHA-256 | No | Exact selected active pointer |
| `identity_logical_fingerprint` | SHA-256 | No | Same-day Identity referenced by EOD |
| `eod_content_fingerprint` | SHA-256 | No | `as_of_session` EOD fingerprint |
| `history_source_fingerprint` | SHA-256 | No | Ordered completed-session source ledger |
| `history_membership_mode` | enum | No | V1A fixed to `current_as_of_constituent_replay` |
| `snapshot_content_fingerprint` | SHA-256 | No | Canonical aggregate of logical output records |
| `logical_fingerprint` | SHA-256 | No | Header plus source/artifact ledger, excluding itself |
| `quality_status` | enum | No | `passed`, `degraded`, or `failed` |
| `warnings` | ordered string array | No | Empty array when none |

The EOD `identity_snapshot_date` must equal `as_of_session`, and its logical
Identity fingerprint must equal the supplied source. A newer/latest Identity is
never substituted. History partitions retain their own same-day Identity
references; ticker is not used to join time series.

For the frozen development baseline, source fingerprints are those recorded in
the product specification. Generated output must preserve the actual formal
reader results rather than hard-code them.

## Business keys and uniqueness

| Record | Business key | Required uniqueness |
|---|---|---|
| Snapshot header | `snapshot_id` | One |
| Universe header | `snapshot_id + universe_id` | One per public Universe |
| Regime dimension | `snapshot_id + universe_id + dimension_id` | Exactly five per Universe |
| Dimension metric | `snapshot_id + universe_id + dimension_id + metric_id` | Unique |
| ETF basket member | `snapshot_id + basket_id + instrument_id` | Unique stable ID; ticker unique within basket at session |
| Relationship | `snapshot_id + pair_id` | At most one; pair IDs fixed by parameter set |
| Opportunity direction | `snapshot_id + direction_id` | Unique |
| Candidate | `snapshot_id + universe_id + instrument_id` | Unique |
| Candidate component | `snapshot_id + universe_id + instrument_id + component_id` | Exactly seven when score is complete |
| Reason/evidence | `snapshot_id + subject_type + subject_id + reason_code + ordinal` | Deterministic and unique |
| Quality gate | `snapshot_id + gate_code` | Unique |

Primary members may also occur in Secondary. Their raw market facts and
stock-specific component values must be byte-equivalent across views. Only
Universe-relative normalization, ADRC policy, concentration filtering, and rank
may differ, and each difference is explicit.

## Universe record

Each public Universe record contains:

- `universe_id`, `display_name`, `is_default`, and `catalog_order`;
- `member_count` and `membership_fingerprint`;
- `security_type_composition`;
- `bar_covered_member_count`, `missing_member_count`, and coverage ratio;
- `legacy=false` for all normal records;
- `selection_status=selected|available`.

The catalog order is Primary then Secondary; Primary is the sole default.
Secondary must equal Primary plus the exact activated ADRC delta. Legacy is not
serialized in the ordinary catalog.

## Regime header and dimensions

### Regime header fields

| Field | Type | Nullable | Rule |
|---|---|---:|---|
| `universe_id` | string | No | Formal active ID |
| `regime_score` | decimal string | Yes | Scale 4, `[0,100]` |
| `regime_state` | enum | Yes | `risk_on`, `balanced`, `defensive`, `stress` |
| `state_is_provisional` | boolean | No | Bootstrap or insufficient confirmation |
| `previous_state` | enum | Yes | Prior completed calculation version-compatible state |
| `score_change_1` | decimal string | Yes | Current minus prior session |
| `score_change_5` | decimal string | Yes | Current minus five sessions prior |
| `supporting_dimension_ids` | ordered array | No | Contribution descending, ID ascending tie-break |
| `conflicting_dimension_ids` | ordered array | No | Conflict magnitude descending, ID ascending tie-break |
| `configured_weight_available` | decimal string | No | Sum of present configured composite weights |
| `state_reason_codes` | ordered array | No | Deterministic transition evidence |
| `history_sessions_used` | ordered dates | No | Ascending |

The five `dimension_id` values and configured composite weights are fixed:

| ID | Weight |
|---|---:|
| `trend` | 30 |
| `breadth` | 25 |
| `volatility` | 20 |
| `liquidity_participation` | 15 |
| `leadership_dispersion` | 10 |

### Dimension record

Each dimension contains:

- `dimension_id`, `score`, `direction`, `configured_weight`,
  `effective_weight`, and `score_contribution`;
- `minimum_observations`, `actual_observations`, `coverage_ratio`, and
  `missing_count`;
- ordered `raw_metrics`, each with raw value, unit, window, source session,
  normalizer ID, bounds, internal configured/effective weight, normalized
  score, and contribution;
- `support_status=supporting|neutral|conflicting|unavailable`;
- `explanation_template_id`, rendered explanation, warnings, and reason codes.

All formulas, bounds, windows, minimum observations, direction, internal
weights, composite weights, state thresholds, and hysteresis rules are
authoritative in the linked product specification and duplicated in the
versioned parameter artifact at implementation time. Runtime input cannot
override them silently.

## Relationship record

Relationship fields are:

- `pair_id`, numerator/denominator stable IDs and session tickers;
- `economic_hypothesis`, `reverse_explanation`, and
  `causality_disclaimer=true`;
- 5- and 20-session returns for each leg;
- 5- and 20-session relative-strength spreads;
- `correlation_20`, `correlation_20_prior_5`, and `correlation_change_5`;
- ratio level, robust z-score, percentile, observation counts, and
  missingness;
- current/previous state and change magnitude;
- `confidence=insufficient|low|medium|high` and confidence reason codes;
- stability results for 18/20/22-return perturbations;
- optional raw and Holm-adjusted p-values;
- invalidation conditions and warnings.

Valid `relationship_state` values are `synchronous_strengthening`,
`synchronous_weakening`, `divergence`, `rotation_candidate`,
`relationship_break_candidate`, and `neutral`. Statistics that do not meet
their minimum history are null, never zero. The pair ledger is exactly the
16-pair set in the product specification.

## Opportunity direction and candidate records

### Opportunity direction

An opportunity direction is an ETF-first research hypothesis in V1A or a
formal sector/industry direction in V1B. Fields include:

- `direction_id` and `direction_type=registered_etf|formal_sector|formal_industry`;
- source stable ID or classification ID;
- current direction score and change;
- relationship evidence IDs;
- `classification_status=not_applicable|price_proxy_only|formal_point_in_time`;
- supporting evidence, counterevidence, invalidation, confidence, and warnings.

V1A must not emit `formal_sector` or `formal_industry`.

### Candidate

| Field | Type | Nullable | Rule |
|---|---|---:|---|
| `instrument_id` | UUID string | No | Stable key |
| `ticker` | string | No | Same-day display metadata |
| `security_type` | string | No | Formal activated security form |
| `universe_id` | string | No | Primary or Secondary |
| `latest_data_session` | date | No | Must equal snapshot as-of |
| `decision_context` | enum | No | `candidate` or `position` |
| `opportunity_stage` | enum | Yes | `watch`, `prepare`, `enter`, `exit` |
| `stage_display_semantics` | enum | No | `candidate_discovery` or `position_management` |
| `base_score` | decimal string | Yes | Scale 4, fixed V1 weights |
| `regime_adjustment` | decimal string | No | V1 fixed to `0.0000`; cannot be implicit |
| `adjusted_score` | decimal string | Yes | V1 equals `base_score` |
| `risk_mode` | enum | No | `conservative`, `balanced`, `aggressive` |
| `risk_adjusted_rank` | integer | Yes | Separate from score |
| `configured_weight_available` | decimal string | No | `[0,100]` |
| `confidence` | decimal string | No | Scale 4, `[0,1]`; data/statistical support only |
| `primary_relationship_id` | string | Yes | Registered relationship or formal taxonomy link |
| `relationship_kind` | enum | Yes | `price_derived_exposure_proxy`, `formal_taxonomy` |
| `data_quality_status` | enum | No | `passed`, `degraded`, `quarantined`, `failed` |
| `stale_state` | boolean | No | Missing session held for at most one session |
| `reason_codes` | ordered array | No | Stable codes |
| `supporting_evidence` | ordered array | No | Strongest contribution first |
| `counterevidence` | ordered array | No | Most adverse contribution first |
| `invalidation_conditions` | ordered array | No | Machine-readable predicates and text |
| `missingness` | object | No | Required/optional missing fields and weights |
| `warnings` | ordered array | No | Empty when none |

Candidate component IDs and configured weights are fixed:

| Component ID | Weight |
|---|---:|
| `market_alignment` | 12 |
| `etf_sector_alignment` | 13 |
| `stock_relative_strength` | 25 |
| `trend_quality` | 18 |
| `volume_participation` | 12 |
| `volatility_risk` | 10 |
| `liquidity_suitability` | 10 |

Each component publishes raw submetrics, normalized submetrics, configured and
effective weights, score, contribution, cap/floor applied, missingness, and
source sessions. The base score is the sum of displayed contributions. A risk
mode cannot alter any component.

Candidate confidence uses the fixed four-term formula in the product
specification. It publishes source-completeness, history-completeness,
relationship-support, and state-confirmation terms separately. It is a measure
of evidence availability and stability, not a predicted success probability.

## State transition record

State history is a separate deterministic ledger rather than an overwritten
field. Grain:

`calculation_version + universe_id + instrument_id + decision_context + as_of_session`.

Fields include prior/proposed/final state, rule ID, confirmation count before
and after, score, gate results, anomaly/quarantine status, reason codes, and
human explanation. The transition rules are fixed in the product specification.
Missing required data pauses confirmation; it does not generate a synthetic
Exit. Position-management input, when added, records only whether an instrument
is held; this contract never stores order credentials or submits trades.

## Risk-mode parameters

Each response includes the entire selected parameter row plus the unselected
rows so users can compare modes. Fields are median dollar-volume floor,
volatility ceiling, gap ceiling, price floor, confidence floor, ADRC policy,
candidate cap, concentration key, and concentration cap. The three fixed rows
are authoritative in the product specification.

`risk_adjusted_rank` is generated by:

1. applying visible mode gates;
2. sorting base score descending, confidence descending, median dollar-volume
   descending, ticker ascending;
3. scanning in order and enforcing the mode’s concentration cap;
4. assigning contiguous ranks to retained rows.

Rejected rows remain queryable with explicit rejection reasons; the UI may
filter them from the default table but cannot remove their factual detail.

## Reason and evidence contract

Reason records distinguish:

- `fact`: source-backed observation;
- `proxy`: declared transformation such as close-times-volume;
- `statistical_inference`: correlation, divergence, or normalized score;
- `hypothesis`: economic interpretation for human review;
- `data_quality`: missingness or quarantine.

Required human blocks are `surfaced_because`, `supporting_evidence`,
`counterevidence`, `invalidation`, and `data_quality_caveat`. Each block carries
stable `template_id`, parameter values, source IDs, source session, and rendered
text. Text may be regenerated only when template version changes; it cannot add
unsupported facts.

## Nullability and missing data

- Source identity, as-of session, Universe identity, membership fingerprint,
  and quality gates are never nullable.
- Unavailable statistics are null plus a reason code; no numeric field is
  zero-filled.
- A dimension is null below 70% internal configured weight.
- Available metric weight is redistributed only within its dimension. Missing
  dimensions are not reweighted across the Composite; present dimensions keep
  their fixed configured weights.
- Regime state is null unless required dimensions and 90 composite weight
  points are present.
- Candidate base score is null when more than 20 component weight points are
  missing.
- Relationship z-score/percentile is null below 60 ratio observations.
- Sector and industry IDs are null in V1A with
  `classification_status=price_proxy_only|not_applicable`.
- Freshness `expected_session` and lag may be null only when the calendar is
  unavailable; this does not fabricate freshness.

## Numeric strategy

- Canonical price, volume, VWAP, returns, gaps, moving averages, and
  close-times-volume calculations use exact Decimal inputs.
- Medians, MAD, covariance, standard deviation, square root, and correlation
  use a fresh local Decimal context with precision 50 and explicit traps for
  `InvalidOperation`, `DivisionByZero`, `Overflow`, `Inexact`, and `Rounded`
  where an exact operation is required. Transcendental outputs use the
  calculation-version-locked routine and are quantized only at the publication
  boundary.
- No global Decimal context, flag, trap, or rounding mode may affect output.
- No binary float enters logical fingerprints.
- API numeric values are decimal strings. Scores use scale 4; returns, ratios,
  correlations, and z-scores use scale 10; monetary values retain the source or
  declared derived scale. Null stays JSON null.
- Frontend parsing is presentation-only and never recomputes scores or states.

Implementations must prove identical logical rows and fingerprints under outer
Decimal precisions 9, 28, and 50 and with `Inexact`/`Rounded` traps enabled.

## Deterministic ordering and fingerprinting

Ordering is part of the contract:

- source sessions ascending;
- Universe catalog order, not lexical ID;
- dimension and component order from the parameter set;
- pair order from the registered pair ledger;
- candidates by stable business key in persisted artifacts;
- displayed rank by the deterministic rank rules;
- reason codes by declared priority then lexical code.

Logical fingerprints use SHA-256 over UTF-8 canonical JSON with sorted object
keys, no insignificant whitespace, NFC-normalized strings, exact ISO dates/UTC
timestamps, arrays in contract order, and numeric strings at declared scales.
The fingerprint payload excludes only its own fingerprint field and physical
publication metadata. Artifact SHA-256 is the raw file digest. A logical
manifest binds each artifact path, row count, byte count, physical SHA-256,
logical content fingerprint, and schema version.

`snapshot_id` is UUIDv5 over:

```text
tip:market-regime-opportunity-map:
{contract_version}:{calculation_version}:{parameter_set_id}:
{as_of_session}:{activation_pointer_fingerprint}:
{identity_logical_fingerprint}:{eod_content_fingerprint}
```

## Quality gates

Publication or API exposure fails closed on:

- missing, incomplete, corrupt, symlinked, or hash-mismatched source;
- EOD/Identity session mismatch or previous/latest Identity fallback;
- unknown/malformed active pointer or membership fingerprint mismatch;
- duplicate business keys, orphan IDs, non-latest EOD revisions, or ticker joins;
- a Legacy member in normal candidate output;
- Primary not first/default, Secondary not Primary plus the formal ADRC delta,
  or security-type leakage;
- future-session input, look-ahead normalization, or current-session data in a
  prior-session-only window;
- component/dimension weights not totaling the versioned value;
- base score differing from displayed contributions;
- non-versioned parameter override;
- unlabelled price-derived taxonomy, flow, causality, or option inference;
- corporate-action quarantine promoting a candidate;
- nondeterministic ordering or fingerprint mismatch.

The following support a `degraded` snapshot when explicitly represented:

- fewer than 60 sessions for relationship z-score/percentile;
- an optional registered ETF missing while required broad proxies remain;
- no point-in-time taxonomy in V1A;
- optional VWAP or trade-count missingness;
- some Universe member bars missing within declared coverage gates.

`degraded` never turns a null metric into zero and cannot bypass a state or risk
gate. Quality-gate results and failure/warning lists are persisted, not inferred
from a presentation label.

## Snapshot, API, and frontend boundary

- The analytics builder reads formal immutable sources and emits a candidate
  only after all quality gates pass.
- A future snapshot publisher must write immutable artifacts, formally reread
  them, and only then use a separately authorized pointer boundary. This design
  does not activate or alter the existing Dashboard Snapshot contract.
- The API returns the persisted calculation and may filter/page candidates; it
  must not recompute scores, infer sectors, or select latest sources.
- The frontend selects a public Universe and risk mode, renders the supplied
  facts and ranks, and never hides methodology or data-quality fields.
- Guest and authenticated sessions receive the same snapshot, precision,
  freshness, and functionality. Authentication may differ only at the session
  boundary.

## Schema evolution

- Patch calculation versions may fix rendering text only when logical numeric
  output is unchanged; template version still increments.
- Any metric formula, threshold, normalizer, state transition, pair, weight,
  risk gate, or reason priority change requires a new calculation version and
  parameter set and cannot rewrite old snapshots.
- Additive nullable fields require a contract minor version and old readers
  must ignore them safely.
- Removed fields, changed business keys, altered meanings, or numeric strategy
  require a major version and parallel reader support during migration.
- Historical snapshots are immutable. Recalculation under a new version creates
  a new snapshot ID and must never masquerade as the original as-of result.

## Explicit non-goals

- trade or option recommendation;
- order creation or position sizing;
- causal inference;
- true fund-flow estimation;
- price-derived sector assignment;
- market-cap weighting;
- automatic pair mining or machine learning;
- fundamentals, valuation, or option payoff modeling in V1.
