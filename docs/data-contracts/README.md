# Data Contracts

This directory holds versioned logical interfaces and invariants. It is not a
copy of current Production state and does not itself authorize provider access,
filesystem writes, publication, deployment, or scheduler changes.

Exact current physical coverage belongs in
[current context](../project/current-context.md). All Markdown files in this
directory remain the full contract archive; this page is the curated map.

## Core identity, market data, and governance

- [Instrument Master V1](instrument-master-v1.md)
- [Provider Instrument Identity V1](provider-instrument-identity-v1.md)
- [Provider Ticker Resolver V1](provider-ticker-resolver-v1.md)
- [EOD Price Bar V1](eod-price-bar-v1.md)
- [Reconciled EOD Price Bar Edition V1](reconciled-eod-price-bar-edition-v1.md)
- [Data Record Governance V1](data-record-governance-v1.md)
- [Source Permission Governance V1](source-permission-governance-v1.md)
- [Security Classification V1](security-classification-v1.md)
- [Classification V1](classification-v1.md)
- [Corporate Action V1](corporate-action-v1.md)

Stable instrument ID is the join key; ticker is effective-dated display
identity. Provider observations, canonical facts, derived facts, research
panels, and product publications remain separate.

## Universe and historical research foundation

- [Universe Membership V1](universe-membership-v1.md)
- [Universe Membership Knowledge Time V1](universe-membership-knowledge-time-v1.md)
- [Universe Membership Canonical Publication V1](universe-membership-canonical-publication-v1.md)
- [Dashboard Universe Activation V2](dashboard-universe-activation-v2.md)
- [Historical Research Foundation V1](historical-research-foundation-v1.md)
- [Strong-Leader Pullback Terminal Gap Census V4](strong-leader-pullback-terminal-gap-census-v4.md)
- [Strong-Leader Pullback Pre-Research Admission Review V1](strong-leader-pullback-pre-research-admission-review-v1.md)
- [Strong-Leader Pullback Method-Engineering Launch Review V1](strong-leader-pullback-method-engineering-launch-review-v1.md)
- [Five-Year Research Foundation Census V1](five-year-research-foundation-census-v1.md)
- [Massive Day Aggregates Flat File Package V1](massive-day-aggregates-flat-file-package-v1.md)
- [FINRA OTC Daily List Source Package V1](finra-otc-daily-list-source-package-v1.md)
- [FINRA OTC Daily List Range Census V1](finra-otc-daily-list-range-census-v1.md)
- [FINRA/Massive Action Cross-Source Census V1](finra-massive-action-cross-source-census-v1.md)
- [SEC Company Facts Source Package V1](sec-companyfacts-source-package-v1.md)
- [SEC Company Facts Payload Census V1](sec-companyfacts-payload-census-v1.md)
- [SEC Submissions Source Package V1](sec-submissions-source-package-v1.md)
- [SEC Submissions Payload Census V1](sec-submissions-payload-census-v1.md)
- [SEC Filing-Clock Ledger V1](sec-filing-clock-ledger-v1.md)
- [SEC Company Facts Normalized Source V1](sec-companyfacts-normalized-source-v1.md)
- [SEC Company Facts Semantic Census V1](sec-companyfacts-semantic-census-v1.md)
- [SEC Fundamental Query Registry V1](sec-fundamental-query-registry-v1.md)
- [SEC Fundamental Query Readiness Census V1](sec-fundamental-query-readiness-census-v1.md)
- [SEC Fundamental Projection Readiness Census V1](sec-fundamental-projection-readiness-census-v1.md)
- [SEC Filer-to-Security Link Decision V1](sec-filer-security-link-decision-v1.md)
- [SEC Point-in-Time Fundamental Selection V1](sec-point-in-time-fundamental-selection-v1.md)
- [Historical Source Package V1](historical-source-package-v1.md)
- [Historical Identity Source Custody V1](historical-identity-source-custody-v1.md)
- [Historical Corporate Action Source Package V1](historical-corporate-action-source-package-v1.md)
- [Historical Corporate Action Resolution Shadow V1](historical-corporate-action-resolution-shadow-v1.md)
- [Historical Corporate Action Unresolved Census V1](historical-corporate-action-unresolved-census-v1.md)
- [Historical Corporate Action Residual Evidence Census V1](historical-corporate-action-residual-evidence-census-v1.md)
- [Historical Identity Extension Family Evidence V1](historical-identity-extension-family-evidence-v1.md)
- [Historical Corporate Action Source Repeat Diff V1](historical-corporate-action-source-repeat-diff-v1.md)
- [Corporate Action Source Publication V1](corporate-action-source-publication-v1.md)
- [Canonical Split Action Publication V1](canonical-split-action-publication-v1.md)
- [Canonical Split Adjustment Publication V1](canonical-split-adjustment-publication-v1.md)

