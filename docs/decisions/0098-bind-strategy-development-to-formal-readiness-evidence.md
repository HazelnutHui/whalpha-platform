# ADR 0098: Bind Strategy Development to Formal Readiness Evidence

## Status

Accepted

## Date

2026-08-30

## Context

ADR 0097 freezes the first personal Strong-Leader Pullback experiment before
outcomes can influence its hypothesis or parameter grid. A preregistration by
itself does not prove that the historical inputs are complete enough to begin
formula selection, chronological evaluation, or performance reporting.

The earlier historical audit described 29 sessions. Canonical Dell state now
contains 31 sessions through 2026-08-28, but still has no research-ready
coverage manifest for daily point-in-time membership, corporate actions,
instrument lifecycle, or adjustment reconciliation. A durable transition rule
is needed so future tasks do not infer readiness from directory presence,
current constituents, or an outdated narrative.

## Decision

Add `strategy-research-readiness/1.0` as a deterministic, read-only assessment
over the exact frozen experiment, formally read canonical EOD/Identity
descriptors, and an optional typed Historical Coverage Manifest.

Every development requirement must be satisfied: at least 252 covered
sessions, completed EOD, point-in-time Identity, daily membership, corporate
action, lifecycle, and adjustment-ledger families, at least the experiment's
20-session feature warm-up, its five-session maximum outcome horizon, and a
non-zero matured signal window. The experiment preregistration itself is a
separate required observation.

The current command intentionally accepts only the canonical Dell data root.
It does not accept an arbitrary manifest file: no operational formal reader yet
proves a physical Historical Coverage publication and its referenced family
artifacts. The pure assessor supports the typed manifest contract so that a
future formal reader can be connected without changing transition semantics.

Even complete evidence may return only `ready_for_development_review`. It does
not change the frozen experiment stage and never grants development,
performance-claim, provider, data-write, publication, deployment, or scheduler
authority. A separate reviewed change is required before development begins.

Correct the first experiment's `adjusted_ohlcv_panel` feature lookback from 252
to 20 sessions. Twenty is the actual feature warm-up; 252 remains the separate
minimum total research-history requirement. This correction changes the
experiment content fingerprint but not its hypothesis, grid, or data-blocked
stage.

## Consequences

- Current state can be re-established from exact Dell evidence rather than a
  remembered session count.
- Missing families and short history remain explicit, machine-readable
  blockers.
- A self-asserted JSON manifest cannot operationally unlock development.
- Reaching data readiness still cannot silently start tuning or create a
  performance claim.
- The next dependency is the permission-cleared physical historical
  foundation and its formal coverage reader, not model optimization.

## Alternatives Considered

### Treat 31-session mechanics as sufficient for exploratory tuning

Rejected because repeated inspection would consume future validation evidence
and combine a short sample with incomplete point-in-time membership and
adjustment controls.

### Let the CLI trust any valid-looking coverage JSON

Rejected because schema validity does not prove that referenced physical
families exist, match their hashes, or passed formal reread.

### Automatically enter development when all requirements pass

Rejected because data readiness and authorization to select a model are
separate decisions.
