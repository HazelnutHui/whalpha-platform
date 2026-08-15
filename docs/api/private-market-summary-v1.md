# Private Market Summary V1

## Purpose

Private Market Summary V1 exposes read-only response contracts for close-to-close returns, Market Summary V1, liquidity-screened movers, and Liquidity Map V1.

## Status

Implemented for local/private development. Routes are default-disabled and are not authentication or authorization.

## Enablement

Routes are registered only when `TIP_ENABLE_PRIVATE_MARKET_DATA_ROUTES=true`.

## Routes

- `GET /api/v1/private/market/summary/latest`
- `GET /api/v1/private/market/movers/latest`
- `GET /api/v1/private/market/liquidity-map/latest`
- `GET /api/v1/private/market/returns/latest`

`returns/latest` supports bounded pagination with `limit` default 100, maximum 200, and `offset >= 0`.

## Decimal Responses

Decimal values are serialized as strings. Return values are decimal ratios: `0.05` means 5%.

## Liquidity Map Naming

The map endpoint is named Liquidity Map V1 because node size uses `current_close * current_volume`. It is not a market-cap heatmap, sector heatmap, fund-flow map, or money-flow map.

## Security Boundary

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
