# Corporate Action V1

## Purpose

Corporate Action V1 records source facts about actions that affect instrument identity, adjustments, payouts, or listing status.

## Status

Accepted Logical Contract — Not Yet Implemented

## Grain

One record represents one corporate action event for an instrument, source, and revision.

## Stable Identifier

`corporate_action_id` is the internal stable identifier.

## Fields

Core fields:

- corporate_action_id
- instrument_id
- action_type
- announcement_date
- ex_date
- record_date
- pay_date
- effective_date
- source
- source_action_id
- ingested_at
- revision
- quality_status
- schema_version

Action-specific nullable fields:

- split_ratio_from
- split_ratio_to
- cash_amount
- currency
- new_ticker
- successor_instrument_id
- related_instrument_id
- termination_reason

## Nullable Fields

Unknown dates and action-specific fields remain null. Distinct dates must not be forced to the same value.

## Enumerations

Initial `action_type` values:

- stock_split
- reverse_split
- cash_dividend
- stock_dividend
- symbol_change
- merger
- spinoff
- delisting

## Validation Rules

- Split ratio direction must be explicit, such as 1 -> 4.
- A symbol change usually keeps the same `instrument_id`.
- Mergers and spinoffs may create or reference distinct instruments.
- Delisting does not delete Instrument Master history.
- Delisting ends validity and updates status.
- Corporate-action facts and derived adjustment factors remain separate.
- Uncertain successor relationships must be flagged for review.

## Temporal Semantics

Announcement, ex, record, pay, and effective dates are distinct concepts and remain separately nullable.

## Revision Semantics

Provider corrections create traceable revisions. Prior revisions remain auditable.

## Provider Mapping Boundary

Provider corporate-action records map into this logical contract. Adjustment factors derived from these facts belong to separate normalized or derived datasets.

## Deferred Fields

- complex tax treatment
- cost-basis allocation
- complete restructuring legal terms
- detailed multi-leg reorganization modeling

## Non-Goals

- adjustment factor calculation
- legal-document storage
- provider adapter implementation
- deletion of instrument history
