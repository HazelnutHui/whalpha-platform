# Quant Research Lab

## Product authority

Quant Research Lab / `量化研究实验室` is WH Alpha's model registry, research
record, validation evidence center, and model-lifecycle authority. It is the
place where a personal quantitative idea becomes falsifiable evidence—or a
recorded failure.

Stock Candidates is a downstream consumer, not a second research system. Only
one to three separately validated and explicitly activated Lab models may
eventually feed its rankings. The deployed heuristic Candidate score and
technical Strategy Channels remain frozen, unvalidated `Baseline V1` until a
later replacement decision.

The Lab does not need to publish a full daily candidate list for every
experiment. It must publish enough method and evidence for a reviewer to
reproduce the claim, find its weaknesses, and understand whether it currently
has any Product authority.

## Non-black-box contract

Every model version must disclose:

- owner, model family, exact version, lifecycle state, and immutable identity;
- intended decision, holding horizon, Universe, benchmark, and economic
  rationale;
- feature names, source fields, as-of clocks, formulas, transformations,
  missingness rules, and expected signs;
- label and entry/exit basis, overlap rules, corporate-action treatment, and
  stock-versus-option boundary;
- complete fixed parameters, search space, selection budget, seed where
  relevant, and reason for each choice;
- development, validation, holdout, walk-forward, purge, embargo, and
  multiplicity method;
- sample coverage, exclusions, quarantines, survivorship controls, revision
  policy, costs, and capacity assumptions;
- result metrics, uncertainty, stability slices, sensitivity, failure cases,
  counterevidence, invalidation, and known missing evidence;
- activation decision, monitoring thresholds, observed decay, retirement, and
  replacement history; and
- source publications, code revision, environment, and reproducibility
  fingerprints.

The compact page may fold these fields. The detailed record may not hide a
material parameter or silently substitute a narrative summary for the formula.
Guest and credential Sessions receive the same Lab evidence and capability
until the product policy is explicitly changed.

## Model lifecycle

| State | Meaning | Candidate authority |
| --- | --- | --- |
| `idea` | Research question exists but is not registered | None |
| `preregistered_data_blocked` | Hypothesis and plan frozen; required evidence incomplete | None |
| `development` | Development interval open; alternatives may be compared only within the registered budget | None |
| `validation` | Parameters locked; validation interval open | None |
| `holdout_review` | One sealed holdout is consumed once | None |
| `validated_research` | Registered gates passed; operational suitability still unapproved | None |
| `shadow` | Frozen model runs prospectively without driving Product rank | None |
| `active` | Separate reviewed activation permits Candidate use | Exact approved scope only |
| `rejected` | A registered gate failed | None |
| `retired` | Formerly useful evidence decayed, became invalid, or was replaced | None |

No state advances from attractive charts, a higher recent return, more price
history alone, or user-interface completion. Rejected and retired versions
remain visible so repeated testing cannot erase unfavorable evidence.

## Research record layout

### Catalog card

The collapsed catalog should show only the decision-critical summary:

- model name/version, family, owner, and lifecycle;
- one-sentence hypothesis and intended 1–5-session or other declared horizon;
- declared Universe and current-market applicability state;
- last validation/monitor date and next required decision;
- out-of-sample scope and sample count;
- net expectancy and worst drawdown when a portfolio simulation exists; and
- one primary strength, one primary weakness, and a clear `not validated` or
  `not active` label where applicable.

Do not show Sharpe, annualized return, or maximum drawdown when the underlying
study is only an event-level contrast and has no defined portfolio construction.

### Expanded model record

The expanded view is organized as:

1. **Logic:** what behavior is being tested and why it might persist.
2. **Inputs:** all data families, clocks, coverage, exclusions, and quality.
3. **Features:** exact formulas, units, windows, transforms, expected signs,
   redundancy, and missingness.
4. **Rules/model:** complete formula, parameters, ranking, signal, and
   applicability logic.
5. **Evaluation:** split diagram, purge/embargo, controls, costs, uncertainty,
   and sealed-holdout custody.
6. **Results:** out-of-sample headline, complete metric ledger, regime/time/
   liquidity/sector slices, and sensitivity.
7. **Failure evidence:** counterexamples, concentration, unstable cells,
   missed opportunities, chase risk, decay, and invalidation.
8. **Lifecycle:** versions, decisions, shadow monitoring, active scope,
   retirement, and rollback.
9. **Reproduction:** source and result fingerprints, code revision, and report
   artifacts.

## Result semantics and metrics

The Lab must identify which of two evidence types is being reported.

### Signal/event study

Use this before a portfolio construction has been fixed. Headline fields are:

- available signal and control observations plus comparable sessions;
- net expected value per signal after the declared cost scenario;
- median outcome and signal-minus-control/benchmark contrast;
- confidence interval or other preregistered uncertainty statement;
- win rate, average win, average loss, payoff ratio, and Profit Factor;
- MFE, MAE, chase/false-positive rate, coverage, and quarantine; and
- stability by time block, Regime, liquidity, volatility, and concentration.

An event-study result cannot claim portfolio annualized return, Sharpe, or
maximum drawdown.

### Tradable portfolio simulation

