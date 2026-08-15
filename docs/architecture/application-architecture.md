# Application Architecture

## Purpose

This document records the approved target application architecture for Trading Intelligence Platform. It describes how the first application scaffold should be organized conceptually; it is not evidence that the full runtime already exists.

## Current Status

Dashboard update: the React Market Dashboard is deployed as a private authenticated static OCI application and supports API, demo, and production snapshot modes.
Publication update: the workstation generates validated dashboard-ready JSON snapshots and versioned OCI bundles; OCI remains a lightweight authenticated static serving plane.

Freshness update: a provider-neutral offline XNYS calendar now determines the expected latest completed session at an injected timezone-aware instant. Dataset availability, file/schema consistency, and market-calendar freshness are separate states.



Instrument identity update: Provider Instrument Identity V1 and deterministic UUIDv5 identity resolution are implemented. The 2026-08-14 logical identity snapshot passed content-integrity review and is accepted as `accepted_with_provenance_exception`; it may be used point-in-time but may not be requested again or overwritten.

Confirmed current state:

- Minimal backend scaffold exists under `apps/api`.
- Minimal frontend scaffold exists under `apps/web`.
- Target frontend/backend boundaries are represented in the repository structure.
- Versioned Health API contract exists at `GET /api/v1/health`.
- Local development scripts exist under `scripts/dev`.
- Local backend tests, direct Health API, frontend production build, Vite server, and Vite-to-FastAPI proxy have been verified.
- Initial EOD Universe, classification boundary, and normalized EOD logical contracts are accepted and documented.
- Instrument Master V1 and EOD Price Bar V1 are implemented as provider-neutral Python/Pydantic contracts with validation tests.
- Minimal synchronous MarketDataProvider boundary, query models, capability declarations, provider errors, and deterministic in-memory contract tests are implemented.
- Massive Stocks Basic is accepted as the first private EOD development provider.
- Massive configuration, credential redaction, transport Protocol, and mocked adapter mapping skeleton are implemented.
- One-session mocked-fixture EOD Price Bar ingestion and Parquet persistence are implemented under temporary test roots.
- Complete market data flow is not implemented.
- Massive credential provisioning, production HTTPS transport, and one reference smoke test are complete.
- No real Grouped Daily retrieval, production ingestion, or production persistence exists.
- No production API is deployed.
- No database exists.
- OCI currently serves only a static development placeholder.

## System Responsibilities

Workstation responsibility:

```text
Market Data
-> Data Processing
-> Analytics
-> Derived Results
-> Published Website Artifacts / API Payloads
```

OCI responsibility:

```text
Nginx
-> Static Frontend and/or Lightweight API
-> Browser
```

The workstation is the source of truth for code, data processing, historical storage, analytics, and derived outputs. OCI is the lightweight public serving boundary and should not run heavy analytics or store complete large market-data history.

## Logical Components

Approved target component flow:

```text
Market Data Providers
        |
        v
Provider Adapters
        |
        v
Normalization
        |
        v
Analytics / Market Structure
        |
        v
Derived Datasets / Events
        |
        v
FastAPI Contracts
        |
        v
React Dashboard
        |
        v
Published through OCI
```

The scaffold represents the FastAPI contract, React dashboard boundary, canonical data contracts, and minimal provider Protocol boundary. Real provider adapters, normalization pipelines, analytics, derived datasets, event generation, and deployment publishing are still future work.

## Data Flow

1. Provider adapters retrieve source data through explicit provider boundaries.
2. Raw vendor data is kept conceptually distinct from normalized data.
3. Normalized datasets feed market structure, breadth, rotation, stock strength, options structure, and relationship calculations.
4. Derived datasets and lightweight event findings become API payloads or published artifacts.
5. FastAPI exposes typed contracts for the dashboard when a backend is needed.
6. React renders the dashboard using typed data contracts and Apache ECharts.
7. OCI serves the public boundary after a deployment mechanism is selected.

The Health API, default-disabled private market-data APIs, EOD return analytics APIs, and local React Market Dashboard V1 exist for local/private development.

## Repository / Application Boundaries

The code repository remains under `/home/hui/projects/trading-intelligence-platform`.

Application data belongs under `/data/trading-intelligence-platform` and must not be committed to Git. Secrets, provider credentials, account credentials, and private configuration must stay outside the repository.

Current scaffold boundaries:

- `apps/api`: FastAPI backend and API contract tests
- `apps/web`: React/Vite Market Dashboard V1 local frontend
- `scripts/dev`: local development launch scripts
- `docs/development`: local development instructions

Future implementation should keep these responsibilities distinct:

- frontend dashboard
- backend API contracts
- analytics calculations
- provider adapters
- normalized and derived data boundaries
- operational documentation

## Runtime Boundaries

Confirmed runtime boundary:

- The workstation handles compute and data processing.
- OCI handles public serving.
- The browser renders the visual dashboard and must not hold provider or brokerage credentials.

Deferred runtime choices:

- whether Phase 1 deployment is static-only, API-backed, or hybrid
- how artifacts are promoted from the workstation to OCI
- whether a lightweight API runs on OCI, the workstation, or both under a future deployment decision

## Data Storage Boundary

Initial storage approach:

- EOD-first development path
- Parquet files for early raw, normalized, and derived datasets where appropriate
- project data root at `/data/trading-intelligence-platform`

Accepted logical data-contract boundary:

- [Initial EOD Universe](../product/initial-eod-universe.md)
- [Classification Boundary](classification-boundary.md)
- [Normalized Market Data Contracts](normalized-market-data-contracts.md)
- [Data Contracts](../data-contracts/README.md)

