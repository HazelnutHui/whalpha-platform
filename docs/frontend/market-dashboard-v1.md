# Market Dashboard V1

## Purpose

Market Dashboard V1 is the first React dashboard for the private provider-backed market summary APIs.

It helps answer whether the completed EOD session was broadly up or down, whether breadth confirmed the move, which liquidity-screened instruments moved the most, where liquidity was concentrated, and whether the displayed data has quality warnings.

## Status

Implemented for local/private development only. It has been designed for the completed 2026-08-13 current session and 2026-08-12 previous session exposed by the default-disabled private APIs.

The static OCI release is deployed behind a branded login page and server-side sessions for the personal prototype. This is not public real-data authorization, and authenticated browser verification is still a manual user step.

## Data Modes
`VITE_MARKET_DATA_MODE=snapshot` is now supported for the static OCI target. Snapshot mode reads authenticated static JSON from `/private-data/v1/` and displays `PRIVATE EOD SNAPSHOT`; it does not call the private FastAPI routes and does not fall back to demo data.


The frontend supports two explicit modes:

- `VITE_MARKET_DATA_MODE=api`: default; calls relative private API routes through the Vite proxy.
- `VITE_MARKET_DATA_MODE=demo`: uses clearly synthetic `TEST*` fixtures and displays a persistent `DEMO DATA` badge.

API mode does not fall back to synthetic fixtures on failure. Failures render explicit error states.

## Implemented Views

- Header with WH Alpha, Trading Intelligence, session dates, EOD badge, private-data badge, load time, and data status.
- Logout button in the authenticated snapshot Dashboard.
- Market Pulse cards for equal-weight return, median return, advancers/decliners, positive return share, A/D net, and up/down volume ratio.
- Market Breadth stacked bar with advancers, unchanged, and decliners.
- Up/Down Volume comparison using share volume, not money flow.
- Apache ECharts Liquidity Map V1 treemap.
- Top Gainers and Top Losers lists using liquidity-screened API results.
- Data Quality and Session Metadata panel.
- Loading, error, empty, and retry states.

## Liquidity Map Semantics

Liquidity Map V1 uses:

- Size: `current_close * current_volume` proxy.
- Color: close-to-close return.
- Fixed diverging color clamp around +/-5% for readability.

It is explicitly not market-cap weighted, not sector grouped, not fund flow, and not money flow. Instrument type may be displayed as metadata but is not a sector taxonomy.

## API Boundary

The frontend uses relative URLs under `/api/...` and consumes the private response contracts documented in [Private Market Summary V1](../api/private-market-summary-v1.md).

Decimal values remain strings in API types and are parsed only for formatting and chart transforms. Invalid decimal strings are treated as data errors rather than displayed as `NaN`.

## Presentation Formatting

- Percentages display with two decimals and optional positive sign.
- Ratios display with two decimals and `x`.
- Counts use thousands separators.
- Share volume uses compact notation such as `9.39B`.
- Prices use standard currency formatting; liquidity proxies use compact currency formatting.
- Raw API Decimal strings remain unchanged.
- Metric cards and numeric cells use tabular numerals, bounded font sizes, and overflow protection.

## Accessibility

V1 includes semantic headings, keyboard focus styles, aria labels for chart regions, visible labels/counts in color-coded charts, `aria-live` loading state, `role=alert` errors, and reduced-motion handling for the treemap animation.

## Local Verification

The dashboard is intended to run locally with:

```bash
TIP_ENABLE_PRIVATE_MARKET_DATA_ROUTES=true scripts/dev/run-api.sh
scripts/dev/run-web.sh
```

The API binds to `127.0.0.1:8000` and Vite binds to `127.0.0.1:5173`. Vite proxies `/api` to the local backend.

## Security Boundary

`TIP_ENABLE_PRIVATE_MARKET_DATA_ROUTES=true` is a development switch only. It is not authentication, authorization, or deployment approval.

Provider-backed data and derived analytics must remain private unless formal access control and provider display rights are accepted and implemented.

## Not Implemented

- Public real-data deployment
- Frontend-stored credentials
- multi-user authentication or authorization
- public real-data display
- market-cap heatmap
- sector/industry grouping
- theme rotation
- multi-day trend charts
- Event Layer
- Options, Portfolio, or AI modules
- intraday or real-time data
