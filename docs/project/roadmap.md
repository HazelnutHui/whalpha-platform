# Roadmap

This is proposed sequencing, not operational authorization. Volatile Production
facts belong in [current context](current-context.md); actual state belongs in
[current status](current-status.md); completed history belongs in the
[changelog](changelog.md), ADRs, and audits.

## Direction

The three established market workspaces remain supported:

1. Market Regime & Opportunities;
2. Sector ETF Rotation; and
3. Market Structure & Activity.

The next product-development center is Quant Research Lab. Stock Candidates is
temporarily a deployed **Baseline V1** consumer, not a formula-tuning target.
Its future rankings will come only from one to three validated and explicitly
activated Lab models.

The longer-term AI Quant Research Factory is a governed Lab backend. It may
increase hypothesis and adversarial-review throughput only after one complete
strategy path proves the reusable controls. It is not an unbounded factor
search and does not create another product workspace.

~~~text
Lab research and validation
-> explicit model activation
-> Stock Candidates
-> entry/invalidation review
-> later position management
~~~

## Working rules

- Research one falsifiable strategy family at a time.
- Add or buy data only for a named feature, label, bias control, or decision.
- Use the simplest defensible baseline before increasing model complexity.
- Keep point-in-time data, features, labels, costs, and holdout custody
  reproducible.
- Show formulas, parameters, evidence, counterevidence, uncertainty, failure,
  and decay; personal ownership never permits a black box.
- Separate event studies from portfolio backtests and stock outcomes from
  option outcomes.
- Keep experiment, validation, shadow, active, rejected, and retired states
  explicit.
- Stop an optimization line when it meets its acceptance criterion; do not
  continue because another improvement is merely possible.

## Priority 1 — Unify product and research authority

1. Make Product Vision, Scope, Roadmap, current context, and Quant Research Lab
   agree with ADR 0191.
2. Mark current Candidate/Strategy Channels as frozen, unvalidated
   **Baseline V1**; preserve their deployed contract and historical evidence.
3. Make the Lab the single model registry and Candidate promotion authority.
4. Reduce default documentation to a short recovery path; keep detailed ADRs
   and audits outside it.

Exit criterion: a new task can identify current Production, future product
direction, first research program, and prohibited shortcuts without reading a
chronological document dump.

## Priority 2 — Design the Lab model record and research substrate

Repository status: implemented on 2026-09-10 under ADR 0192; Production is
unchanged. The first checked-in Strong-Leader Pullback record is method-only
and Candidate-ineligible.

1. Define the typed model registry, lifecycle, version, and result-publication
   contracts from the product record in
   [Quant Research Lab](../product/quant-research-lab-v1.md).
2. Separate signal/event-study metrics from portfolio-simulation metrics.
3. Bind exact model inputs, features, labels, parameters, search budget,
   chronological splits, costs, results, and reproduction evidence.
4. Provide compact catalog summaries and fully transparent expanded records.
5. Keep real performance panels unavailable until a real result publication
   passes formal reread.

Exit criterion met: one contract-validated method record renders and audits
end to end without synthetic performance or Candidate authority. Fixture and
real result scopes remain separately guarded.

## Priority 3 — Close only the first experiment's data blockers

Strong-Leader Pullback remains first. Price depth is sufficient, but its exact
point-in-time research panel is not.

ADR 0196 now makes the Dell-owned rolling five-year foundation the active data
program. Construction proceeds family by family with Massive as the primary
price/reference source and bounded official/free corroboration. A paid
cross-venue source is reconsidered only after the residual-gap census proves a
named blocking fact cannot be established professionally by the composed
sources.

ADR 0193 resolves the first admission-policy question without weakening final
evidence. The later-retrieved, historical-date Identity interval may first be
used only for an outcome-blind coverage census. ADR 0195 requires complete
Primary session cross-sections and at least 252 admitted sessions before any
development. Validation and holdout still require source-time-defensible
point-in-time evidence.

Required work:

