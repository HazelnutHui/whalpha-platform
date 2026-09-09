# ADR 0186: Seal Strong-Leader Pullback Research Inputs Before Outcomes

## Status

Accepted

## Date

2026-09-09

## Context

The first strategy experiment already freezes its question, 24-parameter grid,
chronological splits, cohort mechanics, statistics, and holdout custody. It did
not yet define how real canonical evidence becomes one outcome-free observation.
Leaving that translation implicit would allow current product formulas, partial
cross-sections, or future data to enter the study without a version change.

Two pre-evaluation defects were also found in the existing observation contract.
A leader above its prior 20-session close high has a negative pullback-depth
value and must remain an eligible non-trigger control, but the old contract
rejected all negative values. The Market Regime state machine has four states,
while the observation accepted only three and could not represent Stress.

## Decision

Add a pure, read-only Strong-Leader Pullback research-input adapter and a sealed
batch contract.

- Construction is permitted only from a formally reconciling
  `ready_for_development_review` assessment and its exact `research_ready`
  Historical Coverage manifest.
- Same-session canonical Membership must have a marker-backed,
  signal-eligible knowledge-time assessment. Publication, partition manifest,
  complete row fingerprint, evaluated base, three-state counts, and stable IDs
  must reconcile.
- One batch contains the complete same-session point-in-time Primary membership.
  Every member and the stable-ID SPY benchmark must have exactly 21 contiguous
  XNYS EOD bars and a complete, clear adjustment-ledger row for every source
  session. Adjustment source cutoffs must precede the modeled next open. One
  missing, late, or non-clear item rejects the entire cross-section.
- Prices and volumes are split-adjusted to the signal-session basis. Relative
  leadership, trend quality, ATR pullback depth, close recovery, and volume
  contraction use the exact formulas and windows in the versioned feature
  fingerprint. The adapter does not reuse the current five-session Entry
  Geometry high for the experiment's frozen prior-20-session high.
- The batch and every observation bind their source sessions and evidence
  fingerprints. They contain no forward outcomes and grant no development,
  performance, write, network, publication, or Production authority.
- Widen the pre-real-data execution and observation contracts to 1.1. Stress is
  preserved as Stress, and pullback depth accepts -20 through 20 ATR. The
  positive 0.50–2.50 signal bands do not change; the widening only retains
  valid non-trigger controls and complete Regime stratification.

No filesystem reader, CLI, persistence writer, signal materialization,
backtest, parameter selection, or deployment is added by this decision.

## Consequences

- Feature definitions can no longer drift silently with the current Candidate
  product calculation.
- Cross-sectional ranks cannot improve because incomplete members were dropped.
- New-high leaders and Stress sessions remain visible to the preregistered
  control/stratification logic.
- The adapter remains dormant on real data until the missing historical
  families and final Historical Coverage publication make readiness true.

## Alternatives Considered

### Reuse current Candidate and Entry Geometry outputs directly

Rejected because current product versions may change and Entry Geometry uses a
different prior-high window.

### Emit partial observations and disclose missing rows

Rejected because removing missing members changes the same-session percentile
and introduces selection bias.

### Map Stress to Defensive

Rejected because it destroys an observed market state and contaminates later
stratification.
