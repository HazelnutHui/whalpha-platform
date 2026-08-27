# Documentation Index

- [Authoritative current context](project/current-context.md): compact,
  evidence-scoped handoff for new tasks and devices.
- [Current status](project/current-status.md): current product and operational
  summary; historical execution detail belongs in changelog and audits.
- [Market Regime & Opportunities V1 product specification](product/market-regime-opportunity-map-v1.md)
- [Market Regime & Opportunity Map V1 data contract](data-contracts/market-regime-opportunity-map-v1.md)
- [Market Regime & Opportunity Map V1 architecture and implementation plan](architecture/market-regime-opportunity-map-v1.md)
- [Dashboard Snapshot V2 data contract](data-contracts/dashboard-snapshot-v2.md)
- [Same-Day Identity and EOD Catch-Up V1](data-contracts/same-day-identity-eod-catchup-v1.md)
- [Dashboard Universe Funnel](product/dashboard-universe-funnel.md)
- [Dashboard Snapshot V2 operations](operations/dashboard-snapshot-publication.md)

## Security Type Governance

- [Security Classification V1](data-contracts/security-classification-v1.md)
- [ADR 0015](decisions/0015-govern-security-types-and-universe-eligibility.md)
- [2026-08-14 classification audit](audits/security-type-classification-2026-08-14.md)
- [Provider security-type evidence architecture](architecture/provider-security-type-evidence.md)
- [SEC issuer-structure evidence architecture](architecture/sec-issuer-structure-evidence.md)
- [SEC User-Agent provisioning](operations/sec-user-agent-provisioning.md)
- [SEC issuer-structure evidence operation](operations/sec-issuer-structure-evidence.md)
- [SEC Phase B2B 2026-08-14 audit](audits/sec-issuer-structure-evidence-2026-08-14.md)
- [Massive security-type evidence operation](operations/massive-security-type-evidence.md)
- [2026-08-14 provider-evidence audit](audits/security-type-provider-evidence-2026-08-14.md)

This directory is the project knowledge base. It separates confirmed facts from proposals and deferred work.

## Product

- [Market Regime & Opportunities V1](product/market-regime-opportunity-map-v1.md): Transparent regime, registered ETF relationships, opportunity stages, risk modes, and validation design.
- [Vision](product/vision.md): Product principles and UI language.
- [Scope](product/scope.md): Phase 1 scope, deferred work, and explicit non-goals.
- [Dashboard V1](product/dashboard-v1.md): Confirmed first dashboard structure and target behavior.
- [Dashboard Universe V1](product/dashboard-universe-v1.md): Dashboard V1.1 operating-equity universe, ETF benchmark, and Trading Activity Map boundary.
- [Dashboard Universe Activation V1](data-contracts/dashboard-universe-activation-v1.md): Completed selectable-Universe policy and publication contract.
- [Dashboard Universe Activation V2](data-contracts/dashboard-universe-activation-v2.md): Immutable revision, atomic active pointer, V1 compatibility, and separate rollback contract.
- [Initial EOD Universe](product/initial-eod-universe.md): Accepted V1 universe layers and Candidate Discovery thresholds.

## Architecture

- [Market Regime & Opportunity Map V1](architecture/market-regime-opportunity-map-v1.md): Offline V1A/V1B data flow, six implementation phases, tests, and rollback boundaries.
- [System Context](architecture/system-context.md): Logical system flow and infrastructure responsibilities.
- [Application Architecture](architecture/application-architecture.md): Accepted target application architecture and runtime boundaries.
- [Private Dashboard Publication](architecture/private-dashboard-publication.md): Static private dashboard snapshot and OCI bundle architecture.
- [Market Session Calendar and Freshness](architecture/market-session-calendar.md): Offline XNYS session completion and Dashboard freshness boundary.
- [Classification Boundary](architecture/classification-boundary.md): Accepted Sector/Industry, Theme, and Analytical Group boundary.
- [Normalized Market Data Contracts](architecture/normalized-market-data-contracts.md): Accepted V1 logical market-data contract boundary.
- [Market Data Provider Boundary](architecture/market-data-provider-boundary.md): Implemented minimal synchronous provider Protocol, query models, capabilities, and errors.
- [EOD Parquet Persistence](architecture/eod-parquet-persistence.md): Implemented EOD Price Bar Parquet persistence boundary and first published canonical EOD session.
- [Trailing Liquidity Shadow Publication](architecture/trailing-liquidity-shadow-publication.md): Versioned offline metric/decision Parquet publication with a final logical completion marker.
- [Full-Base Trailing Liquidity Scope Review V1](data-contracts/trailing-liquidity-full-base-scope-review-v1.md): Complete provider-evidence base, decision ledger, funnel, set diff, and shadow publication contract.
- [Universe Pre-Activation Review](architecture/universe-pre-activation-review.md): Reviewed stable-ID override overlay and atomic shadow review publication.
- [Dashboard Universe Activation](architecture/dashboard-universe-activation.md): Formal reader, analytics, snapshot, and selector boundary.
- [Canonical Market Data Query Boundary](architecture/canonical-market-data-query-boundary.md): Implemented read repository, query service, and default-disabled private API boundary.
- [EOD Return Analytics](architecture/eod-return-analytics.md): Close-to-close returns, Market Summary V1, movers, and Liquidity Map V1 semantics.
- [Instrument Identity Resolution](architecture/instrument-identity-resolution.md): Deterministic provider identity mapping and current Instrument Master snapshot gate result.
- [Data Boundaries](architecture/data-boundaries.md): Market Data Provider boundary and data authorization rules.
- [Event Layer](architecture/event-layer.md): Lightweight event positioning and deferred long-term model.

