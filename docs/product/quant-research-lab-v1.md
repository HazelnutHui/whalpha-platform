# Quant Research Lab

## Product authority

Quant Research Lab / `量化研究实验室` is WH Alpha's core research workspace.
It is the human-readable registry for factor discovery, model construction,
strategy expression, evaluation evidence, failure, activation, monitoring, and
retirement.

Model-Driven Equity Selection is a downstream consumer, not a parallel research
system. Market Regime & Opportunities, Sector ETF Rotation, and Market
Structure & Activity are supporting market tools. The deployed Candidate
score, Entry Geometry, and six Strategy Channels remain frozen, unvalidated
**Baseline V1** compatibility behavior; they do not define the future research
taxonomy.

The durable research authority is
[Factor Discovery -> Model Construction -> Strategy Expression](quant-research-three-layer-architecture-v1.md).
There is no permanent list of three, six, or any other number of future models.
The Product may feature only a small reviewed active set, while long-term
research remains open to evidence-led factor and model families through finite
registered campaigns.

## Non-black-box contract

Every lineage must disclose:

- owner, IDs, versions, lifecycle, status, and immutable fingerprints;
- intended decision, horizon, point-in-time Universe, benchmark, and economic
  mechanism;
- every source field, availability clock, formula, transformation,
  missingness/quarantine rule, and expected/counter relationship;
- complete feature/model/expression parameters and the true search budget;
- labels, entry/exit timing, corporate-action treatment, costs, capacity,
  portfolio rules, and stock-versus-option boundary;
- development, Validation, Holdout, walk-forward, purge, embargo, multiplicity,
  and reproduction design;
- coverage, exclusions, uncertainty, stability, sensitivity, concentration,
  counterevidence, invalidation, and missing evidence; and
- activation, shadow monitoring, decay, pause, rollback, and retirement
  history.

Compact views may fold details. Expanded records may not hide material
parameters or replace formulas with marketing summaries. English, Simplified
Chinese, and professional neutral Spanish present the same canonical evidence.
Guest and credential Sessions retain identical data and capability until the
product policy explicitly changes.

## Lab information architecture

### 1. Factor registry

Shows exact definitions, economic role, coverage, missingness, redundancy,
screening evidence, failure, and lineage. It distinguishes directional
candidates from conditioners, neutralizers, risk guards, and execution inputs.
A factor record never implies a strategy or Product rank.

### 2. Model registry

Shows which admitted factor versions feed a ranking, probability,
distribution, conditional estimate, or risk state. It exposes the exact
algorithm/formula, target, benchmark, parameters, baselines, calibration,
uncertainty, out-of-sample evidence, and failure conditions. A model is not an
entry rule or portfolio.

### 3. Strategy-expression registry

Shows how a locked model becomes a decision: eligibility, entry, waiting,
invalidation, exit, holding, re-entry, sizing, concurrency, costs, liquidity,
capacity, portfolio risk, vehicle, and monitoring. Stock and option expressions
remain separate versions and evidence systems.

### 4. Evidence and lifecycle

Links the exact factor/model/expression lineage to data cohort, labels, split,
metrics, uncertainty, sensitivity, counterevidence, reproduction, shadow,
activation, decay, and retirement. Rejected and retired records remain visible
so repeated testing cannot erase failures.

## Lifecycle

| State | Meaning | Candidate authority |
| --- | --- | --- |
| `idea` | Mechanism exists but no registered test | None |
| `registered` | Finite question, data, trial budget, and gates frozen | None |
| `data_blocked` | Required evidence is not admissible | None |
| `development` | Only the registered development partition may be used | None |
| `validation` | Factor/model/expression lineage locked | None |
| `holdout_review` | One sealed Holdout is consumed once | None |
| `validated_research` | Research gates passed; operational review pending | None |
| `shadow` | Frozen lineage runs prospectively without ranking authority | None |
| `active` | Separate activation permits exact Product use | Approved scope only |
| `rejected` | A registered gate failed | None |
| `retired` | Previously useful evidence decayed or was replaced | None |

