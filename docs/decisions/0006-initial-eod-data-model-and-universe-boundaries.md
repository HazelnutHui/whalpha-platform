# 0006: Initial EOD Data Model and Universe Boundaries

## Status

Accepted

## Date

2026-08-13

## Context

Trading Intelligence Platform needs a provider-neutral EOD foundation before any market-data adapter is implemented. The first data model must support market structure, breadth, sector and theme rotation, stock strength, relationship monitoring, and later options or portfolio expansion without coupling domain logic to one vendor response shape.

This decision records logical product and data boundaries only. It does not implement Python models, Pydantic schemas, Parquet schemas, provider adapters, ingestion jobs, or a database.

## Decision

Accept the Initial EOD Universe model, three-layer Classification Boundary, and five Normalized EOD Logical Contracts V1 as the first data foundation.

The accepted boundaries are:

- three universe layers: Market Structure Universe, Dynamic Discovery Universe, and Portfolio / Focus Override Layer
- three classification layers: Sector / Industry Classification, Theme Classification, and Analytical Groups
- five logical contracts: Instrument Master, EOD Price Bar, Corporate Action, Classification Definition / Membership, and Universe Definition / Membership
- provider-neutral mapping through Provider Adapters before domain logic consumes data
- point-in-time universe membership and effective-dated classification membership
- traceable revisions and explicit data quality status
- EOD-first, Parquet-first storage direction under the project data root

## Universe Model

### Market Structure Universe

The Market Structure Universe is the stable comparison layer for market structure, standard treemaps, sector breadth, index/style strength, and large-cap contribution analysis.

Initial composition direction:

- S&P 500 constituents
- major market index ETFs
- sector ETFs
- style/factor ETFs

This layer is not the full stock discovery universe.

### Dynamic Discovery Universe

The Dynamic Discovery Universe is the broader opportunity-discovery layer for stock strength, theme rotation, unusual market changes, and broader daily screens.

Coverage direction:

- NYSE
- Nasdaq
- NYSE American
- common stock only

Exclusions:

- OTC
- warrants
- preferred stock
- funds
- SPAC units
- invalid or inactive securities

### Portfolio / Focus Override Layer

Portfolio and Focus overrides preserve analysis eligibility for current holdings, manually watched names, and deep research targets even when a security does not meet Discovery filters.

Override membership does not imply bullishness, recommendation, or investment strength. Portfolio and Focus are distinct sources. Portfolio integration is not implemented yet.

## Classification Model

Accepted classification layers:

1. Sector / Industry Classification: stable traditional identity path from Sector to Industry Group to Industry to Sub-industry.
2. Theme Classification: many-to-many, versioned, explainable thematic membership.
3. Analytical Groups: constructed analysis baskets for relative leadership, rotation, divergence, rolling correlation, relative performance spreads, hedging relationships, and relationship-regime monitoring.

All classification systems require stable internal IDs, source, methodology version, valid-from and valid-to dates, and review status where applicable. External vendor classifications are mapped into canonical internal classifications; vendor fields are not permanent canonical taxonomy.

## Normalized EOD Contracts

Accepted logical contracts:

1. Instrument Master V1
2. EOD Price Bar V1
3. Corporate Action V1
4. Classification Definition / Membership V1
5. Universe Definition / Daily Membership V1

These are accepted logical contracts, not implemented runtime schemas.

## Provider Boundary

Provider Adapters map proprietary provider responses into canonical contracts. Internal business logic must not consume provider-specific response shapes. Raw, normalized, and derived data remain separate.

No Massive, IBKR, options provider, or other source is configured by this decision.

## Point-in-Time and Revision Semantics

Universe memberships are evaluated by session date and retained historically. Current constituents must never be projected backward into history.

Classification memberships use effective dating. Ticker is not a permanent primary key; `instrument_id` is the stable internal instrument key.

Provider corrections create traceable revisions. Missing values remain null and are not silently converted to zero. Silent destructive overwrite is not allowed.

## Storage Direction

Initial direction remains EOD-first and Parquet-first. Practical date partitioning should avoid one-file-per-ticker small-file proliferation. Raw, normalized, and derived datasets remain separate.

This decision does not define a final physical Parquet schema or file layout.

## Candidate Defaults

Dynamic Discovery Universe V1 Candidate Defaults:

- minimum price: USD 3
- minimum market capitalization: USD 300 million
- minimum 20-day average daily dollar volume: USD 5 million
- minimum trading history: 252 trading sessions
- recalculated after each EOD session

These are Candidate Defaults, not permanent thresholds. They must be calibrated after real coverage evaluation.

Evaluation required before locking thresholds:

- selected instrument count
- market-cap distribution
- sector/industry coverage
- daily membership stability
- excluded high-momentum names
- data availability and quality

## Consequences

- Provider implementation can begin against stable logical boundaries instead of vendor schemas.
- Universe and classification semantics are explicit before calculations depend on them.
- Dashboard V1 can use point-in-time membership and effective-dated classification history.
- Early storage can remain simple while preserving a path to stronger physical schemas later.
- Candidate Discovery thresholds require empirical coverage review before being treated as stable operating rules.

## Deferred Decisions

- Physical Parquet layout and partitioning details
- Python/Pydantic contract models
- Validation test implementation
- Provider adapter implementation
- Massive plan and entitlement
- Exact S&P 500/index constituent source
- Canonical traditional taxonomy source or mapping methodology
- Initial curated Theme list and membership methodology
- Initial Analytical Group basket definitions
- Options data source
- Database introduction threshold
- Source revision reconciliation policy
- Issuer Master introduction threshold

## Non-Goals

- Provider integration
- Market-data download
- Pydantic model creation
- JSON Schema, SQL DDL, or database migration
- Parquet file creation
- Dashboard implementation
- Prediction engine
- Automated trading or execution
- Portfolio integration

## Alternatives Considered

- Start directly with provider response schemas: rejected because it would couple domain logic to one vendor.
- Use only S&P 500 constituents for all analysis: rejected because it would miss broader discovery and theme rotation.
- Treat every listed security as the first universe: rejected because low-liquidity and invalid instruments would reduce signal quality.
- Use a database first: deferred until query, concurrency, persistence, or relational state requirements justify it.
