# ADR 0157: Emit the Candidate Session Segment from Current Objects

## Status

Accepted

## Date

2026-09-07

## Context

ADR 0156 proved that an exact later V1 audit can extend the ADR 0155
segmented Candidate chain without rewriting its parent. That proof was not a
daily implementation: both construction and independent comparison parsed the
complete cumulative V1 audit, took about 8.5 minutes, and peaked near 13.1 GiB.

The verified-prior daily Candidate calculation already holds the current
source panel, two Candidate batches, current states and transitions, raw and
normalization records, six risk results, and zero-mismatch Oracle in memory.
Reconstructing those same current-session values from the just-written
cumulative audit is avoidable work. However, a direct segment cannot claim
that a prepared V1 audit is physically complete, cannot replace V1 authority,
and cannot reuse V1's whole-history raw-fact ordinals as though they were
stable inside an immutable session.

## Decision

Introduce the non-authoritative contracts
`opportunity-candidate-segmented-session-candidate/1.0` and
`opportunity-candidate-segmented-session/1.0`.

For an explicitly requested daily verified-prior Candidate run, the CLI may
emit one session candidate directly from already calculated current objects.
It must:

- bind the exact formally validated parent segmented manifest, source-contract
  fingerprint, session count, and chain tip;
- bind the prepared V1 manifest and the exact incremental validation record
  already committed by that manifest;
- accept only the immediate current session, fixed Universe order, typed
  Candidate/state/risk records, and zero-mismatch Oracle;
- record eight explicit current-projection fingerprints;
- use a named session-local canonical raw-fact order and never claim V1's
  whole-history global ordinal identity;
- write only a new owner-only direct child of `/tmp`, validate exact file set,
  ownership, modes, sizes, and physical SHA-256, then atomically rename the
  completed stage; and
- retain a separate full semantic reader for recovery, idempotency, periodic
  audit, and code/model-change verification.

The new-write path uses `validated_write_plus_physical_custody`. This is valid
because all business objects were typed and semantically validated before
serialization. It does not immediately parse the same 86 MB payload again.
A recovered completed stage and an existing idempotent output are still fully
read and compared because their in-memory construction state is no longer
available.

The direct candidate is deliberately emitted before deferred V1 finalization
releases the calculation objects. Its `intended_source_audit` therefore states
that physical V1 completion is required before append. A later composer must
formally verify that exact V1 completion before it can turn this candidate into
an append package. If V1 finalization fails, the sidecar remains explicitly
non-authoritative.

The two new CLI paths are paired and optional. A resumed run that finds V1
already complete may report success only when its exact direct session
candidate is also present and bound to the same V1 logical fingerprint; it
does not silently omit or recreate the sidecar without the original objects.

## Consequences

- Fixture coverage proves exact current-session equality against the ADR 0156
  cold append, parent and incremental-validation binding, idempotency, paired
  CLI arguments, and resumed V1/sidecar consistency.
- On the real 2026-09-03 parent and 2026-09-04 current objects, direct emission
  wrote an 86,608,577-byte payload in 38.907 seconds. The overall proof process,
  including artificial reconstruction of the current objects from retained
  evidence, took 76.95 seconds and peaked at 2,079,760 KiB.
- Payload logical fingerprint
  `a62455909c0436ad07e4024c329c961dfec8e8cd85b9aa507f0b1144037cb515`
  and physical SHA-256
  `9c9af6fa03357f6135e83568d48c5c6f4355df7e9a903d5db8547e2a9642f967`
  are unchanged from the earlier direct prototype. The final manifest logical
  fingerprint is
  `232ecb6de9fcf412e6c532b8bb70127eac5330e87a57f9e812137dcb4b2b0359`.
- All eight current projections matched the independently constructed ADR 0156
  cold append. A final full semantic read with the completed validation set
  took 32.831 seconds; field-by-field comparison found zero mismatches.
- This reduces direct segment emission relative to the deliberately heavy
  8-minute-37-second cold append proof, but it is not a complete daily-chain
  runtime claim. Input reads in the proof process are not part of the future
  in-memory daily writer.
- Candidate V1, the executor, coordinator, scheduler, publication, MI,
  Snapshot, `/data`, OCI, and Production remain unchanged. Repeated append,
  composition/promotion, downstream compatibility, retention, and periodic
  cold-audit policy remain required before any cutover.

## Alternatives Considered

### Parse the completed cumulative V1 audit every day

Rejected for the direct segment path because it repeats the measured linear
projection and parsing cost after the current objects have already passed all
daily gates.

### Treat the direct sidecar as a completed append

Rejected. It does not itself prove that the prepared V1 audit completed
physically, and it has not yet created the ADR 0156 successor chain node.

### Remove independent semantic rereads entirely

Rejected. Recovery, periodic comparison, code/model changes, and explicit
audits still need a temporally separate semantic reader.