Instrument Master V1 and EOD Price Bar V1 are implemented as Python/Pydantic validation models. EOD Price Bar V1 has a one-session ingestion service and explicit Parquet repository. Corporate Action V1, Classification V1, and Universe Membership V1 remain logical-only. The completed production data root currently contains the 2026-08-13 Instrument Master, provider identity, provider ticker resolver, and EOD Price Bar datasets. No database table, read/query API, analytics workflow, or Dashboard data flow exists yet.

A database is not selected yet. Database introduction should be driven by real requirements such as query patterns, persistence needs, API concurrency, relational event records, portfolio state, or settings.

## Provider Boundary

The application must not let vendor response schemas leak into domain calculations. Use the implemented [Market Data Provider Boundary](market-data-provider-boundary.md) and future provider adapters to return canonical contracts before analysis.

Provider direction:

- Massive Stocks Basic is accepted as the first broad-market EOD provider for private, personal development.
- A future Massive adapter should run on the workstation and map responses into canonical contracts before analysis.
- Provider credentials must remain server-side and outside Git.
- Provider-backed outputs remain private unless public-display or redistribution authorization is separately documented.
- OCI public placeholder content remains data-free.
- IBKR is best positioned for portfolio, account-aware information, selected instrument checks, and brokerage-related integration.
- Options data source remains an open question.

No successful production Grouped Daily publish, historical backfill, analytics, Dashboard data API, or provider-backed deployment is configured by this architecture document. The current Massive adapter has mocked mapping tests, a controlled reference smoke test, a completed Instrument Master snapshot, and one failed quality-gated Grouped Daily publication attempt.

## Dashboard V1 Functional Areas

The first dashboard architecture should support these functional areas without requiring all calculations to be complete on day one:

1. Market Summary / Risk Regime
2. Traditional Market Treemap
3. Breadth and Participation
4. Index / Style Strength
5. Sector / Theme Rotation
6. Dynamic Relationship & Rotation Monitor
7. Key Market Developments

### Market Summary / Risk Regime

The dashboard should quickly show major index performance, volatility context, breadth, risk-on / neutral / risk-off context, and a key market condition summary.

### Traditional Market Treemap

The dashboard must include a traditional market heatmap/treemap:

- sector or industry areas sized by market weight
- major stocks nested inside sectors or industries
- stock tiles sized by market capitalization or weight
- color expressing return
- ticker and return shown inside tiles
- quick identification of market contribution and internal sector structure

### Breadth and Participation

Breadth should support advancing versus declining, above-moving-average views, new highs versus new lows, equal-weight versus cap-weight context, and participation quality. Exact formulas remain to be confirmed before implementation.

### Index / Style Strength

The dashboard should compare index and style relationships such as SPY, QQQ, IWM, DIA, equal weight, growth versus value, and large cap versus small cap.

### Sector / Theme Rotation

Rotation views should identify strengthening, weakening, improving, deteriorating, relative strength, momentum, and leadership persistence.

### Dynamic Relationship & Rotation Monitor

This feature is the professional expression of cross-group rotation and relationship shifts. UI terminology should use language such as Relative Leadership, Rotation, Divergence, Rolling Correlation, Relative Performance Spread, Regime Shift, and Cross-Group Relationship.

Initial relationships can be curated pairs such as software versus semiconductors, mega-cap technology versus semiconductors, growth versus value, large cap versus small cap, and defensive versus cyclical. Automatic discovery is deferred.

The monitor should evolve toward rolling correlation, relative performance spread, standardized spread / z-score, rolling beta, divergence, leadership change, persistence, and relationship regime change.

### Key Market Developments

The lightweight Event Layer should surface about 3-5 important market changes, such as breadth thrust or deterioration, leadership rotation, volatility regime change, relationship regime shift, and unusual options or volume structure.

This is an internal organization layer for important findings, not a large Event Knowledge Base.

## Documentation Checkpoints

Before closing material work, check whether these documents need updates:

- ADRs for accepted architecture decisions
- architecture documents for system boundaries and data contracts
- operations documents for real infrastructure or deployment state
- current-status for actual project state
- roadmap for sequencing changes
- open-questions for resolved or newly discovered decisions
- changelog for meaningful project-level changes
- README and docs index for navigation changes

## Deferred Decisions

- API route structure and versioning beyond the Health API
- exact deployment mechanism to OCI
- database introduction threshold and database choice
- Candidate Discovery threshold calibration
- exact canonical traditional taxonomy source or mapping methodology
- Massive account entitlement verification
- exact private access-control mechanism
- options data source
- Cloudflare proxy state
- obsolete OCI port rule cleanup
- OCI swap strategy
- long-term data backup and retention policy
- automatic relationship discovery methodology

## Non-Goals

- automated trading
- order execution
- HFT
- deep neural networks
- complex prediction engine
- large ML pipeline
- large Event Knowledge Base
- microservices
- Kubernetes
- distributed system architecture

## Canonical EOD Query Boundary

A first private read/query boundary now reads completed canonical EOD Parquet sessions and exposes default-disabled FastAPI routes only when `TIP_ENABLE_PRIVATE_MARKET_DATA_ROUTES=true`. This is a local/private development switch, not authentication or public deployment approval. The frontend is unchanged.

## Market Summary Analytics Boundary

The backend now exposes default-disabled private Market Summary V1, movers, returns, and Liquidity Map V1 routes from completed canonical EOD sessions. The frontend is unchanged. Liquidity Map V1 uses close-times-volume as a liquidity proxy; it is not market-cap weighted and is not sector grouped. A traditional market-cap sector heatmap remains deferred pending market-cap, taxonomy, and point-in-time classification sources.
