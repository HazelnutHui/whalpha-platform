# Market Regime & Opportunity Map V1 Architecture and Implementation Plan

## Production publication integration

The Production chain is formal EOD/Identity/Activation to immutable Market
Intelligence, formal active reader, Snapshot 1.7, explicit OCI bundle, and the
existing read-only API cache/bilingual Frontend. One language-neutral object
serves English and Chinese; locale never affects analytics identity.

No layer selects `latest`, reads Dell `/tmp` in Production, or recalculates the
26-session panel on a request/startup path. Publisher, Snapshot, and OCI are
independent approval and rollback domains.

## Status

Status: **Implemented through MI 1.3 and the additive Snapshot 1.11 /
Dashboard 2.8 consumer boundary, including the bilingual Candidate, Strategy
Channel, Visual Context, and Sector ETF Rotation workspaces. Exact active
publication, release and freshness evidence belongs in
[current context](../project/current-context.md).**

This document sequences the design in
[Market Regime & Opportunity Map V1](../product/market-regime-opportunity-map-v1.md)
against the machine boundary in the
[V1 data contract](../data-contracts/market-regime-opportunity-map-v1.md).
It is deliberately EOD-first, deterministic, and offline. It does not authorize
provider access, Production writes, Dashboard snapshot publication, bundle
creation, or deployment.

## Architectural decisions

1. **V1A is useful without sector taxonomy.** Market Regime Core and a fixed ETF
   Relationship Map use formal EOD, same-day Identity, and activated
   memberships. V1B adds sector breadth only after point-in-time taxonomy.
2. **Calculations are source-bound snapshots.** Every result binds exact source
   paths, sessions, fingerprints, calculation version, parameter set, and
   membership fingerprint. “Latest” is resolved before calculation, never
   inside a metric.
3. **Scores are ledgers, not labels.** Raw inputs, normalization, weights,
   contributions, missingness, transitions, and explanations are persisted.
4. **Facts, proxies, statistical inference, and hypotheses stay distinct.** ETF
   price relationships do not create taxonomy; volume does not create flow;
   correlation does not create causality.
5. **No complex ML in V1.** Pair discovery, hidden regime adaptation, and
   learned scoring are deferred. The fixed parameter set is independently
   evaluable and reversible.

These decisions are summarized in
[ADR 0018](../decisions/0018-stage-market-regime-opportunity-map-v1.md).

## Current read architecture

```text
Offline XNYS calendar
        │
        ├── expected/actual session and freshness
        │
Active Activation V2 reader ── stable Primary/Secondary member IDs
        │
Same-day Identity reader ───── stable ID, ticker, type, exchange
        │
Canonical EOD history reader ─ completed OHLC/volume/VWAP/trade count
        │
        ▼
Versioned calculation services (pure, no I/O)
        │
        ├── regime ledger
        ├── registered ETF relationship ledger
        ├── candidate component/state ledger
        └── quality/evidence ledger
        │
        ▼
Immutable candidate snapshot in /tmp during development
        │
        ├── formal reader and independent oracle
        └── later, separately authorized snapshot/API/frontend integration
```

The calculation service accepts already validated typed records. It cannot
open a provider client, resolve a latest ticker, or mutate `/data`. A future
repository owns publication; the domain service owns no filesystem paths.

## Frozen feasibility evidence

The 2026-08-21 read-only audit used the formal EOD reader across all completed
partitions and confirmed:

- 26 consecutive sessions, 2026-07-17 through 2026-08-21;
- 9,941 latest bars: 4,539 `common_stock` and 5,402 `etf` read models;
- OHLC and volume as Decimal, and 9,941 non-null VWAP/trade-count values on the
  baseline session;
- 5/10/20-session windows ready; 40/60-session windows unavailable;
- all registered V1 ETF basket members have bars in all 26 sessions;
- direct GLD, USO, UUP, and DBA proxies are absent from the formal resolved
  baseline and are not substituted;
- 1,716 of 1,718 Primary and 1,829 of 1,831 Secondary members have a latest
  bar;
- no implemented point-in-time sector/industry dataset, market cap, shares
  outstanding, fundamentals, valuation, options, or true fund-flow dataset.