Implemented mechanics or a canonical partial family never imply complete
Historical Coverage. Missing membership, lifecycle, actions, availability, or
adjustment evidence remains explicit.

## Quant Research Lab

The durable research architecture is Factor Discovery -> Model Construction
-> Strategy Expression. The contracts below include both the first bounded
factor catalog and retained Strong-Leader Pullback/Baseline V1 evidence. A
historical model or Candidate contract is not the permanent research taxonomy;
see [ADR 0274](../decisions/0274-adopt-factor-model-strategy-three-layer-research-architecture.md).

- [Strong-Leader Pullback Method V1](strong-leader-pullback-method-v1.md)
- [Strong-Leader Pullback Method Diagnostics V1](strong-leader-pullback-method-diagnostics-v1.md)
- [Quant Research Lab Model Record V1](quant-research-lab-model-record-v1.md)
- [Candidate Strategy Research Experiment V1](candidate-strategy-research-experiment-v1.md)
- [Strategy Research Readiness V1](strategy-research-readiness-v1.md)
- [Strategy Research Development Activation Review V1](strategy-research-development-activation-review-v1.md)
- [Strong-Leader Pullback Development Coverage Census V1](strong-leader-pullback-development-coverage-census-v1.md)
- [Strong-Leader Pullback Development Admission Decision V1](strong-leader-pullback-development-admission-decision-v1.md)
- [Strong-Leader Pullback Evidence Blocker Census V1](strong-leader-pullback-evidence-blocker-census-v1.md)
- [Strong-Leader Pullback Source Acceptance Sample V1](strong-leader-pullback-source-acceptance-sample-v1.md)
- [Strong-Leader Pullback Source Acceptance Result V1](strong-leader-pullback-source-acceptance-result-v1.md)
- [Strong-Leader Pullback SEC Lifecycle Pilot V1](strong-leader-pullback-sec-lifecycle-pilot-v1.md)
- [Strong-Leader Pullback SEC Document Plan V1](strong-leader-pullback-sec-document-plan-v1.md)
- [Strong-Leader Pullback SEC Document Source V1](strong-leader-pullback-sec-document-source-v1.md)
- [Strong-Leader Pullback SEC Document Content Census V1](strong-leader-pullback-sec-document-content-census-v1.md)
- [Strong-Leader Pullback SEC Form 25 Candidates V1](strong-leader-pullback-sec-form25-candidates-v1.md)
- [Strong-Leader Pullback SEC Form 15 Candidates V1](strong-leader-pullback-sec-form15-candidates-v1.md)
- [Strong-Leader Pullback SEC Transaction Candidates V1](strong-leader-pullback-sec-transaction-candidates-v1.md)
- [Strong-Leader Pullback SEC Case Coverage Census V1](strong-leader-pullback-sec-case-coverage-census-v1.md)
- [Strong-Leader Pullback SEC Case Adjudication V1](strong-leader-pullback-sec-case-adjudication-v1.md)
- [Strong-Leader Pullback SEC Transaction Event Adjudication V1](strong-leader-pullback-sec-transaction-event-adjudication-v1.md)
- [Strong-Leader Pullback SEC Termination Reason Adjudication V1](strong-leader-pullback-sec-termination-reason-adjudication-v1.md)
- [Strong-Leader Pullback SEC Consideration Adjudication V1](strong-leader-pullback-sec-consideration-adjudication-v1.md)
- [Strong-Leader Pullback SEC Party Relation Adjudication V1](strong-leader-pullback-sec-party-relation-adjudication-v1.md)
- [Strong-Leader Pullback Trading Cessation Adjudication V1](strong-leader-pullback-trading-cessation-adjudication-v1.md)
- [Strong-Leader Pullback Terminal Payoff Terms V1](strong-leader-pullback-terminal-payoff-terms-v1.md)
- [Strong-Leader Pullback Fixed-Cash Terminal Evidence V1](strong-leader-pullback-fixed-cash-terminal-evidence-v1.md)
- [Strong-Leader Pullback Listed-Consideration Source Plan V1](strong-leader-pullback-listed-consideration-source-plan-v1.md)
- [Strong-Leader Pullback Listed-Consideration Source V1](strong-leader-pullback-listed-consideration-source-v1.md)
- [Strong-Leader Pullback Listed-Consideration Adjudication V1](strong-leader-pullback-listed-consideration-adjudication-v1.md)
- [Strong-Leader Pullback Listed-Consideration Terminal Evidence V1](strong-leader-pullback-listed-consideration-terminal-evidence-v1.md)
- [Strong-Leader Pullback Listed-Consideration Residual Source Plan V1](strong-leader-pullback-listed-consideration-residual-source-plan-v1.md)
- [Strong-Leader Pullback Listed-Consideration Residual Source V1](strong-leader-pullback-listed-consideration-residual-source-v1.md)
- [Strong-Leader Pullback Listed-Consideration Residual Adjudication V1](strong-leader-pullback-listed-consideration-residual-adjudication-v1.md)
- [Strong-Leader Pullback Listed-Consideration Residual Terminal Evidence V1](strong-leader-pullback-listed-consideration-residual-terminal-evidence-v1.md)
- [Strong-Leader Pullback Terminal Boundary Census V1](strong-leader-pullback-terminal-boundary-census-v1.md)
- [Strong-Leader Pullback Terminal Gap Census V2](strong-leader-pullback-terminal-gap-census-v2.md)
- [Strong-Leader Pullback Terminal-Population SEC Source Plan V1](strong-leader-pullback-terminal-population-sec-source-plan-v1.md)
- [Strong-Leader Pullback Terminal-Population SEC Source V1](strong-leader-pullback-terminal-population-sec-source-v1.md)
- [Strong-Leader Pullback Terminal-Population SEC Content Census V1](strong-leader-pullback-terminal-population-sec-content-census-v1.md)
- [Strong-Leader Pullback Terminal-Population SEC Field Candidates V1](strong-leader-pullback-terminal-population-sec-field-candidates-v1.md)
- [Strong-Leader Pullback Terminal-Population SEC Core Adjudication V1](strong-leader-pullback-terminal-population-sec-core-adjudication-v1.md)
- [Strong-Leader Pullback Terminal-Population Trading Cessation Adjudication V1](strong-leader-pullback-terminal-population-trading-cessation-adjudication-v1.md)
- [Strong-Leader Pullback Terminal-Population Payoff Policy V1](strong-leader-pullback-terminal-population-payoff-policy-v1.md)
- [Strong-Leader Pullback Research Input V1](strong-leader-pullback-research-input-v1.md)
- [Strong-Leader Pullback Research Admission V2](strong-leader-pullback-research-admission-v2.md)
- [Strong-Leader Pullback Terminal Reference Bounds V1](strong-leader-pullback-terminal-reference-bounds-v1.md)
- [Strong-Leader Pullback Reconstructed Development Dataset V1](strong-leader-pullback-reconstructed-development-dataset-v1.md)
- [Strong-Leader Pullback Reconstructed Development Statistics V1](strong-leader-pullback-reconstructed-development-statistics-v1.md)
- [Strong-Leader Pullback Reconstructed Replacement Selection V1](strong-leader-pullback-reconstructed-replacement-selection-v1.md)
- [Quant Research Factor Catalog V1](quant-research-factor-catalog-v1.md)
- [Quant Research Factor Catalog V2](quant-research-factor-catalog-v2.md)
  registers the next adaptive daily-behavior batch with zero outcome access.
