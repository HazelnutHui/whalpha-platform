# Documentation Index

- [Historical Research Backfill Plan ADR](decisions/0119-plan-a-resumable-300-session-historical-foundation.md): exact 300-session target, resumable batching, request/time/storage projections, and non-authorizing Pilot boundary.
- [Dell-local Massive history decision](decisions/0120-allow-dell-local-massive-history-without-written-permission.md): user-directed acquisition posture without a false permission or public-serving claim.
- [Historical Backfill Batch Runner ADR](decisions/0121-run-history-newest-to-oldest-with-canonical-resume.md): newest-to-oldest execution, canonical resume, shared pacing, and fail-stop behavior.

- [Massive Historical Lifecycle Pagination Census V1](data-contracts/massive-historical-lifecycle-pagination-census-v1.md): six-page aggregate-only census within the Historical Pilot ceiling.

- [Massive Historical Lifecycle Completion Census V1](data-contracts/massive-historical-lifecycle-completion-census-v1.md): bounded natural-pagination census used to size the future lifecycle source boundary.
- [2026-09-05 Inactive Lifecycle Completion Census Audit](audits/inactive-lifecycle-completion-census-2026-09-05.md): 20-page truncated result, field coverage, and the source-custody consequence.
- [Historical Inactive Lifecycle Source Package V1](data-contracts/historical-inactive-lifecycle-source-package-v1.md): resumable owner-only temporary source custody with formal reread and no canonical write.
- [2026-09-05 Inactive Lifecycle Source Package Audit](audits/inactive-lifecycle-source-package-2026-09-05.md): complete 24-page source custody, formal reread, and unchanged canonical-state proof.
- [ADR 0148: Disconnected Inactive Lifecycle Resolution Shadow](decisions/0148-build-disconnected-inactive-lifecycle-resolution-shadow.md): lossless one-to-one normalization, stable-ID gates, quarantine, and no canonical authority.
- [2026-09-05 Inactive Lifecycle Resolution Shadow Audit](audits/inactive-lifecycle-resolution-shadow-2026-09-05.md): real dual-anchor decisions, temporal boundary proof, physical custody, and unchanged canonical state.
- [ADR 0149: Sealed and Operational Freshness](decisions/0149-separate-sealed-and-operational-freshness.md): separates immutable Snapshot publication evidence from current canonical and serving-state evaluation.
- [ADR 0150: Atomic Daily Identity Source Custody](decisions/0150-retain-daily-identity-source-observations-atomically.md): adds direct daily source binding, Plan 1.1 atomic publication, legacy-plan compatibility, and append-only exact repair.
- [2026-09-06 Daily EOD Publication and Deployment Audit](audits/daily-eod-publication-deployment-2026-09-06.md): exact 2026-09-04 acquisition, analytics, publication, deployment, and postflight evidence.

- [Massive Historical Lifecycle Coverage Probe V1](data-contracts/massive-historical-lifecycle-coverage-probe-v1.md): two-page inactive-security and lifecycle-field aggregate review.

- [Massive Historical Entitlement Probe V1](data-contracts/massive-historical-entitlement-probe-v1.md): exact-revision, four-request technical account capability review with no response retention or acquisition authority.

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

## Research

