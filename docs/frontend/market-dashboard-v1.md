# Market Dashboard V1

## Classification Boundary

Phase A does not change the Dashboard. A future Phase B must make Market Pulse, Breadth, Movers, and Trading Activity Map share one universe definition ID, version, and as-of date. ETF benchmarks, excluded records, quarantine records, and unknown/ambiguous/heuristic-only classifications cannot enter that equity membership.

The V1.3 response labels unchanged legacy calculations as provisional and carries `universe_definition_id`, `universe_version`, `governance_status`, `classification_as_of_date`, and `evidence_coverage_status`. The UI displays an amber `Provisional classification` state and a material evidence warning. Published provider security-form evidence does not connect Core/Broad candidates to metrics or remove the issuer-structure limitation.

Release `2026-08-14T020535Z-ebb16015b7da` deploys this disclosure with the prior 1,864-member summary, movers, and Trading Activity Map payloads unchanged. Authenticated visual confirmation remains a user-run check because automated deployment does not use the user's password.

## Purpose

Market Dashboard V1 is the first React dashboard for the private provider-backed market summary APIs. Dashboard V1.1 adds a professional default universe and separates operating-equity market structure from ETF benchmark performance.

It helps answer whether the completed EOD session was broadly up or down, whether breadth confirmed the move, which liquidity-screened instruments moved the most, where liquidity was concentrated, and whether the displayed data has quality warnings.

## Status

Implemented for private static production and local development. The deployed snapshot uses the completed 2026-08-14 current session and 2026-08-13 previous session.

The static OCI release is deployed behind a branded login page and server-side sessions for the personal prototype. This is not public real-data authorization, and root login, session login, Dashboard data loading, Logout, and password rotation have been manually verified by the user. Passwords, hashes, and browser credential details are not recorded.

## Data Modes
`VITE_MARKET_DATA_MODE=snapshot` is supported for the static OCI target. Snapshot mode reads authenticated static JSON from `/private-data/v1/`; it does not call the private FastAPI routes and does not fall back to demo data.

The frontend supports three explicit modes:

- `VITE_MARKET_DATA_MODE=api`: default; calls relative private API routes through the Vite proxy.
- `VITE_MARKET_DATA_MODE=demo`: uses clearly synthetic `TEST*` fixtures and displays a persistent `DEMO DATA` badge.

API mode does not fall back to synthetic fixtures on failure. Failures render explicit error states.

## Implemented Views

- Compact header with WH Alpha, Market Overview, Logout, and a meta/control bar for universe, period, data-as-of date, and freshness.
- Universe control with `Common Shares` as the default and `Common Shares + ADRs` as the only ordinary alternative; Legacy remains an internal rollback boundary.
- Market Benchmark Strip for SPY, QQQ, IWM, DIA, and selected-universe equal-weight return.
- Market Pulse cards for equal-weight return, median return, advancers/decliners, and up/down volume ratio.
- Market Breadth stacked bar with advancers, unchanged, decliners, counts, and percentages.
- Up/Down Volume comparison using share volume, not money flow.
- Sector Benchmark ETF 1D relative performance for the eleven fixed Select Sector SPDR tickers, including arithmetic return difference versus SPY.
- Apache ECharts Trading Activity Map treemap, defaulting to top 50 nodes with 50/75/100 controls.
- Top Gainers and Top Losers lists using the selected universe and price-discontinuity isolation.
- Collapsible Data Details panel with categorized quality flags and session metadata.
- Data Details separates Snapshot Status, Universe Funnel, Methodology Notes, Data Limitations, and Material Warnings.
- Loading, error, empty, and retry states.

## Trading Activity Map Semantics

Trading Activity Map uses:

- Size: `current_close * current_volume` proxy.
- Color: close-to-close return.
- Fixed diverging color clamp around +/-5% for readability.

It is explicitly not market-cap weighted, not sector grouped, not fund flow, and not money flow. Instrument type may be displayed as metadata but is not a sector taxonomy. See [Dashboard Universe V1](../product/dashboard-universe-v1.md).

Default node count is 50. The user may switch to 75 or 100 nodes. Labels avoid forced truncation: larger nodes show ticker and return, medium nodes show ticker, and small nodes rely on hover/detail views.

## Benchmark Semantics

The Market Benchmark Strip shows SPY, QQQ, IWM, DIA, and the selected universe equal-weight return. ETF benchmarks are context only and do not enter default stock breadth, movers, or Trading Activity Map.

Sector Benchmark ETFs show 1D return and `relative_to_spy_return`, defined as sector ETF return minus SPY return. This is not alpha, risk-adjusted performance, sector breadth, sector rotation, or fund flow.

## Freshness

The Dashboard displays the completed dataset session, a human-readable snapshot generation time with an explicit timezone, and XNYS calendar freshness. `Fresh` means the actual latest completed dataset session equals the expected latest completed session; stale data shows the exact session lag, and calendar failure shows `Calendar verification unavailable`. File/schema consistency validation remains a separate status and is not presented as proof of price correctness or corporate-action reconciliation.

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

The selector persists a validated stable ID in the `universe` URL query, supports browser history, normalizes invalid input to the activation default, and updates all Universe-dependent modules without using input as a file path.

## Not Implemented

- Public real-data deployment
- Frontend-stored credentials
- multi-user authentication or authorization
- public real-data display
- market-cap heatmap
- sector/industry constituent grouping
- theme rotation
- multi-day trend charts
- Event Layer
- Options, Portfolio, or AI modules
- intraday or real-time data
