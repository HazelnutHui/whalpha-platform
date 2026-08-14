# Trading Intelligence Platform

Trading Intelligence Platform is a personal single-user prototype for U.S. equity market intelligence. It is designed to help the user understand market structure, sector and theme rotation, stock strength, breadth, options structure, relationship shifts, and significant market developments quickly enough to support discretionary research and trading decisions.

The platform should help answer:

- What is the market structure today?
- Which sectors and themes are strengthening or weakening?
- Is risk appetite expanding or contracting?
- Which stocks show genuine relative strength?
- What relationships or rotations deserve further investigation?
- What developments are significant enough for human review?

## Current Phase

Documentation, infrastructure, storage foundation, application stack decision, target architecture, minimal application scaffold, and local frontend/backend development toolchain are complete. Initial EOD universe boundaries, classification boundaries, and normalized EOD logical contracts are documented. Instrument Master V1 and EOD Price Bar V1 are implemented as provider-neutral Python/Pydantic contracts with validation tests. A minimal synchronous MarketDataProvider boundary is implemented with deterministic in-memory contract tests. Massive Stocks Basic is accepted as the first private EOD development provider. Its secure credential-file loader, standard-library HTTPS transport, and mocked adapter skeleton are implemented. A single read-only Stocks reference smoke test has verified authentication and reference entitlement. The first bounded mocked-fixture EOD ingestion slice validates canonical EOD Price Bars and writes deterministic temporary Parquet partitions with manifests in tests. One controlled Massive Grouped Daily inspection for 2026-08-13 verified access and payload structure, but production publication is blocked pending Instrument Master identity coverage. No production `/data` write, database, deployment pipeline, production application, or public real-data authorization has been created for the new project.

## Application Entry Points

- Backend scaffold: [apps/api](apps/api/README.md)
- Frontend scaffold: [apps/web](apps/web/README.md)
- Local development guide: [docs/development/local-development.md](docs/development/local-development.md)

## Accepted Application Stack

- Frontend: React, TypeScript, Vite, Apache ECharts, and lightweight CSS.
- Backend/API boundary: Python 3.12, FastAPI, and Pydantic.
- Analytics: Pandas and NumPy.
- Initial storage path: EOD-first Parquet datasets under `/data/trading-intelligence-platform`.
- Data access: MarketDataProvider / adapter boundary before domain calculations.
- Initial EOD data foundation: accepted universe, classification, and normalized logical contract boundaries.
- Implemented data contracts: Instrument Master V1 and EOD Price Bar V1 Python/Pydantic models.
- Implemented provider boundary: synchronous MarketDataProvider Protocol, query models, capabilities, and errors.
- First EOD development provider: Massive Stocks Basic for private, personal EOD development only; secure credential loader, HTTPS transport, and one-request reference smoke test verified.
- Initial persistence: mocked-fixture one-session EOD Price Bar V1 Parquet writer with manifest, deterministic fingerprint, idempotency, and conflict checks.
- Access boundary: provider-backed data and derived analytics must not be publicly exposed without an accepted authorization and access-control gate.

See [ADR 0005](docs/decisions/0005-application-technology-stack.md) and [Application Architecture](docs/architecture/application-architecture.md) for the authoritative decision details.

## Phase 1 Success Criteria

Phase 1 succeeds when the project delivers a usable Market Dashboard MVP that can show:

- Market Structure Summary
- Market Risk Regime
- Standard Market Heatmap / Treemap
- Market Breadth
- Index & Style Strength
- Sector / Theme Rotation
- Dynamic Relationship & Rotation Monitor
- Key Market Developments

## Core Modules

- Market Structure
- Sector / Theme Rotation
- Stock Strength
- Market Breadth
- Options Structure
- Dynamic Relationship & Rotation Monitor
- Lightweight Event Layer

## Explicitly Not Doing Now

- Automated trading
- Order execution
- HFT
- Complex ML or deep learning
- Large microservice systems
- Kubernetes
- Large Event Knowledge Base

## Public and Data-Licensing Boundary

This project is a personal single-user prototype. It may be reachable over the public internet, but it is not currently a commercial market-data redistribution product. Public access and data licensing must be reassessed before broader promotion or commercial use.

## Documentation Entry Points

- [Agent instructions](AGENTS.md)
- [Documentation index](docs/README.md)
- [Current status](docs/project/current-status.md)
- [Dashboard V1](docs/product/dashboard-v1.md)
- [Application architecture](docs/architecture/application-architecture.md)
- [Initial EOD Universe](docs/product/initial-eod-universe.md)
- [Classification Boundary](docs/architecture/classification-boundary.md)
- [Normalized Market Data Contracts](docs/architecture/normalized-market-data-contracts.md)
- [Market Data Provider Boundary](docs/architecture/market-data-provider-boundary.md)
- [Massive Stocks Basic Evaluation](docs/providers/massive-stocks-basic-evaluation.md)
- [Massive Adapter Boundary](docs/providers/massive-adapter-boundary.md)
- [Massive Credential Provisioning](docs/operations/massive-credential-provisioning.md)
- [Massive Grouped Daily Inspection](docs/operations/massive-grouped-daily-inspection.md)
- [EOD Parquet Persistence](docs/architecture/eod-parquet-persistence.md)
- [Data Access Boundary](docs/operations/data-access-boundary.md)
- [Data Contracts](docs/data-contracts/README.md)
- [System context](docs/architecture/system-context.md)
- [Deployment boundary](docs/operations/deployment-boundary.md)
- [Architecture decisions](docs/decisions/README.md)