- [Quant Research Discovery Trial Ledger V1](quant-research-discovery-trial-ledger-v1.md)
  retains every consumed factor-screen trial before a later adaptive campaign.
- [Quant Research Factor Screening V1](quant-research-factor-screening-v1.md)
  freezes the first Development screen; its completed no-Alpha result and exact
  replay are recorded in the [screening audit](../audits/quant-research-factor-screening-2026-09-15.md).
- `quant-research-factor-value/1.0`, `quant-research-factor-observation/1.0`,
  and `quant-research-factor-diagnostics/1.0` are the typed implementation and
  private qualification-report contracts for that catalog. Their frozen
  protocol and first real report are recorded in [ADR 0275](../decisions/0275-freeze-outcome-blind-factor-qualification-protocol.md)
  and the [qualification audit](../audits/quant-research-factor-qualification-2026-09-15.md).
- [Candidate Strategy Research Execution V1](candidate-strategy-research-execution-v1.md)
- [Candidate Strategy Research Statistics V1](candidate-strategy-research-statistics-v1.md)
- [Candidate Strategy Holdout Custody V1](candidate-strategy-holdout-custody-v1.md)
- [Candidate Strategy Evaluation V1](candidate-strategy-evaluation-v1.md)
- [Equity Execution Cost Scenario V1](equity-execution-cost-scenario-v1.md)

