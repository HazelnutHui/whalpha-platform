# Quant Research Lab V1

## Product role

Quant Research Lab / 量化研究实验室 is the future first-class workspace for
WH Alpha's personal, style-specific quantitative research. It is separate from
the deployed Strategy Channels workspace:

- Strategy Channels explain and triage current candidates with provisional
  cross-sectional mechanics.
- Quant Research Lab preregisters a falsifiable hypothesis, builds point-in-time
  evidence, evaluates it chronologically, and records whether it survives.

The Lab never turns a ranking into a recommendation. Every model must show its
owner, lifecycle state, exact version and parameters, evidence, counterevidence,
data coverage, sample limitations, failure conditions, and validation history.

## Visible lifecycle

The future interface must display one of these states without euphemism:

1. `preregistered_data_blocked` — hypothesis frozen; required data incomplete;
2. `development` — only the chronological development interval is open;
3. `validation` — parameters locked; validation interval under review;
4. `holdout_review` — one untouched holdout is being evaluated once;
5. `validated_research` — research gates passed, but Production activation is
   still a separate decision;
6. `rejected` — hypothesis failed a registered gate; or
7. `retired` — previously useful evidence no longer generalizes or is no longer
   operationally suitable.

The header must always state that this is personal research, not independent
investment advice; parameters may weaken or fail as market structure changes;
historical results do not guarantee future results; and stock outcomes are not
option returns.

## First research program: Strong-Leader Pullback

The first question is deliberately narrower than “does momentum work?”:

> Among securities that were already point-in-time relative leaders, does an
> orderly pullback followed by a close-based recovery improve the next 1-, 3-,
> and 5-session underlying-stock outcome relative to comparable leaders that
> did not trigger the setup?

The primary Universe is the point-in-time Primary Universe. Secondary is a
sensitivity analysis, not a pooled source of extra observations. The signal is
formed after the session close; the earliest modeled entry is the next session
open. Three sessions is the primary horizon, with one and five sessions
secondary. The primary comparison is a same-session eligible-leader non-signal
control; SPY price return is a separate benchmark.

This design tests whether the pullback structure adds information beyond
leadership itself. Comparing only against the whole Universe would confound
the pullback effect with the already-known momentum/leadership selection.

## Frozen first parameter family

Development may compare only 24 preregistered combinations:

- two leadership gates;
- three ATR pullback-depth bands;
- two close-based recovery triggers; and
- two pullback-volume contraction caps.

No adaptive search, arbitrary threshold sweep, random split, or change made to
improve a preferred chart is permitted under V1. Development chooses at most
one specification; that specification is locked before validation. Any changed
grid or definition requires a new research version and a new untouched holdout.

The exact V1 grid is:

| Dimension | Frozen candidates |
| --- | --- |
| Prior leadership | 20-session relative-strength percentile at least 0.80 and trend-quality score at least 70; or percentile at least 0.90 and trend quality at least 75 |
| Pullback depth | Current distance below the prior 20-session high is 0.50–1.50, 0.75–2.00, or 1.00–2.50 ATR units |
| Close-based recovery | Close above the prior close; or close above the prior high |
| Pullback volume | Current pullback-volume ratio to the prior 20-session median is at most 0.80 or 1.00 |

For each combination, one same-session, point-in-time Primary member is a
signal only when it passes that combination's leadership, depth, recovery, and
volume rules. A member that passes the leadership gate but not every setup rule
is an eligible-leader control. A non-member, non-leader, chronologically
excluded row, or row without same-session point-in-time membership is neither a
signal nor a control. This is a cohort rule, not a weighted score or a claim
that every signal is ready to trade.

The implementation input currently contains a relative-strength percentile and
a trend-quality score rather than raw feature columns. A future real adapter
must bind those values to the exact source formula/version and source sessions;
it may not silently inherit whichever current Candidate formula happens to be
active at evaluation time.

## Evaluation requirements

- Minimum 252 contiguous sessions; 504 preferred for Regime review.
- Point-in-time daily membership, corporate-action coverage, lifecycle facts,
  adjustment reconciliation, feature warm-up, and matured labels.
- Chronological 50/25/25 development/validation/holdout boundaries.
- Five-session overlap purge and embargo.
- Session-aware/block inference for overlapping cross-sectional observations.
- Finite-grid multiplicity control on validation.
- Underlying-stock returns shown gross and under the existing 0/10/25/50 bps
  per-side scenarios; option outcomes remain unavailable.
