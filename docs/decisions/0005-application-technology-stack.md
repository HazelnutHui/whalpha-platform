# 0005: Application Technology Stack

## Status

Accepted

## Date

2026-08-13

## Context

Trading Intelligence Platform needs a small, maintainable application stack for a personal U.S. equity market-structure dashboard. Phase 1 needs interactive charts, clear stateful dashboard views, typed data contracts, and a Python-friendly analytics path.

The project is not an automated trading system, a prediction engine, a complex quantitative research platform, or a distributed microservice system. The workstation remains the source of truth for code, data processing, historical storage, and derived results. OCI remains a lightweight public web-serving boundary.

## Decision

Use a React/TypeScript/Vite frontend, Apache ECharts for visualization, Python 3.12/FastAPI/Pydantic for backend API contracts, Pandas/NumPy for analytics, and a Parquet-first EOD development path under `/data/trading-intelligence-platform`.

Application business logic must use a MarketDataProvider boundary and must not depend directly on a vendor-specific response schema.

## Frontend

Accepted frontend stack:

- React
- TypeScript
- Vite
- native CSS or a lightweight CSS architecture
- a small, consistent set of design tokens

A large UI component framework is not part of the initial stack.

Rationale:

- The dashboard needs interactive charts, filters, drilldowns, and linked state.
- React fits composable, maintainable dashboard surfaces.
- TypeScript helps keep data contracts explicit and stable.
- Vite is lightweight enough for the current project scale.

## Visualization

Accepted visualization library:

- Apache ECharts

Rationale:

- It supports treemap, heatmap, scatter plot, line chart, bar chart, radar chart, custom series, tooltip, zoom, and linked interactions.
- It is suitable for market structure, sector and industry heatmaps, rotation views, relationship monitoring, correlation views, and relative-strength displays.

## Backend

Accepted backend stack:

- Python 3.12
- FastAPI
- Pydantic

Rationale:

- Python matches the market-data processing and research ecosystem.
- FastAPI is lightweight and works well for typed API contracts.
- Pydantic provides schema validation and configuration boundaries.
- Django-level complexity is not needed for the initial single-user dashboard.

## Analytics

Accepted analytics stack:

- Pandas
- NumPy

These tools are enough for the initial market structure, breadth, rotation, relationship, and EOD-derived dataset work.

## Initial Storage

Accepted initial storage approach:

- EOD-first development path
- Parquet files for raw, normalized, and derived datasets where appropriate
- project data under `/data/trading-intelligence-platform`

A database is not selected for immediate implementation. PostgreSQL or another database may be introduced later when real requirements justify it, such as multi-user state, query-heavy history, user settings, portfolio persistence, relational event records, API concurrency, or transactional writes.

## Data Provider Boundary

The application must use a MarketDataProvider or adapter boundary. Domain calculations should consume normalized internal data rather than vendor-specific schemas.

Initial provider direction:

- Massive is a candidate EOD broad-market data source for private development and prototype validation.
- Any free or low-cost data plan is subject to entitlement and redistribution limits.
- IBKR is better suited for portfolio data, account-aware information, selected instrument checks, and brokerage-related integration.
- IBKR should not be the default sole source for all broad-market historical website data.
- Options data source selection remains open.

No data provider is configured by this decision.

## Deployment Boundary

The workstation remains the source of truth for code, data, computation, derived results, and published website artifacts or API payloads.

OCI remains the lightweight public serving layer for whalpha.com. It should not run heavy analytics or store complete large-scale raw market history.

The exact deployment mechanism is deferred. Static build publishing and lightweight API serving remain deployment choices to validate later; neither is implemented by this decision.

## Alternatives Considered

- Server-rendered templates: simpler, but less suitable for the interactive dashboard state and chart linking expected in Phase 1.
- Next.js: capable, but adds routing and server-rendering complexity that is not yet needed.
- Django: mature and comprehensive, but heavier than the current backend requirements.
- Early PostgreSQL: useful later if query, state, or concurrency needs appear, but unnecessary before the data model and access patterns are proven.
- Docker-first deployment: useful for repeatability later, but not required before the scaffold and deployment boundary are validated.
- Microservices: not justified by the current single-user prototype and would add unnecessary operational complexity.

## Consequences

- The first scaffold should separate frontend, backend, analytics, and data-provider boundaries clearly.
- API contracts should be typed and documented before they become shared runtime dependencies.
- The frontend can build rich dashboard interactions without committing to a large component framework.
- Parquet keeps early EOD development simple while preserving a path to later database adoption.
- Future provider changes should be isolated behind adapters and normalized data contracts.
- Deployment design remains a separate decision.

## Deferred Decisions

- Exact backend project layout
- Exact frontend project layout
- API route structure and versioning
- Database introduction threshold and database choice
- Initial market universe construction
- Sector and industry taxonomy source
- Options data provider
- Exact OCI deployment mechanism
- Public/private access boundary before wider promotion
- Automatic relationship discovery methodology

## Non-Goals

- Automated trading
- Order execution
- HFT
- Complex prediction engine
- Deep neural networks
- Large ML pipeline
- Large Event Knowledge Base
- Microservices
- Kubernetes
- Distributed system architecture
