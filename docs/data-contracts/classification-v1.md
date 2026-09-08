# Classification V1

## Purpose

Classification V1 records canonical classification definitions and effective-dated instrument membership for Sector / Industry, Theme, and Analytical Group structures.

## Status

Contract 1.1 and offline Parquet persistence implemented. No real source,
canonical dataset, Candidate integration, research activation, or Production
publication exists.

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
- as_of_date
- source_entity_id
- source_security_id
- instrument_id
- identity_resolution_status
- identity_evidence
- assignment_basis
- external_taxonomy
- external_taxonomy_version
- external_classification_code
- external_classification_path
- valid_from
- valid_to
- source_available_at
- knowledge_time_status
- provider_updated_at
- observed_at
- revision_id
- supersedes_source_observation_id
- correction_status
- permission_review_fingerprint
- eligibility_scope
- quality_status
- quality_flags
- schema_version

`instrument_id`, `source_security_id`, `valid_to`, `source_available_at`,
`provider_updated_at`, `revision_id`, and `supersedes_source_observation_id` may
be null when the source does not supply enough evidence. A null
required-for-research field lowers eligibility; it is never imputed from the
business-valid date.

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
- methodology_version
- quality_status
- quality_flags
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

## Coverage Decision Fields

- instrument_id
- as_of_date
- status
- source_observation_ids
- classification_ids
- eligibility_scope
- reason_codes
- evaluated_at
- quality_status

Every expected instrument receives exactly one `classified`, `not_covered`,
`ambiguous`, `excluded`, or `quarantined` decision. Non-classified decisions
cannot carry canonical classification IDs and remain ineligible. The unknown
bucket is part of the denominator rather than being silently dropped.

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
- Corrected or cancelled observations must reference an earlier observation
  from the same provider entity and taxonomy. A superseded observation cannot
  back a current canonical membership.

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

## Physical Snapshot Boundary

The implemented offline repository publishes one immutable, marker-last
snapshot containing:

- `definitions.parquet`
- `source-observations.parquet`
- `coverage.parquet`
- `memberships.parquet`
- `manifest.json`

The manifest binds logical and physical hashes, row counts, all coverage-status
counts, current-display and historical-research eligible counts, provider and
permission-review identities, request/access state, and explicit Production
and research authorization flags. Formal reread validates the exact file set,
schemas, hashes, row contracts, stable ordering, hierarchy, intervals, source
links, coverage reconciliation, and authorization counts.

The implementation has only been exercised under test-controlled temporary
roots. It has not written `/data` or consumed a provider response.

## Deferred Fields

- final canonical traditional taxonomy source
- initial curated Theme list
- initial Analytical Group basket definitions
- automatic Theme inference
- automatic relationship discovery methodology

## Non-Goals

- investment recommendations
- automatic classification inference in V1
- provider adapter implementation or source selection
- Candidate, Snapshot, or Production integration
- replacing formal industry identity with Theme labels
