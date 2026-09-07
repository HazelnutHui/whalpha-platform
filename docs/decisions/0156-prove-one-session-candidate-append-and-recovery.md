# ADR 0156: Prove One-Session Candidate Append and Recovery

## Status

Accepted

## Date

2026-09-07

## Context

ADR 0130 proved lossless immutable Candidate session segments, and ADR 0155
gave those segments a forward identity distinct from V1's cumulative history
fingerprint. The next unresolved question was whether one later session could
extend that chain without rewriting the parent segments, while still proving
that the historical prefix and new session match a complete V1 audit.

V1 raw facts use a whole-history global order. Adding a session can move prior
records' global ordinals even when their values and within-session order are
unchanged. An append must therefore compare explicit per-session semantic
projections and must not claim that its session-major raw-fact identity is the
V1 global-order fingerprint.

## Decision

Introduce two non-authoritative offline contracts:

- `opportunity-candidate-segmented-append/1.0` for one completed append
  package; and
- `opportunity-candidate-segmented-append-session/1.0` for its only new
  session segment.

An append package must:

- extend the exact parent session ledger by one ordered session;
- formally validate the parent segmented custody and its ADR 0155 chain tip;
- formally read the complete comparison V1 audit;
- require identical Candidate/state calculation, parameter, Universe order,
  and every prior per-session source-panel, batch, state, transition, raw-fact,
  and normalization projection;
- require the V1 incremental ledger to bind the exact parent audit when such a
  ledger is present;
- bind the new segment's logical fingerprint, physical SHA-256, record/scope
  counts, current Oracle, risks, source audit, prior chain tip, and new chain
  tip; and
- write only a new owner-only direct child of `/tmp`, with the completion
  manifest written last in a deterministic staging directory and the complete
  directory atomically renamed into place.

The parent shadow is never modified. If final delivery is interrupted after a
complete stage exists, a repeated request must formally verify the staged
parent/source identity and complete the rename. Incomplete or ambiguous stages
are preserved and rejected rather than deleted automatically.

## Consequences

- Fixture tests prove exact one-session extension, unchanged parent bytes,
  idempotent reuse, non-successor rejection, tamper rejection, and
  verify-then-complete recovery after simulated delivery interruption.
- The real 2026-09-03 parent extended through 2026-09-04 as 10 + 1 sessions.
  The new package contains an 86,610,428-byte segment and a 3,248-byte
  manifest. Its logical fingerprint is
  `dd3563f48370c81242f87f376f7156ed67a06e16a6dafdd82ffe786902cae630`;
  its final chain fingerprint is
  `f68d55c17160ab4db98d26f4da0a0742568143e79e2910c804d9c04e306a793d`.
- The exact parent V1 identity and source 9/4 V1 identity are bound. The parent
  manifest SHA-256 remains
  `798fd208401fde9d85a5914dcb1dbe61c7cf491941b4add71cc5efbbcc7eb89f`.
  No staging residue remains.
- Initial construction completed in 8 minutes 37 seconds with 13,073,092 KiB
  peak RSS. An independent cold equivalence completed in 8 minutes 30 seconds
  with 13,073,164 KiB peak RSS, zero mismatches, and logical fingerprint
  `0416ec637c00812e5d99d29e5e2745277d32bb3460db2c035bed836b5d64a202`.
- These times are not a hot-append performance result: both proofs deliberately
  reread the complete cumulative V1 audit. The next implementation must emit
  the daily segment directly from already calculated current-session objects
  and reserve the heavy full-history comparison for periodic/code-change cold
  audits.
- No Candidate formula, parameter, score, rank, state, MI, Snapshot,
  publication, scheduler, `/data`, OCI, or Production behavior changed.

## Alternatives Considered

### Rewrite old segment raw-fact ordinals for each new session

Rejected because it would violate immutable historical segments and recreate
the linear rewrite that segmentation is intended to eliminate.

### Treat V1 global raw-fact ordering as irrelevant

Rejected because changing an identity comparison without naming the changed
canonical order would weaken audit semantics. The append contract explicitly
uses per-session projections instead.

### Cut over the daily Candidate path after this proof

Rejected. Direct hot-segment production, multi-append recovery, downstream
compatibility, retention, and periodic cold-audit scheduling remain unproven.
