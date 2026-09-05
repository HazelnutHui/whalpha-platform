# Historical Identity Source Custody V1

## Purpose and status

This contract converts a fingerprint-bound, custody-valid temporary Identity
reference package into a typed, credential-free source-observation partition.
The implementation boundary is `/tmp` candidate construction and formal
reread only. It does not write `/data` or grant acquisition, membership,
Historical Coverage, research, publication, deployment, or scheduler
authority.

## Row contract

`historical-identity-reference-observation/1.0` preserves every result field
present in the 279 audited packages:

- `active`, `cik`, `composite_figi`, `currency_name`;
- `last_updated_utc`, `locale`, `market`, `name`;
- `primary_exchange`, `share_class_figi`, `ticker`, `type`.

Rows also bind provider, as-of session, source observation time, page sequence,
row sequence, and a deterministic record fingerprint. One row is retained per
source occurrence; duplicates are not silently collapsed. Missing optional
values remain null. Unexpected result keys and unsupported value types fail
closed rather than being discarded.

## Completion and evidence

Each immutable partition contains `part-00000.parquet` and `manifest.json`.
The manifest binds the profile map, exact session binding, selected historical
rebuild profile, temporary package locator and custody hashes, accepted
canonical Identity fingerprints, per-page hashes/counts, the fixed source
field list, row count, logical content fingerprint, Parquet SHA-256, and
materialization time.

The reader verifies the exact path, owner-only/read-only custody, file set,
Arrow schema, deterministic source order, per-row fingerprints, record count,
logical content fingerprint, Parquet hash, package-artifact row reconciliation,
and manifest self-fingerprint. Symlinks and extra files are rejected.

The offline runner accepts a finite maximum of 303 explicitly profile-bound
sessions and at most four worker processes. A profile-map 1.1 inventory may
also contain explicitly unbound dual-profile mismatches; they must be present
exactly once in discovery but cannot be selected or normalized. Each selected
session publishes atomically and independently, so completed partitions—not
an external progress counter—are the resume authority. Worker processes
disable socket creation. A failed session stops the invocation without
deleting or relabelling prior completed partitions.

Response URLs, request identifiers, response-wrapper bodies, credentials, and
Authorization values are not retained. Page status, reported count,
pagination-presence, artifact size, and artifact hash remain as bounded
custody evidence.

## Time and governance

The session is source effective/as-of time. `package_fetched_at` and each
row's `source_observed_at` preserve the actual Dell package observation time.
They are later than the historical session for backfilled or reacquired
packages, so point-in-time eligibility is explicitly
`outcome_reconciliation_only` until a separate availability policy proves a
stronger claim.

Exact reconstruction separately reads the accepted canonical Identity
families' row-level `ingested_at`. Instrument Master, Provider Identity, and
Resolver must each contain one non-null timestamp and all three values must be
equal. That accepted replay timestamp reproduces canonical build provenance;
it never replaces or backdates the source observation timestamp. All three
content fingerprints must still match exactly.

The data family is `point_in_time_identity`, layer `source_observation`, scope
`internal_only`, and retention `canonical_no_auto_expiry`. Durable publication
requires the separate inventory-bound plan and atomic Apply/recovery boundary;
this contract alone creates no canonical presence claim.