No state advances from attractive charts, recent return, more price history,
agent consensus, or user-interface completion.

## Evaluation sequence

```text
mechanism and falsifiable question
-> registered factor batch
-> outcome-blind factor qualification
-> registered development screening
-> admitted small factor set or no selection
-> bounded model and strategy-expression construction
-> locked chronological Validation
-> one sealed Holdout
-> independent reproduction and red-team review
-> prospective shadow / paper evidence
-> separate activation
-> monitoring and retirement
```

Stable-ID joins, point-in-time membership, delisted/terminal outcomes,
corporate actions, source-availability clocks, overlap-aware purge/embargo,
true trial counts, realistic costs, and explicit missingness are mandatory.
Randomly mixing overlapping security-session rows is prohibited. Validation
and Holdout outcomes cannot be used to generate factors, select features, tune
models, or rewrite expressions.

## Result semantics

### Factor screening

Report coverage, rank IC/decay or the registered role-specific statistic,
uncertainty, monotonicity where appropriate, exposure attribution,
time/Regime/liquidity stability, cost implications, concentration, redundancy,
and all counted failures. Factor evidence is not portfolio performance.

### Signal/event study

Before portfolio construction is fixed, report available signal/control
observations, net expectancy under declared cost scenarios, median and
signal-minus-control/benchmark contrast, uncertainty, win/payoff/Profit
Factor, MFE/MAE, false-positive/chase risk, coverage, quarantine, and stability.
Do not publish annualized return, Sharpe, or maximum drawdown as if a portfolio
exists.

### Tradable portfolio simulation

Only after sizing, concurrency, cash, rebalance, turnover, capacity, and costs
are frozen may the Lab report total/annualized return, drawdown, volatility,
Beta/Alpha, Sharpe, Sortino, Calmar, Information Ratio, exposure, turnover,
capacity, cost attribution, and trade statistics. The headline remains
out-of-sample, net of realistic costs, with period, sample, benchmark, and
uncertainty.

## Current research state

Strong-Leader Pullback predates the three-layer architecture. It is retained
only in internal contracts and audits as rejection and anti-retesting evidence;
it is not a current Alpha, model, strategy expression, or public Lab program.
Its V1 24-combination study ended `inconclusive_evidence_floor`, and its only
registered replacement ended `rejected_endpoint_instability`. No parameter was
locked, Validation and Holdout stayed closed, and no performance or Candidate
authority was created.

ADR 0273 registers the first outcome-blind Factor Catalog V1: 12 exact daily
price/volume definitions across five economic families. They are one bounded
catalog version, not the permanent factor universe and not a promised next
strategy. Deterministic formula implementation and the outcome-free coverage,
missingness, distribution, concentration, correlation, and exact-replay report
are complete under ADR 0275. The report covers 418,756 complete factor vectors
across 255 eligible sessions, retains 18,646 explicit quarantines, and finds no
pair meeting the frozen near-duplicate rule. These are calculation-quality
facts, not Alpha evidence. Its later frozen Development screen rejected every
candidate-Alpha factor and retained only one risk guard, so V1 is closed
without a model. ADR 0277 preserves all eight consumed V1 trials. ADR 0278
registered a separate eight-definition V2 catalog; its outcome-blind
qualification passed, but the frozen Development screen rejected all four
candidate-Alpha trials. Two risk guards passed their own gates but were not
selected because no Alpha survived. Ledger V3 now closes all 14 consumed
trials and no model input exists. Campaign Three subsequently completed
outcome-blind intake, qualification, one frozen Development screen, and one
byte-identical replay. Both Alpha interactions and the risk guard failed their
registered gates. Ledger V5 closes all 17 cumulative formal trials with zero
admitted Alpha, zero model input, and no downstream authority.

No candidate-Alpha factor has been admitted. No selected threshold, model
weight, three-layer model,
strategy expression, Lab performance publication, or active Candidate model
currently exists.

