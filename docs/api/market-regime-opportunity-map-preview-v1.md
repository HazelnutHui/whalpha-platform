# Market Regime & Opportunity Map Preview API V1

## Formal Production source

The response contract is unchanged when sourced from formal Market Intelligence.
`TIP_ENABLE_MARKET_INTELLIGENCE_ROUTES=true` selects the active reader once at
startup; preview and formal flags are mutually exclusive. With neither, routes
remain absent. Snapshot mode reads the two-record
`market-regime-overviews.json` envelope through the same response parser.

## Boundary

Contract `market-regime-opportunity-map-api/1.0` is a read-only, private local
preview API. It preserves the existing session boundary and has no role-based
analytics differences. It does not implement guest access, Production
publication, snapshot selection, or automatic calculation.

The routes are registered only when both are explicit:

```text
TIP_ENABLE_MARKET_REGIME_PREVIEW_ROUTES=true
TIP_MARKET_REGIME_PREVIEW_BUNDLE=/tmp/<explicit-completed-bundle>
```

Without that configuration, the existing application and Health endpoint are
unchanged and the preview routes return `404` because they are not registered.
Invalid configured custody fails application startup rather than serving a
partial response.

## Endpoints

### `GET /api/v1/private/market-regime/overview`

Optional query: `universe_id`. Omission selects the first/default `Common
Shares` Universe. An unknown ID returns `422`.

The response includes:

- API and preview versions, bundle/source fingerprints, as-of and source range;
- fixed Primary-first Universe catalog and selected Universe;
- selected Phase 1a Composite, all five dimensions and raw ledgers;
- candidate/confirmed Phase 1b state, state history, explanations, thresholds,
  missingness, and reason codes;
- all 16 current registered ETF relationships in registry order with complete
  5/10/20 metrics and fixed evidence/counterevidence;
- exactly 16 contemporaneous regime comparisons for the selected Universe;
- short-history warnings and quality gates.

ETF relationship values are identical for both Universe queries. Only the
regime record and contemporaneous comparison context change.

### `GET /api/v1/private/market-regime/relationships/{pair_id}`

Returns one registered definition, current metrics/explanation, selected-
Universe comparison, and its chronological Phase 2 history. Unknown pair or
Universe returns `404`.

## Numeric and error semantics

Decimal facts are strings; counts are integers. NaN and Infinity are forbidden.
Unavailable analytics remain null and carry an availability value,
`missing_reason`, and reason codes. Arrays have stable order. The server never
silently mixes source versions or emits fewer than all 16 pairs in the overview.

Reliability expresses source completeness and rule agreement, not predictive
probability. Correlation is not causation, price/volume is not fund flow, and
the response is research context rather than a recommendation.