## Data Contracts

- [Data Contracts Index](data-contracts/README.md)
- [Market Regime & Opportunity Map V1](data-contracts/market-regime-opportunity-map-v1.md)
- [Instrument Master V1](data-contracts/instrument-master-v1.md)
- [EOD Price Bar V1](data-contracts/eod-price-bar-v1.md)
- [Corporate Action V1](data-contracts/corporate-action-v1.md)
- [Classification V1](data-contracts/classification-v1.md)
- [Universe Membership V1](data-contracts/universe-membership-v1.md)
- [Provider Instrument Identity V1](data-contracts/provider-instrument-identity-v1.md)
- [Provider Ticker Resolver V1](data-contracts/provider-ticker-resolver-v1.md)
- [Trailing Liquidity Shadow Publication V1](data-contracts/trailing-liquidity-shadow-v1.md)
- [Reviewed Eligibility Override V1](data-contracts/reviewed-eligibility-override-v1.md)
- [Dashboard Universe Activation V1](data-contracts/dashboard-universe-activation-v1.md)

## Providers

- [Provider Evaluations](providers/README.md)
- [Massive Stocks Basic Evaluation](providers/massive-stocks-basic-evaluation.md): Accepted first private EOD development provider.
- [Massive Adapter Boundary](providers/massive-adapter-boundary.md): Configuration, credential, transport, smoke-test, and mapping boundary.

## API

- [API Index](api/README.md)
- [Private EOD Market Data V1](api/private-eod-market-data-v1.md): Default-disabled private canonical EOD query responses.
- [Private Market Summary V1](api/private-market-summary-v1.md): Private Market Summary, movers, returns, Dashboard Overview V1.1, and Trading Activity Map response contracts.

## Frontend

- [Frontend Index](frontend/README.md)
- [Market Dashboard V1](frontend/market-dashboard-v1.md): Local React dashboard for private Market Summary, Movers, Liquidity Map, and data-quality views.
- [Frontend interface internationalization](frontend/interface-internationalization.md): Typed English/Simplified Chinese catalog, URL and localStorage precedence, terminology, and guest-reuse boundary.
- [Market Regime & Opportunities frontend](frontend/market-regime-opportunity-map-preview.md): Shared shell, local/production presentation, audit details, and immutable payload boundary.

## Operations

