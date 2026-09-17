# Documentation Index

This is the short authority map. It intentionally does not enumerate every
ADR, audit, contract, or operational command.

## Recover current context

Read in this order:

1. [Repository instructions](../AGENTS.md)
2. [Project overview](../README.md)
3. [Authoritative current context](project/current-context.md)
4. [Current status](project/current-status.md)
5. [Current work control](project/current-work.md)
6. [Roadmap](project/roadmap.md)

Then read only the documents tied to the selected objective:

- current context: volatile verified identities and infrastructure;
- current status: concise actual capability and limitations;
- current work: the one active objective, current gate, routed reading, and
  completion checkpoint;
- roadmap: future sequencing, not authorization;
- ADRs: accepted material decisions and supersession;
- data contracts: exact interfaces and invariants;
- operations: procedures, not standing permission;
- audits: dated execution evidence; and
- changelog: milestone history.

## Product direction

- [Product Vision](product/vision.md)
- [Product Scope](product/scope.md)
- [Three-Layer Quant Research Architecture](product/quant-research-three-layer-architecture-v1.md)
- [Quant Research Lab](product/quant-research-lab-v1.md)
- [Opportunity Strategy Channels Baseline V1](product/opportunity-strategy-channels-v1.md)
- [Market Regime & Opportunities](product/market-regime-opportunity-map-v1.md)
- [Dashboard Universe Funnel](product/dashboard-universe-funnel.md)

Quant Research Lab owns factor, model, strategy-expression, evidence, and
lifecycle records. Stock Candidates may consume only separately activated
expressions under [ADR 0191](decisions/0191-promote-validated-research-models-into-stock-candidates.md)
and [ADR 0274](decisions/0274-adopt-factor-model-strategy-three-layer-research-architecture.md).

## Current quantitative-research path

Read this bounded set before new Lab research:

- [Professional Quantitative Research Action Framework](research/professional-quantitative-research-action-framework-v1.md)
- [Three-Layer Quant Research Architecture](product/quant-research-three-layer-architecture-v1.md)
- [Quant Research Lab product contract](product/quant-research-lab-v1.md)
- [Closed Factor Discovery Trial Ledger V5](data-contracts/quant-research-discovery-trial-ledger-v5.md)
- [Renewable Factor Discovery Cycle V1](data-contracts/quant-research-discovery-cycle-v1.md)
- [Current Factor Discovery Cycle State V2](data-contracts/quant-research-discovery-cycle-state-v2.md)
- [U.S. Factor-Space Diagnostic V1](data-contracts/quant-research-factor-space-diagnostic-v1.md)
- [U.S. Successor Hypothesis Registry V1](data-contracts/quant-research-successor-hypothesis-registry-v1.md)
- [U.S. Successor Source Qualification V1](data-contracts/quant-research-successor-source-qualification-v1.md)
- [Reusable Research Artifact Registry V2](data-contracts/quant-research-reusable-artifact-registry-v2.md)
- [Market-State Vector V1.1](data-contracts/quant-research-market-state-vector-v1.md)
- [Market-State Qualification V1](data-contracts/quant-research-market-state-qualification-v1.md)
- [Multi-Agent Governance V1](data-contracts/quant-research-multi-agent-governance-v1.md)
- [Campaign Three Hypothesis Registry V1](data-contracts/quant-research-campaign-three-hypothesis-registry-v1.md)
- [Campaign Three Input Qualification V1](data-contracts/quant-research-campaign-three-input-qualification-v1.md)
- [Campaign Three Screening Protocol V1](data-contracts/quant-research-campaign-three-screening-v1.md)
- [ADR 0274: durable three-layer architecture](decisions/0274-adopt-factor-model-strategy-three-layer-research-architecture.md)
- [ADR 0194: bounded AI-assisted research](decisions/0194-govern-ai-assisted-quant-research-as-a-bounded-factory.md)
- [ADR 0284: renewable bounded campaigns](decisions/0284-adopt-a-renewable-sequence-of-bounded-factor-campaigns.md)
- [ADR 0286: separate market-state inputs](decisions/0286-separate-point-in-time-market-state-inputs-before-campaign-three.md)
- [ADR 0287: stage-isolated multi-Agent pilot](decisions/0287-pilot-stage-isolated-multi-agent-research-governance.md)
- [ADR 0288: hardened market-state qualification](decisions/0288-harden-market-state-qualification-before-materialization.md)
- [ADR 0289: frozen Campaign Three hypothesis intake](decisions/0289-freeze-campaign-three-hypothesis-intake-before-input-qualification.md)
- [ADR 0290: frozen Campaign Three input qualification](decisions/0290-freeze-campaign-three-input-qualification-before-outcomes.md)
- [ADR 0291: Campaign Three screening protocol and Ledger V4](decisions/0291-freeze-campaign-three-screening-protocol-and-ledger-v4.md)
- [ADR 0292: Campaign Three evaluator and execution custody](decisions/0292-freeze-campaign-three-evaluator-and-execution-custody.md)
- [ADR 0293: close Campaign Three and append Ledger V5](decisions/0293-close-campaign-three-without-alpha-and-append-ledger-v5.md)
- [ADR 0295: freeze the successor factor-space diagnostic](decisions/0295-freeze-us-factor-space-diagnostic-before-successor-intake.md)
- [ADR 0296: freeze the U.S. successor hypothesis intake](decisions/0296-freeze-us-successor-hypothesis-intake-before-source-qualification.md)
- [ADR 0297: freeze the A-share full-population coverage diagnostic](decisions/0297-freeze-a-share-full-population-offline-coverage-diagnostic.md)
- [ADR 0298: close the U.S. successor intake at source qualification](decisions/0298-close-us-successor-intake-at-source-qualification.md)
- [Closed V2 screening result](audits/quant-research-factor-screening-v2-2026-09-15.md)
- [Qualified Campaign Three market-state input](audits/quant-research-market-state-qualification-2026-09-16.md)
- [Campaign Three outcome-blind input qualification](audits/quant-research-campaign-three-input-qualification-2026-09-16.md)
- [Closed Campaign Three Development screen](audits/quant-research-campaign-three-screening-2026-09-16.md)
- [Completed U.S. factor-space diagnostic](audits/quant-research-factor-space-diagnostic-2026-09-17.md)
- [Factor-space and A-share source UI deployment](audits/factor-space-and-a-share-source-ui-deployment-2026-09-17.md)
- [U.S. successor intake and A-share coverage gates](audits/us-successor-intake-and-a-share-coverage-gates-2026-09-17.md)

