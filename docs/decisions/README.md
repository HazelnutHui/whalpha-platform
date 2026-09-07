# Architecture Decision Records

- [ADR 0155](0155-version-segmented-candidate-chain-identity.md): assign the segmented Candidate shadow a distinct forward hash-chain identity without relabeling it as V1 whole-history evidence.

- [ADR 0154](0154-prepare-daily-membership-outside-the-serving-gate.md): prepare or reuse a prospective daily Membership candidate and next-open timing assessment outside the website serving gate and without canonical writes.

- [ADR 0153](0153-publish-membership-physical-first-marker-last.md): publish exact Membership physical bytes first and the eligibility marker last, with fail-closed recovery and a governed canonical reader.

- [ADR 0152](0152-plan-membership-with-a-last-publication-marker.md): bind signal-eligible Membership bytes, timing evidence, target absence, and `/data` CAS in a no-write plan whose future logical marker must be published last.

- [ADR 0151](0151-gate-membership-by-next-open-knowledge-time.md): separate close-bounded market information from next-open source/evaluation timing, and keep retrospective Membership out of signal-eligible coverage.

- [ADR 0149](0149-separate-sealed-and-operational-freshness.md): preserve immutable publication-time Snapshot freshness while separately reporting current canonical and active-Snapshot operational freshness.

- [ADR 0143](0143-separate-identity-observation-and-replay-time.md): separate later source observation from canonical Identity replay provenance and keep dual-profile mismatches explicitly unbound.

- [ADR 0142](0142-plan-explicit-append-only-identity-source-custody.md): plan an exact profile-bound candidate subset for immutable append without replaying existing canonical source partitions.

- [ADR 0141](0141-fetch-historical-identity-source-gaps-without-canonical-writes.md): recover exact missing historical Identity reference packages through one serial, checkpointed, `/tmp`-only operation before independent dual-profile proof.

- [ADR 0140](0140-expose-canonical-identity-source-custody-in-current-context.md): project canonical historical Identity source-observation inventory and exact session gaps separately from resolved snapshots without weakening Historical Coverage gates.

- [ADR 0139](0139-apply-historical-identity-source-custody-atomically.md): publish an exact reviewed historical Identity source plan through immutable per-session renames, shared locking, full formal reread, and non-destructive verify-then-complete recovery.

- [ADR 0138](0138-bind-historical-identity-source-apply-plan.md): combine the complete normalized-source census and immutable-copy mapping in one no-write plan bound to candidate bytes, absent targets, and the current `/data` inventory.

- [ADR 0137](0137-normalize-historical-identity-source-custody.md): preserve the complete audited Identity result facts in typed source-observation Parquet without promoting raw response envelopes.

- [ADR 0133](0133-reuse-bounded-eod-panels-for-membership-shadow-batches.md): reuse one formally validated, memory-bounded EOD panel across adjacent historical membership shadow sessions.

- [ADR 0132](0132-reconstruct-complete-base-historical-universe-membership.md): reconstruct complete same-day Identity bases into source-bound, three-state historical Universe shadows without treating local mapping conflicts as whole-day loss.

- [ADR 0131](0131-expose-family-specific-research-readiness.md): Expose exact acquired-versus-missing historical input families in the authoritative read-only context report without weakening formal Coverage gates.

- [ADR 0130](0130-prove-segmented-candidate-custody-before-cutover.md): Prove a lossless per-session Candidate shadow before any change to the V1 daily or publication boundary.

- [ADR 0129](0129-bind-snapshot-rollback-and-cas-to-one-active-read.md): Bind one Snapshot plan's rollback reference and expected current-state fingerprint to the same fully validated active read while preserving fresh Apply checks.

- [ADR 0128](0128-separate-daily-candidate-commit-from-periodic-semantic-reread.md): Commit daily Candidate output through validated write plus complete physical custody while retaining full semantic reread for periodic and code-change tiers.

- [ADR 0127](0127-bound-strategy-input-to-current-candidate-evidence.md): Read only finalized current Candidate batches for Strategy Channels instead of reconstructing unused cumulative Candidate histories.

- [ADR 0126](0126-reuse-exact-panel-and-current-candidate-evidence-downstream.md): Reuse the exact formal panel cache and finalized current Candidate evidence in downstream daily stages without changing business outputs.

- [ADR 0125](0125-separate-session-discovery-from-partition-validation.md): Use the immutable completion index for date-only control paths while retaining deep validation for consumed partitions and explicit full-history audits.

- [ADR 0124](0124-exclude-catalog-known-etv-without-inferring-etf.md): Treat catalog-known ETV as unsupported and excluded without inferring ETF or weakening the malformed-data gate.

