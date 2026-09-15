# Documentation Index

This is the short authority map. It intentionally does not enumerate every
ADR, audit, contract, or operational command.

## Recover current context

Read in this order:

1. [Repository instructions](../AGENTS.md)
2. [Project overview](../README.md)
3. [Authoritative current context](project/current-context.md)
4. [Current status](project/current-status.md)
5. [Roadmap](project/roadmap.md)

Then read only the documents tied to the selected objective:

- current context: volatile verified identities and infrastructure;
- current status: concise actual capability and limitations;
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
- [Outcome-blind Factor Catalog V1](data-contracts/quant-research-factor-catalog-v1.md)
- [Outcome-blind Factor Qualification V1 audit](audits/quant-research-factor-qualification-2026-09-15.md)
- [Factor Screening V1 contract](data-contracts/quant-research-factor-screening-v1.md)
- [Factor Screening V1 result audit](audits/quant-research-factor-screening-2026-09-15.md)
- [Cumulative Factor Discovery Trial Ledger V1](data-contracts/quant-research-discovery-trial-ledger-v1.md)
- [ADR 0277: cumulative factor trial accounting](decisions/0277-establish-cumulative-factor-discovery-trial-accounting.md)
- [Outcome-blind Factor Catalog V2](data-contracts/quant-research-factor-catalog-v2.md)
- [ADR 0278: register Factor Catalog V2 without outcomes](decisions/0278-register-factor-catalog-v2-without-outcomes.md)
- [Factor Catalog V2 qualification contract](data-contracts/quant-research-factor-qualification-v2.md)
- [ADR 0279: freeze V2 outcome-blind qualification](decisions/0279-freeze-factor-catalog-v2-outcome-blind-qualification.md)
- [ADR 0280: admit the private five-year split extension only for outcome-blind qualification](decisions/0280-admit-private-five-year-split-evidence-for-outcome-blind-factor-qualification.md)
- [Factor Catalog V2 qualification result audit](audits/quant-research-factor-qualification-v2-2026-09-15.md)
- [Factor Catalog V2 five-year split requalification audit](audits/quant-research-factor-qualification-v2-split-requalification-2026-09-15.md)
- [Factor Catalog V2 requalification UI deployment audit](audits/quant-research-v2-requalification-ui-deployment-2026-09-15.md)
- [Factor Screening V2 contract](data-contracts/quant-research-factor-screening-v2.md)
- [Cumulative Factor Discovery Trial Ledger V2](data-contracts/quant-research-discovery-trial-ledger-v2.md)
- [ADR 0281: frozen Factor Catalog V2 Development screen](decisions/0281-freeze-factor-catalog-v2-development-screening-protocol.md)
- [ADR 0282: separated V2 factor/control/label evidence sources](decisions/0282-separate-v2-factor-control-and-label-evidence-sources.md)
- [Factor Catalog V2 screen-registration UI deployment audit](audits/quant-research-v2-screen-registration-ui-deployment-2026-09-15.md)
- [Factor Screening V1 UI deployment audit](audits/quant-research-factor-screening-ui-deployment-2026-09-15.md)
- [Factor Qualification UI deployment audit](audits/quant-research-factor-qualification-ui-deployment-2026-09-15.md)
- [ADR 0276: frozen Development screening protocol](decisions/0276-freeze-factor-catalog-v1-development-screening-protocol.md)
- [ADR 0275: frozen factor-qualification protocol](decisions/0275-freeze-outcome-blind-factor-qualification-protocol.md)
- [ADR 0274: durable three-layer architecture](decisions/0274-adopt-factor-model-strategy-three-layer-research-architecture.md)
- [ADR 0273: first governed factor batch](decisions/0273-separate-governed-factor-discovery-from-strategy-construction.md)
- [ADR 0194: bounded AI-assisted research](decisions/0194-govern-ai-assisted-quant-research-as-a-bounded-factory.md)
- [Strong-Leader Pullback final rejection audit](audits/strong-leader-pullback-reconstructed-replacement-selection-2026-09-15.md)

The Pullback contracts, operations, and intermediate audits remain immutable
historical evidence, but are no longer part of default recovery. Use the
[data-contract index](data-contracts/README.md), [ADR index](decisions/README.md),
or dated [audits](audits/) when reproducing that program.

## Architecture and data

- [Application Architecture](architecture/application-architecture.md)
- [System Context](architecture/system-context.md)
- [Data Boundaries](architecture/data-boundaries.md)
- [Historical Research Data Foundation](architecture/historical-research-data-foundation-v1.md)
- [Canonical Market Data Query Boundary](architecture/canonical-market-data-query-boundary.md)
- [Instrument Identity Resolution](architecture/instrument-identity-resolution.md)
- [Classification Boundary](architecture/classification-boundary.md)
- [Dashboard Universe Activation](architecture/dashboard-universe-activation.md)
- [Provider Review Index](providers/README.md)

## Operations

- [Infrastructure](operations/infrastructure.md)
- [Daily EOD Automation](operations/daily-eod-automation.md)
- [Five-Year EOD and Identity Backfill](operations/five-year-eod-identity-backfill.md)
- [Quant Research Factor Screening](operations/quant-research-factor-screening.md)
- [Quant Research Factor Screening V2](operations/quant-research-factor-screening-v2.md)
- [Quant Research Factor Qualification V2](operations/quant-research-factor-qualification-v2.md)
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
