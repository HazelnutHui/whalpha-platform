# Trading Intelligence Web

React/TypeScript/Vite frontend for Trading Intelligence Platform.

## Purpose

The current frontend implements Market Dashboard V1 for local/private development. It consumes the default-disabled private Market Summary, Movers, and Liquidity Map APIs when explicitly enabled locally.

## Data Modes
`VITE_MARKET_DATA_MODE=snapshot` is the production static-dashboard target. It reads `/private-data/v1/manifest.json`, `market-summary.json`, `movers.json`, and `liquidity-map.json` from the authenticated static release. It does not call FastAPI and does not fall back to demo data. The deployed OCI release uses `/` as the public WH Alpha login entry, keeps `/login/` as a compatibility redirect, and protects Dashboard/private JSON with server-side session cookies; the frontend never stores usernames or passwords.


- `VITE_MARKET_DATA_MODE=api` is the default. It calls relative `/api/...` URLs through the Vite proxy.
- `VITE_MARKET_DATA_MODE=demo` uses clearly synthetic `TEST*` fixtures and displays a persistent `DEMO DATA` badge.

API mode does not fall back to demo data on failure.

## Implemented Views

- Market Pulse
- Market Breadth
- Up/Down Volume
- Market Benchmark Strip for SPY, QQQ, IWM, DIA, and equal-weight universe return
- Sector Benchmark ETF 1D relative performance versus SPY
- Trading Activity Map treemap, default top 50
- Top Gainers and Top Losers
- Categorized Data Details
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

- No public real-data display
- No frontend access to credentials or password hashes
- No formal multi-user authentication or authorization
- No market-cap heatmap
- No sector/industry grouping
- No theme rotation
- No intraday or real-time data

## Dashboard V1.1

The dashboard consumes the versioned overview payload. API mode calls `/api/v1/private/market/overview/latest`; snapshot mode reads `/private-data/v1/market-overview.json`; demo mode remains synthetic. The default universe is `Tradable U.S. Equities`, with ETFs shown separately as market and Sector Benchmark ETFs. Freshness is conservative until a reliable market-session calendar is accepted.