- completed 2026-09-11: define and census the exact rolling five-year XNYS
  target, including explicitly separate experiment warm-up and outcome-tail
  sessions; the active target is 1,255 sessions from 2021-09-13 through
  2026-09-11 with zero EOD/Identity target-session gaps;
- completed for rolling source depth: expand EOD/Identity to that target while
  preserving exact source custody; exact-interval execution is implemented.
  Starter S3 access is verified for a current Day Aggregates object but denied
  for 2021-09-09, and Flat Files are not field-equivalent to REST because they
  omit VWAP and its zero-volume path. ADR 0206 ends retries or a purchase for
  the two expired boundary sessions: normal daily updates rolled the active
  source target to 2021-09-13 and the offline census verified it;
- build ADR 0204's complete immutable Reconciled EOD Edition after acquisition
  quiesces; prefer retained original packages, retain later reacquisitions as a
  distinct provenance class, and reject unexplained removals or economic-value
  changes rather than hiding the ADR 0203 defect behind a sparse overlay;
  persistent owner-only custody, memory-bounded validation, bounded resumable
  1–40-session/1–4-worker construction, exact Apply planning, and atomic whole-
  edition Apply and a sealed per-session source-coverage/selection contract are
  implemented; a coverage-bound bounded/resumable later-source reacquisition
  runner and complete-interval resumable candidate controller are also
  implemented; the corrected final census confirms zero price-package gaps
  after 307 reacquisitions and leaves only two Identity-source gaps. Later
  Identity diagnostics omitted canonical business keys, so ADR 0207 preserves
  the no-removal gate and selects the maximal preceding 1,234-session interval
  through 2026-08-12 for the first real candidate. Construct and formally
  reread that exact edition before planning any canonical Apply. The first
  1.0 run retained 275 sessions before five proven legacy case-normalized
  misbindings stopped it. ADR 0208 distinguishes source-proven expected
  removals from every unexpected absence. The clean 1.1 successor retained 300
  sessions before exact provider-case restoration in 30 otherwise-identical
  source IDs stopped it; ADR 0209 and contract 1.2 admit only that fully proven
  provenance repair. Start a new clean 1.2 candidate rather than mixing either
  stopped predecessor;
- use the first 20 available target sessions as explicit outcome-free feature
  warm-up and begin performance eligibility only afterward. Preserve the
  separate external-warm-up contract for a future deeper dataset, but do not
  populate it under Starter;
- reconstruct daily historical Membership without projecting current
  constituents or current classifications backward; ADR 0197 requires its
  durable latest-vintage output to live in a research-only family, separate
  from signal-eligible Membership; the first 300 sessions through 2026-09-03
  are now durably archived and formally reread;
- completed 2026-09-10: the fixed census reconciled 437,402 raw-complete
  included paths but zero all-required-evidence-complete paths, without
  calculating triggers, returns, metrics, or parameter results;
- completed 2026-09-10: the missingness-only decision froze a 100% complete-
  session threshold, retained the 252-session floor, and rejected current
  evidence with zero admitted sessions;
- lifecycle and terminal-outcome evidence;
- complete split/action handling for the declared underlying-stock price-
  return basis, with dividends retained as event context rather than silently
  changing the label to total return;
- final transitive Historical Coverage for the declared admitted cohort;
- outcome labels, realistic cost sensitivity, and sealed evaluation custody.

V1 remains immutable and strict. Missing securities, unresolved actions, and
terminal events stay in denominators and quarantine; no source gap is imputed
and no current membership is projected backward.

Sector/industry data is not a blocker for the V1 primary test, but becomes
important for concentration and stability diagnosis. GICS History remains the
first sample candidate; no source is selected until its actual fields, clocks,
retention, and identity mapping pass the existing review.

Exit criterion: one immutable readiness report says exactly which sessions and
securities are admitted, with no unresolved mandatory family hidden by an
aggregate completion percentage.

## Priority 4 — Execute Strong-Leader Pullback research

1. Run the preregistered development stage on Dell.
2. Lock at most one specification under the registered search budget.
3. Evaluate chronological validation with purge/embargo, session-balanced
   inference, multiplicity control, and costs.