The EOD physical schema contains `notional` and adjustment-factor columns, but
current Grouped Daily mapping writes zero notional and unit adjustment factors.
They are not treated as usable notional or corporate-action evidence.

## Proposed module boundaries

Names are suggestions and may be refined during implementation without changing
the domain boundary:

```text
apps/api/src/tip_api/contracts/analytics/v1/
  market_regime.py
  etf_relationship.py
  opportunity_candidate.py
  market_regime_snapshot.py

apps/api/src/tip_api/services/
  market_regime.py
  etf_relationships.py
  opportunity_candidates.py
  opportunity_state_machine.py
  market_regime_explanations.py
  market_regime_validation.py

apps/api/src/tip_api/persistence/parquet/
  market_regime_snapshot.py

apps/api/src/tip_api/schemas/
  private_market_regime.py

apps/web/src/features/market-regime/
  (page, decomposition, relationship ledger, candidates, detail drawer)
```

Versioned parameters should be checked-in data, for example
`apps/api/src/tip_api/parameters/market_regime/v1_0_0.json`, loaded into a
strict contract and fingerprinted. Environment variables and request arguments
must not override formula parameters.

## Calculation pipeline

### 1. Source resolution

Resolve a caller-supplied `as_of_session`; never select a date because it is the
maximum directory name. Require:

- completed EOD and its exact same-day completed Identity reference;
- explicit completed history-session tuple;
- active Activation pointer and both membership fingerprints;
- offline calendar evaluation;
- no symlink, partial, corrupt, duplicate, orphan, or future reference.

The development baseline intentionally accepts stale calendar freshness because
it is explicitly frozen. A future Production snapshot uses the existing
freshness policy and represents stale data rather than silently mixing dates.

### 2. Canonical panel

Construct stable-ID panels with one row per instrument/session. Keep ticker,
name, type, and exchange as session display metadata. Produce explicit presence
masks for close, open, volume, VWAP, trade count, membership, and ETF basket.
Do not forward-fill bars or Identity.

The V1 historical membership mode applies the current as-of activated IDs to
earlier bars and records the survivorship limitation. Phase 3 supplies true
effective-dated membership/classification panels for unbiased historical
evaluation.

### 3. Pure metric ledgers

Calculate raw values first, then normalized values, then contributions. Each
stage returns typed immutable records. The independent test oracle recomputes
business-key sets, core formulas, weights, and fingerprints from raw reader
output rather than reusing service intermediates.

Local Decimal contexts are created inside each calculation. Global context and
external traps must not affect output. Cross-sectional order is stable-ID order
before rank operations; average ties and ticker tie-breaks are explicit.

### 4. Explanation generation

Explanation templates consume reason records only. They do not query market
data or invent narrative. Template changes are versioned. Evidence type is
always one of fact, proxy, statistical inference, hypothesis, or data quality.

### 5. Candidate snapshot boundary

During initial phases, the builder writes only an isolated `/tmp` candidate and
formally rereads it. Production publication, active pointer design, API
registration, and frontend consumption are deferred to Phase 6 and require
separate authorization.

## Phase plan

Each phase is an independent commit series with its own rollback boundary.

### Phase 1 — Market Regime Core

**Inputs**

- explicit completed EOD history through the as-of session;
- exact same-day Identity reference;
- active Primary/Secondary membership;
- offline XNYS calendar;
- fixed V1 parameter set.

**Outputs**

- typed raw metric, dimension, composite, hysteresis, explanation, and quality
  records for both public Universes;
- `/tmp` canonical JSON review artifact only;
- no candidate ranking and no Production snapshot.

Phase 1 is split into two independently versioned offline boundaries. Phase 1a
owns metrics, normalization, missingness, and Composite. Phase 1b reads those
verified Composites, replays the fixed candidate/confirmed state machine, and
owns no Phase 1a formula or output field.

**Suggested files/modules**

- analytics contracts, parameter loader, `market_regime.py`, explanation
  templates, independent oracle, and focused tests;
- no API or frontend files.

**Tests**

- exact formulas and every threshold boundary;
- 5/10/20 window inclusion and no future/current leakage;
- stable-ID joins, missing bars, zero denominators, Decimal contexts 9/28/50;
- all hysteresis transitions, bootstrap, immediate Stress override, and missing
  session behavior;
