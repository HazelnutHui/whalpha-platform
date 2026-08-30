# ADR 0097: Preregister Personal Strategy Research Before Backtesting

## Status

Accepted

## Date

2026-08-30

## Context

The deployed Strategy Channels are transparent current-candidate triage, not
validated quantitative strategies. The user has explicitly chosen personal,
style-specific quantitative research as the next major product direction and
wants direct visibility into assumptions, parameter choices, evidence,
counterevidence, and model failure risk.

The canonical history currently spans only 31 sessions. Performance-eligible
daily membership, complete corporate actions, lifecycle/terminal evidence, and
a research-ready adjustment ledger are absent. Starting formula tuning or
reporting a win rate now would create small-sample selection bias and could
embed current-constituent look-ahead.

## Decision

Name the future first-class workspace **Quant Research Lab / 量化研究实验室** and
keep it separate from current Strategy Channels and Production ranking.

Add `candidate-strategy-research-experiment/1.0` as an immutable preregistration
contract. Its first program is Strong-Leader Pullback. It tests whether an
orderly pullback plus recovery adds information beyond leadership by comparing
signals with same-session eligible-leader non-signal controls. The primary
horizon is three sessions; one and five are secondary.

Freeze a maximum 24-combination development-only grid and four decision gates
before historical evaluation. Parameter selection must then lock before
validation and an untouched holdout. Existing chronological split, purge,
embargo, point-in-time membership, sealed-signal, and stock-versus-option
boundaries remain mandatory.

The model is labelled `WH Alpha Personal Quantitative Research`. Every future
consumer must state that it is research rather than a trading recommendation,
may decay or fail across market structures, and cannot represent stock labels
as option returns.

Keep the first registration at `preregistered_data_blocked`. This decision
does not authorize historical acquisition, `/data` writes, signal generation,
outcome maturation, evaluation, publication, a browser page, or deployment.

## Consequences

- Formula and parameter discretion becomes auditable before outcomes exist.
- Pullback value is tested against an appropriate leader control rather than
  being confused with momentum itself.
- A failed experiment remains visible and cannot be silently retuned under the
  same version.
- Current Strategy Channels remain useful descriptive triage but gain no new
  performance claim.
- The next executable dependency is still the permission-cleared historical
  data pilot and research-readiness chain on Dell.

## Alternatives Considered

### Tune the current pullback score on 31 sessions

Rejected because the sample is too short, membership is not performance-
eligible, and repeated threshold inspection would consume the future holdout.

### Begin with a cross-asset macro model

Rejected as the first program because it adds timestamp, market-calendar,
causal-interpretation, and regime-sample complexity before the single-security
research machinery is proven. Macro and cross-asset facts should later
stratify or condition strategies rather than replace a falsifiable first setup.

### Compare pullback signals only with the whole Universe

Rejected because that would attribute general prior leadership effects to the
pullback structure.