- Results by Regime, liquidity, volatility, signal age, and later by governed
  sector/industry data rather than current taxonomy projected backward.
- Coverage, quarantine, turnover, MFE, MAE, drawdown, false positives, chase,
  missed opportunities, and eligible-base rates shown beside returns.

Passing research gates does not activate a Production signal. Activation needs
a separate review covering economic plausibility, stability, capacity and
costs, user interpretation, monitoring, decay triggers, and rollback.

## Minimum data admission baseline

The following matrix is the single product-level acceptance checklist for the
first real study. Contract-level validation remains authoritative; this table
explains what the evidence means and prevents price depth from being mistaken
for research readiness.

| Evidence family | Minimum admission condition | Current Dell evidence | Decision |
| --- | --- | --- | --- |
| EOD Price Bars | At least 252 contiguous XNYS sessions, exact session completion, stable-ID linkage, and transitive hashes | 305 contiguous canonical sessions through 2026-09-08 | Length met; final coverage binding remains open |
| Point-in-time Identity | Completed Identity for every admitted session, aligned to EOD and keyed by stable `instrument_id` | 305 canonical completed snapshots; 303 normalized source-observation partitions, with 2026-08-13 and 2026-08-19 unbound | Snapshot depth met; source lineage incomplete |
| Daily Universe Membership | A same-session, methodology-bound decision for every instrument and every admitted session; no current-constituent replay | 2 signal-eligible sessions / 39,928 decisions; disconnected mechanics cover 302 source-available dates | Blocking |
| Corporate Actions | Canonical, availability-aware action coverage for the full interval, including explicit no-event semantics and quarantine | Bounded source custody and split-only outcome evidence exist; dividend/total-return and absent-row neutrality do not | Blocking |
| Instrument Lifecycle | Effective-dated active, delisted, successor, and terminal evidence across venues | A 547-item temporary corroboration queue exists; no canonical cross-venue family | Blocking |
| Adjustment Ledger | Raw-to-basis split price/volume and total-return treatment reconciled for the full admitted interval; null when unknown rather than assumed factor one | Sparse split adjustment is outcome-only; 387 severe discontinuities remain unexplained; total return unavailable | Blocking |
| Feature construction | Exact as-of formulas, windows, source fingerprints, and no-forward-data proof for every frozen observation field | Fixture mechanics exist; no canonical real input adapter | Blocking after the physical families pass |
| Outcome labels | Exact next-open to 1/3/5-session-close paths; affected or incomplete paths quarantined; validation and holdout signal/control coverage equals 1.0000 | Fixture-only scheduler and maturer | Blocking for real evaluation |
| Costs and liquidity | Gross result plus 0/10/25/50 bps-per-side sensitivity; realistic quote/impact evidence before economic or Production interpretation | Scenario-only equity mechanics; no observed spread or calibrated impact | Development sensitivity available; economic interpretation blocked |
| Classification and events | Point-in-time sector/industry for governed stratification; earnings/events retained as risk context when available | No canonical historical classification or governed earnings-event family | Not a V1 primary-test gate; unavailable context must remain explicit |
| Historical Coverage | One immutable manifest transitively binding every admitted required family and exact payload hash | Family evidence exists for EOD and Identity only; final publication absent | Blocking |

The minimum formal readiness result is therefore still `data_blocked`. No
backtest, parameter choice, win rate, or performance chart may be inferred from
the 305-session price panel alone. A mechanics-only dry run over synthetic or
quarantined inputs may test software behavior but is never investment evidence.

## V1 falsification focus

The frozen name “Strong-Leader Pullback” is a hypothesis label, not proof that
the four rules capture an orderly pullback. Before any activation review, the
evidence must explicitly examine these failure modes:

- **Static geometry versus path:** distance from a prior 20-session high does
  not by itself prove a recent, orderly retracement or a recovery sequence.
- **Stale or composite leadership:** the exact construction and stability of
  the relative-strength percentile and trend-quality score must be reproduced,
  not treated as unexplained inputs.
- **Control comparability:** same-session non-triggering leaders may differ in
  liquidity, volatility, industry, prior extension, and pullback depth. The
  frozen primary contrast stays unchanged, while matched/reweighted
  sensitivity analysis may diagnose this imbalance without replacing it.
