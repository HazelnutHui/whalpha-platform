# Documentation Index

This page is the short navigation map. It intentionally does not repeat every
ADR, audit, contract, release, or historical execution step.

## Recover current context

Read in this order:

1. [Repository instructions](../AGENTS.md)
2. [Project overview](../README.md)
3. [Authoritative current context](project/current-context.md)
4. [Current status](project/current-status.md)
5. [Roadmap](project/roadmap.md)

Then read only the product, architecture, contract, operations, ADR, and audit
documents related to the selected objective.

Authority is separated deliberately:

- volatile verified identities and infrastructure: current context;
- concise actual state and limitations: current status;
- proposed sequencing: roadmap;
- accepted material decisions: ADRs;
- exact interfaces and invariants: data contracts;
- operational procedure: operations;
- dated execution evidence: audits;
- completed project-level change history: changelog.

Do not copy a dated release, count, or next-step claim from a historical ADR or
audit into current work.

## Product direction

- [Product Vision](product/vision.md): decision chain and durable product role.
- [Product Scope](product/scope.md): current, active, later, and excluded scope.
- [Quant Research Lab](product/quant-research-lab-v1.md): model registry,
  transparency, bounded AI-assisted research, evaluation, lifecycle, metrics,
  and Candidate promotion.
- [Opportunity Strategy Channels V1](product/opportunity-strategy-channels-v1.md):
  deployed, frozen, unvalidated Baseline V1 mechanics.
- [Market Regime & Opportunities V1](product/market-regime-opportunity-map-v1.md):
  current market/regime and relationship product contract.
- [Dashboard Universe Funnel](product/dashboard-universe-funnel.md): Universe
  interpretation and eligibility boundaries.
- [Dashboard V1](product/dashboard-v1.md): historical original design, not
  current roadmap authority.

The key future product decision is
[ADR 0191](decisions/0191-promote-validated-research-models-into-stock-candidates.md):
Quant Research Lab validates models; only separately activated models drive
Stock Candidates.

## Quantitative research

- [Professional Quantitative Research Action Framework V1](research/professional-quantitative-research-action-framework-v1.md):
  standalone end-to-end research method.
- [Historical Research Data Foundation V1](architecture/historical-research-data-foundation-v1.md):
  point-in-time data and readiness requirements.
- [Five-Year Research Foundation Census V1](data-contracts/five-year-research-foundation-census-v1.md):
  exact rolling target and family-by-family coverage diagnostic.
- [SEC Company Facts Semantic Census V1](data-contracts/sec-companyfacts-semantic-census-v1.md):
  source-level concept, unit, duplicate, conflict, and revision coverage before
  fundamental feature registration.
- [SEC Fundamental Query Registry V1](data-contracts/sec-fundamental-query-registry-v1.md)
  and [Readiness Census V1](data-contracts/sec-fundamental-query-readiness-census-v1.md):
  exact first issuer-query semantics and complete source-readiness accounting.
- [Candidate Strategy Evaluation V1](data-contracts/candidate-strategy-evaluation-v1.md):
  signals, labels, chronology, and stock-outcome boundary.
- [Candidate Strategy Research Experiment V1](data-contracts/candidate-strategy-research-experiment-v1.md):
  frozen first preregistration.
- [Quant Research Lab Model Record V1](data-contracts/quant-research-lab-model-record-v1.md):
  transparent model registry, result semantics, and Candidate activation
  boundary.
- [Strong-Leader Pullback Research Input V1](data-contracts/strong-leader-pullback-research-input-v1.md):
  outcome-free input semantics.
- [Strong-Leader Pullback Development Coverage Census V1](data-contracts/strong-leader-pullback-development-coverage-census-v1.md):
  fixed latest-vintage, outcome-blind development-admission census.
- [Strong-Leader Pullback Development Admission Decision V1](data-contracts/strong-leader-pullback-development-admission-decision-v1.md):
  complete-session missingness rule and current evidence rejection.
