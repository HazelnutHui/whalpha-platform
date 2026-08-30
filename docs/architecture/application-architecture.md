# Application Architecture

## Purpose

This document records the approved target application architecture for Trading Intelligence Platform. It describes how the first application scaffold should be organized conceptually; it is not evidence that the full runtime already exists.

## Current Status

Dashboard update: the React Market Dashboard supports API, demo, and production snapshot modes. Git records private authenticated static OCI deployments; current OCI runtime state requires a separate authorized verification.
Publication update: the workstation generates validated dashboard-ready JSON snapshots and versioned OCI bundles; the recorded deployment architecture keeps OCI as a lightweight authenticated static serving plane.

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
- Mocked-fixture and bounded live EOD ingestion paths are implemented with Parquet persistence and logical manifests.
- Completed Instrument Master, provider identity, ticker resolver, and EOD datasets exist for 2026-08-12 through 2026-08-14; provider security evidence exists for 2026-08-14.
- Massive credential provisioning, production HTTPS transport, reference smoke test, bounded All Tickers ingestion, and bounded Grouped Daily publication are complete.
- Default-disabled canonical EOD query APIs, close-to-close analytics, Dashboard Overview, snapshot export, and bundle publication paths are implemented.
- The initial 29-session EOD historical window through 2026-08-26 is
  implemented; broader backfill and automated daily ingestion are not.
- No production API is deployed.
- No database exists.
- The last OCI deployment recorded in Git is a private session-protected static Dashboard with a branded root login; this document does not assert current live health.

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

The repository implements the FastAPI contract, React dashboard, canonical data contracts, provider Protocol, Massive adapter, bounded normalization/persistence workflows, EOD analytics, private snapshot export, and static deployment tooling. Broader historical ingestion, sector/theme analytics, options, and event generation remain future work.

## Data Flow

1. Provider adapters retrieve source data through explicit provider boundaries.
2. Raw vendor data is kept conceptually distinct from normalized data.
3. Normalized datasets feed market structure, breadth, rotation, stock strength, options structure, and relationship calculations.
4. Derived datasets and lightweight event findings become API payloads or published artifacts.
5. FastAPI exposes typed contracts for the dashboard when a backend is needed.
6. React renders the dashboard using typed data contracts and Apache ECharts.
7. The accepted static deployment mechanism publishes only reviewed Dashboard-ready private assets to OCI.

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

Current runtime choice:

- Phase 1 private deployment is static snapshot based.
- Versioned artifacts are built on the workstation and promoted with an atomic OCI release switch.
- FastAPI private routes remain a default-disabled local/private development boundary; no production FastAPI service is deployed.

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

Instrument Master V1 and EOD Price Bar V1 are implemented as Python/Pydantic
validation models. Bounded Parquet repositories exist for Instrument Master,
provider identity, ticker resolver, EOD bars, provider security evidence, and
the not-yet-published SEC evidence boundary. Corporate Action V1 and broader
issuer classification remain incomplete. The production data root contains
completed point-in-time Identity and canonical EOD sessions through 2026-08-28,
active provider-form Primary/Secondary Universe memberships, immutable Market
Intelligence 1.3, and Snapshot 1.11 / Dashboard 2.8. Exact volatile release,
session, and inventory evidence belongs in
[current-context](../project/current-context.md). Default-disabled read/query
APIs, EOD analytics, Dashboard Overview, and private Snapshot export consume
these completed datasets.

Repository source adds Snapshot 1.8 / Dashboard 2.5 as a consumer-only
Candidate delivery optimization: a compact list projection and stable-ID
detail shards formally reconstruct the unchanged Candidate publication 1.1.
Snapshot 1.9 / Dashboard 2.6 adds one lazy, source-bound strategy-channel
product. Snapshot 1.10 / Dashboard 2.7 carries Visual Context in detail-shard
1.1 while the first-load summary remains unchanged. Snapshot 1.11 /
Dashboard 2.8. It projects the MI 1.3 market-wide Sector ETF Rotation product
into one dedicated checksum-bound lazy file and freezes the exact source and
product lineage through Approval Plan 2.6 and OCI validation. This newer pair
is active in Production.

