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

Instrument Master V1 and EOD Price Bar V1 are implemented as Python/Pydantic
validation models with point-in-time/per-session PyArrow persistence, formal
manifests, and canonical readers. Provider Identity and ticker resolution are
also physically implemented. Universe Membership V1, Corporate Action V1, and
the other listed logical-only contracts are not implemented as physical
Parquet datasets, provider adapters, or database tables.


## Implemented Provider Boundary

The minimal synchronous provider boundary is implemented in `tip_api.providers.market_data` and documented in [Market Data Provider Boundary](market-data-provider-boundary.md). It currently supports only Instrument Master and EOD Price Bar retrieval through canonical contracts.

The Massive boundary implements configuration validation, credential
redaction, protected credential loading, bounded HTTPS transport, fake-
transport tests, All Tickers pagination, Grouped Daily mapping, canonical
Identity/EOD Apply workflows, and request custody. Bounded operations produced
the current 30 Identity snapshots and 29 EOD partitions. Provider-neutral
readers, private analytics, protected Snapshot serving, Session authentication,
and deployment exist outside the adapter. Corporate actions, lifecycle,
verified adjustments, general historical research backfill, and unattended
scheduling remain unimplemented.

The future performance-evaluation boundary is defined separately in
[Historical Research Data Foundation V1](historical-research-data-foundation-v1.md).
It requires point-in-time daily membership, corporate actions, lifecycle and
terminal evidence, explicit adjustment ledgers, and bounded coverage manifests
before a historical panel can be declared research ready.

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
