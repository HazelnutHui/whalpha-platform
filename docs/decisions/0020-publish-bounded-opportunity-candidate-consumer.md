# ADR 0020: Publish a Bounded Opportunity Candidate Consumer

## Status

Accepted

## Date

2026-08-26

## Context

Phase 5 produces a canonical two-session Candidate audit of about 170 MB with
full score, state, risk, Oracle, raw-fact, normalization, and replay evidence.
That artifact is appropriate for offline audit, but copying it to the public-
serving Snapshot would expose a large rejected population, couple the browser
to audit encodings, and create a second source of product semantics.

The Candidate UI needs three risk-mode ranks, current stages, component facts,
supporting and counterevidence, invalidation, and source limitations. It must
remain bilingual without shipping Python-generated English explanations, and
must not let the browser recalculate ranks or parse opaque strings.

## Decision

Market Intelligence remains the single immutable aggregate publication and is
upgraded additively to contract 1.1. It embeds one language-neutral,
source-bound `opportunity-candidate-publication/1.0` projection produced only
after formal Candidate audit reread. The projection contains the stable-ID
union of the fixed Conservative/Balanced/Aggressive display lists plus current
Prepare, Enter, and invalidated review rows. It retains structured component,
metric, state, gate, risk, evidence, invalidation, warning, and lineage facts,
but omits raw bars, full rejected assessments, audit paths, and rendered
English prose.

Snapshot 1.6 / Dashboard 2.3 adds exactly one Candidate JSON file derived from
the same MI 1.1 payload. The Snapshot and its plan bind the MI publication,
Candidate audit, parameters, file hash, Universe order, and display counts.
Existing MI 1.0, Snapshot 1.5 / Dashboard 2.2, pointer versions, namespaces,
and rollback releases remain readable without optional Candidate fields.

The React application exposes Stock Candidates as the third first-level
workspace. Balanced is the default risk mode. The browser selects formal ranks
and localizes stable codes; it does not recompute analytics. Guest and
credential Sessions load the same protected file.

## Consequences

- Production Candidate payload is about 5 MB rather than the full audit size.
- Audit, publication, Snapshot, bundle, and deployment remain separately
  reviewable and freshness-gated.
- Candidate invalidation remains distinct from a position exit or sell action.
- Confidence remains data support, ETF relation remains a price-derived proxy,
  and the underlying-stock result remains distinct from option returns.
- A new exact authorization is required to deploy the current stale review;
  the prior review exception does not automatically extend to MI 1.1.
- Future per-candidate history or event/fundamental evidence requires an
  additive contract rather than browser inference.

## Alternatives Considered

- Copy the full audit into Snapshot: rejected for size, unnecessary rejected
  rows, audit-path coupling, and weak product boundaries.
- Publish a second independent Candidate pointer: rejected because it permits
  Market Regime and Candidate state to drift across publications.
- Parse existing colon-delimited evidence and English explanations in React:
  rejected because it is brittle, not language neutral, and obscures formal
  semantics.
- Recalculate risk modes in the browser: rejected because formal ranking and
  concentration rules must remain reproducible server-side facts.
