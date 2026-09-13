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

- [Quant Research Lab Model Record V1](quant-research-lab-model-record-v1.md)
- [Candidate Strategy Research Experiment V1](candidate-strategy-research-experiment-v1.md)
- [Strategy Research Readiness V1](strategy-research-readiness-v1.md)
- [Strategy Research Development Activation Review V1](strategy-research-development-activation-review-v1.md)
- [Strong-Leader Pullback Development Coverage Census V1](strong-leader-pullback-development-coverage-census-v1.md)
- [Strong-Leader Pullback Development Admission Decision V1](strong-leader-pullback-development-admission-decision-v1.md)
- [Strong-Leader Pullback Evidence Blocker Census V1](strong-leader-pullback-evidence-blocker-census-v1.md)
- [Strong-Leader Pullback Source Acceptance Sample V1](strong-leader-pullback-source-acceptance-sample-v1.md)
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
- [Strong-Leader Pullback Research Input V1](strong-leader-pullback-research-input-v1.md)
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