- component weights, score reconciliation, deterministic ordering/fingerprint;
- fixture and formal-reader `/tmp` dry-run with socket prohibition.

**Acceptance**

- five dimensions and composite independently reproduce exactly;
- raw metrics, normalized scores, effective weights, and explanations reconcile;
- both Universe fingerprints match Activation and no Legacy member enters;
- the 2026-08-21 baseline can calculate 5/10/20 windows and declares 40/60
  unavailable;
- no source, repository, or Production mutation.

**Risk / new data / complexity**

- Main risk: current-constituent replay can bias historical interpretation.
- New provider: no. New derived data: yes, `/tmp` calculation ledger.
- Complexity: medium.

**Rollback boundary**

Remove the Phase 1 modules and tests; no persisted or runtime consumer exists.

### Phase 2 — ETF Relationship Map

**Implementation status: complete at the offline `/tmp` audit boundary.**

**Inputs**

- Phase 1 source panel;
- fixed, data-audited ETF basket and 16-pair ledger;
- exact 26-session baseline history, later expanding naturally.

**Outputs**

- pair statistics, state, stability, confidence, rationale, reverse explanation,
  and invalidation records;
- null robust z/percentile with `insufficient_history` until 60 sessions.

**Implemented files/modules**

- typed ETF/pair contracts; `etf_relationships.py`;
  `relationship_v1_0_0.py`; independent `etf_relationship_oracle.py`;
  canonical `etf_relationship_audit.py`; and a socket-guarded, no-apply CLI.

**Tests**

- pair allowlist and missing-ticker fail/degrade behavior;
- return/spread/correlation windows and 18/20/22 perturbations;
- current versus five-session-prior correlation at exactly 26 closes;
- state precedence, min observations, confidence tiers, Holm adjustment;
- no automatic ticker mining, taxonomy assignment, or causal text.

**Acceptance**

- every emitted relationship belongs to the registered ledger;
- all stats independently reproduce and all confidence limits are visible;
- missing dollar/commodity proxies remain absent and warned;
- relationship cards carry counterevidence and causality label.

**Risk / new data / complexity**

- Main risk: short history makes relationships unstable and highly overlapping.
- New provider: no. New derived data: relationship ledger.
- Complexity: medium.

**Rollback boundary**

Remove the relationship ledger and optional Phase 1 reference; regime core
remains intact.

### Phase 3 — Point-in-time Sector Taxonomy

**Inputs**

- an explicitly selected, licensed taxonomy source;
- stable Instrument Master IDs;
- canonical hierarchy mapping and review policy;
- validity intervals and source evidence.

**Outputs**

- classification definitions and effective-dated memberships conforming to
  [Classification V1](../data-contracts/classification-v1.md);
- formal reader, quality ledger, coverage report, and immutable snapshot.

**Suggested files/modules**

- provider-neutral classification contracts already planned in the repository;
- source adapter, mapping tables, persistence reader/writer, and review
  operation. Keep this separate from market-regime calculation code.

**Tests**

- one traditional path per stable ID and effective instant;
- hierarchy closure, interval overlap, orphan, duplicate, and source evidence;
- ticker changes and reused tickers; unknown/quarantine behavior;
- point-in-time historical reads with no latest fallback.

**Acceptance**

- coverage and unknowns reconcile to the eligible base;
- no ambiguous or heuristic-only record becomes formal membership;
- historical validity can be reconstructed exactly;
- licensing/display boundary is documented.

**Risk / new data / complexity**

- Main risks: vendor licensing, taxonomy drift, issuer/security identity mismatch,
  and incomplete historical validity.
- New provider/data: likely yes.
- Complexity: high.

**Rollback boundary**

Taxonomy is a separate immutable dataset and inactive until a consumer version
explicitly references its logical fingerprint.

### Phase 4 — Sector Breadth and Opportunity Transmission

**Inputs**

- completed Phase 3 taxonomy valid at every evaluated session;
- Phase 1 regime and Phase 2 ETF evidence;
- active Universe and canonical EOD panel.

**Outputs**

- formal sector/industry breadth and relative-strength ledgers;
- ETF/sector-to-stock transmission records;
- explicit comparison of formal taxonomy and price-derived proxy.