- [Professional Quantitative Research Action Framework V1](research/professional-quantitative-research-action-framework-v1.md): standalone, source-neutral manual covering point-in-time data, feature engineering, labels, backtesting, costs, anti-overfitting, portfolio construction, options research, promotion gates, monitoring, and retirement. A [PDF edition](research/professional-quantitative-research-action-framework-v1.pdf) is maintained beside the source.

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
- [Historical Research Data Foundation V1](architecture/historical-research-data-foundation-v1.md): Point-in-time membership, corporate-action/lifecycle, adjustment, coverage, and retention requirements before strategy evaluation.
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
- [Historical Research Foundation Contracts V1](data-contracts/historical-research-foundation-v1.md)
- [Candidate Strategy Research Experiment V1](data-contracts/candidate-strategy-research-experiment-v1.md)
- [Strategy Research Readiness V1](data-contracts/strategy-research-readiness-v1.md)
- [Strategy Research Development Activation Review V1](data-contracts/strategy-research-development-activation-review-v1.md): Separates complete data evidence from exact user authorization and any later real-evaluation capability.
- [Data Record Governance V1](data-contracts/data-record-governance-v1.md): Cross-family layer, disposition, evidence, quality, coverage, point-in-time, retention, content-scope, and equal-capability serving classification.
- [Source Permission Governance V1](data-contracts/source-permission-governance-v1.md): Effective-dated, use-specific source permission reviews and default-deny equal-capability assessment.
- [Source Resolution Governance V1](data-contracts/source-resolution-governance-v1.md): Family/fact-specific evidence roles, corroboration, and fail-closed conflict resolution.
- [Provider Instrument Identity V1](data-contracts/provider-instrument-identity-v1.md)
- [Provider Ticker Resolver V1](data-contracts/provider-ticker-resolver-v1.md)
- [Trailing Liquidity Shadow Publication V1](data-contracts/trailing-liquidity-shadow-v1.md)
- [Reviewed Eligibility Override V1](data-contracts/reviewed-eligibility-override-v1.md)
- [Dashboard Universe Activation V1](data-contracts/dashboard-universe-activation-v1.md)

## Providers

