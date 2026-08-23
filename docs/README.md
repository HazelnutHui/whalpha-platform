# Documentation Index

- [Dashboard Snapshot V2 data contract](data-contracts/dashboard-snapshot-v2.md)
- [Dashboard Universe Funnel](product/dashboard-universe-funnel.md)
- [Dashboard Snapshot V2 operations](operations/dashboard-snapshot-publication.md)

## Security Type Governance

- [Security Classification V1](data-contracts/security-classification-v1.md)
- [ADR 0015](decisions/0015-govern-security-types-and-universe-eligibility.md)
- [2026-08-14 classification audit](audits/security-type-classification-2026-08-14.md)
- [Provider security-type evidence architecture](architecture/provider-security-type-evidence.md)
- [SEC issuer-structure evidence architecture](architecture/sec-issuer-structure-evidence.md)
- [SEC User-Agent provisioning](operations/sec-user-agent-provisioning.md)
- [SEC issuer-structure evidence operation](operations/sec-issuer-structure-evidence.md)
- [SEC Phase B2B 2026-08-14 audit](audits/sec-issuer-structure-evidence-2026-08-14.md)
- [Massive security-type evidence operation](operations/massive-security-type-evidence.md)
- [2026-08-14 provider-evidence audit](audits/security-type-provider-evidence-2026-08-14.md)

This directory is the project knowledge base. It separates confirmed facts from proposals and deferred work.

## Product

- [Vision](product/vision.md): Product principles and UI language.
- [Scope](product/scope.md): Phase 1 scope, deferred work, and explicit non-goals.
- [Dashboard V1](product/dashboard-v1.md): Confirmed first dashboard structure and target behavior.
- [Dashboard Universe V1](product/dashboard-universe-v1.md): Dashboard V1.1 operating-equity universe, ETF benchmark, and Trading Activity Map boundary.
- [Dashboard Universe Activation V1](data-contracts/dashboard-universe-activation-v1.md): Completed selectable-Universe policy and publication contract.
- [Dashboard Universe Activation V2](data-contracts/dashboard-universe-activation-v2.md): Immutable revision, atomic active pointer, V1 compatibility, and separate rollback contract.
- [Initial EOD Universe](product/initial-eod-universe.md): Accepted V1 universe layers and Candidate Discovery thresholds.

## Architecture

- [System Context](architecture/system-context.md): Logical system flow and infrastructure responsibilities.
- [Application Architecture](architecture/application-architecture.md): Accepted target application architecture and runtime boundaries.
- [Private Dashboard Publication](architecture/private-dashboard-publication.md): Static private dashboard snapshot and OCI bundle architecture.
- [Market Session Calendar and Freshness](architecture/market-session-calendar.md): Offline XNYS session completion and Dashboard freshness boundary.
- [Classification Boundary](architecture/classification-boundary.md): Accepted Sector/Industry, Theme, and Analytical Group boundary.
- [Normalized Market Data Contracts](architecture/normalized-market-data-contracts.md): Accepted V1 logical market-data contract boundary.
- [Market Data Provider Boundary](architecture/market-data-provider-boundary.md): Implemented minimal synchronous provider Protocol, query models, capabilities, and errors.
- [EOD Parquet Persistence](architecture/eod-parquet-persistence.md): Implemented EOD Price Bar Parquet persistence boundary and first published canonical EOD session.
- [Trailing Liquidity Shadow Publication](architecture/trailing-liquidity-shadow-publication.md): Versioned offline metric/decision Parquet publication with a final logical completion marker.
- [Full-Base Trailing Liquidity Scope Review V1](data-contracts/trailing-liquidity-full-base-scope-review-v1.md): Complete provider-evidence base, decision ledger, funnel, set diff, and shadow publication contract.
- [Universe Pre-Activation Review](architecture/universe-pre-activation-review.md): Reviewed stable-ID override overlay and atomic shadow review publication.
- [Dashboard Universe Activation](architecture/dashboard-universe-activation.md): Formal reader, analytics, snapshot, and selector boundary.
- [Canonical Market Data Query Boundary](architecture/canonical-market-data-query-boundary.md): Implemented read repository, query service, and default-disabled private API boundary.
- [EOD Return Analytics](architecture/eod-return-analytics.md): Close-to-close returns, Market Summary V1, movers, and Liquidity Map V1 semantics.
- [Instrument Identity Resolution](architecture/instrument-identity-resolution.md): Deterministic provider identity mapping and current Instrument Master snapshot gate result.
- [Data Boundaries](architecture/data-boundaries.md): Market Data Provider boundary and data authorization rules.
- [Event Layer](architecture/event-layer.md): Lightweight event positioning and deferred long-term model.

