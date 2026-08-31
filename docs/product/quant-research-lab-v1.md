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

The experiment remains
`preregistered_data_blocked`: current 31-session mechanics are insufficient,
and canonical daily membership, complete corporate actions, lifecycle, and a
research-ready adjustment ledger are absent. No signal writer, outcome
maturer, real evaluator, Production consumer, result publication, or deployment
is created by this product definition. ADR 0106 adds a bilingual first-level
page that exposes this blocked state and the registered method while leaving
every performance area unavailable and never projecting fixture results. There
is still no canonical research input adapter, persistence, CLI, real strategy
evaluator, or result report.

ADR 0098 now makes that boundary executable without starting a backtest. The
socket-guarded Dell-local assessment rereads canonical EOD and its bound
Identity evidence and reports every research prerequisite separately. On
2026-08-30 it returned `data_blocked` through 2026-08-28 with 31 of 252 required
sessions and no research-ready Historical Coverage Manifest. The result cannot
authorize development or performance claims. Even a future complete result may
advance only to a separate development-activation review.
