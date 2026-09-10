# Trading Intelligence Web

The React application has five first-level workspaces: Market Regime &
Opportunities (`市场风向与机会`), Sector Rotation, Market Dashboard, Stock
Candidates (`个股候选`), and Quant Research Lab (`量化研究实验室`). Desktop navigation uses a
persistent left rail, with Market Regime & Opportunities first and selected by
default; Universe, language, and private Session controls share an
opaque sticky utility header. The Universe selector exposes only `Common
Shares` and `Common Shares + ADRs`, with CS-only as default. A validated stable
ID is persisted in the URL; Legacy remains an internal rollback boundary.

The active Dashboard uses Activation V2 Primary/Secondary Universes. Provider
security form remains provisional and does not establish issuer structure or
domicile.

React/TypeScript/Vite frontend for Trading Intelligence Platform.

## Purpose

The frontend implements the five product workspaces and shared bilingual shell
for local/private development and versioned static publication. Quant Research
Lab is the model/evidence view; a future AI Quant Research Factory is its
backend capability and does not create another navigation item.

## Data Modes
`VITE_MARKET_DATA_MODE=snapshot` is the production static-dashboard target. It reads `/private-data/v1/manifest.json`, `market-summary.json`, `movers.json`, and `liquidity-map.json` from the authenticated static release. It does not call FastAPI and does not fall back to demo data. The deployed OCI release uses `/` as the public WH Alpha login entry, keeps `/login/` as a compatibility redirect, and protects Dashboard/private JSON with server-side session cookies; the frontend never stores usernames or passwords.


- `VITE_MARKET_DATA_MODE=api` is the default. It calls relative `/api/...` URLs through the Vite proxy.
- `VITE_MARKET_DATA_MODE=demo` is development-only, lazily loads clearly
  synthetic `TEST*` fixtures, and displays a persistent `DEMO DATA` badge.

API and Snapshot modes do not fall back to demo data on failure. Production
builds reject known synthetic fixture markers.

Snapshot 1.11 / Dashboard 2.8 serves bounded Candidate summary/detail shards,
Entry Geometry, Strategy Channels, Candidate Visual Context, and Sector ETF
Rotation without browser-side score or rank recomputation. Exact active
sessions and release identity belong in
[current context](../../docs/project/current-context.md), not this application
guide.

## Implemented Views

- Persistent first-level workspace navigation and shared utility controls
- Factual first-screen market summary and Universe/comparable explanation
- Market Pulse
- Market Breadth
- Up/Down Volume
- Market Benchmark Strip for SPY, QQQ, IWM, DIA, and equal-weight universe return
- Sector Benchmark ETF 1D relative performance versus SPY
- Trading Activity Map treemap, default top 50
- Top Gainers and Top Losers
- Categorized Data Details
- Market Regime five-dimension evidence and six highlighted ETF relationships
- Complete 16-pair relationship table and detail drawer
- Language-neutral, risk-mode-specific Stock Candidate ranking, entry-location
  review, strategy channels, cross-channel decision desk, price-path/level
  context, contribution ledgers, and evidence drawer
- Bilingual Quant Research Lab readiness and preregistered-method workspace;
  price depth has passed the length floor while the page keeps point-in-time
  membership, lifecycle, actions/adjustment, costs, and evaluation gates
  separately blocked and all real result areas locked
- Logout in snapshot mode
- loading, error, empty, and retry states

## Local Setup

Use the repository-level instructions in [Local Development](../../docs/development/local-development.md).

For local provider-backed verification, run the backend with private routes explicitly enabled:

```bash
TIP_ENABLE_PRIVATE_MARKET_DATA_ROUTES=true scripts/dev/run-api.sh
scripts/dev/run-web.sh
```

The private route enable flag is a development switch only, not authentication or deployment approval. The OCI static dashboard uses `snapshot` mode behind server-side session authentication.

## Tests

```bash
npm test
npm run build
```

## Current Non-Goals

- No real data on the public data-free landing page; guest and credential
  Sessions intentionally receive identical protected product capability
- No frontend access to credentials or password hashes
- No formal multi-user authentication or authorization
- No market-cap heatmap
- No sector/industry grouping
- No theme rotation
- No intraday or real-time data
- No real Quant Research Lab performance or research-stage activation
- No browser-side agent orchestration, model selection, or holdout access

The deployed Candidate score and technical Strategy Channels are frozen,
unvalidated Baseline V1. Future Stock Candidate rankings will come only from
separately validated and activated Quant Research Lab models; this frontend
guide does not authorize direct baseline tuning.

## Dashboard V1.1

The dashboard consumes the versioned overview payload. API mode calls `/api/v1/private/market/overview/latest`; snapshot mode reads `/private-data/v1/market-overview.json`; demo mode remains synthetic. The default universe is `Tradable U.S. Equities`, with ETFs shown separately as market and Sector Benchmark ETFs. Freshness compares the actual latest completed dataset session with the offline XNYS expected latest completed session and displays `Fresh`, an explicit session lag, or calendar unavailability separately from file validation.
