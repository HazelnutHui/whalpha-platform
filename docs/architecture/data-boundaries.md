# Data Boundaries

## Confirmed Boundary

Analysis code should consume normalized internal interfaces rather than vendor response schemas.

The Market Data Provider boundary should cover:

- reference data
- bars/aggregates
- snapshots
- corporate actions
- options data
- portfolio/account data

Raw, normalized, and derived data must remain conceptually distinct.


## Accepted Logical Contracts

The Initial EOD data boundary is now documented as accepted logical contracts:

- [Initial EOD Universe](../product/initial-eod-universe.md)
- [Classification Boundary](classification-boundary.md)
- [Normalized Market Data Contracts](normalized-market-data-contracts.md)
- [Data Contracts](../data-contracts/README.md)

Instrument Master V1 and EOD Price Bar V1 are implemented as Python/Pydantic validation models. The remaining contracts are logical-only. EOD Price Bar V1 now has an explicit PyArrow Parquet schema and mocked-fixture persistence tests. The remaining contracts are not implemented as Parquet schemas, provider adapters, or database tables.


## Implemented Provider Boundary

The minimal synchronous provider boundary is implemented in `tip_api.providers.market_data` and documented in [Market Data Provider Boundary](market-data-provider-boundary.md). It currently supports only Instrument Master and EOD Price Bar retrieval through canonical contracts.

The Massive adapter boundary now implements configuration validation, credential redaction, secure credential-file loading, a minimal standard-library HTTPS transport, injected fake transport tests, and local response mapping tests. One read-only Stocks reference smoke test has verified authentication and reference entitlement. A mocked-fixture EOD Price Bar ingestion and Parquet persistence slice exists for temporary test roots. The first 2026-08-13 Grouped Daily canonical EOD partition is published. A provider-neutral read repository and default-disabled private query API can read completed canonical sessions locally. Analytics, Dashboard data flow, formal authentication, public provider-backed routes, and provider-backed deployment are not implemented.

## Provider Selection Status

Massive Stocks Basic is accepted as the first private EOD development provider. This is an adapter candidate and private development source, not a permanent exclusive provider, public display authorization, redistribution authorization, or options provider decision.

- Massive: first broad-market EOD development provider candidate for private use.
- IBKR: portfolio, positions, selected instruments, and selected options.
- Options provider: may be selected separately later.

Provider choice must remain replaceable. Provider response fields must not become canonical contracts.

## Data Authorization Boundary

The local React Market Dashboard V1 is provider-backed derived content when run in API mode. It must remain private and local until a formal access-control mechanism and provider display boundary are accepted. Demo mode is data-free and uses clearly synthetic fixtures.
Snapshot mode is also provider-backed derived content. The static `/private-data/` JSON snapshot must share the same private authentication boundary as `/dashboard/` and must not be publicly exposed.



## Instrument Identity Boundary

Provider Instrument Identity V1 is now an explicit canonical boundary. Ticker and CIK alone are insufficient for security-level identity. The first Massive All Tickers snapshot attempt remained private, did not persist raw payloads, and did not publish because quality gates failed.


See [Data Access Boundary](../operations/data-access-boundary.md) for the
accepted public data-free login/demo and private provider-backed Dashboard
boundary.

Massive-backed Market Data and derived works must remain private-owner only unless explicit public-display or redistribution authorization, a suitable business/display agreement, or an alternative public-display data source is documented. The private route enable flag is not authentication or authorization. Public accessibility does not grant redistribution rights.

Licensing and entitlement must be reviewed before broader distribution, commercial use, or public provider-backed content.

## Prohibited in Repository

Do not record API keys, subscription secrets, account credentials, or provider tokens in Git.