**Suggested files/modules**

- `sector_breadth.py`, `opportunity_transmission.py`, new typed records, and
  source-reference validation.

**Tests**

- taxonomy effective-date joins, hierarchy reconciliation, breadth denominators,
  Primary/Secondary consistency, 113 ADRC isolation, and missing classifications;
- proof that correlation cannot write a classification ID;
- deterministic best-driver and formal-sector precedence.

**Acceptance**

- all formal stock transmission has a valid taxonomy source reference;
- sector totals close to member/unknown totals;
- no security-type, Legacy, duplicate, or orphan leakage;
- proxy and taxonomy evidence remain separately labelled.

**Risk / new data / complexity**

- Main risk: accidental look-ahead or treating current taxonomy as historical.
- New provider: no beyond Phase 3. New derived data: yes.
- Complexity: high.

**Rollback boundary**

Disable the Phase 4 calculation version; Phase 1/2 V1A remains valid.

### Phase 5 — Candidate States and Risk Modes

**Implementation status: score/risk core, chronological candidate-state replay,
independent Oracle, canonical `/tmp` audit/reread, bounded publication, MI 1.1,
Snapshot 1.6 / Dashboard 2.3, bilingual frontend, and OCI deployment are
implemented.**

**Inputs**

- Phase 1 regime, Phase 2 relationships, optional Phase 4 formal transmission;
- active-Universe stable IDs and 20-session EOD panel;
- fixed score, state, risk-mode, and explanation parameters.

**Outputs**

- seven-component base-score ledger;
- candidate/position state-transition ledger;
- Conservative/Balanced/Aggressive eligibility and risk-adjusted ranks;
- human and machine evidence blocks.

**Suggested files/modules**

- candidate contracts, score service, state machine, risk ranker, explanation
  templates, and independent oracle.

**Tests**

- robust normalization, winsorization/ties/zero MAD, all component formulas,
  caps/floors and missing reweighting;
- score sum and unchanged base score across risk modes;
- every state transition and hysteresis counter;
- corporate-action/extreme-return quarantine, missing-data pause, gap risk;
- deterministic concentration scan and rank ties;
- for the same session, source panel, and stable ID, shared Primary/Secondary
  members have identical security-level raw facts, missing reasons, anomaly
  flags, and registered-ETF proxy selection. Universe Regime input,
  cross-sectional normalization, normalized components, base score,
  confidence, state, eligibility, and rank remain explicitly Universe-
  contextual; ADRC policy affects only eligibility/rank and never rewrites raw
  facts or the base score.

**Acceptance**

- no hidden parameter or regime-adjusted base score;
- reason codes and explanation blocks cover every promotion/demotion;
- candidate Exit is displayed as invalidation when no position exists;
- no position amount, option payoff, certainty, flow, or causality claim.

**Risk / new data / complexity**

- Main risks: false precision from short history and user over-reading the Enter
  label. UI copy and evaluation gates are mandatory.
- New provider: no for underlying-stock V1. Options remain deferred.
- Complexity: high.

**Rollback boundary**

Candidate feature flag/calculation version can be removed while preserving
regime and relationship ledgers.

### Phase 6 — Validation and Dashboard Integration

**Inputs**

- immutable calculations from Phases 1–5;
- at least 252 sessions for initial chronological evaluation;
- existing snapshot/API/frontend boundaries.

**Outputs**

- walk-forward evaluation artifacts and holdout report;
- immutable Market Regime snapshot repository and formal reader;
- default-disabled private API response;
- desktop-first page, mobile degradation, and methodology drawer;
- later, separately approved Dashboard snapshot integration.

**Suggested files/modules**

- evaluation CLI and report contracts;
- Parquet/JSON repository and formal reader;
- private API schema/route behind explicit configuration;
- isolated frontend feature directory and component tests.

**Tests**

- no-look-ahead walk-forward splits, point-in-time source replay, corporate-action
  isolation, costs, rank/state metrics, parameter sensitivity;
- repository schema/count/hash/source/fingerprint/atomicity and replay rejection;
- API Decimal-string fidelity, pagination/filtering, unknown Universe/risk mode;
- frontend formula traceability, accessibility, desktop/mobile layout, no
  recomputation, same guest/auth payload;
