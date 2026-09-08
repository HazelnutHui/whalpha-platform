# Data Contracts

- [Universe Membership Knowledge Time V1](universe-membership-knowledge-time-v1.md)
- [Universe Membership Canonical Publication V1](universe-membership-canonical-publication-v1.md)

- [Daily EOD Scheduler Runtime Plan V1](daily-eod-scheduler-runtime-plan-v1.md)

- [Massive Historical Lifecycle Pagination Census V1](massive-historical-lifecycle-pagination-census-v1.md)
- [Massive Historical Lifecycle Completion Census V1](massive-historical-lifecycle-completion-census-v1.md)
- [Historical Inactive Lifecycle Source Package V1](historical-inactive-lifecycle-source-package-v1.md)
- [Historical Inactive Lifecycle Corroboration Plan V1](historical-inactive-lifecycle-corroboration-plan-v1.md)

- [Massive Historical Lifecycle Coverage Probe V1](massive-historical-lifecycle-coverage-probe-v1.md)

- [Massive Historical Entitlement Probe V1](massive-historical-entitlement-probe-v1.md)

- [Market Regime Local Preview Bundle V1](market-regime-preview-bundle-v1.md)

- [Dashboard Snapshot V2](dashboard-snapshot-v2.md)
- [Opportunity Candidate Publication V1](opportunity-candidate-publication-v1.md)
- [Opportunity Candidate Segmented Shadow V1](opportunity-candidate-segmented-shadow-v1.md)
- [Opportunity Candidate Segmented Append V1](opportunity-candidate-segmented-append-v1.md)
- [Opportunity Candidate Segmented Session Candidate V1](opportunity-candidate-segmented-session-candidate-v1.md)
- [Opportunity Candidate Segmented Chain Head V1](opportunity-candidate-segmented-chain-head-v1.md)
- [Opportunity Candidate Segmented Chain-Head Publication V1](opportunity-candidate-segmented-chain-head-publication-v1.md)
- [Opportunity Candidate Segmented Chain-Head Apply V1](opportunity-candidate-segmented-chain-head-apply-v1.md)
- [Opportunity Candidate Segmented Chain-Head Full-Lineage Audit V1](opportunity-candidate-segmented-chain-head-full-lineage-audit-v1.md)
- [Candidate Strategy Evaluation V1](candidate-strategy-evaluation-v1.md)
- [Candidate Strategy Research Experiment V1](candidate-strategy-research-experiment-v1.md)
- [Candidate Strategy Research Execution V1](candidate-strategy-research-execution-v1.md)
- [Candidate Strategy Research Statistics V1](candidate-strategy-research-statistics-v1.md)
- [Candidate Strategy Holdout Custody V1](candidate-strategy-holdout-custody-v1.md)
- [Strategy Research Readiness V1](strategy-research-readiness-v1.md)
- [Strategy Research Development Activation Review V1](strategy-research-development-activation-review-v1.md)
- [Candidate Strategy Channel Product V1](candidate-strategy-channel-product-v1.md)
- [Candidate Entry Geometry V1](candidate-entry-geometry-v1.md)
- [Candidate Visual Context V1](candidate-visual-context-v1.md)
- [Same-Day Identity and EOD Catch-Up V1](same-day-identity-eod-catchup-v1.md)
- [Historical Research Foundation Contracts V1](historical-research-foundation-v1.md)
- [Data Record Governance V1](data-record-governance-v1.md)
- [Source Permission Governance V1](source-permission-governance-v1.md)
- [Historical Source Package V1](historical-source-package-v1.md)
- [Historical Identity Source Custody V1](historical-identity-source-custody-v1.md)
- [Historical Identity Source Apply Plan V1](historical-identity-source-apply-plan-v1.md)
- [Historical Identity Source Apply V1](historical-identity-source-apply-v1.md)
- [Universe Membership Knowledge Time V1](universe-membership-knowledge-time-v1.md)
- [Universe Membership Canonical Publication V1](universe-membership-canonical-publication-v1.md)

- [Security Classification V1](security-classification-v1.md)

