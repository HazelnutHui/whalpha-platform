# Open Questions

The following decisions remain open. Final workstation storage layout, frontend framework, backend framework, charting library, initial storage format, initial repository application layout, local frontend toolchain availability, Initial EOD Universe structure, classification boundary, normalized EOD logical contract boundary, minimal provider Protocol shape, synchronous EOD V1 boundary, minimal provider error taxonomy, first real EOD development provider, general public/private data boundary, unrestricted public display under the selected individual plan, Massive adapter configuration contract shape, mocked transport boundary, mocked mapping boundary, protected credential-file loader, standard-library HTTPS transport choice, actual Stocks reference entitlement smoke test, minimal live reference request boundary, initial EOD Price Bar Parquet physical layout, mocked-fixture one-session ingestion service shape, content fingerprint behavior, idempotent partition publish behavior, first canonical EOD read/query service shape, default-disabled private route exposure, Decimal response serialization, close-to-close return calculation boundary, and the personal-prototype session login mechanism are no longer open. See [Infrastructure](../operations/infrastructure.md), [Storage Provisioning](../operations/storage-provisioning.md), [ADR 0005](../decisions/0005-application-technology-stack.md), [ADR 0006](../decisions/0006-initial-eod-data-model-and-universe-boundaries.md), [ADR 0007](../decisions/0007-use-massive-for-private-eod-development.md), [Application Architecture](../architecture/application-architecture.md), [Initial EOD Universe](../product/initial-eod-universe.md), [Classification Boundary](../architecture/classification-boundary.md), [Normalized Market Data Contracts](../architecture/normalized-market-data-contracts.md), [Market Data Provider Boundary](../architecture/market-data-provider-boundary.md), [Massive Stocks Basic Evaluation](../providers/massive-stocks-basic-evaluation.md), and [Data Access Boundary](../operations/data-access-boundary.md).

- Final credential rotation and service-injection mechanism beyond the protected local credential file
- Rate limiter implementation
- Historical backfill strategy
- Adjustment reconciliation
- Identity resolution methodology
- Rejected Massive reference type mapping policy
- Duplicate ticker handling policy for point-in-time reference snapshots
- Provider type `ETV` taxonomy decision after the completed 2026-08-13 Instrument Master snapshot
- Massive plan upgrade threshold
- Public demo data source
- Business/display/redistribution license threshold
- Candidate Discovery thresholds after real coverage evaluation
- Exact S&P 500/index constituent source
- Exact canonical traditional taxonomy source or mapping methodology
- Initial curated Theme list and membership methodology
- Initial Analytical Group basket definitions
- Options data source
- Database introduction threshold
- Cloudflare proxy state
- Cleanup of obsolete OCI port rules
- OCI swap strategy
- Data backup and retention policy
- Automatic relationship discovery methodology
- Parquet compaction strategy
- Source revision reconciliation policy
- Issuer Master introduction threshold
- Whether public contract identifiers remain UUID-based across persistence
- Physical Decimal representation in Parquet for future datasets beyond EOD Price Bar V1
- Exact provider revision reconciliation behavior
- Production session selection and exchange-calendar source
- Raw provider payload retention policy
- Production data-root publish review process for future datasets
- Formal multi-user authentication and authorization mechanism beyond the personal-prototype session login

- Traditional Market-Cap Sector Heatmap source requirements: market cap, sector taxonomy, point-in-time classification, and licensing boundary
- Post-deployment visual/runtime defect list, if any

- Trailing median dollar-volume rule after at least 20 completed sessions
- Explicit ADR/common-stock distinction if Instrument Master can support it
- Point-in-time sector constituent source and market-cap source for traditional heatmap
- Whether Trading Activity Map should later use a documented display transform for concentrated activity weights while preserving raw close-times-volume tooltip values
- Corporate-action verification source and adjustment reconciliation workflow for high-price or high-activity names such as SNDK