- snapshot compatibility and explicit immutable release selection.

**Acceptance**

- all evaluation gates in the product specification pass or are labelled
  inconclusive;
- persisted rows and API payload exactly match the calculation ledger;
- every visible conclusion links to formula, source session, and warnings;
- deployment remains a separate authorization after snapshot publication.

**Risk / new data / complexity**

- Main risks: data leakage in evaluation, schema drift, frontend recomputation,
  and conflating underlying-stock results with option outcomes.
- New provider: not for the core; longer EOD history is required. Options,
  fundamentals, and taxonomy remain independent data programs.
- Complexity: high.

**Rollback boundary**

Immutable snapshots remain readable; API/feature flag can revert to the prior
Dashboard. Active Dashboard pointer, bundle, and OCI release are not changed by
calculation rollback.

## Focused verification strategy

Implementation should prefer small, deterministic suites:

- contract serialization and validation;
- formula fixtures with hand-computed Decimal results;
- independent oracle over raw formal-reader rows;
- path/symlink/source-session/fingerprint gates;
- current-versus-same-day Identity regression;
- stable-ID ticker-change fixtures;
- Decimal precision/trap invariance;
- deterministic order and repeated-build byte equivalence;
- socket prohibition during calculations and formal rereads.

Full backend/frontend matrices are reserved for Phase 6 integration, not early
domain commits.

## Operational and security boundaries

- Calculations do not read credentials and do not instantiate provider clients.
- No network is needed for any V1A calculation.
- No `/data` writer is introduced before a separate publication design and
  authorization.
- Existing EOD, Identity, Activation, Universe, Dashboard snapshot, and OCI
  artifacts are immutable inputs.
- A failure leaves source data untouched and retains only bounded `/tmp` review
  evidence.
- No operation selects a “latest” bundle or release implicitly.

## Implemented offline slices and next minimum slice

Phase 1a is implemented as an isolated offline commit series:

1. strict contracts and checked-in parameter set;
2. explicit 2026-08-21 source read into an in-memory panel;
3. five raw dimension calculations, normalization, composite, missingness, and
   explanations;
4. independent oracle and Decimal-context invariance tests;
5. canonical `/tmp` review output only.

The implementation adds typed analytics contracts, the fixed checked-in
parameter set, formal EOD/Identity/Activation source binding, a pure
five-dimension service, a separate raw-panel oracle, and a socket-guarded
administrator CLI that accepts only a direct `/tmp` output directory. The
2026-08-21 formal run calculated both public Universes with all 18 metrics
available in each, zero oracle mismatch, and deterministic logical
fingerprints.

Phase 1b is also implemented as an isolated offline commit series. It loads the
formal panel once, calculates compatible Phase 1a prefixes entirely in memory,
then executes a pure chronological state machine. A second implementation path
independently evaluates candidate bands, bootstrap, pending counters,
hysteresis, immediate Stress, unavailable rows, and reason codes without
importing the production state service. Full replay, append, restart,
permutation, future-prefix, cross-Universe, and Decimal-context gates are part
of the boundary.

The formal 2026-08-21 run produced six calculable Composite sessions per
Universe, initialized Balanced provisionally on 2026-08-17, cleared
provisional on 2026-08-18, held Balanced through a Defensive candidate inside
the 45–55 hysteresis band on 2026-08-20, and ended with Balanced candidate and
confirmed state for both Universes on 2026-08-21. This short trajectory verifies
implementation mechanics only; it is not a backtest or predictive validation.

Phase 2 is implemented as an isolated offline slice. The formal 2026-08-21 run
loaded the EOD/Identity/Activation panel once, emitted all 16 registered pairs
over 21 calculable as-of sessions (336 history rows), and reproduced every
window/state/reason code through an independent raw-panel Oracle. Full replay,
append, input permutation, future-prefix, Decimal-context, canonical reread,
and two-run byte determinism are required gates. The Phase 2 logical audit
fingerprint is `e5acfa29771d965e9bdf21d1bfab24148220217ac474327cdc60e2212532e3a5`.

