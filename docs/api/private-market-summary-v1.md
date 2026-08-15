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

`overview/latest` returns a versioned dashboard payload with multiple universes, Sector Benchmark ETFs, and a Trading Activity Map projection. The default universe is `Tradable U.S.-Listed Equities V1`, displayed as `Tradable U.S. Equities`. See [Dashboard Universe V1](../product/dashboard-universe-v1.md).

## Liquidity and Trading Activity Naming

The legacy broad endpoint remains named Liquidity Map V1. Dashboard V1.1 displays the universe-filtered projection as Trading Activity Map. Node size uses `current_close * current_volume`; it is not a market-cap heatmap, sector heatmap, fund-flow map, or money-flow map.

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