The Pullback contracts, operations, and intermediate audits remain immutable
historical evidence, but are no longer part of default recovery. Use the
[data-contract index](data-contracts/README.md), [ADR index](decisions/README.md),
or dated [audits](audits/) when reproducing that program.

## Internal research thinking

- [Quantitative Research Thinking Notebook / 量化研究思考簿](research/quantitative-research-thinking-notebook.md):
  non-authoritative human and quantitative-research ideas. Entries require
  explicit user review before they can change data acquisition, experiments,
  code, Product, publication, or deployment, and are never published to the
  website merely because they were recorded.

## Architecture and data

- [Application Architecture](architecture/application-architecture.md)
- [System Context](architecture/system-context.md)
- [Data Boundaries](architecture/data-boundaries.md)
- [Historical Research Data Foundation](architecture/historical-research-data-foundation-v1.md)
- [China A-Share Research Foundation V1](architecture/china-a-share-research-foundation-v1.md)
- [China A-Share Daily Research Contract V1](data-contracts/china-a-share-daily-research-foundation-v1.md)
- [China A-Share Pilot Market-Mechanics Audit](audits/china-a-share-market-mechanics-2026-09-17.md)
- [China A-Share Corporate-Action Reconciliation Audit](audits/china-a-share-corporate-action-reconciliation-2026-09-17.md)
- [China A-Share Stable Identity and Lifecycle Audit](audits/china-a-share-identity-lifecycle-2026-09-17.md)
- [China A-Share Daily Universe Audit](audits/china-a-share-daily-universe-2026-09-17.md)
- [China A-Share Five-Year Population Audit](audits/china-a-share-five-year-population-2026-09-17.md)
- [China A-Share Five-Year Source Expansion Completion](audits/china-a-share-five-year-source-expansion-completion-2026-09-17.md)
- [China A-Share Full-Population Coverage Diagnostic V1](data-contracts/china-a-share-full-population-coverage-v1.md)
- [China A-Share Five-Year Population Operation](operations/china-a-share-five-year-population.md)
- [China A-Share Five-Year Source Expansion Operation](operations/china-a-share-five-year-source-expansion.md)
- [China A-Share Foundation UI Deployment Audit](audits/china-a-share-foundation-ui-deployment-2026-09-17.md)
- [China A-Share Market Selector Deployment Audit](audits/china-a-share-market-selector-deployment-2026-09-17.md)
- [Canonical Market Data Query Boundary](architecture/canonical-market-data-query-boundary.md)
- [Instrument Identity Resolution](architecture/instrument-identity-resolution.md)
- [Classification Boundary](architecture/classification-boundary.md)
- [Dashboard Universe Activation](architecture/dashboard-universe-activation.md)
- [Provider Review Index](providers/README.md)

## Operations

- [Deployment and Public GitHub Boundary](operations/deployment-boundary.md)
- [Infrastructure](operations/infrastructure.md)
- [Daily EOD Automation](operations/daily-eod-automation.md)
- [Five-Year EOD and Identity Backfill](operations/five-year-eod-identity-backfill.md)
- [Quant Research Factor Screening](operations/quant-research-factor-screening.md)
- [Quant Research Factor Screening V2](operations/quant-research-factor-screening-v2.md)
- [Quant Research Factor Qualification V2](operations/quant-research-factor-qualification-v2.md)
- [Quant Research Market-State Qualification](operations/quant-research-market-state-qualification.md)
- [Campaign Three Input Qualification](operations/quant-research-campaign-three-input-qualification.md)
- [Campaign Three Development Screening](operations/quant-research-campaign-three-screening.md)
- [Market Intelligence Publication](operations/market-intelligence-publication.md)
- [Dashboard Snapshot Publication](operations/dashboard-snapshot-publication.md)
- [OCI Dashboard Deployment](operations/oci-private-dashboard-deployment.md)

Strategy-specific runbooks are historical or objective-specific and remain
discoverable in [`docs/operations`](operations/). A runbook never authorizes
credentials, provider access, canonical Apply, publication, deployment,
scheduler mutation, or cleanup by itself.

## Application

- [Backend](../apps/api/README.md)
- [Frontend](../apps/web/README.md)
- [API documentation](api/README.md)
- [Frontend documentation](frontend/README.md)
- [Local development](development/local-development.md)

## Historical evidence

- [Concise changelog](project/changelog.md)
- [2026-09-15 research-direction reconciliation](audits/quant-research-direction-reconciliation-2026-09-15.md)
- [Granular execution archive through 2026-09-14](audits/project-execution-archive-through-2026-09-14.md)
- [Open Questions](project/open-questions.md)
- [Dated audits](audits/)

Historical records preserve reproducibility but are not part of default
recovery. They never override a later accepted ADR or current verified state.
