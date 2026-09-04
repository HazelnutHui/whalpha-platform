# Roadmap

This document records proposed sequencing, not authorization or current
Production identity. Exact sessions, releases, fingerprints, runtime state,
and active risks belong only in the [authoritative current context](current-context.md)
and [current status](current-status.md). Completed execution history belongs in
the [changelog](changelog.md) and ADRs.

## Delivery principles

- Preserve the chain from market state through position management.
- Improve data and runtime foundations before tuning formulas.
- Develop one falsifiable strategy family at a time.
- Keep broad research baselines separate from WH Alpha personal proprietary
  models.
- Expose inputs, parameters, evidence, counterevidence, market fit, and
  invalidation; personal ownership is not permission for a black box.
- Keep research, validation, shadow, Production, monitoring, and retirement
  states distinct.
- Prefer bounded reuse of existing immutable evidence over new services,
  databases, caches, or duplicated status documents.

## Priority 1 — Daily-chain performance and reliability

The first measured reuse optimizations are complete under ADRs 0125–0129:
date-only control paths use the immutable completion index; Entry Geometry and
ETF Relationships reuse the exact formal panel and finalized current Candidate
evidence; Strategy Channels reads only its finalized current batches; daily
Candidate commit uses validated write plus complete physical custody while
periodic and code-change tiers retain full semantic reread; Snapshot planning
derives rollback and CAS from one validated active observation while Apply
retains a fresh comparison. Consumed inputs and explicit full audits retain
their deep validation boundaries.

Next:

1. Measure one complete post-ADR-0125–0129 daily chain on Dell.
2. Use the completed Candidate attribution: the cumulative writer is the
   remaining hotspot, while finalization and explicit garbage collection are
   negligible.
3. Retain the completed current-code ranking: MI is bounded at 53.84 seconds;
   Snapshot is 121.57 seconds after removing its duplicate active read.
4. Advance ADR 0130's disconnected segmented Candidate shadow from exact V1
   reconstruction to an explicitly versioned state-chain identity, append,
   interruption recovery, and periodic cold equivalence. The checkpoint already
   reproduces every numerical/state support row; do not relabel its different
   history fingerprint as V1 or cut over the daily/publication path until all
   gates pass.
5. Remove any remaining repeated evidence reconstruction only where the new
   complete-chain measurement justifies it.
6. Vectorize or process-parallelize only independent CPU-heavy work after exact
   serial equivalence is proven.
7. Preserve every custody, freshness, source, CAS, Oracle, residue, and
   postflight gate.

Do not reconnect the write-capable scheduler as part of performance work. The
installed timer remains read-only until automation receives its own review.

## Priority 2 — Governed historical research inputs

Connect canonical history to research without projecting current membership
backward. Required families are:

- point-in-time Identity and daily Universe membership;
- lifecycle, inactive, terminal, and successor evidence;
- splits, dividends, and other corporate actions;
- explicit price/return adjustment reconciliation;
- realistic costs and liquidity constraints;
- source availability timestamps and revision lineage;
- sealed chronological evaluation and holdout datasets.

Canonical price coverage can satisfy a time-length requirement while research
remains blocked by these missing families. Coverage claims must stay
family-specific.

Current membership implementation sequence:

1. Complete-base single-session shadow is proven on 2026-09-03 with 9,979
   stable IDs, two full three-state ledgers, and localized conflict quarantine.
2. Replace repeated single-day reads with one formally validated shared EOD
   panel and deterministic rolling 20-session calculations.
3. Define durable, minimal source custody without copying raw provider bodies.
4. Acquire or independently resolve only the exact 24 missing reference
   sessions; never project current Activation backward.
5. Run all available sessions into a disconnected `/tmp` batch, reconcile
   completeness and timing, then separately review canonical publication.

## Priority 3 — First real strategy research

Begin with the preregistered Strong-Leader Pullback study after formal data
readiness. Compare candidates only against the same eligible opportunity set,
using chronological development/validation/holdout splits, purge/embargo,
session-balanced inference, cost sensitivity, and adversarial falsification.

Subsequent strategy families:

1. Momentum Breakout.
2. Trend Continuation.
3. Oversold Technical Reversal.
4. Fundamental Value Reversal.

Defensive or anti-market opportunities are regime-conditioned context rather
than a single universal score. Earnings, macro, and news initially serve as
risk and interpretation inputs rather than claims of first-information
advantage.

## Priority 4 — Decision-useful visualization

Visualization may proceed alongside research foundations when it does not
change model logic or delay critical data work. Each chart must answer a
decision question, such as:

- where price sits relative to breakout, pullback, support, and invalidation;
- how far a signal is from a threshold and how old it is;
- which inputs contribute to or contradict a conclusion;
- how market regime, sector direction, and the candidate connect;
- whether a relationship is new, persistent, strengthening, or weakening.

Default views should emphasize the most important five to eight items. Raw
values, parameters, sources, and hashes remain available but folded.

## Priority 5 — Options expression

Options are a separate expression layer over a stock thesis, not a relabeling
of stock forward returns. Required data include bid/ask, spread, volume, open
interest, implied volatility, term structure, skew, Greeks, earnings/dividend
dates, adjustments, and historical chains.

The layer may compare long Calls/Puts, debit spreads, covered calls, moneyness,
and DTE with explicit payoff, volatility, liquidity, and time-decay risks.
Naked short-option strategies remain outside intended scope.

## Priority 6 — Fundamentals, valuation, and events

Proposed order:

1. Point-in-time statements and earnings dates.
2. Growth, margins, earnings quality, cash flow, and balance-sheet change.
3. Relative valuation.
4. Transparent valuation ranges and scenario assumptions.
5. Earnings/guidance and macro-event state.
6. Fundamental Value Reversal research.

Without historical consensus data, actual results and price response may be
analyzed, but they must not be presented as a complete expectations-surprise
model.

## Priority 7 — Portfolio and broker integration

Position management, account-level risk, and broker connectivity follow the
research and options foundations. The first intended broker is IBKR. Initial
work may define inactive navigation and contracts, but no order execution or
automated trading is authorized.

## Explicitly deferred

- intraday/HFT architecture;
- ungoverned complex ML or deep learning;
- automated order execution;
- broad role differentiation between guest and credential Sessions;
- large microservice, distributed-system, or Event Knowledge Base designs;
- new paid-data integration before a concrete missing fact family requires it.