The read-only API and desktop integration is now implemented as a local-only
slice. An explicit three-audit builder emits a two-file canonical `/tmp`
preview bundle; the API formally verifies it once at startup and retains an
immutable cache. The default application does not register the route. The
desktop view renders both Universes, the five-dimension ledger, all 16 pairs,
fixed highlights, filters, pair detail, and short-history boundaries without
recalculation.

Phase 5 is implemented as an isolated offline slice. It adds strict
candidate fact/component/confidence/batch and risk-assessment contracts, a
checked-in seven-component and three-risk-mode parameter set, deterministic
Decimal Type-7 winsor boundaries and average-tie percentiles, a 26-session
active-Universe scorer, anomaly quarantine, missing-component reweighting, and
concentration-aware ranking. Focused fixtures prove score/contribution
reconciliation, unchanged facts across risk modes, ADRC exclusion in
Conservative mode, proxy-component absence/cap behavior, more-than-20-point
missingness failure, anomaly quarantine, stable ordering, and Decimal-context
invariance.

The bounded Candidate publication, Snapshot/API/frontend consumer, entry-
geometry layer, bundle, and deployment are implemented. Guest Session entry
uses the same Candidate data and has no role-dependent variant. Repository
development now adds the verified-prior Candidate audit described in ADR 0022
and the stable-prefix Phase 1b correction described in ADR 0023. Phase 1b also
supports the verified-upstream one-session append described in ADR 0024: the
daily path consumes current Phase 1a plus prior Phase 1b audits without
reopening `/data`; the stable-prefix cold path remains the reference. Production
publication remains a separate authorization.

ADR 0025 adds an optional Dell-local immutable panel-stage boundary between
Phase 1a and the daily Candidate append. Phase 1a writes the already validated
26-session panel under a content-derived key. Candidate selects it only from
the exact current Phase 1b source ledger; a miss invokes the formal canonical
reader, while an existing invalid entry fails closed. The cache is explicit,
owner-controlled, has no mutable latest pointer, and is never an OCI or
Production source. Candidate business artifacts and Oracle semantics remain
identical to the cold-reader path.

ADR 0026 keeps the completed Candidate audit contract byte-compatible while
streaming canonical JSON and hashes through bounded buffers. An explicit
owner-controlled `/tmp` work directory holds a source-bound recovery journal
and a contiguous prefix of immutable artifacts. A fully prepared interruption
can finish before calculation sources are reopened; an earlier writer
interruption reuses its verified artifact prefix after reconstruction. One
formal completed-audit reread precedes atomic delivery to the final path.
Calculation-stage checkpointing remains separate future work.

ADR 0027 makes validation intent an explicit execution input. The daily path
is the verified-prior one-session append, the periodic path creates a cold
reference and compares all eight business projections to the daily result, and
the code/model-change path requires the cold full replay. Mode/date/reference
drift fails closed. This is an audit and automation boundary, not a claim of
predictive efficacy or publication authorization.

ADR 0028 permits deterministic process parallelism only across independent
cold-replay session Oracles. Isolated workers have no network/DNS access; the
parent preserves chronological state, canonical order, comparisons, aggregate
fingerprints, and audit delivery. Daily append keeps one effective Oracle
worker because measured Universe-level process splitting was slower.

The first accepted formal Phase 5 audit covers 2026-08-21 and 2026-08-24 under
candidate calculation `market-regime-opportunity-candidate-v1.1.1`. Its
logical fingerprint is
`1f25a1c9060d459e372903ad116579973c709363f365f19fa66bb515774c93df`,
with zero independent-Oracle mismatch and all append/restart/permutation/
future-prefix gates true. Its roughly 928-second, 1.9-GiB cold replay is an
audit path, not the future scheduler path; daily operation must append from the
previous verified state and avoid duplicate full-history source reconstruction.

Phase 7 keeps the
Candidate score, state, and risk rank unchanged, then calculates fixed
SMA/ATR/return/gap/range/volume entry-location facts, low through extreme
extension risk, bounded breakout/pullback structures, and explicit review
postures. A separate raw-panel Oracle and canonical `/tmp` audit require zero
mismatch and input-permutation equivalence. It is published through the active
MI 1.2 / Snapshot 1.7 / Dashboard 2.4 consumer without altering the leadership
score or risk rank.
