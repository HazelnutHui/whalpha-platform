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

Instrument Master V1 and EOD Price Bar V1 are implemented as Python/Pydantic validation models. The remaining contracts are logical-only. None of the contracts are implemented as Parquet schemas, provider adapters, or database tables.


## Implemented Provider Boundary

The minimal synchronous provider boundary is implemented in `tip_api.providers.market_data` and documented in [Market Data Provider Boundary](market-data-provider-boundary.md). It currently supports only Instrument Master and EOD Price Bar retrieval through canonical contracts.

No real provider adapter, credential handling, network integration, ingestion, persistence, or entitlement verification is implemented.

## Provider Selection Status

Massive Stocks Basic is accepted as the first private EOD development provider. This is an adapter candidate and private development source, not a permanent exclusive provider, public display authorization, redistribution authorization, or options provider decision.

- Massive: first broad-market EOD development provider candidate for private use.
- IBKR: portfolio, positions, selected instruments, and selected options.
- Options provider: may be selected separately later.

Provider choice must remain replaceable. Provider response fields must not become canonical contracts.

## Data Authorization Boundary

See [Data Access Boundary](../operations/data-access-boundary.md) for the accepted public placeholder, public data-free demo, and private provider-backed dashboard boundary.

Massive-backed Market Data and derived works must remain private-owner only unless explicit public-display or redistribution authorization, a suitable business/display agreement, or an alternative public-display data source is documented. Public accessibility does not grant redistribution rights.

Licensing and entitlement must be reviewed before broader distribution, commercial use, or public provider-backed content.

## Prohibited in Repository

Do not record API keys, subscription secrets, account credentials, or provider tokens in Git.
