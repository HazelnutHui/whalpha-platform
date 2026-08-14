# Open Questions

The following decisions remain open. Final workstation storage layout, frontend framework, backend framework, charting library, initial storage format, initial repository application layout, local frontend toolchain availability, Initial EOD Universe structure, classification boundary, normalized EOD logical contract boundary, minimal provider Protocol shape, synchronous EOD V1 boundary, minimal provider error taxonomy, first real EOD development provider, general public/private data boundary, unrestricted public display under the selected individual plan, Massive adapter configuration contract shape, mocked transport boundary, mocked mapping boundary, protected credential-file loader, standard-library HTTPS transport choice, actual Stocks reference entitlement smoke test, and minimal live reference request boundary are no longer open. See [Infrastructure](../operations/infrastructure.md), [Storage Provisioning](../operations/storage-provisioning.md), [ADR 0005](../decisions/0005-application-technology-stack.md), [ADR 0006](../decisions/0006-initial-eod-data-model-and-universe-boundaries.md), [ADR 0007](../decisions/0007-use-massive-for-private-eod-development.md), [Application Architecture](../architecture/application-architecture.md), [Initial EOD Universe](../product/initial-eod-universe.md), [Classification Boundary](../architecture/classification-boundary.md), [Normalized Market Data Contracts](../architecture/normalized-market-data-contracts.md), [Market Data Provider Boundary](../architecture/market-data-provider-boundary.md), [Massive Stocks Basic Evaluation](../providers/massive-stocks-basic-evaluation.md), and [Data Access Boundary](../operations/data-access-boundary.md).

- Final credential rotation and service-injection mechanism beyond the protected local credential file
- Exact private access-control mechanism before deploying provider-backed data
- Rate limiter implementation
- Grouped Daily one-session retrieval authorization and response verification
- Historical backfill strategy
- Adjustment reconciliation
- Identity resolution methodology
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
- Exact OCI deployment mechanism
- Cloudflare proxy state
- Cleanup of obsolete OCI port rules
- OCI swap strategy
- Data backup and retention policy
- Automatic relationship discovery methodology
- Parquet physical layout details
- Source revision reconciliation policy
- Issuer Master introduction threshold
- Whether public contract identifiers remain UUID-based across persistence
- Physical Decimal representation in Parquet
- Exact provider revision reconciliation behavior