Security Classification V1 now includes offline-tested SEC issuer evidence observation, canonical evidence, and completion-manifest contracts. No production SEC evidence partition exists.

This directory records accepted logical market-data contracts for Trading Intelligence Platform.

## Implementation Status

Implemented as Python/Pydantic contracts:

- [Instrument Master V1](instrument-master-v1.md)
- [EOD Price Bar V1](eod-price-bar-v1.md)
- [Provider Instrument Identity V1](provider-instrument-identity-v1.md)
- [Provider Ticker Resolver V1](provider-ticker-resolver-v1.md)
- [Trailing Liquidity Shadow Publication V1](trailing-liquidity-shadow-v1.md)
- [Reviewed Eligibility Override V1](reviewed-eligibility-override-v1.md)
- [Dashboard Universe Activation V2](dashboard-universe-activation-v2.md)
- [Candidate Entry Geometry V1](candidate-entry-geometry-v1.md)
- [Candidate Visual Context V1](candidate-visual-context-v1.md)
- [Historical Research Foundation Contracts V1](historical-research-foundation-v1.md)
- [Data Record Governance V1](data-record-governance-v1.md)
- [Source Permission Governance V1](source-permission-governance-v1.md)
- [Historical Source Package V1](historical-source-package-v1.md)
- [Historical Identity Source Custody V1](historical-identity-source-custody-v1.md)
- [Historical Identity Source Apply Plan V1](historical-identity-source-apply-plan-v1.md)
- [Historical Identity Source Apply V1](historical-identity-source-apply-v1.md)
- [Candidate Strategy Research Execution V1](candidate-strategy-research-execution-v1.md)
- [Candidate Strategy Research Statistics V1](candidate-strategy-research-statistics-v1.md)

Accepted logical contracts only or only partially represented by the
historical typed boundary:

- [Market Regime & Opportunity Map V1](market-regime-opportunity-map-v1.md)
- [Corporate Action V1](corporate-action-v1.md)
- [Classification V1](classification-v1.md)
- [Universe Membership V1](universe-membership-v1.md)

These documents are not JSON Schema, SQL DDL, sample production data, or
provider adapters. The historical foundation now has provider-neutral
Pydantic row/manifest contracts, explicit PyArrow schemas, governed
temporary/persistent Parquet custody, and an applied atomic source-custody
executor.
Normalized Identity source observations are canonical for 302/304 sessions;
the two provider-revised dates remain explicitly unbound. Canonical Membership
contains one signal-eligible 2026-09-04 partition and is not a historical
series. The Membership timing gate keeps the corrected 9/3 historical
reconstruction outcome-only; neither result is a Coverage publication.
EOD Price Bar V1 and the point-in-time Instrument/Provider
Identity contracts have implemented PyArrow persistence and formal readers.
The initial blocked live attempts remain historical audit evidence; corrected
bounded operations subsequently published the current canonical sequence. The
remaining logical or partial contracts have no physical storage.

The EOD and point-in-time Identity persistence boundaries hold the completed
canonical sequence recorded in
[current context](../project/current-context.md). The 300-session historical
price target is complete, but that does not complete a research-ready
Historical Coverage publication.
Universe Membership V1 now has one physical canonical partition plus a
marker-backed reader and a prospective daily preparation boundary. Corporate
Action V1 remains contract-only. Their required historical composition is
defined in [Historical Research Data Foundation V1](../architecture/historical-research-data-foundation-v1.md).

## Public Python Import Path

```python
from tip_api.contracts.market_data.v1 import (
    EodPriceBarV1,
    InstrumentMasterV1,
    InstrumentStatus,
    InstrumentType,
    QualityStatus,
)
```

## Shared Rules

- Use provider-neutral canonical contracts.
- Keep raw, normalized, and derived layers separate.
- Use `instrument_id` as the stable internal instrument key.
- Do not treat `ticker` as a permanent primary key.
- Preserve point-in-time and effective-dated history.
- Keep missing values null unless a documented rule says otherwise.
- Keep revisions traceable.
- Do not silently overwrite corrected data.
- Store operational timestamps in UTC.
- Interpret `session_date` through exchange calendars.
