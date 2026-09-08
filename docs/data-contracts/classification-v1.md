# Classification V1

## Purpose

Classification V1 records canonical classification definitions and effective-dated instrument membership for Sector / Industry, Theme, and Analytical Group structures.

## Status

Accepted Logical Contract 1.1 — Not Yet Implemented

## Grain

Source Observation grain: one provider taxonomy observation for one provider
entity/security and observed business-valid range.

Classification Definition grain: one canonical classification definition for
a methodology version and validity range.

Classification Membership grain: one instrument-to-classification membership for a validity range.

## Stable Identifier

`classification_id` is the stable internal classification key. Display name is not a primary key.

## Source Observation Fields

- source_observation_id
- source
- source_entity_id
- source_security_id
- instrument_id
- identity_resolution_status
- identity_resolution_evidence
- assignment_basis
- external_taxonomy
- external_taxonomy_version
- external_classification_code
- external_classification_path
- valid_from
- valid_to
- source_available_at
- provider_updated_at
- observed_at
- revision_id
- correction_status
- permission_review_fingerprint
- schema_version

`instrument_id`, `source_security_id`, `valid_to`, `source_available_at`,
`provider_updated_at`, and `revision_id` may be null when the source does not
supply enough evidence. A null required-for-research field lowers eligibility;
it is never imputed from the business-valid date.

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
- source_observation_id
- assignment_basis
- source_available_at
- eligibility_scope
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
- source_available_at

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
- Ticker and name may create review flags only; they never resolve a source
  observation or canonical membership positively.
- Company/issuer classification projected to a listed security uses
  `assignment_basis=issuer_projected` and retains the reviewed crosswalk.
- Missing or ambiguous identity, taxonomy mapping, validity, or permission
  evidence remains quarantined.

## Temporal Semantics

Definitions and memberships use half-open effective dating through `valid_from`
and `valid_to`. Business validity and knowledge time are separate.
`source_available_at` records when an observation was defensibly knowable.
Historical research requires `source_available_at` at or before the signal
cutoff and must not project current membership backward.

## Revision Semantics

Methodology versions, effective dating, source availability, revision IDs, and
correction status preserve classification history. Manual review status records
uncertainty or approval state. A later correction appends evidence; it does not
silently overwrite a previously consumed observation.

## Provider Mapping Boundary

Provider taxonomy fields map into canonical classification IDs. Domain logic should not depend on vendor taxonomy field names.

Current-display eligibility and historical-research eligibility are distinct.
A current completed observation may support a current product view without
becoming research evidence. Historical eligibility additionally requires
knowledge-time, historical interval, revision, and inactive-coverage gates.

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
