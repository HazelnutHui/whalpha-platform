# Trading Intelligence Platform

## Security Type Governance Phase A

The repository includes a provider-neutral, effective-dated Security Classification V1 boundary. Classification fact, evidence quality, and candidate-universe eligibility are separate. Unknown, ambiguous, malformed, heuristic-only, and insufficient-evidence records are quarantined. The [2026-08-14 read-only audit](docs/audits/security-type-classification-2026-08-14.md) found that the binary Instrument Master cannot reliably resolve most non-ETF records, so production Dashboard membership remains unchanged pending a Core-versus-Broad policy decision and stronger evidence.

Phase B1 accepts Core as the future default and Broad as the future secondary view. Provider security-type evidence persistence and provisional Dashboard disclosure are implemented, but the first bounded live evidence attempt failed ambiguity/business-key gates and published nothing. Production remains unchanged. See the [attempt audit](docs/audits/security-type-provider-evidence-2026-08-14.md).

Trading Intelligence Platform is a personal single-user prototype for U.S. equity market intelligence. It is designed to help the user understand market structure, sector and theme rotation, stock strength, breadth, options structure, relationship shifts, and significant market developments quickly enough to support discretionary research and trading decisions.

The platform should help answer:

- What is the market structure today?
- Which sectors and themes are strengthening or weakening?
- Is risk appetite expanding or contracting?
- Which stocks show genuine relative strength?
- What relationships or rotations deserve further investigation?
- What developments are significant enough for human review?

## Current Phase

Documentation, infrastructure, storage foundation, application stack, canonical EOD contracts, point-in-time identity, private analytics, Dashboard, and authenticated static deployment boundaries are implemented. Completed canonical EOD sessions now cover 2026-08-12 through 2026-08-14. The 2026-08-14 identity snapshot is accepted with a provenance exception after a full content-integrity audit, and its one authorized Grouped Daily request published 9,912 verified canonical bars. An offline XNYS calendar reports the deployed 2026-08-14 Dashboard snapshot as fresh with session lag zero. Server-side sessions protect `/dashboard/` and `/private-data/`; `/` is the branded login entry and `/login/` is a compatibility redirect. No public real-data authorization, database, automated daily ingestion, or general production API deployment has been created.

## Application Entry Points

- Backend scaffold: [apps/api](apps/api/README.md)
- Frontend dashboard: [apps/web](apps/web/README.md)
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
- Initial persistence: EOD Price Bar V1 Parquet writer with manifest, deterministic fingerprint, idempotency, and conflict checks; the first real 2026-08-13 canonical EOD session is published under the approved project data root.
- Initial private read API: default-disabled canonical EOD query routes can list completed sessions, summarize completed sessions, and return paginated joined bars with Decimal values serialized as strings.
- Initial market summary analytics: the latest completed pair, 2026-08-13 and 2026-08-14, supports close-to-close returns, Market Summary V1, liquidity-screened movers, and Trading Activity Map private responses.
- Market-session freshness: an offline XNYS exchange calendar distinguishes expected completed sessions from actual completed datasets and from file/schema consistency validation.
- Initial local dashboard: React Market Dashboard V1 renders Market Pulse, breadth, up/down volume, liquidity-screened movers, a Trading Activity Map, market/sector benchmarks, and categorized data details from default-disabled private APIs.
- Private static deployment: the workstation exports private Dashboard JSON snapshots, builds a `/dashboard/` React bundle, and deploys a versioned OCI release with `/` as the branded session-login entry for the personal prototype.
- Private session login: a localhost-only OCI Auth Service validates the existing server-side htpasswd credential and issues opaque HttpOnly session cookies for the personal prototype. A deployed admin helper rotates the single Dashboard password through an interactive TTY flow without accepting or printing passwords or hashes.

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
- [Massive Grouped Daily Ingestion](docs/operations/massive-grouped-daily-ingestion.md)
- [Massive Instrument Master Ingestion](docs/operations/massive-instrument-master-ingestion.md)
- [Instrument Identity Resolution](docs/architecture/instrument-identity-resolution.md)
- [EOD Parquet Persistence](docs/architecture/eod-parquet-persistence.md)
- [Canonical Market Data Query Boundary](docs/architecture/canonical-market-data-query-boundary.md)
- [Private EOD Market Data API V1](docs/api/private-eod-market-data-v1.md)
- [Private Market Summary API V1](docs/api/private-market-summary-v1.md)
- [EOD Return Analytics](docs/architecture/eod-return-analytics.md)
- [Frontend Market Dashboard V1](docs/frontend/market-dashboard-v1.md)
- [Private Dashboard Publication](docs/architecture/private-dashboard-publication.md)
- [OCI Private Dashboard Deployment](docs/operations/oci-private-dashboard-deployment.md)
- [Private Dashboard Access](docs/operations/private-dashboard-access.md)

- [Data Access Boundary](docs/operations/data-access-boundary.md)
- [Data Contracts](docs/data-contracts/README.md)
- [System context](docs/architecture/system-context.md)
- [Deployment boundary](docs/operations/deployment-boundary.md)
- [Architecture decisions](docs/decisions/README.md)

## Current Dashboard

Dashboard V1.1 is deployed as a private, session-protected static dashboard. It uses a default `Tradable U.S. Equities` universe for Market Pulse, breadth, movers, and Trading Activity Map, and shows Sector Benchmark ETFs separately. Provider-backed data remains private.
