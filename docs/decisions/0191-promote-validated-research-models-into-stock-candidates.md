# ADR 0191: Promote Validated Research Models into Stock Candidates

## Status

Accepted

## Date

2026-09-09

## Context

WH Alpha currently serves one heuristic Candidate score, Entry Geometry, and
three provisional technical Strategy Channels. They are transparent and useful
for descriptive triage, but they were not derived through a professional
point-in-time research and validation process. In the interface they can also
look like three independent answers rather than one evidence funnel.

The intended product is different: Quant Research Lab records and tests
personal, style-specific models, while Stock Candidates shows the small subset
of models that have earned an explicit current activation. Users must be able
to understand both the ranking and the evidence behind the model without
turning either page into a black box.

## Decision

Adopt this product authority chain:

```text
governed point-in-time data
-> registered hypothesis and features
-> chronological development
-> locked validation and sealed holdout
-> validated research
-> separate activation review
-> Stock Candidates
-> monitoring, retirement, or rollback
```

Quant Research Lab is the authority for model identity, ownership, economic
logic, feature definitions, formulas, parameters, datasets, labels, costs,
evaluation design, limitations, professional metrics, validation history,
failure/decay evidence, and lifecycle state. Its summary view may be compact,
but the detailed record must expose all material model information to both
guest and credential Sessions.

Stock Candidates may eventually consume only one to three explicitly
activated Lab models. Every Candidate result must identify the exact
model/version, explain why that model is considered applicable to the current
market, show its within-model rank and supporting/counter evidence, distinguish
ranking quality from entry readiness, and link back to the full Lab record.
Ranks from different models remain separate unless a distinct ensemble is
preregistered and validated. Recent performance alone may not auto-select or
auto-switch a model.

The current Candidate score and technical Strategy Channels are frozen as
transparent, unvalidated `Baseline V1`. They may remain deployed until a later
reviewed replacement, but receive no direct parameter tuning and gain no
performance claim from this decision. Stock Candidate redesign, model
activation, result publication, `/data` mutation, and Production deployment
are not part of this documentation change.

The three stable market workspaces remain independent product capabilities:
Market Regime & Opportunities, Sector ETF Rotation, and Market Structure &
Activity. They provide context and inputs; they do not become one hidden model
score.

## Consequences

- Candidate ranking and Quant Research Lab no longer compete as parallel model
  products; Lab produces evidence and Candidate consumes approved results.
- Unvalidated experiments can be visible without filling the Candidate page
  with daily rankings.
- Model transparency applies to logic and parameters as well as performance.
- Model failure is a retained research result, not a reason to silently retune
  the same version.
- Current Production remains truthful while the future architecture stops
  extending the provisional heuristic baseline.

## Supersession scope

This ADR supersedes only future-direction language that implied direct
extension or tuning of the V1 Candidate/Strategy Channels formulas. ADRs 0049,
0050, 0051, 0056, 0097, 0104, 0106, 0109, and 0186 remain authoritative for
their historical decisions, safety boundaries, and implemented contracts.

## Alternatives considered

### Keep Candidate and Lab as independent ranking products

Rejected because users would see multiple competing answers without a clear
promotion or ownership boundary.

### Tune the current heuristic scores directly

Rejected because post-hoc weight adjustment before governed chronological
evaluation would produce fragile and hard-to-falsify results.

### Show every experimental model in Stock Candidates

Rejected because it would create signal overload and blur experiment status
with decision-ready evidence.