- [Strong-Leader Pullback SEC Document Source V1](data-contracts/strong-leader-pullback-sec-document-source-v1.md):
  exact resumable private custody for the frozen 219-document plan.
- [Strong-Leader Pullback SEC Document Content Census V1](data-contracts/strong-leader-pullback-sec-document-content-census-v1.md):
  deterministic parse and lexical candidate localization without fact
  promotion.
- [Candidate Strategy Research Statistics V1](data-contracts/candidate-strategy-research-statistics-v1.md):
  session-balanced inference and registered gates.
- [Candidate Strategy Holdout Custody V1](data-contracts/candidate-strategy-holdout-custody-v1.md):
  sealed single-use holdout boundary.
- [Strategy Research Readiness V1](data-contracts/strategy-research-readiness-v1.md):
  readiness without performance authority.

The current governing sequence is anchored by
[ADR 0191](decisions/0191-promote-validated-research-models-into-stock-candidates.md)
for model promotion,
[ADR 0194](decisions/0194-govern-ai-assisted-quant-research-as-a-bounded-factory.md)
for bounded AI research,
[ADR 0196](decisions/0196-build-a-five-year-point-in-time-research-foundation-on-dell.md)
for the Dell data program, and
[ADR 0224](decisions/0224-gate-sec-facts-by-security-projection-class-and-evidence-tier.md)
for SEC security projection, and
[ADR 0227](decisions/0227-localize-collision-derived-join-failures-only-in-research-membership.md)
for collision-localized research Membership, and
[ADR 0228](decisions/0228-use-sec-submissions-as-a-lifecycle-document-locator-not-a-terminal-fact.md)
for bounded SEC lifecycle-document discovery, and
[ADR 0230](decisions/0230-retain-transition-period-sec-primary-documents-in-resumable-private-custody.md)
for resumable private source custody of the frozen documents. Use the
[ADR index](decisions/README.md) to trace
the detailed dependency and supersession chain.

## Architecture and data

- [Application Architecture](architecture/application-architecture.md)
- [System Context](architecture/system-context.md)
- [Data Boundaries](architecture/data-boundaries.md)
- [Canonical Market Data Query Boundary](architecture/canonical-market-data-query-boundary.md)
- [Market Data Provider Boundary](architecture/market-data-provider-boundary.md)
- [Classification Boundary](architecture/classification-boundary.md)
- [Instrument Identity Resolution](architecture/instrument-identity-resolution.md)
- [Dashboard Universe Activation](architecture/dashboard-universe-activation.md)
- [Private Dashboard Publication](architecture/private-dashboard-publication.md)
- [Data Contract Index](data-contracts/README.md)
- [Provider Review Index](providers/README.md)
- [Five-Year Foundation Baseline](audits/five-year-research-foundation-baseline-2026-09-10.md)
- [Five-Year Research Membership Continuation](audits/five-year-research-membership-continuation-2026-09-13.md)
- [Five-Year Research Membership Collision Recovery](audits/five-year-research-membership-collision-recovery-2026-09-13.md)
- [First-Strategy Source Acceptance Sample](audits/strong-leader-pullback-source-acceptance-sample-2026-09-13.md)
- [First-Strategy SEC Lifecycle Pilot](audits/strong-leader-pullback-sec-lifecycle-pilot-2026-09-13.md)
- [First-Strategy SEC Document Plan](audits/strong-leader-pullback-sec-document-plan-2026-09-13.md)
- [First-Strategy SEC Document Source](audits/strong-leader-pullback-sec-document-source-2026-09-13.md)
- [SEC Company Facts Semantic Census](audits/sec-companyfacts-semantic-census-2026-09-13.md)
- [SEC Fundamental Query Readiness Census](audits/sec-fundamental-query-readiness-census-2026-09-13.md)
- [SEC Fundamental Projection Readiness Census](audits/sec-fundamental-projection-readiness-census-2026-09-13.md)
- [Five-Year SEC Filer-to-Security Link Candidate](audits/five-year-sec-filer-security-link-candidate-2026-09-13.md)
- [SEC Filer/Security Projection Readiness](audits/sec-filer-security-projection-readiness-2026-09-13.md)