Only after position sizing, concurrent holdings, cash, rebalance timing,
turnover, capacity, and costs are frozen may the Lab additionally report:

- total and annualized return;
- maximum drawdown, volatility, Beta, and benchmark Alpha;
- Sharpe, Sortino, Calmar, and Information Ratio where their assumptions are
  meaningful;
- turnover, exposure, capacity, cost attribution, and worst period; and
- trade count, win rate, payoff ratio, Profit Factor, and net expectancy.

The primary headline is always out-of-sample and net of the declared realistic
cost scenario. In-sample metrics are visibly secondary. Point estimates must
appear with sample size, period, uncertainty, and benchmark; more metrics do
not compensate for a weak design.

## Evaluation standard

Every model must begin from a written decision and label, not from indiscriminate
factor mining. The standard sequence is:

```text
question and mechanism
-> point-in-time admitted data cohort
-> leakage-safe features and labels
-> simple baseline
-> bounded development search
-> locked chronological validation
-> single sealed holdout
-> prospective shadow
-> separate activation
-> ongoing monitoring and retirement
```

Required protections include stable-ID joins, point-in-time membership,
delisted/terminal outcomes, corporate actions, source-availability clocks,
chronological splits, overlap-aware purge/embargo, search-budget and
multiplicity controls, realistic costs, and explicit missing/quarantine
statistics. Randomly mixing overlapping security-session rows is prohibited.

Data readiness is scoped to the exact experiment rather than an endless claim
that every possible dataset must be complete. Before outcomes are opened, each
version declares an admitted interval/cohort, mandatory evidence, acceptable
coverage, and rejection policy. Missing evidence may never be silently filled
or selectively dropped. The registered Strong-Leader Pullback V1 retains its
stricter complete-cross-section rule unless a new pre-outcome versioned
decision replaces it.

## First program: Strong-Leader Pullback

The first registered question is:

> Among securities that were already point-in-time relative leaders, does an
> orderly pullback followed by a close-based recovery improve the next 1-, 3-,
> and 5-session underlying-stock outcome relative to comparable leaders that
> did not trigger the setup?

The Primary Universe is primary; Secondary is sensitivity-only. The signal is
formed at the close, modeled entry is no earlier than the next open, three
sessions is the primary horizon, and same-session eligible non-trigger leaders
are the primary control. SPY price return is a separate benchmark.

The immutable V1 preregistration contains 24 combinations: two leadership
gates, three ATR pullback-depth bands, two close-recovery triggers, and two
volume caps. It uses chronological 50/25/25 development/validation/holdout,
five-session purge/embargo, session-balanced inference, block bootstrap,
multiplicity control, fixed cost scenarios, and single-use holdout custody.
Failure may not be repaired by editing V1.

V1 remains `preregistered_data_blocked`. Current canonical price depth has
passed the minimum length, but full historical point-in-time Membership,
lifecycle/terminal evidence, complete corporate-action and adjustment
coverage, final transitive Historical Coverage, calibrated execution evidence,
and a real sealed evaluation dataset are incomplete. Exact current counts
belong only in [current context](../project/current-context.md).

ADR 0186 fixes an outcome-free, complete-cross-section input adapter and exact
21-session feature semantics. It has fixture evidence only and has never run a
real backtest. Before activation, the study must also challenge whether static
geometry captures an orderly path, whether leadership predates the pullback,
whether the control is comparable, whether next-open gaps destroy the setup,
and whether apparent evidence is concentrated by date or industry.

## Model sequence

Research proceeds one family at a time:

1. Strong-Leader Pullback;
2. Momentum Breakout;
3. Trend Continuation only after proving it is distinct from the first two;
4. Oversold Technical Reversal; and
5. Fundamental Value Reversal after point-in-time fundamental and valuation
   evidence exists.

Defensive opportunity is initially a Regime-conditioned search for relative
resilience, not one universal defensive score. Earnings, guidance, macro, and
news begin as risk/context or stratification evidence rather than a claim of
first-information advantage. Cross-asset macro models follow the first proven
single-security research pipeline rather than replacing it.

## Candidate promotion

A `validated_research` result is necessary but not sufficient. Activation also
reviews economic plausibility, temporal and Regime stability, concentration,
cost/capacity, operational reproducibility, user interpretation, monitoring,
decay thresholds, and rollback.

An active Candidate consumer must show:

- exact active model/version and validation date;
- why the model is currently applicable, neutral, adverse, or unavailable;
- within-model rank and the facts that raised or lowered it;
- entry readiness and chase risk as a separate axis;
- supporting evidence, counterevidence, event context, and invalidation; and
- a link to the complete Lab record.

Different strategy ranks remain separate unless an ensemble is independently
registered and validated. No automatic model switch may be based only on which
model recently performed best.

## Publication cadence and boundary

Daily price/data operation does not require monthly research recalculation.
Model evaluation and public research metrics should normally refresh monthly,
on a registered review cadence, or after a material data/model version—not
every day. Active-model signals may update daily while the frozen model and its
validation evidence remain unchanged.

This document authorizes no provider request, `/data` write, real evaluation,
parameter selection, model activation, Candidate replacement, Snapshot change,
deployment, order, or trading recommendation.
