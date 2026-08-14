# Documentation Index

This directory is the project knowledge base. It separates confirmed facts from proposals and deferred work.

## Product

- [Vision](product/vision.md): Product principles and UI language.
- [Scope](product/scope.md): Phase 1 scope, deferred work, and explicit non-goals.
- [Dashboard V1](product/dashboard-v1.md): Confirmed first dashboard structure and target behavior.
- [Initial EOD Universe](product/initial-eod-universe.md): Accepted V1 universe layers and Candidate Discovery thresholds.

## Architecture

- [System Context](architecture/system-context.md): Logical system flow and infrastructure responsibilities.
- [Application Architecture](architecture/application-architecture.md): Accepted target application architecture and runtime boundaries.
- [Classification Boundary](architecture/classification-boundary.md): Accepted Sector/Industry, Theme, and Analytical Group boundary.
- [Normalized Market Data Contracts](architecture/normalized-market-data-contracts.md): Accepted V1 logical market-data contract boundary.
- [Market Data Provider Boundary](architecture/market-data-provider-boundary.md): Implemented minimal synchronous provider Protocol, query models, capabilities, and errors.
- [Data Boundaries](architecture/data-boundaries.md): Market Data Provider boundary and data authorization rules.
- [Event Layer](architecture/event-layer.md): Lightweight event positioning and deferred long-term model.

## Data Contracts

- [Data Contracts Index](data-contracts/README.md)
- [Instrument Master V1](data-contracts/instrument-master-v1.md)
- [EOD Price Bar V1](data-contracts/eod-price-bar-v1.md)
- [Corporate Action V1](data-contracts/corporate-action-v1.md)
- [Classification V1](data-contracts/classification-v1.md)
- [Universe Membership V1](data-contracts/universe-membership-v1.md)

## Providers

- [Provider Evaluations](providers/README.md)
- [Massive Stocks Basic Evaluation](providers/massive-stocks-basic-evaluation.md): Accepted first private EOD development provider; adapter not implemented.

## Operations

- [Infrastructure](operations/infrastructure.md): Non-sensitive infrastructure facts.
- [Deployment Boundary](operations/deployment-boundary.md): Source-of-truth and deployment constraints.
- [Data Access Boundary](operations/data-access-boundary.md): Public placeholder, data-free demo, and private provider-backed dashboard boundary.
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

## Project

- [Current Status](project/current-status.md): Actual current project state.
- [Roadmap](project/roadmap.md): Proposed sequencing without date commitments.
- [Open Questions](project/open-questions.md): Decisions still required.
- [Changelog](project/changelog.md): Meaningful project-level changes.