- **Next-open gap risk:** a close-based signal can become overextended or
  invalid before the modeled next-open entry; gap and fill sensitivity must be
  visible.
- **Crowding and concentration:** many cross-sectional signals on one session
  may represent one market or industry event rather than independent evidence.
- **Event contamination:** unavailable point-in-time earnings or material-event
  context must be disclosed; later versions may add a preregistered exclusion
  or stratification, but V1 cannot be edited after seeing outcomes.
- **Regime and parameter instability:** an aggregate result cannot hide a
  reversal across time, Regime, liquidity, volatility, or concentration cells.

A V2 research version is justified only by a pre-outcome defect review or by a
formally recorded V1 failure. Candidate V2 additions may include explicit
pullback recency/duration, path smoothness, support integrity, next-open gap,
and point-in-time event risk. They are not part of V1 and must not be introduced
opportunistically during evaluation.

## Current state

Repository source contains the immutable first preregistration, readiness gate,
and fixture-only chronological execution mechanics. The mechanics
deterministically assign the 50/25/25 split, warm-up, purge/embargo and label-
maturity exclusions; enumerate all 24 registered combinations; separate same-
session leader signals from eligible-leader controls before outcomes; and
mature exact 1/3/5-session underlying-stock labels only after the future path
is known. They create no performance statistic or claim.

ADR 0104 adds a fixture-only statistics layer before any real labels exist. It
uses session-balanced signal-versus-control differences, a deterministic five-
session block bootstrap, 90% intervals, 24-family Holm correction, fixed cost
scenarios, explicit coverage/quarantine counts and one immutable development
parameter lock. Validation cannot change the lock, and holdout exposes only the
locked combination after every validation gate passes. All reports explicitly
deny stage-transition and performance-claim authority.

ADR 0105 adds an independent descriptive Oracle and adversarial fixtures for
null effects, validation reversal, date crowding, extreme values, missing
labels and stage leakage. The audit found that visible missingness alone was
not sufficient protection, so validation and holdout now require complete
available outcome coverage in both signal and control cohorts. This remains a
synthetic mechanics result, not evidence for the hypothesis.

ADR 0107 adds a durable external reserve-before-evaluation seam for the future
sealed holdout. Completion, failure and ambiguous interruption all prevent a
second capability invocation for the same validation/lock identity. This is
fixture-proven custody only; it creates no real result or activation authority.

ADR 0108 closes the remaining implementation-audit gap by independently
reproducing the registered moving-block Bootstrap, 90% interval, one-sided
probability and 24-family Holm correction on arbitrary nonconstant fixtures.
This verifies mechanics, not alpha or future validity.

ADR 0109 defines the separate development-activation review. Even complete
252-session readiness cannot start real evaluation: the unchanged experiment,
code, inference Oracle, holdout custody and zero prior real-research state must
first produce an exact review, followed by separate user authorization and a
future activation capability.

The experiment remains `preregistered_data_blocked`. The original 31-session
assessment is historical; canonical price depth now covers 305 sessions through
2026-09-08, while canonical signal-eligible daily Membership covers only 2 of
those 305 sessions. Complete corporate actions, lifecycle, a research-ready
adjustment ledger, and an immutable Historical Coverage publication remain
absent. No signal writer, outcome maturer, real evaluator, Production consumer,
result publication, or deployment is created by this product definition. ADR
0106 adds a bilingual first-level page that exposes this blocked state and the
registered method while leaving every performance area unavailable and never
projecting fixture results. There is still no canonical research input adapter,
real-strategy result persistence, CLI, real strategy evaluator, or result
report.

The page no longer presents the dated 31/252 result as current readiness.
Instead it shows family-specific gates: the minimum price-history length is
met, while point-in-time Membership, canonical corporate actions and
adjustment, cross-venue lifecycle, realistic costs, and sealed evaluation
remain incomplete or locked. These states must not be averaged into a progress
percentage because they are not interchangeable observations.

ADR 0098 now makes that boundary executable without starting a backtest. The
socket-guarded Dell-local assessment rereads canonical EOD and its bound
Identity evidence and reports every research prerequisite separately. On
2026-08-30 it returned `data_blocked` through 2026-08-28 with 31 of 252 required
sessions and no research-ready Historical Coverage Manifest. That count is a
dated result, not the current canonical depth. The result cannot
authorize development or performance claims. Even a future complete result may
advance only to a separate development-activation review.