- [Local build artifact retention](operations/local-build-artifact-retention.md): retained rollback/current bundles and safe ignored-output cleanup boundary.
- [Infrastructure](operations/infrastructure.md): Non-sensitive infrastructure facts.
- [Deployment Boundary](operations/deployment-boundary.md): Source-of-truth and deployment constraints.
- [OCI Private Dashboard Deployment](operations/oci-private-dashboard-deployment.md): Private static Dashboard deployment status and operations boundary.
- [Private Dashboard Access](operations/private-dashboard-access.md): Session credential boundary, rotation, and manual verification runbook.
- [Dashboard Universe Activation](operations/dashboard-universe-activation.md): Dry-run, one-apply, verification, and rollback boundary.
- [Market Intelligence Publication V1](data-contracts/market-intelligence-publication-v1.md): Immutable language-neutral analytics and reader contract.
- [Opportunity Candidate Publication V1](data-contracts/opportunity-candidate-publication-v1.md): Bounded, language-neutral Candidate consumer and lineage contract.
- [Candidate Entry Geometry V1](data-contracts/candidate-entry-geometry-v1.md): Offline source audit and additive consumer contract separating leadership quality from entry location and chase risk.
- [Candidate Pipeline Performance](operations/candidate-pipeline-performance.md): Dell-only compute/data authority, worktree-safe runner, measured baseline, and deterministic optimization sequence.
- [Daily EOD Automation Control Plane](operations/daily-eod-automation.md): XNYS/provider readiness, bounded retry, provider-attempt custody, exact-session planning, single-action offline execution, interruption recovery, and remaining unattended-operation gates.
- [ADR 0022: Verified-prior Candidate increment](decisions/0022-bind-daily-candidate-calculation-to-a-verified-prior-audit.md): separates daily append validation from the cold full-replay reference.
- [ADR 0030: Single-action daily custody](decisions/0030-custody-one-offline-daily-action-at-a-time.md): binds one offline action to an unchanged plan, immutable journal, lock, post-action re-plan, and inspection-only recovery.
- [ADR 0031: Market close versus provider readiness](decisions/0031-separate-market-close-from-provider-readiness.md): defines the network-free stabilization, bounded retry, alert, and oldest-gap recovery policy.
- [ADR 0032: Provider-attempt custody](decisions/0032-custody-provider-fetch-attempts-before-automation.md): reserves and reconciles exact provider attempts under the shared immutable daily journal without executing them.
- [ADR 0033: Standing daily data authorization](decisions/0033-bound-standing-daily-data-authorization.md): defines an expiring, externally SHA-pinned, default-deny scope for exact Identity/EOD fetch and canonical apply without activating it.
- [ADR 0034: One-transition daily coordination](decisions/0034-coordinate-exactly-one-daily-transition.md): joins planning, readiness, recovery, authorization review, and offline execution while invoking at most one explicitly installed capability.
- [ADR 0035: Canonical daily Apply custody](decisions/0035-custody-canonical-daily-apply.md): reserves exact approved Identity/EOD writes and classifies interruption without replaying or guessing about partial `/data` state.
- [ADR 0036: Authorized daily data capabilities](decisions/0036-compose-authorized-daily-data-capabilities.md): composes external authorization, acquisition/Apply custody, exact HTTP request counts, and existing Massive boundaries without installing or activating them.
- [ADR 0037: Host-gated one-transition CLI](decisions/0037-gate-one-transition-cli-with-host-runtime.md): keeps capability ports default-absent and independently proves the external host config, actual Dell/source/clean revision, and explicit invocation opt-in before installation.
- [ADR 0038: One-transition recovery routing](decisions/0038-route-one-interrupted-daily-transition.md): formally rereads one exact pending journal event and invokes only its matching no-request/no-replay recovery boundary.
- [ADR 0039: Daily alert intent](decisions/0039-separate-daily-alert-intent-from-delivery.md): preserves alert-required state and emits a stable deduplication envelope without claiming persistence or notification delivery.
- [ADR 0040: Daily alert delivery custody](decisions/0040-custody-one-daily-alert-delivery-attempt.md): records one immutable pre-send reservation and bounded terminal evidence while prohibiting automatic replay of an ambiguous attempt.
- [ADR 0041: External SMTP daily alerts](decisions/0041-deliver-daily-alerts-through-external-smtp.md): adds a default-disabled, exact-revision email adapter with external owner-only config and credentials behind alert custody.
- [ADR 0042: Joint external-control preflight](decisions/0042-preflight-external-daily-controls-together.md): reconciles host, data-authorization, and email artifacts without reading credentials, networking, writing, or granting rehearsal/scheduler authority.
- [ADR 0043: Explicit post-coordination email](decisions/0043-compose-explicit-email-delivery-after-coordination.md): composes alert intent, at-most-once custody, and SMTP only after one formal coordinator result and explicit CLI opt-in.
- [ADR 0044: Data-only external preflight](decisions/0044-allow-data-only-preflight-when-email-is-deferred.md): permits an explicit no-email review of the full daily data scope without weakening authorization or implying an alert channel.
- [ADR 0045: Safe provider failure evidence](decisions/0045-retain-safe-provider-failure-evidence.md): retains bounded request counts and numeric HTTP status without response content so failed acquisition can be diagnosed without replay.
- [ADR 0046: Identity/EOD context separation](decisions/0046-separate-latest-identity-from-eod-binding-in-context-report.md): reports latest canonical Identity separately from the Identity snapshot bound into latest EOD.
- [ADR 0047: Plan-aware provider readiness](decisions/0047-make-provider-readiness-plan-aware-and-reviewable.md): gives Identity and EOD distinct recency profiles and adds an immutable, non-executing operator-review gate for Basic current-session EOD and terminal recovery.
- [ADR 0048: Split Candidate summary/detail delivery](decisions/0048-split-candidate-summary-from-on-demand-detail.md): reduces first-load Candidate bytes while preserving lossless, on-demand explanation and full source binding.
- [Market Intelligence Publication](operations/market-intelligence-publication.md): Approval, atomic publication, recovery, rollback, and downstream order.
- [2026-08-19 Dashboard Universe Activation Audit](audits/dashboard-universe-activation-2026-08-19.md): Completed two-Universe publication and integrity evidence.
- [2026-08-20 Selectable Universe Deployment Audit](audits/selectable-universe-dashboard-deployment-2026-08-20.md): Snapshot, bundle, OCI, and unauthenticated protection evidence.
- [Data Access Boundary](operations/data-access-boundary.md): Public placeholder, data-free demo, and private provider-backed dashboard boundary.
- [Massive Credential Provisioning](operations/massive-credential-provisioning.md): Secure credential file and one-request smoke-test operations record.
- [Massive Grouped Daily Inspection](operations/massive-grouped-daily-inspection.md): One-request Grouped Daily inspection record for 2026-08-13.
- [Massive Grouped Daily Ingestion](operations/massive-grouped-daily-ingestion.md): Grouped Daily publication attempts and quality-gate results for 2026-08-13.
- [Massive Instrument Master Ingestion](operations/massive-instrument-master-ingestion.md): Bounded All Tickers snapshot ingestion record and quality-gate result.
- [Same-Day Identity and EOD Catch-Up Readiness](audits/same-day-identity-eod-catchup-readiness-2026-08-23.md): Offline four-stage publication and recovery verification.
- [2026-08-27 Daily EOD Terminal Review Audit](audits/daily-eod-terminal-review-2026-08-27.md): Public provider evidence boundary, immutable real review, conservative next-day gate, and zero-request/write postflight.
- [2026-08-27 Candidate Snapshot Split Audit](audits/candidate-snapshot-split-2026-08-27.md): Real 8/26 payload size, shard distribution, lossless reconstruction, and Production-isolation evidence.
- [2026-08-14 Instrument Snapshot Audit](operations/data-audits/2026-08-14-instrument-snapshot-audit.md): Accepted integrity audit with an explicit provenance exception.
- [2026-08-14 Grouped Daily Run Report](operations/data-audits/2026-08-14-grouped-daily-run.md): Non-sensitive single-request quality and publication record.
- [Storage Provisioning](operations/storage-provisioning.md): Completed workstation storage implementation record and historical procedure.
- [Node Toolchain Provisioning](operations/node-toolchain-provisioning.md): Completed Node.js 24 LTS system toolchain record and historical procedure.

