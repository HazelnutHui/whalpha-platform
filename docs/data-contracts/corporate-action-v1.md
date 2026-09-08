# Corporate Action V1

## Purpose

Corporate Action V1 records source facts about actions that affect instrument identity, adjustments, payouts, or listing status.

## Status

Partially Implemented — Typed Source Observation Only

The provider-neutral historical source-observation record implements the
action scope, source revision/correction state, three clocks, stable-ID
resolution, evidence quality, action-specific validation, and fixture-only
PyArrow persistence. Canonical event IDs, canonical Corporate Action
persistence, completed coverage, and a source-to-canonical provider adapter
remain unimplemented. ADR 0169 adds resumable temporary source custody for
Massive V1 split and dividend pages, but it deliberately performs no stable-ID
mapping or canonical write.

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

## Historical Implementation Prerequisites

The historical typed boundary now binds the source-observation metadata
required by the
[Historical Research Data Foundation V1](../architecture/historical-research-data-foundation-v1.md):
first observed/ingested time, source-published or source-available time when
provided, evidence quality, ambiguity reasons, cancellation/correction state,
and the exact source revision. Physical schemas and repositories must preserve
those fields rather than hiding them in free-form notes.

Corporate-action coverage needs its own completion manifest. A missing event
row is not proof that no action occurred unless the declared source/range
coverage is complete.

## Deferred Fields

- complex tax treatment
- cost-basis allocation
- complete restructuring legal terms
- detailed multi-leg reorganization modeling

## Non-Goals

- adjustment factor calculation
- legal-document storage
- source-to-canonical provider adapter implementation
- deletion of instrument history
