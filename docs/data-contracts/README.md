# Data Contracts

- [Market Regime Local Preview Bundle V1](market-regime-preview-bundle-v1.md)

- [Dashboard Snapshot V2](dashboard-snapshot-v2.md)
- [Opportunity Candidate Publication V1](opportunity-candidate-publication-v1.md)
- [Candidate Strategy Evaluation V1](candidate-strategy-evaluation-v1.md)
- [Candidate Entry Geometry V1](candidate-entry-geometry-v1.md)
- [Same-Day Identity and EOD Catch-Up V1](same-day-identity-eod-catchup-v1.md)
- [Historical Research Foundation Contracts V1](historical-research-foundation-v1.md)
- [Data Record Governance V1](data-record-governance-v1.md)

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
- [Historical Research Foundation Contracts V1](historical-research-foundation-v1.md)
- [Data Record Governance V1](data-record-governance-v1.md)

Accepted logical contracts only or only partially represented by the
historical typed boundary:

- [Market Regime & Opportunity Map V1](market-regime-opportunity-map-v1.md)
- [Corporate Action V1](corporate-action-v1.md)
- [Classification V1](classification-v1.md)
- [Universe Membership V1](universe-membership-v1.md)

These documents are not JSON Schema, SQL DDL, sample production data, or
provider adapters. The historical foundation now has provider-neutral
Pydantic row/manifest contracts, explicit PyArrow schemas, and temporary-root
Parquet repository validation, but no canonical dataset. EOD Price Bar V1 and the point-in-time Instrument/Provider
Identity contracts have implemented PyArrow persistence and formal readers.
The initial blocked live attempts remain historical audit evidence; corrected
bounded operations subsequently published the current canonical sequence. The
remaining logical or partial contracts have no physical storage.

The EOD and point-in-time Identity persistence boundaries now hold 29 completed
canonical EOD sessions through 2026-08-26 and 30 Identity snapshots through
2026-08-27. Universe Membership V1 and Corporate Action V1 now have partial
provider-neutral historical row contracts but no physical dataset, complete
partition manifest, or adapter. Their required historical composition is
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
