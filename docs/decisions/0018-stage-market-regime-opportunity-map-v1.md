# ADR 0018: Stage Market Regime & Opportunity Map V1 as Transparent EOD Analytics

## Status

Accepted

## Date

2026-08-25

## Context

The product needs to help a discretionary short-horizon user understand market
conditions, find new stocks, time research/entry candidates, and manage existing
holdings. The current formal data supports completed EOD OHLC/volume history,
same-day stable Identity, active Common Share and ADRC memberships, and a large
resolved ETF set. It does not yet support point-in-time sector/industry
taxonomy, market cap, fundamentals, options/IV/Greeks, corporate-action
reconciliation, or true fund flows.

A useful first version must not wait for every future dataset, but it must not
invent sector membership, flow, option outcomes, or causal claims. Scores and
states must remain inspectable and reproducible.

## Decision

Implement the product in two data-capability layers:

- V1A provides Market Regime Core and a fixed, pre-registered ETF Relationship
  Map from formal EOD, same-day Identity, and Activation inputs.
- V1B adds sector breadth and formal stock opportunity transmission only after
  an effective-dated canonical taxonomy is completed.

Use fixed, versioned formulas, weights, thresholds, normalizers, pair lists,
risk gates, and hysteresis. Persist raw inputs, normalized values, effective
weights, score contributions, reason codes, counterevidence, invalidation,
missingness, and source fingerprints. Risk mode changes eligibility and ranking
only; it cannot alter source facts or the base score.

Price-derived ETF exposure remains a separately labelled proxy and cannot
populate sector/industry identity. Close-times-volume remains a participation
or liquidity proxy and cannot be called fund flow. Correlation is statistical
evidence, not causality. V1 evaluates underlying-stock opportunity and does not
simulate option outcomes.

Start with an offline `/tmp` Phase 1 calculation ledger and focused independent
oracle tests. Production snapshot, API, frontend, bundle, and deployment remain
separately authorized later phases.

## Consequences

- The project can deliver an explainable market-state core from existing data.
- Short history limits confidence and prevents robust 60-session relationship
  standardization and credible performance claims until more EOD accumulates.
- V1A can show ETF direction and price-derived stock exposure, but not formal
  sector breadth or sector membership.
- Every calculation is reproducible from exact completed sources, at the cost
  of more verbose ledgers and version governance.
- Future taxonomy, fundamentals, options, and flow datasets can extend the
  product without rewriting V1 facts or silently changing scores.

## Alternatives considered

### Wait for taxonomy, options, and fundamentals

Rejected because regime and registered ETF relationship analytics are useful
and verifiable now. Missing future data is better represented as a scoped V1B
dependency.

### Infer sector membership from price correlation

Rejected because statistical co-movement is not stable company identity and
would contaminate point-in-time classification history.

### Mine all ETFs or use an opaque learned score

Rejected for V1 because the 26-session baseline creates severe multiple-testing
and overfitting risk, and hidden weights would violate the product’s explanation
requirements.

### Change the base score by risk mode or market regime

Rejected because it obscures what changed. V1 exposes one fixed base score and
separate risk-mode gates/ranks; any future regime adjustment must be an explicit
additional contribution with a new version.
