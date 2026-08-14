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

## Proposed Providers

- Massive: proposed primary stock/ETF/market-structure backbone.
- IBKR: portfolio, positions, selected instruments, and selected options.
- Options provider: may be selected separately later.

Provider choice must remain replaceable.

## Data Authorization Boundary

The prototype is for personal use. Public accessibility does not automatically grant redistribution rights. Delayed/EOD or derived displays should be used until entitlements are confirmed.

Licensing must be reviewed before broader distribution or commercial use.

## Prohibited in Repository

Do not record API keys, subscription secrets, account credentials, or provider tokens in Git.