## Development

- [Local Development](development/local-development.md): Project-local backend and frontend setup, run, and verification instructions.

## Decisions

- [ADR Index](decisions/README.md)
- [ADR 0001: Workstation Source of Truth](decisions/0001-workstation-source-of-truth.md)
- [ADR 0002: Separate Compute and Public Web Serving](decisions/0002-separate-compute-and-web-serving.md)
- [ADR 0003: Market Data Provider Boundary](decisions/0003-market-data-provider-boundary.md)
- [ADR 0004: Lightweight Event Layer First](decisions/0004-lightweight-event-layer-first.md)
- [ADR 0005: Application Technology Stack](decisions/0005-application-technology-stack.md)
- [ADR 0006: Initial EOD Data Model and Universe Boundaries](decisions/0006-initial-eod-data-model-and-universe-boundaries.md)
- [ADR 0007: Use Massive for Private EOD Development](decisions/0007-use-massive-for-private-eod-development.md)
- [ADR 0008: Use Partitioned Parquet for Initial Canonical EOD Persistence](decisions/0008-use-partitioned-parquet-for-initial-canonical-eod-persistence.md)
- [ADR 0009: Use Stable Provider Identifiers for Canonical Instrument Identity](decisions/0009-use-stable-provider-identifiers-for-canonical-instrument-identity.md)
- [ADR 0010: Represent Aggregate Volume as Decimal](decisions/0010-represent-aggregate-volume-as-decimal.md)
- [ADR 0011: Publish Private Dashboard Snapshots as Authenticated Static Assets](decisions/0011-publish-private-dashboard-snapshots-as-authenticated-static-assets.md)
- [ADR 0014: Use an Exchange Calendar for EOD Freshness](decisions/0014-use-an-exchange-calendar-for-eod-freshness.md)
- [ADR 0012: Use Server-Side Sessions for the Private Dashboard](decisions/0012-use-server-side-sessions-for-private-dashboard.md)
- [ADR 0013: Establish Dashboard Universe V1 for Market Overview](decisions/0013-establish-dashboard-universe-v1.md)
- [ADR 0015: Govern Security Types and Universe Eligibility](decisions/0015-govern-security-types-and-universe-eligibility.md)
- [ADR 0019: Offer Equal-Capability Guest Sessions](decisions/0019-offer-equal-capability-guest-sessions.md)
- [ADR 0016: Publish Versioned Trailing Liquidity Shadow Results](decisions/0016-publish-versioned-trailing-liquidity-shadow-results.md)
- [ADR 0018: Stage Market Regime & Opportunity Map V1 as Transparent EOD Analytics](decisions/0018-stage-market-regime-opportunity-map-v1.md)
- [ADR 0020: Publish a Bounded Opportunity Candidate Consumer](decisions/0020-publish-bounded-opportunity-candidate-consumer.md)
- [ADR 0021: Separate Candidate Leadership from Entry Geometry](decisions/0021-separate-candidate-leadership-from-entry-geometry.md)
- [ADR 0022: Bind Daily Candidate Calculation to a Verified Prior Audit](decisions/0022-bind-daily-candidate-calculation-to-a-verified-prior-audit.md)
- [ADR 0023: Preserve Market Regime State Prefix Across As-Of Sessions](decisions/0023-preserve-market-regime-state-prefix-across-as-of-sessions.md)
- [ADR 0024: Bind Daily Market Regime State to Verified Upstream Audits](decisions/0024-bind-daily-market-regime-state-to-verified-upstream-audits.md)
- [ADR 0025: Share Formally Validated Panels Between Dell Stages](decisions/0025-share-formally-validated-panels-between-dell-stages.md)
- [ADR 0026: Stream and Resume Candidate Audit Artifacts](decisions/0026-stream-and-resume-candidate-audit-artifacts.md)
- [ADR 0027: Make Candidate Validation Tiers Explicit](decisions/0027-make-candidate-validation-tiers-explicit.md)
- [ADR 0028: Parallelize Only Independent Cold-Replay Oracle Sessions](decisions/0028-parallelize-only-independent-cold-replay-oracle-sessions.md)
- [ADR 0029: Separate Daily Run Planning from Authorized Execution](decisions/0029-separate-daily-run-planning-from-authorized-execution.md)