- [ADR 0118](0118-use-the-completion-index-for-current-snapshot-session-selection.md): Select the two current Snapshot sessions from the bounded completion index, then fully validate only the partitions actually consumed.

- [ADR 0117](0117-reuse-finalized-candidate-evidence-and-parse-snapshots-once.md): Reuse exact finalized Candidate bytes for daily append inputs and parse each Snapshot artifact once per full validation.

- [ADR 0116](0116-quarantine-low-ratio-stable-identity-collisions.md): Permit only a bounded low ratio of fully quarantined stable-identity conflicts without choosing a winner.

- [ADR 0115](0115-bind-systemd-review-to-the-immutable-runtime.md): Verify and render exact detached-runtime scheduler service candidates without installing them.

- [ADR 0114](0114-run-the-read-only-scheduler-from-an-immutable-worktree.md): Separate the read-only scheduler from moving `main` with an exact detached Dell worktree.

- [ADR 0113](0113-treat-degraded-user-systemd-as-review-available.md): Permit exact repair review when the reachable user manager is degraded by a failed pinned oneshot.

- [ADR 0112](0112-census-inactive-pagination-within-the-pilot-ceiling.md): Determine whether inactive history completes within the existing six-request Pilot ceiling without starting acquisition.

- [ADR 0111](0111-bound-inactive-security-lifecycle-coverage-probing.md): Bound inactive-Tickers pagination and lifecycle-field probing without retaining identifiers or granting coverage authority.

- [ADR 0110](0110-probe-account-entitlement-separately-from-historical-acquisition.md): Separate a four-request, non-retaining account capability probe from Historical Pilot acquisition and permission conclusions.

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

