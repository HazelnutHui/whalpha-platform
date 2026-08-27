# Architecture Decision Records

ADRs record material project decisions and their context.

## Status Values

- Proposed
- Accepted
- Superseded
- Rejected

## Format

Each ADR should include:

- Title
- Status
- Date
- Context
- Decision
- Consequences
- Alternatives Considered

## Records

- [0001: Use the Workstation as the Project Source of Truth](0001-workstation-source-of-truth.md)
- [0002: Separate Compute and Public Web Serving](0002-separate-compute-and-web-serving.md)
- [0003: Introduce a Market Data Provider Boundary](0003-market-data-provider-boundary.md)
- [0004: Start with a Lightweight Event Layer](0004-lightweight-event-layer-first.md)
- [0005: Application Technology Stack](0005-application-technology-stack.md)
- [0006: Initial EOD Data Model and Universe Boundaries](0006-initial-eod-data-model-and-universe-boundaries.md)
- [0007: Use Massive for Private EOD Development](0007-use-massive-for-private-eod-development.md)
- [0008: Use Partitioned Parquet for Initial Canonical EOD Persistence](0008-use-partitioned-parquet-for-initial-canonical-eod-persistence.md)
- [0009: Use Stable Provider Identifiers for Canonical Instrument Identity](0009-use-stable-provider-identifiers-for-canonical-instrument-identity.md)
- [0010: Represent Aggregate Volume as Decimal](0010-represent-aggregate-volume-as-decimal.md)
- [0011: Publish Private Dashboard Snapshots as Authenticated Static Assets](0011-publish-private-dashboard-snapshots-as-authenticated-static-assets.md)
- [0012: Use Server-Side Sessions for the Private Dashboard](0012-use-server-side-sessions-for-private-dashboard.md)
- [0013: Establish Dashboard Universe V1 for Market Overview](0013-establish-dashboard-universe-v1.md)
- [0014: Use an Exchange Calendar for EOD Freshness](0014-use-an-exchange-calendar-for-eod-freshness.md)
- [0015: Govern Security Types and Universe Eligibility](0015-govern-security-types-and-universe-eligibility.md)
- [0016: Publish Versioned Trailing Liquidity Shadow Results](0016-publish-versioned-trailing-liquidity-shadow-results.md)
- [0017: Activate Selectable Dashboard Universes](0017-activate-selectable-dashboard-universes.md)
- [0018: Stage Market Regime & Opportunity Map V1 as Transparent EOD Analytics](0018-stage-market-regime-opportunity-map-v1.md)
- [0019: Offer Equal-Capability Guest Sessions](0019-offer-equal-capability-guest-sessions.md)
- [0020: Publish a Bounded Opportunity Candidate Consumer](0020-publish-bounded-opportunity-candidate-consumer.md)
- [0021: Separate Candidate Leadership from Entry Geometry](0021-separate-candidate-leadership-from-entry-geometry.md)
- [0022: Bind Daily Candidate Calculation to a Verified Prior Audit](0022-bind-daily-candidate-calculation-to-a-verified-prior-audit.md)
- [0023: Preserve Market Regime State Prefix Across As-Of Sessions](0023-preserve-market-regime-state-prefix-across-as-of-sessions.md)
- [0024: Bind Daily Market Regime State to Verified Upstream Audits](0024-bind-daily-market-regime-state-to-verified-upstream-audits.md)
- [0025: Share Formally Validated Panels Between Dell Stages](0025-share-formally-validated-panels-between-dell-stages.md)
- [0026: Stream and Resume Candidate Audit Artifacts](0026-stream-and-resume-candidate-audit-artifacts.md)
- [0027: Make Candidate Validation Tiers Explicit](0027-make-candidate-validation-tiers-explicit.md)
- [0028: Parallelize Only Independent Cold-Replay Oracle Sessions](0028-parallelize-only-independent-cold-replay-oracle-sessions.md)
- [0029: Separate Daily Run Planning from Authorized Execution](0029-separate-daily-run-planning-from-authorized-execution.md)
- [0030: Custody One Offline Daily Action at a Time](0030-custody-one-offline-daily-action-at-a-time.md)
- [0031: Separate Market Close from Provider Readiness](0031-separate-market-close-from-provider-readiness.md)
- [0032: Custody Provider Fetch Attempts Before Automation](0032-custody-provider-fetch-attempts-before-automation.md)
- [0033: Bound Standing Daily Data Authorization](0033-bound-standing-daily-data-authorization.md)
- [0034: Coordinate Exactly One Daily Transition](0034-coordinate-exactly-one-daily-transition.md)
- [0035: Custody Canonical Daily Apply](0035-custody-canonical-daily-apply.md)
- [0036: Compose Authorized Daily Data Capabilities](0036-compose-authorized-daily-data-capabilities.md)