## Project

- [Current Status](project/current-status.md): Actual current project state.
- [Roadmap](project/roadmap.md): Proposed sequencing without date commitments.
- [Open Questions](project/open-questions.md): Decisions still required.
- [Changelog](project/changelog.md): Meaningful project-level changes.

## Universe Shadow Audits

- [Provider-Classified Common Shares V1](product/provider-classified-common-shares-v1.md): Non-production CS-only and CS+ADRC definitions.
- [2026-08-14 Provider-Classified Audit](audits/provider-classified-common-shares-2026-08-14.md): Validated inputs, type distributions, funnels, Legacy comparison, edge records, and hard gates.
- [EOD Historical Window](architecture/eod-historical-window.md): Bounded multi-session reads and point-in-time identity rules.
- [20-Session Median Dollar-Volume Proxy](product/20-session-trailing-liquidity.md): Exact Decimal methodology and readiness semantics.
- [EOD History Backfill Plan](operations/eod-history-backfill-plan.md): Planning-only same-day identity and request/batch boundary.
- [Trailing Liquidity Shadow Publication Runbook](operations/trailing-liquidity-shadow-publication.md): Offline dry-run/apply, atomic publication, and postflight boundary.
- [Universe Pre-Activation Review Runbook](operations/universe-pre-activation-review.md): Offline stable-ID comparison and reviewed-override shadow publication.
- [2026-08-14 Trailing-Liquidity Readiness Audit](audits/trailing-liquidity-readiness-2026-08-14.md): Current two-session coverage and 18-session gap.
- [2026-08-19 Trailing-Liquidity Shadow Publication Audit](audits/trailing-liquidity-shadow-publication-2026-08-19.md): Production derived artifacts, A/B reconciliation, gap evidence, hashes, and safety postflight.
- [2026-08-19 Full-Base Scope Review Audit](audits/trailing-liquidity-full-base-scope-review-2026-08-19.md): V1 reproduction, corrected full-base funnels, set differences, analytics, hashes, and production-isolation evidence.
- [2026-08-19 Universe Pre-Activation Review Audit](audits/universe-pre-activation-review-2026-08-19.md): Stable-ID Legacy/A/B comparison, reviewed overrides, final shadow proposals, publication hashes, and safety postflight.