- [0143: Separate Identity Observation and Replay Time](0143-separate-identity-observation-and-replay-time.md)
- [0142: Plan Explicit Append-Only Identity Source Custody](0142-plan-explicit-append-only-identity-source-custody.md)
- [0141: Fetch Historical Identity Source Gaps Without Canonical Writes](0141-fetch-historical-identity-source-gaps-without-canonical-writes.md)
- [0133: Reuse Bounded EOD Panels for Membership Shadow Batches](0133-reuse-bounded-eod-panels-for-membership-shadow-batches.md)
- [0132: Reconstruct Complete-Base Historical Universe Membership](0132-reconstruct-complete-base-historical-universe-membership.md)
- [0131: Expose Family-Specific Research Readiness](0131-expose-family-specific-research-readiness.md)
- [0130: Prove Segmented Candidate Custody Before Cutover](0130-prove-segmented-candidate-custody-before-cutover.md)
- [0129: Bind Snapshot Rollback and CAS to One Active Read](0129-bind-snapshot-rollback-and-cas-to-one-active-read.md)
- [0128: Separate Daily Candidate Commit from Periodic Semantic Reread](0128-separate-daily-candidate-commit-from-periodic-semantic-reread.md)
- [0127: Bound Strategy Input to Current Candidate Evidence](0127-bound-strategy-input-to-current-candidate-evidence.md)
- [0126: Reuse Exact Panel and Current Candidate Evidence Downstream](0126-reuse-exact-panel-and-current-candidate-evidence-downstream.md)
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
- [0037: Gate One-Transition CLI with Host Runtime](0037-gate-one-transition-cli-with-host-runtime.md)
- [0038: Route One Interrupted Daily Transition](0038-route-one-interrupted-daily-transition.md)
- [0039: Separate Daily Alert Intent from Delivery](0039-separate-daily-alert-intent-from-delivery.md)
- [0040: Custody One Daily Alert Delivery Attempt](0040-custody-one-daily-alert-delivery-attempt.md)
- [0041: Deliver Daily Alerts Through External SMTP](0041-deliver-daily-alerts-through-external-smtp.md)
- [0042: Preflight External Daily Controls Together](0042-preflight-external-daily-controls-together.md)
- [0043: Compose Explicit Email Delivery After Coordination](0043-compose-explicit-email-delivery-after-coordination.md)
- [0044: Allow Data-Only Preflight When Email Is Deferred](0044-allow-data-only-preflight-when-email-is-deferred.md)
- [0045: Retain Safe Provider Failure Evidence](0045-retain-safe-provider-failure-evidence.md)
- [0046: Separate Latest Identity From EOD Binding in Context Report](0046-separate-latest-identity-from-eod-binding-in-context-report.md)
- [0047: Make Provider Readiness Plan-Aware and Reviewable](0047-make-provider-readiness-plan-aware-and-reviewable.md)
- [0048: Split Candidate Summary from On-Demand Detail](0048-split-candidate-summary-from-on-demand-detail.md)
- [0049: Separate Candidate Strategy Channels](0049-separate-candidate-strategy-channels.md)
- [0050: Seal Strategy Signals Before Forward Outcomes](0050-seal-strategy-signals-before-forward-outcomes.md)
- [0051: Require a Point-in-Time Historical Research Foundation](0051-require-point-in-time-historical-research-foundation.md)
- [0052: Unify Cross-Family Data Record Governance Classification](0052-unify-data-record-governance-classification.md)
- [0053: Separate Historical Pilot Approval Review from Authorization](0053-separate-historical-pilot-approval-review-from-authorization.md)
- [0054: Gate Data Sources by Explicit Use Permission](0054-gate-data-sources-by-explicit-use-permission.md)
- [0055: Resolve Canonical Facts by Family-Specific Source Policy](0055-resolve-canonical-facts-by-family-specific-source-policy.md)
- [0056: Prototype Explainable Strategy Channels Offline](0056-prototype-explainable-strategy-channels-offline.md)
- [0057: Add a Lazy Strategy-Channel Product Payload](0057-add-lazy-strategy-channel-product-payload.md)
- [0058: Carry Strategy Bindings Through Publication and Bundle](0058-carry-strategy-bindings-through-publication-and-bundle.md)
- [0059: Authorize a Second Exact Stale Review](0059-authorize-second-exact-stale-review.md)
- [0060: Reuse Candidate Completion Evidence for Publication](0060-reuse-candidate-completion-evidence-for-publication.md)
- [0061: Bind Displayed Strategy Methods and Audit Channel Overlap](0061-bind-displayed-strategy-methods-and-audit-channel-overlap.md)
- [0062: Add Descriptive Continuation Facts Before Rescoring](0062-add-descriptive-continuation-facts-before-rescoring.md)
- [0063: Formalize Continuation Fact Audit with a Bounded Current Read](0063-formalize-continuation-fact-audit-with-bounded-current-read.md)
- [0064: Separate Breakout Stage from Breakout Quality](0064-separate-breakout-stage-from-breakout-quality.md)
- [0065: Reuse Candidate Completion Evidence in Daily Planning](0065-reuse-candidate-completion-evidence-in-daily-planning.md)
- [0066: Project Incremental Candidate Evidence into Publication](0066-project-incremental-candidate-evidence-into-publication.md)
- [0067: Extend the Daily Offline Analysis Chain](0067-extend-daily-offline-analysis-chain.md)
- [0068: Custody the Daily Market Intelligence Plan](0068-custody-daily-market-intelligence-plan.md)
- [0069: Custody One-Shot Market Intelligence Apply](0069-custody-one-shot-market-intelligence-apply.md)
- [0070: Custody the Daily Dashboard Snapshot Plan](0070-custody-daily-dashboard-snapshot-plan.md)
- [0071: Custody One-Shot Dashboard Snapshot Apply](0071-custody-one-shot-dashboard-snapshot-apply.md)
- [0072: Custody Daily Serving-Bundle Construction](0072-custody-daily-serving-bundle-construction.md)
- [0073: Custody One OCI Dashboard Deployment](0073-custody-one-oci-dashboard-deployment.md)
- [0074: Project Descriptive ETF Relationship Change](0074-project-descriptive-etf-relationship-change.md)
- [0075: Project a Bounded ETF Relationship State Timeline](0075-project-bounded-etf-relationship-state-timeline.md)
- [0076: Plan a Default-Off Daily Scheduler Wake](0076-plan-default-off-daily-scheduler-wake.md)
- [0077: Compose One Default-Off Scheduled Wake](0077-compose-one-default-off-scheduled-wake.md)
- [0078: Render a Non-Installed Read-Only systemd Wake](0078-render-non-installed-read-only-systemd-wake.md)
- [0079: Install the Read-Only User Scheduler](0079-install-read-only-user-scheduler.md)
- [0080: Separate Scheduler Operation from Host State](0080-separate-scheduler-operation-from-host-state.md)
- [0081: Make Scheduler Wakes Pipeline-Aware](0081-make-scheduler-wakes-pipeline-aware.md)
- [0082: Bound Distinct Pipeline Wake Cadence](0082-bound-distinct-pipeline-wake-cadence.md)
- [0083: Reuse the Run Journal for Cadence Evidence](0083-reuse-run-journal-for-cadence-evidence.md)
- [0084: Reserve One Pipeline Wake Before Invocation](0084-reserve-one-pipeline-wake-before-invocation.md)
- [0085: Diagnose Unresolved Cadence Wakes Without Replay](0085-diagnose-unresolved-cadence-wakes-without-replay.md)
- [0086: Physically Prove Point-in-Time Universe Membership](0086-physically-prove-point-in-time-universe-membership.md)
- [0087: Visualize Candidate Position Without Inventing Price History](0087-visualize-candidate-position-without-inventing-price-history.md)
- [0088: Bind Candidate Visual Context to Real Dell History](0088-bind-candidate-visual-context-to-real-dell-history.md)
- [0089: Publish Candidate Visual Context in Lazy Detail Shards](0089-publish-candidate-visual-context-in-lazy-detail-shards.md)
- [0090: Build Sector ETF Rotation Without a Composite Score](0090-build-sector-etf-rotation-without-a-composite-score.md)
- [0091: Custody Sector ETF Rotation After Phase 1a](0091-custody-sector-etf-rotation-after-phase1a.md)
- [0092: Project Sector Rotation as Lazy Market Intelligence](0092-project-sector-rotation-as-lazy-market-intelligence.md)
- [0093: Integrate Candidate Visual Context into Daily Planning](0093-integrate-candidate-visual-context-into-daily-planning.md)
- [0094: Block Unreconciled Persistent Workspace Execution](0094-block-unreconciled-persistent-workspace-execution.md)
- [0095: Share Offline Artifact Custody Across Persistent Analytics](0095-share-offline-artifact-custody-across-persistent-analytics.md)
- [0096: Resume Persistent Workspace Planning After Proof](0096-resume-persistent-workspace-planning-after-proof.md)
- [0097: Preregister Personal Strategy Research Before Backtesting](0097-preregister-personal-strategy-research-before-backtesting.md)
- [0098: Bind Strategy Development to Formal Readiness Evidence](0098-bind-strategy-development-to-formal-readiness-evidence.md)
- [0099: Require Transitive Physical Evidence for Historical Coverage](0099-require-transitive-physical-evidence-for-historical-coverage.md)
- [0100: Adapt Current EOD and Identity Without Publishing Coverage](0100-adapt-current-eod-and-identity-without-publishing-coverage.md)
- [0101: Bind Current History to a Blocked Pilot Review](0101-bind-current-history-to-a-blocked-pilot-review.md)
- [0102: Freeze Provider-Neutral Historical Source Packages](0102-freeze-provider-neutral-historical-source-packages.md)
- [0103: Separate Chronological Research Mechanics from Performance](0103-separate-chronological-research-mechanics-from-performance.md)
- [0104: Freeze Session-Balanced Research Statistics Before Real Labels](0104-freeze-session-balanced-research-statistics.md)
- [0105: Require Adversarial Statistics Audit and Complete Labels](0105-require-adversarial-statistics-audit-and-complete-labels.md)
- [0106: Expose Research Readiness Without Performance](0106-expose-research-readiness-without-performance.md)
- [0107: Reserve Holdout Before Evaluation](0107-reserve-holdout-before-evaluation.md)
- [0108: Independently Reproduce Research Inference](0108-independently-reproduce-research-inference.md)
- [0109: Separate Research Readiness from Development Authorization](0109-separate-research-readiness-from-development-authorization.md)
- [0110: Probe Account Entitlement Separately from Historical Acquisition](0110-probe-account-entitlement-separately-from-historical-acquisition.md)
- [0111: Bound Inactive Security Lifecycle Coverage Probing](0111-bound-inactive-security-lifecycle-coverage-probing.md)
- [0112: Census Inactive Pagination Within the Pilot Ceiling](0112-census-inactive-pagination-within-the-pilot-ceiling.md)
- [0113: Treat Degraded User systemd as Review Available](0113-treat-degraded-user-systemd-as-review-available.md)
- [0114: Run the Read-Only Scheduler from an Immutable Worktree](0114-run-the-read-only-scheduler-from-an-immutable-worktree.md)
- [0115: Bind systemd Review to the Immutable Runtime](0115-bind-systemd-review-to-the-immutable-runtime.md)
- [0116: Quarantine Low-Ratio Stable-Identity Collisions](0116-quarantine-low-ratio-stable-identity-collisions.md)
- [0117: Reuse Finalized Candidate Evidence and Parse Snapshots Once](0117-reuse-finalized-candidate-evidence-and-parse-snapshots-once.md)
- [0118: Use the Completion Index for Current Snapshot Session Selection](0118-use-the-completion-index-for-current-snapshot-session-selection.md)
- [0119: Plan a Resumable 300-Session Historical Foundation](0119-plan-a-resumable-300-session-historical-foundation.md)
- [0120: Allow Dell-Local Massive History Without Written Permission](0120-allow-dell-local-massive-history-without-written-permission.md)
- [0121: Run History Newest-to-Oldest with Canonical Resume](0121-run-history-newest-to-oldest-with-canonical-resume.md)
- [0122: Bound Transient Retries Inside Historical Batches](0122-bound-transient-retries-inside-historical-batches.md)
- [0123: Chain Bounded History Batches to a Finite Target](0123-chain-bounded-history-batches-to-a-finite-target.md)
- [0124: Exclude Catalog-Known ETV Without Inferring ETF](0124-exclude-catalog-known-etv-without-inferring-etf.md)
- [0125: Separate Session Discovery from Partition Validation](0125-separate-session-discovery-from-partition-validation.md)
- [0126: Reuse Exact Panel and Current Candidate Evidence Downstream](0126-reuse-exact-panel-and-current-candidate-evidence-downstream.md)
- [0127: Bound Strategy Input to Current Candidate Evidence](0127-bound-strategy-input-to-current-candidate-evidence.md)
- [0128: Separate Daily Candidate Commit from Periodic Semantic Reread](0128-separate-daily-candidate-commit-from-periodic-semantic-reread.md)
- [0129: Bind Snapshot Rollback and CAS to One Active Read](0129-bind-snapshot-rollback-and-cas-to-one-active-read.md)
- [0130: Prove Segmented Candidate Custody Before Cutover](0130-prove-segmented-candidate-custody-before-cutover.md)
- [0131: Expose Family-Specific Research Readiness](0131-expose-family-specific-research-readiness.md)
- [0132: Reconstruct Complete-Base Historical Universe Membership](0132-reconstruct-complete-base-historical-universe-membership.md)
- [0133: Reuse Bounded EOD Panels for Membership Shadow Batches](0133-reuse-bounded-eod-panels-for-membership-shadow-batches.md)
- [0134: Census Historical Identity Package Equivalence Before Reconstruction](0134-census-historical-identity-package-equivalence.md)
- [0135: Reconstruct Legacy ETV Identity Semantics by Explicit Version](0135-reconstruct-legacy-etv-identity-semantics-by-version.md)
- [0136: Bind Historical Identity Rebuild Profiles by Fingerprint](0136-bind-historical-identity-rebuild-profile-by-fingerprint.md)
- [0137: Normalize Historical Identity Source Custody](0137-normalize-historical-identity-source-custody.md)
- [0138: Bind Historical Identity Source Apply Planning](0138-bind-historical-identity-source-apply-plan.md)
- [0139: Apply Historical Identity Source Custody Atomically](0139-apply-historical-identity-source-custody-atomically.md)
- [0140: Expose Canonical Identity Source Custody in Current Context](0140-expose-canonical-identity-source-custody-in-current-context.md)
- [0141: Fetch Historical Identity Source Gaps Without Canonical Writes](0141-fetch-historical-identity-source-gaps-without-canonical-writes.md)
- [0142: Plan Explicit Append-Only Identity Source Custody](0142-plan-explicit-append-only-identity-source-custody.md)
- [0143: Separate Identity Observation and Replay Time](0143-separate-identity-observation-and-replay-time.md)
- [0144: Consume Canonical Identity Source for Membership Shadows](0144-consume-canonical-identity-source-for-membership-shadows.md)
- [0145: Collapse Exact-Duplicate Identity Index References](0145-collapse-exact-duplicate-identity-index-references.md)
- [0146: Complete Bounded Inactive Lifecycle Pagination Census](0146-complete-bounded-inactive-lifecycle-pagination-census.md)
- [0147: Stage Inactive Lifecycle Source with Resumable Custody](0147-stage-inactive-lifecycle-source-with-resumable-custody.md)
- [0148: Build a Disconnected Inactive Lifecycle Resolution Shadow](0148-build-disconnected-inactive-lifecycle-resolution-shadow.md)
- [0149: Separate Sealed and Operational Freshness](0149-separate-sealed-and-operational-freshness.md)
- [0150: Retain Daily Identity Source Observations Atomically](0150-retain-daily-identity-source-observations-atomically.md)
- [0151: Gate Membership by Next-Open Knowledge Time](0151-gate-membership-by-next-open-knowledge-time.md)
- [0152: Plan Membership with a Last Publication Marker](0152-plan-membership-with-a-last-publication-marker.md)
- [0153: Publish Membership Physical First and Marker Last](0153-publish-membership-physical-first-marker-last.md)
- [0154: Prepare Daily Membership Outside the Serving Gate](0154-prepare-daily-membership-outside-the-serving-gate.md)
- [0155: Version the Segmented Candidate Chain Identity](0155-version-segmented-candidate-chain-identity.md)