A database is not selected yet. Database introduction should be driven by real requirements such as query patterns, persistence needs, API concurrency, relational event records, portfolio state, or settings.

## Provider Boundary

The application must not let vendor response schemas leak into domain calculations. Use the implemented [Market Data Provider Boundary](market-data-provider-boundary.md) and future provider adapters to return canonical contracts before analysis.

Provider direction:

- Massive Stocks Basic is accepted as the first broad-market EOD provider for private, personal development.
- The Massive adapter runs on the workstation boundary and maps responses into canonical contracts before analysis.
- Provider credentials must remain server-side and outside Git.
- Provider-backed outputs remain private unless public-display or redistribution authorization is separately documented.
- OCI public login content remains data-free; provider-backed Dashboard and
  static JSON remain behind the shared Session boundary.
- IBKR is best positioned for portfolio, account-aware information, selected instrument checks, and brokerage-related integration.
- Options data source remains an open question.

Bounded Grouped Daily publications produced completed canonical sessions from
2026-07-17 through 2026-08-26. Close-to-close analytics, default-disabled
private Dashboard APIs, immutable Market Intelligence, private snapshots, and
versioned deployment tooling are implemented. Automated daily ingestion,
unrestricted public provider-backed display, and a production API service are
not implemented.

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
- database introduction threshold and database choice
- Candidate Discovery threshold calibration
- exact canonical traditional taxonomy source or mapping methodology
- broader Massive entitlement verification beyond the already exercised endpoints
- formal multi-user access control beyond the personal-prototype session boundary
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

A private read/query boundary reads completed canonical EOD Parquet sessions and exposes default-disabled FastAPI routes only when `TIP_ENABLE_PRIVATE_MARKET_DATA_ROUTES=true`. This is a local/private development switch, not authentication or public deployment approval. The React Dashboard consumes the versioned overview payload in API mode and equivalent protected JSON in snapshot mode.

## Market Summary Analytics Boundary

The backend exposes default-disabled private Market Summary V1, movers, returns, Liquidity Map V1, and Dashboard Overview routes from completed canonical EOD sessions. The frontend renders these results in API or snapshot mode. Liquidity Map V1 uses close-times-volume as a liquidity proxy; it is not market-cap weighted and is not sector grouped. A traditional market-cap sector heatmap remains deferred pending market-cap, taxonomy, and point-in-time classification sources.

## Opportunity Candidate Consumer Boundary

The canonical Candidate audit remains an offline computation and replay
boundary. Production consumers do not scan its `/tmp` files, recompute ranks,
or expose the full rejected population. A single bounded language-neutral
projection is built only after the audit reader, Oracle, equivalence, session,
Universe, EOD, Identity, and Activation gates pass. Active Market Intelligence
1.2 is the immutable aggregate owner; active Snapshot 1.7 / Dashboard 2.4
exports the same projection as protected static JSON. Repository-only Snapshot
1.8 / Dashboard 2.5 changes delivery to a compact summary and on-demand detail
shards without changing Candidate publication 1.1.

The React Candidate workspace selects server-calculated risk ranks and
localizes stable codes. It never treats ticker as identity, confidence as win
probability, ETF price proxies as formal sector membership, price/volume as
fund flow, invalidation as a position exit, or the underlying-stock result as
an option return. Guest and credential Sessions consume the identical file;
role never enters the analytics, cache, or filtering boundary.

ADR 0049 adds a repository-only strategy-channel shadow boundary above the
existing Candidate and entry-geometry facts. Six fixed archetypes produce
independent assessments and within-channel ranks; there is no cross-channel
score. Market fit, event context, and future option expression remain separate
axes. ADR 0057 now supplies the bounded lazy product and bilingual React
consumer; ADR 0058 carries its exact identity through Approval Plan 2.4 and OCI
bundle/postflight validation. These remain unpublished and do not make the
fixed baseline chronologically validated.

ADR 0050 separates future evaluation into sealed, outcome-free signal records
and later-maturing forward-outcome records. Only point-in-time membership may
be performance-eligible. The contracts are repository-only: no evaluation
writer, historical dataset, formula, or consumer is connected to the runtime.