The public Lab is a reviewed milestone projection, not a live process log. It
shows the current three-layer research lineage and its governed results; named
pre-architecture methods remain internal audit history so they cannot be
mistaken for active strategies. A
material state change must update the typed record, cumulative ledger,
authoritative project state, dated audit, trilingual Product projection, and
tests together. Deployment remains separately verified. Current decisions stay
expanded; formulas, parameters, lineage, hashes, limitations, and current
three-layer campaigns may use disclosure panels without becoming unavailable.

Every completed factor-space milestone must also project its interpretable
diagnostics into the public Lab. The compact view states the point-in-time
standardization and neutralization method, factor-family or cluster identity,
effective dimensionality, and the decision those diagnostics support. The
expanded view shows the exact transformation, missingness treatment,
correlation or cluster evidence, PCA fitting boundary, explained variance, and
factor loadings when PCA is registered. Correlation heatmaps and two-dimensional
PCA loading maps are diagnostics, not Alpha evidence. They must never be fit on
Validation or Holdout, and an unfinished diagnostic must display `not computed`
rather than a decorative or synthetic chart.

The Market / Universe selector separates the U.S. Lab from the China A-share
research foundation. The A-share view uses the same Factor Discovery -> Model
Construction -> Strategy Expression governance, but has separate data,
calendar, rules, execution mechanics, Universe, and admission. Until all 13
foundation families pass, it shows readiness and blockers only; it cannot
render U.S. research as A-share evidence or publish an A-share model or rank.

The Lab also exposes the renewable Factor Discovery cycle. This is a permanent
process contract, not a third model or a promise that research is unattended:
the overall program can keep returning to hypothesis intake, while each
campaign remains finite, deduplicated, outcome-isolated, preregistered,
replayed, and closed into the cumulative ledger. A successful campaign may
open a separate Model Construction path without stopping later discovery.

## AI Quant Research Factory

The future Factory is a governed backend of these three layers, not another
workspace or an unlimited search engine. Hypothesis, data, factor,
implementation, statistics, cost, red-team, reproduction, and shadow roles
share an append-only registry but not unrestricted data access. Numerical
calculation and gates are deterministic on Dell; narrative or agent consensus
cannot override chronology, cost, multiplicity, fingerprint, Validation, or
Holdout failures.

ADR 0287 permits one manually supervised, stage-isolated multi-Agent pilot for
Campaign Three. Its outcome-blind market-state input has passed the frozen
qualification and one exact independent replay. ADR 0289 freezes five
hypothesis cards; ADR 0290 completes outcome-blind input qualification and its
exact replay. Two Alpha interactions and one risk guard advance to protocol
freeze, one Alpha design stops before outcomes, and the near-duplicate remains
rejected. ADR 0291 now freezes the three-trial protocol and registers all three
as unread in Ledger V4. Agents still cannot independently read Development, Validation, or
Holdout outcomes, activate a model, deploy, or trade. Development evaluation
remains a single deterministic boundary after a typed grant bound to a clean
implementation revision and a separate exact authorization.
Wider autonomous Factory operation still begins only after one complete
factor-to-model-to-expression path survives locked evaluation and prospective
shadow review. The first success criterion is reliable rejection and
reproduction, not a high-return chart.

## Candidate promotion

Validated research is necessary but insufficient. Activation separately
reviews economic plausibility, stability, concentration, cost/capacity,
operational reproducibility, interpretation, monitoring, decay, and rollback.
Every active Candidate result must show:

- exact model and strategy-expression versions;
- current applicability and freshness;
- within-model rank/estimate and factor contributions;
- entry readiness and chase/fragility risk as separate evidence;
- supporting evidence, counterevidence, event context, and invalidation; and
- a link to the complete Lab record.

Different outputs remain separate unless an ensemble is independently
registered, evaluated, and activated. Recent performance cannot automatically
select or switch the active model.

## Publication boundary

Research evidence normally refreshes on a reviewed cadence or after a material
data/model version, not merely because daily EOD data arrived. Active signals
may later update daily while their frozen method and validation evidence remain
unchanged.

This document authorizes no provider request, `/data` write, outcome access,
Validation/Holdout opening, result publication, model activation, Candidate
replacement, Snapshot change, deployment, broker action, or order execution.
