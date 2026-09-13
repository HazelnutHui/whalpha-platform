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
- [Candidate Strategy Research Statistics V1](data-contracts/candidate-strategy-research-statistics-v1.md):
  session-balanced inference and registered gates.
- [Candidate Strategy Holdout Custody V1](data-contracts/candidate-strategy-holdout-custody-v1.md):
  sealed single-use holdout boundary.
- [Strategy Research Readiness V1](data-contracts/strategy-research-readiness-v1.md):
  readiness without performance authority.

Pivotal research ADRs include
[0049](decisions/0049-separate-candidate-strategy-channels.md),
[0050](decisions/0050-seal-strategy-signals-before-forward-outcomes.md),
[0051](decisions/0051-require-point-in-time-historical-research-foundation.md),
[0097](decisions/0097-preregister-personal-strategy-research-before-backtesting.md),
[0104](decisions/0104-freeze-session-balanced-research-statistics.md),
[0109](decisions/0109-separate-research-readiness-from-development-authorization.md),
[0186](decisions/0186-seal-strong-leader-pullback-research-inputs.md),
[0191](decisions/0191-promote-validated-research-models-into-stock-candidates.md),
[0192](decisions/0192-publish-lab-model-records-without-candidate-authority.md),
[0193](decisions/0193-admit-latest-vintage-reconstruction-for-development-only.md),
[0194](decisions/0194-govern-ai-assisted-quant-research-as-a-bounded-factory.md),
[0195](decisions/0195-require-complete-session-cross-sections-for-reconstructed-development.md),
[0196](decisions/0196-build-a-five-year-point-in-time-research-foundation-on-dell.md),
[0197](decisions/0197-separate-reconstructed-research-membership-from-signal-eligible-membership.md),
[0198](decisions/0198-scale-corporate-action-custody-to-the-five-year-range.md),
[0199](decisions/0199-retain-complete-corporate-action-source-packages-privately.md),
and [0200](decisions/0200-retain-inactive-lifecycle-source-anchors-privately.md).
ADR [0216](decisions/0216-census-sec-fundamental-semantics-before-feature-registration.md)
requires a complete semantic/conflict census before any SEC fundamental
feature registry or security projection.
ADR [0201](decisions/0201-admit-bounded-quarantined-historical-identity-alias-collisions.md)
keeps later-vintage historical alias conflicts quarantined while allowing the
unrelated resolved cross-section to advance under a separate bounded profile.

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
- [Five-Year EOD/Identity Continuous Run](audits/five-year-eod-identity-continuous-run-2026-09-10.md)
- [Five-Year Corporate-Action Source Audit](audits/five-year-corporate-action-source-2026-09-10.md)
- [Five-Year Lifecycle Source Custody Audit](audits/five-year-lifecycle-source-custody-2026-09-10.md)
- [Five-Year FINRA OTC Daily List Source](audits/five-year-finra-otc-daily-list-source-2026-09-10.md)
- [Five-Year FINRA/Massive Action Census](audits/five-year-finra-massive-action-cross-source-census-2026-09-10.md)
- [SEC Company Facts and Filing-Time Evidence](audits/sec-companyfacts-payload-census-2026-09-10.md)
- [Retained FINRA/SEC Foundation Integration](audits/retained-finra-sec-foundation-integration-2026-09-12.md)
- [SEC Company Facts Semantic Census](audits/sec-companyfacts-semantic-census-2026-09-13.md)

Dell owns code, data, governance, and heavy computation. OCI receives only
separately approved bounded serving artifacts.

## Operations

- [Infrastructure](operations/infrastructure.md)
- [Storage Provisioning](operations/storage-provisioning.md)
- [Daily EOD Automation](operations/daily-eod-automation.md)
- [Massive Day Aggregates Flat File Ingestion](operations/massive-day-aggregates-flat-file-ingestion.md)
- [Five-Year EOD and Identity Backfill](operations/five-year-eod-identity-backfill.md)
- [Five-Year Corporate-Action Resolution](operations/five-year-corporate-action-resolution.md)
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
