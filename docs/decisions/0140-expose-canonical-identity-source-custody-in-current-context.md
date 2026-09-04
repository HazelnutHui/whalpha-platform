# ADR 0140: Expose Canonical Identity Source Custody in Current Context

- Status: Accepted
- Date: 2026-09-04

## Context

The exact historical Identity source Apply added 279 canonical
`point_in_time_identity` source-observation partitions. Current-context report
1.3 includes the changed whole-`/data` inventory but its family projection
describes only resolved Identity snapshots. A new task can therefore see the
files only indirectly and may incorrectly repeat the completed source-custody
work.

The report must remain fast and read-only. Routine context recovery must not
parse 3,399,877 Parquet rows, and partition presence must not be promoted to
Historical Coverage or research readiness.

## Decision

Advance the authoritative report to `tip-current-context-report/1.4` and add a
separate `point_in_time_identity_source_observation` projection. It preserves
the governed `data_family_id=point_in_time_identity` and
`record_layer=source_observation` while distinguishing that layer from the
resolved snapshot entry.

Routine reporting validates the exact non-symlink dataset path, expected
provider/session partition shape, exact two-file partition custody, canonical
modes, unique ordered dates, manifest count, Parquet count, and alignment to
the canonical EOD session index. It exposes first/last date, covered count,
all missing EOD dates, any source-only dates, and an explicit inventory-level
validation scope.

Even a complete partition inventory remains
`canonical_partitions_observed_not_coverage_validated`. Missing source dates
emit a distinct incompleteness blocker; complete physical custody would still
emit a not-formally-coverage-validated blocker. Existing research readiness,
development-review, and performance-claim gates remain false.

## Consequences

- Cross-device and new-task recovery can identify the 279 durable source
  partitions and exact 24-session gap without relying on prose or `/tmp`.
- Malformed dates, symlinks, wrong modes, and missing/extra partition files
  fail closed. Source dates outside the canonical EOD index are exposed
  explicitly and block a complete-alignment interpretation.
- Routine context latency remains bounded because the report does not parse
  all historical Parquet rows. The Apply audit and explicit canonical reader
  remain the semantic proof.
- No data write, provider request, source acquisition, Membership, Historical
  Coverage, research run, scheduler change, publication, or deployment is
  authorized.

## Alternatives Considered

### Fold source custody into the existing resolved Identity row

Rejected because source observations and resolved canonical snapshots are
different record layers with different coverage and knowledge-time meaning.

### Formally parse all 279 Parquet partitions on every context report

Rejected because the two-to-three-minute full semantic pass is appropriate
for Apply and explicit audit, not routine recovery.

### Infer completion from the whole-`/data` fingerprint

Rejected because an aggregate fingerprint does not explain family coverage or
the exact missing sessions.