## Data Contracts

- [Data Contracts Index](data-contracts/README.md)
- [Instrument Master V1](data-contracts/instrument-master-v1.md)
- [EOD Price Bar V1](data-contracts/eod-price-bar-v1.md)
- [Corporate Action V1](data-contracts/corporate-action-v1.md)
- [Classification V1](data-contracts/classification-v1.md)
- [Universe Membership V1](data-contracts/universe-membership-v1.md)
- [Provider Instrument Identity V1](data-contracts/provider-instrument-identity-v1.md)
- [Provider Ticker Resolver V1](data-contracts/provider-ticker-resolver-v1.md)
- [Trailing Liquidity Shadow Publication V1](data-contracts/trailing-liquidity-shadow-v1.md)
- [Reviewed Eligibility Override V1](data-contracts/reviewed-eligibility-override-v1.md)
- [Dashboard Universe Activation V1](data-contracts/dashboard-universe-activation-v1.md)

## Providers

- [Provider Evaluations](providers/README.md)
- [Massive Stocks Basic Evaluation](providers/massive-stocks-basic-evaluation.md): Accepted first private EOD development provider.
- [Massive Adapter Boundary](providers/massive-adapter-boundary.md): Configuration, credential, transport, smoke-test, and mapping boundary.

## API

- [API Index](api/README.md)
- [Private EOD Market Data V1](api/private-eod-market-data-v1.md): Default-disabled private canonical EOD query responses.
- [Private Market Summary V1](api/private-market-summary-v1.md): Private Market Summary, movers, returns, Dashboard Overview V1.1, and Trading Activity Map response contracts.

## Frontend

- [Frontend Index](frontend/README.md)
- [Market Dashboard V1](frontend/market-dashboard-v1.md): Local React dashboard for private Market Summary, Movers, Liquidity Map, and data-quality views.

## Operations

- [Infrastructure](operations/infrastructure.md): Non-sensitive infrastructure facts.
- [Deployment Boundary](operations/deployment-boundary.md): Source-of-truth and deployment constraints.
- [OCI Private Dashboard Deployment](operations/oci-private-dashboard-deployment.md): Private static Dashboard deployment status and operations boundary.
- [Private Dashboard Access](operations/private-dashboard-access.md): Basic Auth credential boundary and manual verification runbook.
- [Dashboard Universe Activation](operations/dashboard-universe-activation.md): Dry-run, one-apply, verification, and rollback boundary.
- [2026-08-19 Dashboard Universe Activation Audit](audits/dashboard-universe-activation-2026-08-19.md): Completed two-Universe publication and integrity evidence.
- [2026-08-20 Selectable Universe Deployment Audit](audits/selectable-universe-dashboard-deployment-2026-08-20.md): Snapshot, bundle, OCI, and unauthenticated protection evidence.
- [Data Access Boundary](operations/data-access-boundary.md): Public placeholder, data-free demo, and private provider-backed dashboard boundary.
- [Massive Credential Provisioning](operations/massive-credential-provisioning.md): Secure credential file and one-request smoke-test operations record.
- [Massive Grouped Daily Inspection](operations/massive-grouped-daily-inspection.md): One-request Grouped Daily inspection record for 2026-08-13.
- [Massive Grouped Daily Ingestion](operations/massive-grouped-daily-ingestion.md): Grouped Daily publication attempts and quality-gate results for 2026-08-13.
- [Massive Instrument Master Ingestion](operations/massive-instrument-master-ingestion.md): Bounded All Tickers snapshot ingestion record and quality-gate result.
- [2026-08-14 Instrument Snapshot Audit](operations/data-audits/2026-08-14-instrument-snapshot-audit.md): Accepted integrity audit with an explicit provenance exception.
- [2026-08-14 Grouped Daily Run Report](operations/data-audits/2026-08-14-grouped-daily-run.md): Non-sensitive single-request quality and publication record.
- [Storage Provisioning](operations/storage-provisioning.md): Completed workstation storage implementation record and historical procedure.
- [Node Toolchain Provisioning](operations/node-toolchain-provisioning.md): Completed Node.js 24 LTS system toolchain record and historical procedure.

## Development

- [Local Development](development/local-development.md): Project-local backend and frontend setup, run, and verification instructions.

## Decisions

