# Open Questions

Only unresolved decisions belong here. Resolved rationale and implementation
history remain in ADRs, the changelog, and the relevant architecture or
operations document.

## Security Type Governance

- Should `material_return_outlier_review` remain an overlapping display/analytics review signal, or become a future versioned Universe quarantine policy after corporate-action evidence exists?

- What authoritative issuer/domicile evidence coverage threshold should eventually gate Core/Broad production activation after Phase B2B evidence is reviewed?
- Which non-content landing-page structural fields are sufficient to diagnose official table-shape changes while preserving the no-raw-HTML boundary?
- Which bounded SEC bulk sources and quality gates should be authorized for Phase B2B after private User-Agent provisioning?
- What authoritative evidence will close remaining domicile, REIT subtype, SPAC, partnership, and security-to-filer gaps without ticker-only joins?

- Core is selected as the future default and Broad as the secondary view; when can evidence coverage safely activate them?
- Which point-in-time source will provide issuer structure, domicile/incorporation, ADR status, REIT subtype, BDC/CEF/SPAC status, and security form at sufficient coverage?
- How should reviewed overrides be approved, versioned, and retired without backfilling current facts into history?
- What approval and retirement workflow should govern future rows in the now-completed Reviewed Eligibility Override V1 dataset?
- What operational cadence should create a new activation after membership evidence, EOD session, or reviewed overrides advance?
- What reviewed evidence would permit a historical session to use an identity snapshot other than the same date without introducing latest-resolver or survivorship bias?

## Data and operations

- Final credential rotation and service-injection mechanism beyond the protected local credential file
- Provider-wide rate limiter beyond the bounded historical runner
- Exact current provider entitlement and permitted endpoint/use scope for
  retained history, future repairs, and new datasets
- Which written permission, license, or alternate source will support the
  confirmed equal-capability guest/credential shared product? Owner-only
  market-analysis serving is not a permitted fallback.
- Which exact raw EOD plan clears all six Source Permission Governance uses,
  including indefinite canonical retention and browser/API delivery, and what
  deletion obligation remains after termination? Use the prepared, unsent
  `Source Selection and Permission Inquiry Packet V1`; do not infer answers
  from marketing pages.
- Which all-exchange lifecycle composition supplements Nasdaq Daily List for
  non-Nasdaq delistings, merger consideration, successor identity, spinoffs,
  and last-tradable-session evidence?
- What account-specific permission supports owner non-display calculations,
  derived strategy research, retained history, and required deletion on
  provider termination?
- Exact adjustment formulas, basis convention, and independent split/dividend
  reconciliation fixtures before Adjustment Ledger implementation
- Rejected Massive reference type mapping policy
- Duplicate ticker handling policy for point-in-time reference snapshots
- Massive plan upgrade threshold
- Business/display/redistribution license threshold
- Candidate Discovery thresholds after real coverage evaluation
- Exact S&P 500/index constituent source
- Initial curated Theme list and membership methodology
- Initial Analytical Group basket definitions
- Options data source
- Database introduction threshold
- Cloudflare proxy state
- Cleanup of obsolete OCI port rules
- OCI swap strategy
- Backup and recovery policy for no-expiry canonical history; rebuildable panel
  caches have a 90-day minimum direction but no deletion job is authorized
- Automatic relationship discovery methodology
- Parquet compaction strategy
- Source/provider revision reconciliation policy
- Issuer Master introduction threshold
- Whether public contract identifiers remain UUID-based across persistence
- Physical Decimal representation in Parquet for future datasets beyond EOD Price Bar V1
- Operational ownership and update cadence for the accepted offline XNYS calendar dependency
- Whether any future source requires bounded raw-response retention; the
  accepted default is no raw provider response-body retention
- Production data-root publish review process for future datasets
- Formal multi-user authentication and authorization mechanism beyond the personal-prototype session login

## Product inputs

- Traditional Market-Cap Sector Heatmap sources: market cap, canonical sector
  taxonomy, point-in-time classification, constituents, and licensing boundary
- Point-in-time sector taxonomy and constituent breadth/rotation policy for both activated universes
- Explicit ADR/common-stock distinction if Instrument Master can support it
- Whether Trading Activity Map should later use a documented display transform for concentrated activity weights while preserving raw close-times-volume tooltip values
- Corporate-action verification source and adjustment reconciliation workflow for high-price or high-activity names such as SNDK