- [Provider Evaluations](providers/README.md)
- [Massive Stocks Basic Evaluation](providers/massive-stocks-basic-evaluation.md): Accepted first private EOD development provider.
- [Massive Adapter Boundary](providers/massive-adapter-boundary.md): Configuration, credential, transport, smoke-test, and mapping boundary.
- [Historical Research Source Capability V1](providers/historical-research-source-capability-v1.md): Repository-evidenced source, entitlement, implementation, and gap matrix for 252/504-session history.
- [2026-08-28 Massive Historical Research Review](providers/massive-historical-research-review-2026-08-28.md): Current official plan, endpoint, licensing, guest-compatibility, and entitlement gates.
- [2026-08-28 Equal-Capability Historical Source Review](providers/equal-capability-historical-source-review-2026-08-28.md): Official-source role, permission, coverage, and hybrid-composition decision.
- [Source Selection and Permission Inquiry Packet V1](providers/source-selection-permission-inquiry-packet-v1.md): Prepared, unsent questions for exact shared-product permission, retention, coverage, and pricing.
- [Massive Corporate Action Fixture Mapping V1](providers/massive-corporate-action-fixture-mapping-v1.md): Network-free split/dividend source mapping, quarantine rules, and adjustment-factor invariants.

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
- [ADR 0066: Incremental Candidate publication evidence](decisions/0066-project-incremental-candidate-evidence-into-publication.md): Projects the formally bound verified-prior/current-Oracle chain into the stable Candidate source shape with explicit validation-mode warnings.
- [Opportunity Strategy Channels V1](product/opportunity-strategy-channels-v1.md): Independent Candidate archetypes, evidence boundaries, within-channel ranking, and temporal-validation requirements.
- [Quant Research Lab V1](product/quant-research-lab-v1.md): Personal-model research lifecycle, first Strong-Leader Pullback program, visible validation state, and failure/decay disclosures.
- [Candidate Strategy Channel Preview V1](data-contracts/candidate-strategy-channel-preview-v1.md): Fixed offline formulas, explicit unavailable channels, explanations, bounded consumer, independent Oracle, and immutable temporary-root audit.
- [Candidate Strategy Evaluation V1](data-contracts/candidate-strategy-evaluation-v1.md): Sealed point-in-time signals, separately matured stock outcomes, and anti-leakage evaluation policy.
- [Candidate Strategy Research Experiment V1](data-contracts/candidate-strategy-research-experiment-v1.md): Immutable preregistration, bounded development grid, leader-control contrast, decision gates, ownership, and current data blockers.
- [Candidate Entry Geometry V1](data-contracts/candidate-entry-geometry-v1.md): Offline source audit and additive consumer contract separating leadership quality from entry location and chase risk.
- [Candidate Visual Context V1](data-contracts/candidate-visual-context-v1.md): Source-bound real 20-session close paths and left-censor-aware observed Candidate-state age for future lazy details.
- [ADR 0089: Lazy Candidate Visual Context publication](decisions/0089-publish-candidate-visual-context-in-lazy-detail-shards.md): Snapshot 1.10/detail-shard 1.1 binding with unchanged first-load summary.
- [2026-08-30 Candidate Visual Context Product Integration Audit](audits/candidate-visual-context-product-integration-2026-08-30.md): real Dell tmp-only Snapshot 1.10, Plan 2.5, size, lineage, and no-Production-write evidence.
- [Candidate Pipeline Performance](operations/candidate-pipeline-performance.md): Dell-only compute/data authority, worktree-safe runner, measured baseline, and deterministic optimization sequence.
- [ADR 0125: Session discovery versus partition validation](decisions/0125-separate-session-discovery-from-partition-validation.md): fast date-only completion discovery with explicit deep validation for consumed data and periodic full-history audits.
- [ADR 0126: Exact downstream evidence reuse](decisions/0126-reuse-exact-panel-and-current-candidate-evidence-downstream.md): reuses formally bound panel and current-Candidate evidence in Entry Geometry and ETF Relationships.
- [ADR 0127: Bounded Strategy input](decisions/0127-bound-strategy-input-to-current-candidate-evidence.md): prevents Strategy Channels from reconstructing unused cumulative Candidate histories.
- [ADR 0128: Daily Candidate commit scope](decisions/0128-separate-daily-candidate-commit-from-periodic-semantic-reread.md): uses validated write plus complete physical custody daily while retaining full semantic reread for periodic and code-change tiers.
- [ADR 0129: Snapshot rollback/CAS single observation](decisions/0129-bind-snapshot-rollback-and-cas-to-one-active-read.md): derives both approval-plan bindings from one fully validated active Snapshot while preserving fresh Apply checks.
- [ADR 0130: Segmented Candidate shadow](decisions/0130-prove-segmented-candidate-custody-before-cutover.md): proves lossless per-session custody before any V1 daily or publication cutover.
- [Candidate Segmented Shadow V1](data-contracts/opportunity-candidate-segmented-shadow-v1.md): offline session-segment contract, custody, equivalence, and explicit non-authority boundary.
- [ADR 0132: Complete-base historical Universe reconstruction](decisions/0132-reconstruct-complete-base-historical-universe-membership.md): uses retained, custody-validated point-in-time Identity packages to build tmp-only complete three-state membership shadows while localizing record conflicts.
- [ADR 0133: Bounded membership shadow batches](decisions/0133-reuse-bounded-eod-panels-for-membership-shadow-batches.md): reuses one formally validated EOD panel and Identity evidence across at most five adjacent, tmp-only reconstruction sessions.
- [ADR 0134: Historical Identity package equivalence census](decisions/0134-census-historical-identity-package-equivalence.md): formally distinguishes exact same-day reconstruction sources from missing, custody-failed, mismatched, and duplicate retained packages before broad membership work.
- [ADR 0135: Versioned legacy ETV Identity reconstruction](decisions/0135-reconstruct-legacy-etv-identity-semantics-by-version.md): reproduces only the pre-governance ETV Identity representation without changing current classification or admitting non-ETV differences.
- [ADR 0136: Fingerprint-bound historical Identity profile map](decisions/0136-bind-historical-identity-rebuild-profile-by-fingerprint.md): replaces date/operator profile choice with an exact per-session package and accepted-family binding required by membership shadows.
- [ADR 0137: Normalized historical Identity source custody](decisions/0137-normalize-historical-identity-source-custody.md): retains every audited provider result fact in typed source-observation Parquet while excluding raw response envelopes and sensitive transport metadata.
- [ADR 0138: Inventory-bound historical Identity source planning](decisions/0138-bind-historical-identity-source-apply-plan.md): uses one formally reread candidate census and no-write plan to bind all prospective files, absent targets, and the current `/data` pre-state.
- [ADR 0139: Atomic historical Identity source Apply and recovery](decisions/0139-apply-historical-identity-source-custody-atomically.md): adds exact-plan execution, immutable per-session publication, full canonical reread, and fail-closed verify-then-complete recovery without authorizing the real `/data` transition.
- [ADR 0140: Canonical Identity source custody in current context](decisions/0140-expose-canonical-identity-source-custody-in-current-context.md): exposes the source-observation layer, exact canonical counts, and missing sessions separately from resolved Identity without changing research authority.
- [Historical Identity Source Gap Recovery](operations/historical-identity-source-gap-recovery.md): bounded `/tmp`-only acquisition, shared pacing, custody checkpoints, and mandatory dual-profile proof for exact missing source dates.
- [ADR 0141: Historical Identity source-gap fetch](decisions/0141-fetch-historical-identity-source-gaps-without-canonical-writes.md): separates exact source-package recovery from canonical replay, normalization, Apply, and research authority.
- [ADR 0142: Append-only Identity source planning](decisions/0142-plan-explicit-append-only-identity-source-custody.md): binds only an explicit profile-map subset while keeping existing canonical source partitions immutable and inside the whole-data pre-state.
- [ADR 0143: Identity observation versus replay time](decisions/0143-separate-identity-observation-and-replay-time.md): preserves reacquisition time while deriving exact replay provenance from the accepted three-family snapshot and keeping revised packages explicitly unbound.
- [ADR 0144: Canonical Identity source Membership shadows](decisions/0144-consume-canonical-identity-source-for-membership-shadows.md): removes temporary package/profile-map dependencies from normal shadow execution, preserves V2 decision equivalence, and eliminates repeated PyArrow timezone-module lookup overhead.
- [ADR 0145: Exact-duplicate Identity index references](decisions/0145-collapse-exact-duplicate-identity-index-references.md): prevents provider rows already classified as exact duplicates from becoming false downstream stable-identifier collisions while preserving every genuinely distinct reference.
- [2026-09-05 Canonical-Source Universe Membership Shadow Audit](audits/canonical-source-universe-membership-shadow-2026-09-05.md): 303-session source preflight, 301-session disconnected V3 evidence, exact-duplicate correction, performance evidence, physical custody, and the remaining two source gaps.
- [2026-09-04 Bounded Membership Shadow Batch Audit](audits/bounded-universe-membership-shadow-batch-2026-09-04.md): exact single/two-session equivalence, measured runtime and memory, five-session isolation, and the custody-valid versus exact-equivalent source distinction.
- [2026-09-04 Historical Identity Package Equivalence Census](audits/historical-identity-package-equivalence-census-2026-09-04.md): full 303-session exact-current-builder result, mismatch ranges, bounded parallel proof, ETV migration diagnosis, and the no-reacquisition decision for 221 retained packages.
- [2026-09-04 Historical Identity ETV Compatibility Census](audits/historical-identity-etv-compatibility-census-2026-09-04.md): proves that current and versioned pre-governance ETV profiles form a disjoint exact cover of all 279 retained packages, leaving only 24 physical gaps.
- [2026-09-04 Historical Identity Rebuild Profile Map Audit](audits/historical-identity-rebuild-profile-map-2026-09-04.md): owner-only 279-session routing map, independent index/inventory reconciliation, and repeatable real current/legacy boundary membership proof.
- [2026-09-04 Historical Identity Source Custody Audit](audits/historical-identity-source-custody-2026-09-04.md): complete 279-session normalization, independent formal reread, physical determinism, four-process planning speedup, and no-write evidence.
- [2026-09-04 Historical Identity Source Apply/Recovery Audit](audits/historical-identity-source-apply-recovery-2026-09-04.md): `/tmp` proof of exact ordinary Apply, interrupted mixed-state recovery, immutable-target refusal, drift/staging/partial-state blocking, CLI binding, and unchanged real `/data`.
- [2026-09-06 Daily Identity Source Custody Audit](audits/daily-identity-source-custody-2026-09-06.md): direct-bound Plan 1.1, exact 9/4 append-only Apply, zero-write recovery, full reconstruction, and unchanged research authority.
- [2026-09-04 Historical Identity Source Canonical Apply Audit](audits/historical-identity-source-canonical-apply-2026-09-04.md): exact 279-partition Dell Apply, complete typed reread, physical census, zero-write recovery postflight, and the unchanged research boundary.
- [2026-09-05 Historical Identity Source Gap Recovery Audit](audits/historical-identity-source-gap-recovery-2026-09-05.md): resumes the 24-date acquisition, proves 22 exact packages, preserves two provider-revised dates as unbound, and records the append-only canonical Apply and zero-write recovery.
- [ADR 0131: Family-specific research readiness](decisions/0131-expose-family-specific-research-readiness.md): exposes exact acquired-versus-missing historical input families in the authoritative read-only context report without weakening formal Coverage gates.
- [Historical Research Storage and Pilot Plan V1](operations/historical-research-storage-and-pilot-plan-v1.md): Dell capacity, physical families, request estimates, fixture sequence, and bounded pilot gates.
- [Historical Source Package V1](data-contracts/historical-source-package-v1.md): provider-neutral `/tmp` response custody, exact Pilot-plan binding, atomic publication, and formal reread without provider or Apply authority.
- [Historical Identity Source Custody V1](data-contracts/historical-identity-source-custody-v1.md): typed complete-result observations, per-page custody, profile binding, immutable partitions, and explicit post-session knowledge limits.
- [Historical Identity Source Apply Plan V1](data-contracts/historical-identity-source-apply-plan-v1.md): combined candidate census and inventory-bound prospective copy plan that grants no Apply authority; execution is a separate boundary.
- [Historical Identity Source Apply V1](data-contracts/historical-identity-source-apply-v1.md): exact-plan atomic executor, canonical reader, shared publication lock, non-destructive recovery, and explicit non-authority boundary.
- [Candidate Strategy Research Execution V1](data-contracts/candidate-strategy-research-execution-v1.md): fixture-only chronological splits, purge/embargo, leader controls, and later-matured underlying-stock labels without performance authority.
- [Candidate Strategy Research Statistics V1](data-contracts/candidate-strategy-research-statistics-v1.md): fixture-only session-balanced contrast, block bootstrap, Holm correction, cost scenarios, and locked stage sequence.
- [Candidate Strategy Holdout Custody V1](data-contracts/candidate-strategy-holdout-custody-v1.md): reserve-before-evaluation, immutable event-chain, and no-replay semantics for a future single-use holdout.
- [Massive Permission and Entitlement Inquiry V1](providers/massive-permission-entitlement-inquiry-v1.md): concise send-ready account, retention, derived-use, equal-capability display, browser-delivery, coverage, and pricing questions; prepared but not sent.
- [Daily EOD Automation Control Plane](operations/daily-eod-automation.md): XNYS/provider readiness, bounded retry, provider-attempt custody, exact-session planning, single-action offline execution, interruption recovery, and remaining unattended-operation gates.
- [Daily EOD Pipeline Scheduler V2](data-contracts/daily-eod-pipeline-scheduler-v2.md): pipeline-aware wake phases and deterministic Dell-local per-session workspace contract.
- [ADR 0095: Shared persistent analytics custody](decisions/0095-share-offline-artifact-custody-across-persistent-analytics.md): exact owner-only dated-session policy, legacy `/tmp` compatibility, and real nine-stage analytics proof.
- [ADR 0096: Resume persistent workspace planning](decisions/0096-resume-persistent-workspace-planning-after-proof.md): Plan 1.8 removal of the superseded early stop after deterministic real-lineage proof, without publication, deployment, or scheduler authority.
- [ADR 0097: Preregister personal strategy research](decisions/0097-preregister-personal-strategy-research-before-backtesting.md): names Quant Research Lab and freezes the first data-blocked Strong-Leader Pullback experiment before outcomes can influence its design.
- [ADR 0098: Bind strategy development to formal readiness](decisions/0098-bind-strategy-development-to-formal-readiness-evidence.md): evaluates exact Dell evidence without authorizing development or performance claims.
- [ADR 0099: Require transitive physical Historical Coverage evidence](decisions/0099-require-transitive-physical-evidence-for-historical-coverage.md): binds each coverage family to immutable source completion manifests and payload hashes before formal reread.
- [ADR 0100: Adapt current EOD and Identity without publication](decisions/0100-adapt-current-eod-and-identity-without-publishing-coverage.md): formally rereads current Dell bytes into deterministic, transitively validated in-memory family evidence while preserving the no-`/data`-write boundary.
- [ADR 0101: Bind current history to a blocked pilot review](decisions/0101-bind-current-history-to-a-blocked-pilot-review.md): joins current physical inventory, exact preceding sessions, repository proof, and dated permission conclusions without creating pilot authority.
- [ADR 0102: Freeze provider-neutral Historical Source packages](decisions/0102-freeze-provider-neutral-historical-source-packages.md): isolates already captured historical responses under exact temporary custody before any provider-specific mapping or canonical Apply.
- [ADR 0103: Separate chronological research mechanics from performance](decisions/0103-separate-chronological-research-mechanics-from-performance.md): freezes and tests the first experiment's time-order mechanics before real outcomes or model selection.
- [ADR 0104: Freeze session-balanced research statistics](decisions/0104-freeze-session-balanced-research-statistics.md): fixes conservative development selection, multiplicity-aware validation, and locked holdout access before real labels exist.
- [ADR 0105: Require adversarial statistics audit and complete labels](decisions/0105-require-adversarial-statistics-audit-and-complete-labels.md): independently checks descriptive mechanics and blocks incomplete validation/holdout labels.
- [ADR 0106: Expose research readiness without performance](decisions/0106-expose-research-readiness-without-performance.md): adds the bilingual first-level Lab page while keeping real and fixture performance unavailable.
- [ADR 0107: Reserve holdout before evaluation](decisions/0107-reserve-holdout-before-evaluation.md): adds durable no-replay custody without connecting real inputs or granting performance authority.
- [ADR 0108: Independently reproduce research inference](decisions/0108-independently-reproduce-research-inference.md): exact independent moving-block Bootstrap, percentile, probability, and Holm verification for arbitrary nonconstant fixtures.
- [ADR 0109: Separate research readiness from development authorization](decisions/0109-separate-research-readiness-from-development-authorization.md): keeps 252-session readiness review-only and binds any future authorization to exact unchanged controls.
- [2026-08-31 Quant Research Statistics Adversarial Audit](audits/quant-research-statistics-adversarial-audit-2026-08-31.md): synthetic null, reversal, crowding, outlier, missingness and stage-isolation evidence.
- [2026-08-31 Quant Research Inference Oracle Audit](audits/quant-research-inference-oracle-audit-2026-08-31.md): independent exact inference equivalence across nonconstant series and the full validation family.
- [Daily EOD Bounded Cadence V1](data-contracts/daily-eod-bounded-cadence-v1.md): finite distinct-wake planning, evidence-chain, timing, failure, and manual-stop contract.
- [Daily EOD Cadence Diagnosis V1](data-contracts/daily-eod-cadence-diagnosis-v1.md): read-only unresolved-wake classification without replay, retry, recovery, or inferred resolution.
- [ADR 0083: Cadence Evidence in the Run Journal](decisions/0083-reuse-run-journal-for-cadence-evidence.md): single-store owner-only retention and exact coordinator/offline result projection.
- [ADR 0080: Scheduler operation versus host state](decisions/0080-separate-scheduler-operation-from-host-state.md): prevents read-only planner output from being mistaken for an observation of installed systemd state.
- [ADR 0073: One-shot OCI deployment custody](decisions/0073-custody-one-oci-dashboard-deployment.md): binds exact Serving Bundle and remote pre/post state, reserves before one Apply, and classifies interruption without replay.
- [ADR 0074: Descriptive ETF relationship change](decisions/0074-project-descriptive-etf-relationship-change.md): projects state-run duration and rolling relative-return change from retained history without changing formulas or rankings.
- [ADR 0075: Bounded ETF relationship state timeline](decisions/0075-project-bounded-etf-relationship-state-timeline.md): projects the latest ten frozen relationship states and window-relative returns without browser recomputation.
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
- [ADR 0049: Separate Candidate strategy channels](decisions/0049-separate-candidate-strategy-channels.md): fixes independent same-archetype research channels and prohibits a cross-strategy total score.
- [ADR 0056: Prototype explainable strategy channels offline](decisions/0056-prototype-explainable-strategy-channels-offline.md): adds the unvalidated three-channel shadow calculation without Production activation.
- [ADR 0050: Seal strategy signals before outcomes](decisions/0050-seal-strategy-signals-before-forward-outcomes.md): separates contemporaneous point-in-time signals from later stock outcomes and prohibits random-split leakage.
- [ADR 0051: Require a point-in-time historical research foundation](decisions/0051-require-point-in-time-historical-research-foundation.md): requires governed membership, actions, lifecycle, adjustments, and coverage before formula evaluation.
- [ADR 0054: Gate data sources by explicit use permission](decisions/0054-gate-data-sources-by-explicit-use-permission.md): requires evidence-backed acquisition, retention, derived-use, display, and delivery permission without weakening guest parity.
- [ADR 0055: Resolve canonical facts by family-specific source policy](decisions/0055-resolve-canonical-facts-by-family-specific-source-policy.md): prohibits first-non-null, ticker joins, and silent conflict precedence.
- [ADR 0052: Unify cross-family data record governance](decisions/0052-unify-data-record-governance-classification.md): keeps domain states separate while enforcing one executable family registry and shared-content parity.
- [ADR 0053: Separate historical Pilot review from authorization](decisions/0053-separate-historical-pilot-approval-review-from-authorization.md): binds exact scope and external gates without granting acquisition or Apply authority.
- [ADR 0086: Physically prove point-in-time Universe membership](decisions/0086-physically-prove-point-in-time-universe-membership.md): requires complete same-base daily ledgers and permits only source-bound reconstruction.
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
- [2026-08-27 Strategy Evaluation Readiness Audit](audits/strategy-evaluation-readiness-2026-08-27.md): EOD/Identity/benchmark coverage, membership/adjustment/lifecycle gaps, and the formal not-ready result.
- [2026-08-30 Daily Universe Membership Physical Pilot](audits/daily-universe-membership-pilot-2026-08-30.md): one real tmp-only reconstructed partition, complete coverage totals, fingerprints, and later-known-source warning.
- [2026-09-04 Complete-Base Universe Membership Shadow](audits/complete-base-universe-membership-shadow-2026-09-04.md): real 2026-09-03 all-Identity-base reconstruction, localized collision quarantine, deterministic custody, and exact remaining package gap.
- [2026-08-28 Candidate Strategy Channel Preview Review](audits/candidate-strategy-channel-preview-2026-08-28.md): Offline fixed-formula mechanics, independent Oracle, immutable audit, full-population counts, bounded views, and validation limits.
- [2026-08-28 Stale-Review Publication and OCI Deployment](audits/stale-review-publication-deployment-2026-08-28.md): Exact authorization, MI/Snapshot plans and applies, 1.9/2.6 bundle deployment, guest postflight, timings, and post-deployment reconciliation.
- [2026-08-29 Daily Publication Review](audits/daily-eod-publication-review-2026-08-29.md): Same-session Phase 2/preview completion, incremental Candidate publication correction, freshness-blocked MI Plan, and unchanged Production state.
- [2026-08-29 Daily Readiness Review](audits/daily-eod-readiness-2026-08-29.md): Network-free 2026-08-28 gap reconciliation, unchanged canonical/Production custody, and exact Identity-first authorization boundary.
- [2026-08-29 ETF Relationship Explanation Deployment](audits/etf-relationship-explanation-deployment-2026-08-29.md): backward-compatible Snapshot publication, 50-file OCI deployment, independent guest/service/residue postflight, and final Dell inventory.
- [2026-08-30 Sector Rotation Publication and Deployment](audits/sector-rotation-publication-deployment-2026-08-30.md): persistent MI/Snapshot lineage, two fail-closed consumer corrections, Snapshot 1.11 / Dashboard 2.8 deployment, guest Sector Rotation postflight, and final Dell/OCI reconciliation.
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
