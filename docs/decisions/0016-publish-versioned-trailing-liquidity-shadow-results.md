# ADR 0016: Publish Versioned Trailing Liquidity Shadow Results

## Status

Accepted

## Date

2026-08-19

## Context

The provider-neutral EOD history boundary can calculate the audited 20-session median dollar-volume proxy in memory. That result is not yet a durable data product: it cannot be reread through a formal repository, independently hashed, or tied by a logical completion marker to its exact EOD window and Provider-Classified membership evidence.

Candidate A and Candidate B remain non-production shadow candidates. Metric facts should not be duplicated merely because the same instrument appears in both candidates, and a liquidity calculation must not silently become production Universe activation.

## Decision

Publish two schema-versioned Parquet components and one logical completion manifest:

1. one metric fact per stable `instrument_id` in the union of the requested shadow candidates;
2. one decision per `(universe_id, instrument_id)`, keeping Candidate A and Candidate B separate;
3. one logical marker, published last, that binds both components to the exact 20 EOD sessions, same-day identity references, membership-evidence snapshot, thresholds, Decimal policy, counts, hashes, and fingerprints.

The physical Decimal policy remains `decimal128(38, 10)`. Values outside the accepted precision or scale fail rather than round. Publication uses same-filesystem staging, complete reread validation, atomic rename, idempotent identical-target handling, conflict rejection, and cleanup of newly created targets on failure.

The existing stable identifiers remain:

- `provider_classified_common_shares_v1`;
- `provider_classified_common_shares_plus_adrs_shadow_v1`.

The second identifier retains the explicit `shadow` qualifier; it is not renamed into a production Universe.

The completed decision table is also the immutable upstream input for a later Universe pre-activation review. Reviewed exclusions may remove a `passed` member in a separate versioned overlay; they do not rewrite Trailing Liquidity V1 or convert non-passed rows into members.

## Consequences

- Trailing Liquidity V1 becomes versioned, auditable derived data without changing canonical EOD, identity, or provider evidence.
- Metric facts are calculated once, while A/B eligibility decisions and primary reasons remain separately reconcilable.
- The logical marker is the only completion boundary; component data without it is not a completed publication.
- Production Universe activation, Dashboard/API consumption, snapshots, bundles, and deployment remain deferred.
- `current_as_of_constituent_liquidity` remains distinct from a survivorship-free historical panel.

## Alternatives Considered

- Save CLI stdout as JSON. Rejected because it lacks a versioned schema, physical integrity checks, and a logical completion boundary.
- Duplicate metric facts per candidate. Rejected because it creates two sources of truth for the same instrument/session/window metric.
- Replace the Legacy Universe during publication. Rejected because publication mechanics and production policy approval are separate decisions.