Other dated runs remain discoverable in [`docs/audits`](audits/). They are
evidence, not part of the default recovery path.

Dell owns code, data, governance, and heavy computation. OCI receives only
separately approved bounded serving artifacts.

## Operations

- [Infrastructure](operations/infrastructure.md)
- [Storage Provisioning](operations/storage-provisioning.md)
- [Daily EOD Automation](operations/daily-eod-automation.md)
- [Massive Day Aggregates Flat File Ingestion](operations/massive-day-aggregates-flat-file-ingestion.md)
- [Five-Year EOD and Identity Backfill](operations/five-year-eod-identity-backfill.md)
- [Five-Year Corporate-Action Resolution](operations/five-year-corporate-action-resolution.md)
- [Five-Year Corporate-Action Unresolved Census](operations/five-year-corporate-action-unresolved-census.md)
- [Five-Year Corporate-Action Residual Evidence Census](operations/five-year-corporate-action-residual-evidence-census.md)
- [Strong-Leader Pullback Evidence Blocker Census](operations/strong-leader-pullback-evidence-blocker-census.md)
- [Strong-Leader Pullback Source Acceptance Sample](operations/strong-leader-pullback-source-acceptance-sample.md)
- [Strong-Leader Pullback SEC Lifecycle Pilot](operations/strong-leader-pullback-sec-lifecycle-pilot.md)
- [Strong-Leader Pullback SEC Document Plan](operations/strong-leader-pullback-sec-document-plan.md)
- [Strong-Leader Pullback SEC Document Source Custody](operations/strong-leader-pullback-sec-document-source.md)
- [Strong-Leader Pullback SEC Document Content Census](operations/strong-leader-pullback-sec-document-content-census.md)
- [Bounded Identity Extension Family Evidence](operations/bounded-identity-extension-family-evidence.md)
- [Reconciled EOD Edition](operations/reconciled-eod-edition.md)
- [Reconciled EOD Source Reacquisition](operations/reconciled-eod-source-reacquisition.md)
- [FINRA OTC Daily List Source Custody](operations/finra-otc-daily-list-source-custody.md)
- [SEC Company Facts Source Custody](operations/sec-companyfacts-source-custody.md)
- [SEC Company Facts Normalization](operations/sec-companyfacts-normalization.md)
- [SEC Submissions Source Custody](operations/sec-submissions-source-custody.md)
- [SEC Filing-Clock Ledger](operations/sec-filing-clock-ledger.md)
- [SEC Filer-to-Security Link Decisions](operations/sec-filer-security-link-decisions.md)
- [SEC Point-in-Time Fundamental Census](operations/sec-point-in-time-fundamental-census.md)
- [Research Universe Membership Custody](operations/research-universe-membership-custody.md)
- [Market Intelligence Publication](operations/market-intelligence-publication.md)
- [Dashboard Snapshot Publication](operations/dashboard-snapshot-publication.md)
- [OCI Private Dashboard Deployment](operations/oci-private-dashboard-deployment.md)

Operational instructions do not authorize credentials, provider requests,
canonical Apply, publication, deployment, scheduler mutation, or cleanup by
themselves.

## Application

- [Backend](../apps/api/README.md)
- [Frontend](../apps/web/README.md)
- [API documentation](api/README.md)
- [Frontend documentation](frontend/README.md)
- [Local development](development/local-development.md)

## Historical evidence

- [ADR index](decisions/README.md): accepted decisions and supersession scope.
- [Changelog](project/changelog.md): meaningful completed changes.
- [Open Questions](project/open-questions.md): unresolved decisions only.
- [Audits](audits/): dated execution and verification evidence.
- [Candidate Pipeline Performance](operations/candidate-pipeline-performance.md):
  retained Baseline V1 optimization and measurement history; not an active
  model-research plan.

Historical records are retained for reproducibility. They are not part of the
default recovery path and must not override a later accepted decision or the
current verified state.
