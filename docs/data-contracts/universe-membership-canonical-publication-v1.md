# Universe Membership Canonical Publication V1

## Status

Apply plan, physical-first/marker-last executor, recovery, and canonical reader
are implemented. The real 2026-09-04 partition and marker are published and
zero-write postflight verified. This is one signal-eligible session, not
Historical Coverage or research-performance authorization.

## Completion Rule

Canonical Membership is complete only when both exist and formally reconcile:

1. the immutable two-file Membership physical partition;
2. the single-file canonical publication marker written last.

The raw Membership directory is not a completion claim by itself.

## Publication Marker

The marker binds:

- session and methodology;
- relative Membership partition path;
- record count;
- Membership logical fingerprint;
- physical manifest and Parquet SHA-256;
- the complete signal-eligible Knowledge Time V1 assessment;
- creation time and a self-validating logical fingerprint.

It explicitly leaves Historical Coverage and research-performance authority
false.

## Apply Plan

The owner-only plan binds the exact candidate and target files, current `/data`
inventory, target absence, prospective publication-marker bytes, total file
and byte change, and the complete timing assessment. It rejects
`outcome_reconciliation_only` input before any plan file is created.

The plan is no-write with respect to canonical data. Apply requires its own
exact plan-file hash, logical fingerprint, current-state fingerprint, shared
lock, network prohibition, recoverable physical-first/marker-last ordering,
full formal reread, and post-state inventory proof.

## Administrator Entry Point

`scripts/admin/plan-universe-membership-apply.sh`

`scripts/admin/apply-universe-membership-plan.sh`
