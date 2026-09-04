# ADR 0142: Plan Explicit Append-Only Identity Source Custody

## Status

Accepted

## Date

2026-09-04

## Context

The first historical Identity source transition published 279 immutable
partitions from one complete candidate and profile map. After the 24 missing
packages are recovered and fingerprint-bound, their normalized candidates
must be appended without rebuilding, copying, or treating the existing 279
canonical partitions as mutable plan targets.

The original planner intentionally required one candidate for every profile-
map binding and every target to be absent. That is correct for a first
publication but cannot express an append after part of the governed session
set is already canonical.

## Decision

Keep contract `historical-identity-source-apply-plan/1.0` and add an optional
explicit session selection to plan construction:

- absence of a selection preserves the original complete-candidate behavior;
- an explicit selection must be nonempty, unique, ascending, and entirely
  present in the formally validated profile map;
- only selected candidate partitions are formally read, inventoried, mapped,
  aggregated, and required absent in canonical storage;
- every selected partition must still bind the full profile-map fingerprint,
  its exact session binding, source package, accepted Identity families, and
  immutable candidate bytes;
- the fresh whole-`/data` inventory still includes all previously canonical
  partitions and remains the Apply compare-and-swap pre-state; and
- the produced plan still has no self-authorization and uses the unchanged
  atomic Apply/recovery executor.

The selection is a planning scope, not a weaker validation mode. Unselected
candidate files do not enter the plan inventory and unselected canonical
partitions are never Apply targets.

## Consequences

- The exact 24 recovered source sessions can be added without rebuilding or
  replaying the existing 279 canonical partitions.
- Existing source custody remains immutable and contributes to whole-`/data`
  drift detection.
- The original all-bindings planner behavior and plan contract remain
  backward compatible.
- Historical Coverage, membership, research, publication, deployment, and
  scheduling authority remain unchanged.

## Alternatives Considered

### Rebuild and republish all 303 partitions

Rejected because existing canonical partitions are immutable and must not be
treated as replaceable merely because the profile map gained new bindings.

### Create a second dataset version for only 24 sessions

Rejected because the normalized source schema and meaning are unchanged; this
is an append to the same family, not a semantic migration.

### Construct a synthetic 24-session profile map

Rejected because it would detach the new candidates from the complete
fingerprint-proven session routing and create a misleading partial map.