- [ADR Index](decisions/README.md)
- [ADR 0001: Workstation Source of Truth](decisions/0001-workstation-source-of-truth.md)
- [ADR 0002: Separate Compute and Public Web Serving](decisions/0002-separate-compute-and-web-serving.md)
- [ADR 0003: Market Data Provider Boundary](decisions/0003-market-data-provider-boundary.md)
- [ADR 0004: Lightweight Event Layer First](decisions/0004-lightweight-event-layer-first.md)
- [ADR 0005: Application Technology Stack](decisions/0005-application-technology-stack.md)
- [ADR 0006: Initial EOD Data Model and Universe Boundaries](decisions/0006-initial-eod-data-model-and-universe-boundaries.md)
- [ADR 0007: Use Massive for Private EOD Development](decisions/0007-use-massive-for-private-eod-development.md)
- [ADR 0008: Use Partitioned Parquet for Initial Canonical EOD Persistence](decisions/0008-use-partitioned-parquet-for-initial-canonical-eod-persistence.md)
- [ADR 0009: Use Stable Provider Identifiers for Canonical Instrument Identity](decisions/0009-use-stable-provider-identifiers-for-canonical-instrument-identity.md)
- [ADR 0010: Represent Aggregate Volume as Decimal](decisions/0010-represent-aggregate-volume-as-decimal.md)
- [ADR 0011: Publish Private Dashboard Snapshots as Authenticated Static Assets](decisions/0011-publish-private-dashboard-snapshots-as-authenticated-static-assets.md)
- [ADR 0014: Use an Exchange Calendar for EOD Freshness](decisions/0014-use-an-exchange-calendar-for-eod-freshness.md)
- [ADR 0012: Use Server-Side Sessions for the Private Dashboard](decisions/0012-use-server-side-sessions-for-private-dashboard.md)
- [ADR 0013: Establish Dashboard Universe V1 for Market Overview](decisions/0013-establish-dashboard-universe-v1.md)
- [ADR 0015: Govern Security Types and Universe Eligibility](decisions/0015-govern-security-types-and-universe-eligibility.md)
- [ADR 0016: Publish Versioned Trailing Liquidity Shadow Results](decisions/0016-publish-versioned-trailing-liquidity-shadow-results.md)

## Project

- [Current Status](project/current-status.md): Actual current project state.
- [Roadmap](project/roadmap.md): Proposed sequencing without date commitments.
- [Open Questions](project/open-questions.md): Decisions still required.
- [Changelog](project/changelog.md): Meaningful project-level changes.

## Universe Shadow Audits

- [Provider-Classified Common Shares V1](product/provider-classified-common-shares-v1.md): Non-production CS-only and CS+ADRC definitions.
- [2026-08-14 Provider-Classified Audit](audits/provider-classified-common-shares-2026-08-14.md): Validated inputs, type distributions, funnels, Legacy comparison, edge records, and hard gates.
- [EOD Historical Window](architecture/eod-historical-window.md): Bounded multi-session reads and point-in-time identity rules.
- [20-Session Median Dollar-Volume Proxy](product/20-session-trailing-liquidity.md): Exact Decimal methodology and readiness semantics.
- [EOD History Backfill Plan](operations/eod-history-backfill-plan.md): Planning-only same-day identity and request/batch boundary.
- [Trailing Liquidity Shadow Publication Runbook](operations/trailing-liquidity-shadow-publication.md): Offline dry-run/apply, atomic publication, and postflight boundary.
- [Universe Pre-Activation Review Runbook](operations/universe-pre-activation-review.md): Offline stable-ID comparison and reviewed-override shadow publication.
- [2026-08-14 Trailing-Liquidity Readiness Audit](audits/trailing-liquidity-readiness-2026-08-14.md): Current two-session coverage and 18-session gap.
- [2026-08-19 Trailing-Liquidity Shadow Publication Audit](audits/trailing-liquidity-shadow-publication-2026-08-19.md): Production derived artifacts, A/B reconciliation, gap evidence, hashes, and safety postflight.
- [2026-08-19 Full-Base Scope Review Audit](audits/trailing-liquidity-full-base-scope-review-2026-08-19.md): V1 reproduction, corrected full-base funnels, set differences, analytics, hashes, and production-isolation evidence.
- [2026-08-19 Universe Pre-Activation Review Audit](audits/universe-pre-activation-review-2026-08-19.md): Stable-ID Legacy/A/B comparison, reviewed overrides, final shadow proposals, publication hashes, and safety postflight.
