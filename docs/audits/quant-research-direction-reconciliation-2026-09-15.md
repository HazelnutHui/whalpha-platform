# Quant Research Direction Reconciliation — 2026-09-15

## Objective

Reconcile the default project-recovery path, research architecture, Product
language, and website source with the accepted Factor Discovery -> Model
Construction -> Strategy Expression direction. Preserve valid historical
evidence while removing superseded fixed-strategy sequencing from current
authority.

## Pre-change review

- The repository contained 1,014 Markdown files.
- A broad text census returned 227 references to the original named strategy
  families, fixed Candidate channels, or Strong-Leader Pullback.
- Those references belonged to three different classes:
  1. current authority that required revision;
  2. current Production compatibility behavior that required an explicit
     Baseline V1 boundary; and
  3. historical ADRs, contracts, audits, and result evidence that must remain
     immutable and searchable.
- The first research program was already closed: V1 ended
  `inconclusive_evidence_floor`; the only registered replacement ended
  `rejected_endpoint_instability`; Validation and Holdout were not opened.
- One untracked draft Python factor-catalog contract existed without package
  exports or tests and contained an internally duplicated literal. It was not
  an implemented or published contract.

## Reconciliation performed

- Added ADR 0274 and the Quant Research Three-Layer Architecture V1 as the
  durable current authority.
- Rewrote the default documentation path—root/docs indexes, vision, scope,
  application architecture, Lab product specification, current status,
  current context, roadmap, framework, and app READMEs—to use the three layers.
- Reclassified fixed named setups as hypothesis territories or historical
  records, not a permanent model-development queue.
- Preserved the deployed Candidate score, Entry Geometry, and six Strategy
  Channels only as frozen, unvalidated Baseline V1 compatibility behavior.
- Kept all historical Pullback ADRs, contracts, audits, fingerprints, and
  failure results. Detailed dated execution narrative remains outside the
  compact default recovery path.
- Curated duplicate ADR index entries instead of adding another chronological
  catalog.
- Removed the incomplete untracked factor-contract draft. ADR 0273 and the
  Factor Catalog V1 document remain the definition authority until a complete,
  exported, tested implementation is built.
- Updated website source in English, Simplified Chinese, and Spanish to expose
  the current three-layer architecture, current outcome-blind Factor Catalog
  state, locked downstream layers, retained Pullback rejection, and frozen
  Candidate Baseline V1 boundary.

## Current truthful boundary

- Twelve factor definitions are registered as the first finite discovery
  batch. Factor values, coverage, redundancy, and outcomes have not been
  computed under the new architecture.
- No factor Alpha, model, strategy expression, Product ranking authority, or
  performance claim exists under the three-layer path.
- The next authorized research step is outcome-blind factor implementation and
  qualification. A separate frozen protocol is required before development
  outcomes may be read.
- AI research automation remains a governed future extension. It is not an
  active autonomous search, activation, trading, or execution system.
- This reconciliation changes repository documents and website presentation;
  it does not mutate canonical data, Validation, Holdout, model activation,
  market publications, daily scheduling, or broker/execution state.

## Slimming decision

No historical ADR, audit, or evidence artifact was deleted merely because its
direction was superseded. That history is required to reconstruct trial count,
decisions, and failed research. Slimming was applied to the default navigation
and recovery sources, with historical detail retained in its proper archive.

## Verification and deployment

Pre-deployment verification:

- all 126 frontend tests across 22 files passed;
- the production TypeScript/Vite build passed; the Quant Research Lab route is
  a lazy 44.96 kB JavaScript chunk (16.86 kB gzip) and the shared CSS is
  124.26 kB (21.27 kB gzip);
- 763 project Markdown files and 545 local links were checked with zero missing
  target;
- `git diff --check` passed; and
- no backend source, canonical data, Validation, Holdout, model activation, or
  market publication was changed.

Production release identity and postflight evidence are appended only after
the deployment completes.
