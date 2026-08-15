# Private Market Summary V1

## Purpose

Private Market Summary V1 exposes read-only response contracts for close-to-close returns, Market Summary V1, liquidity-screened movers, the broad Liquidity Map V1, and Dashboard Overview V1.1.

## Status

Implemented for local/private development. Routes are default-disabled and are not authentication or authorization.

## Enablement

Routes are registered only when `TIP_ENABLE_PRIVATE_MARKET_DATA_ROUTES=true`.

## Routes

- `GET /api/v1/private/market/summary/latest`
- `GET /api/v1/private/market/movers/latest`
- `GET /api/v1/private/market/liquidity-map/latest`
- `GET /api/v1/private/market/returns/latest`
- `GET /api/v1/private/market/overview/latest`

`returns/latest` supports bounded pagination with `limit` default 100, maximum 200, and `offset >= 0`.

## Decimal Responses

Decimal values are serialized as strings. Return values are decimal ratios: `0.05` means 5%.

## Dashboard Overview V1.1

`overview/latest` returns a versioned dashboard payload with multiple universes, Market Benchmark Strip data, Sector Benchmark ETFs, and a Trading Activity Map projection. The default universe is `Tradable U.S.-Listed Equities V1`, displayed as `Tradable U.S. Equities`. See [Dashboard Universe V1](../product/dashboard-universe-v1.md).

The Market Benchmark Strip contains SPY, QQQ, IWM, DIA, and the selected universe equal-weight return. These benchmark rows are market context only and are not included in the default stock universe.

Sector Benchmark ETF rows include:

- `close_to_close_return`
- `relative_to_spy_return`

`relative_to_spy_return` is the arithmetic difference between the sector ETF return and SPY return. It is not alpha, factor attribution, risk-adjusted return, sector breadth, sector rotation, or fund flow.

The overview payload also includes:

- `snapshot_validation_status`, `file_schema_consistency_checks_passed` after file/schema/count/fingerprint validation
- `expected_latest_completed_session` and `actual_latest_completed_session`
- `session_lag`, nullable only when calendar evaluation is unavailable
- `freshness_status`: `fresh`, `stale`, or `unavailable`
- `calendar_id` and `freshness_checked_at`
- `snapshot_generated_at`, populated for static private dashboard snapshots as an exact UTC timestamp

## Liquidity and Trading Activity Naming

The legacy broad endpoint remains named Liquidity Map V1. Dashboard V1.1 displays the universe-filtered projection as Trading Activity Map. Node size uses `current_close * current_volume`; it is not a market-cap heatmap, sector heatmap, fund-flow map, or money-flow map. The frontend default display is top 50 nodes, with 50/75/100 controls.

## Security Boundary

The local React Market Dashboard V1 consumes these routes only when private routes are explicitly enabled in local development. Decimal values remain strings in the frontend API boundary and are parsed only for display/chart transforms.


Responses are provider-backed derived works and must remain private unless a separate public-display authorization and access-control decision is completed.

The route enable flag is a development switch only.

## Non-Goals

- authentication or authorization
- public API exposure
- frontend Dashboard rendering
- raw provider payloads
- filesystem paths or manifests
- market-cap or sector heatmap responses
- OCI deployment
