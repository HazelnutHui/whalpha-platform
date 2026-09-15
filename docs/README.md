# Documentation Index

This is the short navigation map. It intentionally does not enumerate every
ADR, audit, contract, or operational command.

## Recover current context

Read in this order:

1. [Repository instructions](../AGENTS.md)
2. [Project overview](../README.md)
3. [Authoritative current context](project/current-context.md)
4. [Current status](project/current-status.md)
5. [Roadmap](project/roadmap.md)

Then read only the documents tied to the selected objective. Authority is
separated deliberately:

- current context: volatile verified identities and infrastructure;
- current status: concise actual capability and limitations;
- roadmap: future sequencing, not authorization;
- ADRs: accepted material decisions;
- data contracts: exact interfaces and invariants;
- operations: procedures, not standing permission;
- audits: dated execution evidence; and
- changelog: milestone history.

## Product direction

- [Product Vision](product/vision.md)
- [Product Scope](product/scope.md)
- [Quant Research Lab](product/quant-research-lab-v1.md)
- [Opportunity Strategy Channels Baseline V1](product/opportunity-strategy-channels-v1.md)
- [Market Regime & Opportunities](product/market-regime-opportunity-map-v1.md)
- [Dashboard Universe Funnel](product/dashboard-universe-funnel.md)

Quant Research Lab owns model evidence and lifecycle. Stock Candidates may
consume only separately validated and explicitly activated models under
[ADR 0191](decisions/0191-promote-validated-research-models-into-stock-candidates.md).

## First quantitative-research path

Read this bounded set before Strong-Leader Pullback or Lab work:

- [Professional Quantitative Research Action Framework](research/professional-quantitative-research-action-framework-v1.md)
- [Quant Research Lab product contract](product/quant-research-lab-v1.md)
- [First experiment preregistration](data-contracts/candidate-strategy-research-experiment-v1.md)
- [Canonical Strong-Leader Pullback method](data-contracts/strong-leader-pullback-method-v1.md)
- [Outcome-free research input](data-contracts/strong-leader-pullback-research-input-v1.md)
- [Outcome-blind method diagnostics](data-contracts/strong-leader-pullback-method-diagnostics-v1.md)
- [Method-engineering launch review](data-contracts/strong-leader-pullback-method-engineering-launch-review-v1.md)
- [Frozen source sample](data-contracts/strong-leader-pullback-source-acceptance-sample-v1.md)
- [Provider-neutral source result](data-contracts/strong-leader-pullback-source-acceptance-result-v1.md)
- [Current launch audit](audits/strong-leader-pullback-method-engineering-launch-review-2026-09-14.md)
- [Current diagnostics audit](audits/strong-leader-pullback-method-diagnostics-2026-09-14.md)
- [ADR 0194: bounded AI-assisted research](decisions/0194-govern-ai-assisted-quant-research-as-a-bounded-factory.md)
- [ADR 0195: complete reconstructed session cross-sections](decisions/0195-require-complete-session-cross-sections-for-reconstructed-development.md)
- [ADR 0196: five-year Dell foundation](decisions/0196-build-a-five-year-point-in-time-research-foundation-on-dell.md)
- [ADR 0266: method engineering versus performance admission](decisions/0266-separate-outcome-blind-method-engineering-from-performance-admission.md)
- [ADR 0267: provider-neutral evidence acceptance](decisions/0267-freeze-provider-neutral-performance-evidence-acceptance.md)

The complete registries remain available through the
[data-contract index](data-contracts/README.md) and
[ADR index](decisions/README.md).

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
- [Strong-Leader Pullback Method Launch Review](operations/strong-leader-pullback-method-engineering-launch-review.md)
- [Strong-Leader Pullback Method Diagnostics](operations/strong-leader-pullback-method-diagnostics.md)
- [Market Intelligence Publication](operations/market-intelligence-publication.md)
- [Dashboard Snapshot Publication](operations/dashboard-snapshot-publication.md)
- [OCI Dashboard Deployment](operations/oci-private-dashboard-deployment.md)

Other runbooks are discoverable in [`docs/operations`](operations/). They do
not authorize credentials, provider access, canonical Apply, publication,
deployment, scheduler mutation, or cleanup by themselves.

## Application

- [Backend](../apps/api/README.md)
- [Frontend](../apps/web/README.md)
- [API documentation](api/README.md)
- [Frontend documentation](frontend/README.md)
- [Local development](development/local-development.md)

## Historical evidence

- [Concise changelog](project/changelog.md)
- [Granular execution archive through 2026-09-14](audits/project-execution-archive-through-2026-09-14.md)
- [Open Questions](project/open-questions.md)
- [Dated audits](audits/)

Historical records preserve reproducibility but are not part of the default
recovery path. They never override a later accepted ADR or current verified
state.
