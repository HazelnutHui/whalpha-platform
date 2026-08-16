# Trading Intelligence Platform

## Security Type Governance Phase A

The repository includes a provider-neutral, effective-dated Security Classification V1 boundary. Classification fact, evidence quality, and candidate-universe eligibility are separate. Unknown, ambiguous, malformed, heuristic-only, and insufficient-evidence records are quarantined. The [2026-08-14 read-only audit](docs/audits/security-type-classification-2026-08-14.md) found that the binary Instrument Master cannot reliably resolve most non-ETF records, so production Dashboard membership remains unchanged pending a Core-versus-Broad policy decision and stronger evidence.

Phase B1 accepts Core as the future default and Broad as the future secondary view. The corrected bounded run published the official 25-code provider catalog, 13,110 normalized observations, 9,939 canonical evidence records, and a verified logical completion marker. Provider type improves security-form evidence but does not establish issuer structure or domicile, so production membership remains unchanged and provisional. See the [evidence audit](docs/audits/security-type-provider-evidence-2026-08-14.md).

Phase B2A added the offline SEC issuer-structure boundary. Phase B2B added the bounded streaming transport, source-cache safety checks, normalized observation persistence, canonical evidence persistence, and logical completion contract. Five separately authorized bounded runs each stopped at Series/Class landing discovery and published no completed SEC cache or evidence snapshot. The fifth run verified the exact 2024 legacy exception and candidate-derived counts, then failed closed on a newly observed 2023 underscore-style basename after three requests and zero retries. Offline remediation now accepts only that exact 2023 public path for parsed file year 2023; a four-candidate official-shape fixture deterministically selects the 2026 release and leaves 2025, 2024, and 2023 eligible but unselected. No new live run occurred, and no rule is inferred for 2022 or earlier. See [SEC Issuer-Structure Evidence](docs/architecture/sec-issuer-structure-evidence.md) and the [B2B run audit](docs/audits/sec-issuer-structure-evidence-2026-08-14.md).

Trading Intelligence Platform is a personal single-user prototype for U.S. equity market intelligence. It is designed to help the user understand market structure, sector and theme rotation, stock strength, breadth, options structure, relationship shifts, and significant market developments quickly enough to support discretionary research and trading decisions.

The platform should help answer:

- What is the market structure today?
- Which sectors and themes are strengthening or weakening?
- Is risk appetite expanding or contracting?
- Which stocks show genuine relative strength?
- What relationships or rotations deserve further investigation?
- What developments are significant enough for human review?

## Current Phase

Documentation, infrastructure, storage foundation, application stack, canonical EOD contracts, point-in-time identity, bounded real-data ingestion, private analytics, Dashboard, and authenticated static publication boundaries are implemented. Completed canonical EOD sessions cover 2026-08-12 through 2026-08-14. The 2026-08-14 identity snapshot is accepted with a provenance exception after a full content-integrity audit, and its one authorized Grouped Daily request published 9,912 verified canonical bars. The last deployment recorded in Git used the 2026-08-14 snapshot with XNYS session lag zero and server-side session protection; current OCI runtime health requires a separate authorized check. No public real-data authorization, database, automated daily ingestion, historical backfill, or general production API deployment has been created.

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
- First EOD development provider: Massive Stocks Basic for private, personal EOD development only; secure credential/HTTPS transport, bounded All Tickers identity ingestion, Grouped Daily publication, and provider security evidence workflows are verified.
- Initial persistence: Instrument Master, provider identity, ticker resolver, provider security evidence, and EOD Price Bar Parquet repositories use manifests, deterministic fingerprints, idempotency, and conflict checks. Completed canonical EOD sessions exist for 2026-08-12 through 2026-08-14.
- Initial private read API: default-disabled canonical EOD query routes can list completed sessions, summarize completed sessions, and return paginated joined bars with Decimal values serialized as strings.
- Initial market summary analytics: the latest completed pair, 2026-08-13 and 2026-08-14, supports close-to-close returns, Market Summary V1, liquidity-screened movers, and Trading Activity Map private responses.
- Market-session freshness: an offline XNYS exchange calendar distinguishes expected completed sessions from actual completed datasets and from file/schema consistency validation.
- Initial local dashboard: React Market Dashboard V1 renders Market Pulse, breadth, up/down volume, liquidity-screened movers, a Trading Activity Map, market/sector benchmarks, and categorized data details from default-disabled private APIs.
- Private static deployment: the workstation exports private Dashboard JSON snapshots and versioned `/dashboard/` React bundles. Git records authenticated OCI deployments with `/` as the branded session-login entry; live OCI state is not implied without a current check.
- Private session login: the deployed design uses a localhost-only OCI Auth Service, opaque HttpOnly session cookies, and an interactive password-rotation helper. Git records successful verification of that design; current service health is an operational check, not a repository fact.

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

Dashboard V1.1 is implemented for private, session-protected static publication. The last deployment recorded in Git used the default `Tradable U.S. Equities` universe for Market Pulse, breadth, movers, and Trading Activity Map, with Sector Benchmark ETFs shown separately. Provider-backed data remains private; current OCI health was not verified by this documentation reconciliation.