4. Consume the sealed holdout once only if validation gates pass.
5. Record rejection without retuning V1, or mark the passing version
   validated research.
6. If appropriate, run a prospective shadow before any activation review.

Headline evidence initially belongs to a signal/event study: net expectancy,
signal-control contrast, uncertainty, sample/coverage, MFE/MAE, win/payoff/PF,
cost sensitivity, and stability. Portfolio AR, Sharpe, and MDD require a
separately frozen portfolio construction.

Exit criterion: a reproducible real result or recorded failure exists; neither
automatically changes Stock Candidates.

## Priority 5 — Generalize the bounded AI research factory

Only after Priority 4 proves one complete and rejection-capable path:

1. extract reusable hypothesis, data-admission, feature, label, experiment,
   result, and failure registries;
2. record every attempted experiment and group materially equivalent ideas so
   agent volume cannot hide the true search count;
3. enforce role-based data visibility for development, validation, holdout,
   red-team, reproduction, and shadow stages;
4. pilot a small set of specialized agents on one strategy family while Dell
   remains the deterministic calculation authority;
5. measure reproducibility, unique-hypothesis yield, rejection quality,
   leakage detection, compute cost, and holdout integrity before scaling; and
6. keep long-running services, distributed infrastructure, and automated model
   activation out of scope until a measured need exists.

Exit criterion: the same registered experiment produces the same decision
under independent replay; failed attempts remain visible; no agent can inspect
or promote evidence outside its stage.

## Priority 6 — Activate and redesign Stock Candidates

Only after a model passes research and operational review:

1. approve exact model/version, Universe, market-applicability rule, monitoring,
   decay, and rollback;
2. publish one bounded active-model result;
3. show model identity, why it fits the current market, within-model rank,
   evidence, counterevidence, entry readiness, chase risk, and invalidation;
4. link every Candidate to the complete Lab record; and
5. keep model ranks separate unless an ensemble is separately registered and
   validated.

The page may remain sparse or explicitly unavailable before this criterion.
Daily updates of the old provisional rank are not a product-development
priority.

## Priority 7 — Additional strategy families

After the first pipeline proves reusable:

1. Momentum Breakout;
2. Trend Continuation, only with distinct features and incremental value;
3. Oversold Technical Reversal;
4. Fundamental Value Reversal; and
5. Regime-conditioned defensive/resilience opportunity.

Cross-asset macro relationships may later condition or stratify these models.
They should not be the first complex model because their calendars, timestamps,
causal interpretations, and small number of independent regimes make
overfitting easier.

## Priority 8 — Fundamentals, valuation, events, and options

Add point-in-time statements and earnings dates first, then business quality,
growth/margins/cash flow/balance sheet, relative valuation, transparent value
ranges, consensus/guidance where available, and macro/news context. Event data
initially changes risk/context rather than claiming first-information speed.

Options remain a separate expression layer over a stock thesis. Historical
chain quotes, bid/ask, spread, volume, open interest, IV/term/skew, Greeks,
earnings/dividend dates, adjustments, and payoff/cost modeling are prerequisites
to comparing Calls/Puts, debit spreads, covered calls, moneyness, and DTE.

## Priority 9 — Portfolio and broker integration

Position management, account-level risk, and IBKR integration follow reliable
stock research and options expression. An inactive navigation/framework may be
prepared earlier, but automated order execution remains unauthorized.

## Parallel operational maintenance

Daily EOD reliability and one bounded next-session automation rehearsal may run
in parallel when a completed market session exists. It must not block Lab
design or become another indefinite optimization program. Current Candidate
segmentation remains a cutover NO-GO; reopen it only after a measured clean-path
runtime breaches an agreed budget and one design solves both known gaps.

## Explicitly deferred

- automated trading, order routing, and HFT;
- broad intraday architecture without a defined strategy requirement;
- opaque ML/deep learning or unbounded factor search;
- guest/credential capability differentiation;
- new database, microservices, Kubernetes, or distributed systems without a
  measured need; and
- paid datasets without a concrete fact-family and acceptance test.
