# SEC Fundamental Projection Readiness Census V1

## Purpose

`sec-fundamental-projection-readiness-census/1.0` measures how often a
registered issuer-level SEC fact can be selected at a historical decision
cutoff and carried through ADR 0224's conservative
`single_common_security_per_cik_v1` class. It retains aggregate coverage only;
it is not a security-level fact family or a research feature.

## Time boundary

For each filer/security link `as_of_date`:

- the signal session is that date;
- the evaluated session is the following XNYS session;
- the query cutoff is the following session's market open; and
- an occurrence must have `source_available_at_utc` no later than that cutoff,
  `signal_eligible_session` no later than the evaluated session, and period end
  no later than the cutoff date.

The filing-clock eligible session is already the first XNYS open strictly
after conservative SEC acceptance. This prevents an acceptance exactly at the
open from entering that session.

## Link denominator

Every row in the bound link package receives exactly one disposition:

- source custody missing;
- not a common stock;
- common-stock link not admitted;
- admitted common stock in a multi-common-stock CIK/session group;
- admitted single-common-stock CIK with `as_operated_next_open` evidence; or
- admitted single-common-stock CIK with
  `reconstructed_latest_vintage_development_only` evidence.

The common-stock cardinality is recomputed within each session. The source
package's all-security `cik_instrument_count` is not misused as common-stock
share-class cardinality.

## Query result

For each query, evidence tier, and signal session, the report records the
projection-class denominator and exact `selected`, `not_available`, and
`quarantined` counts. Aggregate query/tier results add:

- distinct selected stable instruments;
- sessions with at least one selected row; and
- selected fact age in calendar-day buckets `0_120`, `121_240`, `241_450`,
  `451_730`, and `731_plus`.

Every query denominator must equal the applicable projection-class row count.
Every aggregate must reproduce its session summaries. The complete query
evaluation count must equal total structurally projectable link rows times the
registered query count.

## Inputs and custody

The report binds the exact query-registry fingerprint, query-readiness census
file and logical fingerprints, normalized-source logical/content fingerprints,
filer/security link manifest SHA-256 and logical/content fingerprints, XNYS
calendar/version, implementation revision, session range, and full link-row
denominator.

The output is an owner-only mode-`0700` immutable package containing one
mode-`0400` `census.json`. Build uses an exact sibling partial path and
no-overwrite atomic rename. Formal readback transitively verifies both the
query-readiness source chain and the complete filer/security link chain.

## Authority boundary

Issuer values, security-fact rows, and a daily Cartesian panel are not retained.
Feature materialization, strategy outcomes, research performance, canonical
data, Membership, Candidate, publication, deployment, scheduling, and external
requests remain unauthorized. Reconstructed coverage cannot support sealed
validation, holdout, headline performance, model activation, or Production.

Implementation:
`tip_api.providers.sec.fundamental_projection_readiness_census`.
