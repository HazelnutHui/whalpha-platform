# Trading Intelligence API

## Purpose

`apps/api` contains the provider-neutral contracts, canonical readers,
analytics and research services, guarded provider workflows, persistence
boundaries, and the default-disabled private FastAPI surface.

Exact sessions, row counts, fingerprints, subscriptions, and Production
releases belong in
[current context](../../docs/project/current-context.md), not this package
guide.

## Runtime boundary

The default HTTP application exposes only:

- `GET /api/v1/health`

Local/private market-data routes are registered only when
`TIP_ENABLE_PRIVATE_MARKET_DATA_ROUTES=true`, including bounded EOD session,
bar, summary, mover, return, liquidity-map, and overview reads. This flag is a
development switch, not authentication or deployment permission.

Production currently serves immutable static Snapshots through OCI; no
production FastAPI service reads canonical Dell data remotely.

## Implemented domains

- stable-ID Instrument Master, provider Identity, ticker Resolver, and
  effective-dated security evidence;
- canonical EOD bars, offline XNYS session logic, Parquet manifests, formal
  readers, and bounded query services;
- provisional provider-form Primary/Secondary Universe activation and
  prospective daily Membership custody;
- Market Regime, ETF relationships, sector ETF rotation, Candidate Baseline
  V1, Entry Geometry, Strategy Channels, and visual-context analytics;
- immutable Market Intelligence and Dashboard Snapshot publication contracts;
- partial corporate-action, split-only fact, sparse adjustment, lifecycle-
  review, and Historical Coverage mechanics;
- Quant Research Lab model records, result semantics, chronological research,
  statistics, cost scenarios, holdout custody, and Strong-Leader Pullback
  fixture-only input mechanics plus private outcome-blind reconstructed-
  population diagnostics; and
- guarded daily planning, acquisition, Apply, analytics, publication, bundle,
  deployment-custody, recovery, and read-only scheduler contracts.

Implemented mechanics do not imply complete research data, a real backtest,
model activation, or an unattended write-capable scheduler. Consult
[current status](../../docs/project/current-status.md).

## Provider boundary

Provider-neutral interfaces live under `tip_api.providers.market_data`.
Massive-specific configuration, protected credential loading, transport,
mapping, request custody, Identity, and Grouped Daily workflows remain inside
`tip_api.providers.massive`. Provider schemas are normalized before domain
calculation.

Credentials, Authorization values, request secrets, and raw provider bodies
must never be committed, printed, or copied into browser/OCI artifacts. Live
requests and canonical Apply remain guarded operational actions.

## Quantitative research boundary

Quant Research Lab separates method records, fixture evidence, real event
studies, portfolio simulations, lifecycle, and independent Candidate
activation. Strong-Leader Pullback is the first program; no real performance
result or Candidate authority exists.

ADR 0194 defines a future bounded AI Quant Research Factory. Specialized
agents may assist hypothesis, data, implementation, statistics, cost,
red-team, reproduction, and shadow stages only through finite experiment
budgets and stage-isolated data. Dell deterministic code remains the numerical
authority. No agent orchestration service is implemented yet.

## Local setup and tests

Use the repository-level
[Local Development](../../docs/development/local-development.md) instructions
and runner so linked worktrees resolve the project environment correctly:

```bash
scripts/dev/run-project-python.sh -m pytest apps/api/tests
```

## Non-goals

- unrestricted public APIs over canonical data;
- a production API service on OCI;
- automated trading or order execution;
- opaque or ungoverned model search;
- a database/ORM without measured need; and
- distributed research infrastructure before the workstation path requires it.
