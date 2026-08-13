# Data Contracts

This directory records accepted logical market-data contracts for Trading Intelligence Platform.

Status for all V1 contracts: Accepted Logical Contract — Not Yet Implemented.

These documents are not JSON Schema, SQL DDL, Python models, Pydantic classes, Parquet schemas, sample data, or provider adapters.

## Contracts

- [Instrument Master V1](instrument-master-v1.md)
- [EOD Price Bar V1](eod-price-bar-v1.md)
- [Corporate Action V1](corporate-action-v1.md)
- [Classification V1](classification-v1.md)
- [Universe Membership V1](universe-membership-v1.md)

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
