# Classification V1

## Purpose

Classification V1 records canonical classification definitions and effective-dated instrument membership for Sector / Industry, Theme, and Analytical Group structures.

## Status

Accepted Logical Contract — Not Yet Implemented

## Grain

Classification Definition grain: one classification definition for a methodology version and validity range.

Classification Membership grain: one instrument-to-classification membership for a validity range.

## Stable Identifier

`classification_id` is the stable internal classification key. Display name is not a primary key.

## Definition Fields

- classification_id
- classification_type
- name
- description
- parent_classification_id
- methodology_version
- status
- valid_from
- valid_to
- source
- schema_version

## Membership Fields

- instrument_id
- classification_id
- valid_from
- valid_to
- membership_role
- membership_weight
- confidence
- source
- source_reference
- assigned_at
- review_status
- schema_version

## Nullable Fields

Definition:

- description
- parent_classification_id
- valid_to

Membership:

- valid_to
- membership_weight
- confidence
- source_reference

## Enumerations

`classification_type` values:

- sector
- industry_group
- industry
- sub_industry
- theme
- analytical_group

## Validation Rules

- Hierarchy uses `parent_classification_id`.
- Methodology changes are versioned.
- External taxonomies are mapped into canonical internal classifications.
- Traditional industry path is unique at a given effective time.
- Theme membership is many-to-many.
- Analytical Group membership is many-to-many.
- `membership_weight` is used only when backed by a defined methodology.
- Do not assign equal weights by default without a reason.
- `confidence` measures classification certainty, not investment strength.
- Manual assignments retain source and review status.
- Theme and Analytical Group membership do not replace traditional industry identity.

## Temporal Semantics

Definitions and memberships use effective dating through `valid_from` and `valid_to`. Historical analytics should avoid projecting current membership backward.

## Revision Semantics

Methodology versions and effective dating preserve classification history. Manual review status records uncertainty or approval state.

## Provider Mapping Boundary

Provider taxonomy fields map into canonical classification IDs. Domain logic should not depend on vendor taxonomy field names.

## Deferred Fields

- final canonical traditional taxonomy source
- initial curated Theme list
- initial Analytical Group basket definitions
- automatic Theme inference
- automatic relationship discovery methodology

## Non-Goals

- investment recommendations
- automatic classification inference in V1
- provider adapter implementation
- replacing formal industry identity with Theme labels
