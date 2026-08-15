# Trading Intelligence Web

React/TypeScript/Vite frontend for Trading Intelligence Platform.

## Purpose

The current frontend implements Market Dashboard V1 for local/private development. It consumes the default-disabled private Market Summary, Movers, and Liquidity Map APIs when explicitly enabled locally.

## Data Modes
`VITE_MARKET_DATA_MODE=snapshot` is the production static-dashboard target. It reads `/private-data/v1/manifest.json`, `market-summary.json`, `movers.json`, and `liquidity-map.json` from the authenticated static release. It does not call FastAPI and does not fall back to demo data.


- `VITE_MARKET_DATA_MODE=api` is the default. It calls relative `/api/...` URLs through the Vite proxy.
- `VITE_MARKET_DATA_MODE=demo` uses clearly synthetic `TEST*` fixtures and displays a persistent `DEMO DATA` badge.

API mode does not fall back to demo data on failure.

## Implemented Views

- Market Pulse
- Market Breadth
- Up/Down Volume
- Liquidity Map V1 treemap
- Top Gainers and Top Losers
- Data Quality / Session Metadata
- loading, error, empty, and retry states

## Local Setup

Use the repository-level instructions in [Local Development](../../docs/development/local-development.md).

For local provider-backed verification, run the backend with private routes explicitly enabled:

```bash
TIP_ENABLE_PRIVATE_MARKET_DATA_ROUTES=true scripts/dev/run-api.sh
scripts/dev/run-web.sh
```

The private route enable flag is a development switch only, not authentication or deployment approval. The OCI static dashboard uses `snapshot` mode behind server-side Basic Auth.

## Tests

```bash
npm test
npm run build
```

## Current Non-Goals

- No frontend-originated authentication flow
- No public real-data display
- No authentication or authorization
- No market-cap heatmap
- No sector/industry grouping
- No theme rotation
- No intraday or real-time data
