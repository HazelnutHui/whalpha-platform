# ADR 0130: Prove segmented Candidate custody before cutover

## Status

Accepted.

## Date

2026-09-04.

## Context

Candidate Audit V1 is self-contained: every daily audit repeats all prior
source panels, score batches, state rows, transitions, raw facts, and
normalization rows. This made early audit and recovery boundaries simple, but
daily cost grows with the complete Candidate history and retaining each daily
audit grows approximately with the square of session count.

The three unchanged Dell audits through 2026-09-01, 2026-09-02, and
2026-09-03 contain 674,868,781, 758,853,957, and 842,945,142 bytes. The observed
increment is approximately 84 MB per Candidate session. A linear projection to
303 Candidate sessions is about 25.5 GB for the latest self-contained audit;
retaining every cumulative daily version would approach 3.9 TB. More
importantly, the 2026-09-03 daily path already takes 294.99 seconds and assigns
193.525 seconds to cumulative artifact construction and writing.

Changing the active audit directly would also change prior-state evidence,
logical identities, recovery, retention, publication, and periodic comparison.
A storage optimization must therefore be proven independently before it can
replace the mature V1 boundary.

## Decision

- Introduce a Dell-local, offline Candidate segmented-shadow contract. It is a
  research/architecture proof and has no Production, publication, scheduler,
  or model authority.
- Convert one fully validated V1 audit into immutable per-session segments.
  Preserve exact ordered source panels, score batches, state rows, transition
  rows, raw facts, normalization rows, current risk results, parameter
  contracts, Oracle evidence, and incremental validation evidence.
- Bind each segment by canonical logical fingerprint, byte count, and physical
  SHA-256. Bind the completed shadow manifest to the exact V1 manifest SHA,
  V1 logical fingerprint, calculation/parameter identities, ordered sessions,
  segment descriptors, and the eight schema-neutral business projection
  fingerprints used by periodic comparison.
- Require the shadow reader to validate custody, exact files, canonical bytes,
  physical and logical fingerprints, session order, typed Candidate/state/risk
  records, and lossless reconstruction of all eight V1 business projections.
- Keep Candidate Audit V1 as the only daily, planning, publication, and
  Production input. Do not add shadow creation to the normal executor yet.
- A later append design may consume only the prior current-state checkpoint and
  prior chain identity, but it requires a calculation/parameter version review,
  a multi-session real shadow proof, periodic cold equivalence, interruption
  recovery, retention/compaction rules, and explicit cutover decision.

## Consequences

- The project can test the storage shape and exact semantic reconstruction
  without weakening or replacing the existing daily chain.
- The real 2026-09-03 V1 audit converted into ten immutable segments in 548.57
  seconds with 11,008,352 KiB peak RSS. The shadow contains 840,660,184 bytes
  versus 842,945,142 bytes in V1; reducing total bytes is not the principal
  benefit. Its logical fingerprint is
  `f2f253f14deeca3ee4d8eebb60c1ee0b1edbbaab82934cadde7b35ed71e4fc8e`,
  and all eight V1 business projections reconstructed exactly.
- A bounded current-checkpoint read rehashed all 840,642,650 segment bytes but
  parsed only the latest 86,537,118-byte segment. It completed in 16.53 seconds
  with 855,712 KiB peak RSS and returned the exact two Candidate batches,
  3,549 current state rows, and six risk results. The existing V1 full semantic
  reread took 228.285 seconds and 8,737,080 KiB on the same business state.
- The first real reconstruction correctly rejected a changed ordering in raw
  facts. Preserving each raw fact's exact V1 global ordinal made the second
  proof exact; the comparison was not weakened to unordered equality.
- A one-time V1 conversion still pays the complete V1 read; it is migration
  evidence, not the final fast append path.
- Per-session segments eliminate repeated historical bytes in the shadow store
  and make a later O(current-session) append technically possible.
- Existing Candidate values, scores, ranks, state transitions, publication,
  Snapshot, and OCI output remain unchanged.
- No `/data` write is authorized. Real proofs must use new owner-controlled
  temporary output and remain socket-free.

## Alternatives Considered

### Continue optimizing the monolithic V1 writer

Rejected as the long-term answer. It can reduce constants but cannot remove
the linear daily rewrite and quadratic retained-history shape.

### Replace V1 immediately

Rejected. A direct cutover would combine storage, logical-identity,
calculation-input, recovery, and publication changes without independent
evidence.

### Keep only the latest monolithic audit

Rejected. It limits retained storage but not daily 25-GB-scale rewrite/read
cost, and it weakens historical audit and recovery availability.

### Use a mutable database table without immutable segments

Rejected. Mutable rows alone do not preserve the current content-addressed,
point-in-time, fail-closed audit boundary.
