# ADR 0153: Publish Membership Physical First and Marker Last

## Status

Accepted

## Date

2026-09-07

## Context

ADR 0152 defined a no-write plan and a separate logical completion marker for
signal-eligible Universe Membership. The plan still needed an executor that
could tolerate interruption without allowing raw physical bytes to become
canonical, plus a reader that would enforce the same boundary for every
consumer.

## Decision

Implement one exact-plan-bound, network-prohibited Apply and one canonical
reader.

Apply requires the plan file SHA-256, plan logical fingerprint, expected
pre-state inventory fingerprint, and approved Dell data root. It takes the
shared canonical-data lock and repeats the complete plan read after acquiring
the lock. It then:

1. copies the two exact Membership artifacts into an fsynced sibling staging
   directory and atomically renames the physical partition;
2. verifies the physical artifact set, sizes, modes, hashes, and semantic
   Parquet read before exposing a completion marker;
3. writes the one-file publication marker through a separate fsynced staging
   directory and atomically renames it last;
4. performs a canonical read that reconciles marker, physical manifest,
   Parquet rows, hashes, timing assessment, and canonical Identity source;
5. proves that inventory outside the two planned targets did not change.

The canonical reader refuses a physical-only partition. It recognizes
completion only when the marker is present, canonical, signal-eligible, and
transitively bound to the exact physical Membership and Identity source
custody.

`verify_then_complete` is a distinct recovery mode. It may reuse an exact
completed physical partition and add the absent final marker, or prove an
already completed pair without rewriting it. It rejects ordinary replay,
recovery with no completed target, marker-before-physical state, corrupt or
partial targets, unrelated inventory drift, and deterministic staging residue.
It never deletes ambiguous residue.

## Consequences

- Raw Membership directory presence can no longer be mistaken for canonical
  completion by the governed reader.
- An interruption after physical rename and before marker rename is safely
  recoverable under the same approved plan.
- An interruption while a staging directory exists remains fail-closed and
  requires explicit operator diagnosis; recovery does not silently delete it.
- Publication authorizes neither Historical Coverage nor performance claims.
- The separately reviewed 2026-09-04 plan was applied exactly: 3 files /
  463,460 bytes and 19,964 formally reread decisions. The post-state inventory
  fingerprint is
  `d7ddbace6669c1870e86d79fd48aa86ff99d276699d23b84939983f950b236b4`.
- A separate `verify_then_complete` postflight reused both targets and wrote
  zero files/bytes. Publication fingerprint is
  `3f71cd40edd2ed6d7e215a95e0cb89c08c7e96dcb9a8fb543a4de34286c15518`.
- Current-context report 1.6 consumes the governed reader rather than raw
  directory presence and therefore reports the exact 1/304 canonical state.

## Alternatives Considered

### One directory containing physical bytes and the logical marker

Rejected because a single directory rename would require rewriting or
repackaging the already evidence-bound physical partition and would blur
physical custody with logical eligibility.

### Treat any valid physical partition as complete

Rejected because it loses the next-open timing gate and permits partial
publication to leak into research consumers.

### Automatically remove any recovery residue

Rejected because residue can be ambiguous after interruption. Fail-closed
operator diagnosis preserves evidence and avoids destructive guesses.