These contracts separate the model registry, result publication, Product
activation, input construction, signals, future labels, statistics, costs,
readiness, and holdout custody. Fixture-tested mechanics are not real model
performance. A Lab result never grants Candidate authority.

## Deployed Candidate baseline and product publication

- [Opportunity Candidate Publication V1](opportunity-candidate-publication-v1.md)
- [Candidate Entry Geometry V1](candidate-entry-geometry-v1.md)
- [Candidate Strategy Channel Product V1](candidate-strategy-channel-product-v1.md)
- [Candidate Visual Context V1](candidate-visual-context-v1.md)
- [Market Intelligence Publication V1](market-intelligence-publication-v1.md)
- [Dashboard Snapshot V2](dashboard-snapshot-v2.md)
- [Market Regime & Opportunity Map V1](market-regime-opportunity-map-v1.md)

These describe current Production-compatible Baseline V1 behavior. They remain
valid until a versioned replacement, but do not authorize direct parameter
tuning or make the baseline chronologically validated.

The segmented Candidate family is retained as a distinct experimental custody
line and remains a cutover NO-GO. See the relevant numbered contracts and
ADRs 0155–0164; do not relabel it as current Candidate V1.

## Daily operation and recovery

- [Same-Day Identity and EOD Catch-Up V1](same-day-identity-eod-catchup-v1.md)
- [Daily EOD Bounded Cadence V1](daily-eod-bounded-cadence-v1.md)
- [Daily EOD Bounded Offline Run V1](daily-eod-bounded-offline-run-v1.md)
- [Daily EOD Scheduler Runtime Plan V1](daily-eod-scheduler-runtime-plan-v1.md)
- [Daily Universe Membership Sidecar Plan V1](daily-universe-membership-sidecar-plan-v1.md)
- [Daily Universe Membership Bounded Run V1](daily-universe-membership-bounded-run-v1.md)

Operational contracts preserve finite budgets, exact custody, fail-closed
recovery, and separation between read-only review and write-capable actions.

## Shared implementation rules

- Use provider-neutral canonical contracts.
- Keep raw, normalized, canonical, derived, research, and serving layers
  separate.
- Preserve point-in-time/effective-dated facts, revisions, and UTC clocks.
- Keep missing values null or quarantined unless a versioned rule says
  otherwise.
- Never overwrite a completed revision silently.
- Interpret session date through the governed exchange calendar.
- Keep contract version, code revision, source lineage, and fingerprints
  reproducible.

The public Python contract import surface is documented by package code and
tests; do not duplicate a partial import list here.
