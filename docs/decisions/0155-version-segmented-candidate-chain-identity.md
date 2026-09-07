# ADR 0155: Version the Segmented Candidate Chain Identity

## Status

Accepted

## Date

2026-09-07

## Context

ADR 0130 proved that a completed Candidate Audit V1 can be reconstructed
losslessly as immutable per-session segments. Its bounded current reader also
reproduces every numerical and state-support row required for the next daily
calculation. It cannot, however, recreate V1's cumulative
`state_history_fingerprint` from only the latest checkpoint because that
fingerprint canonically hashes every historical state row.

Reusing a checkpoint-derived value in the V1 field would falsely claim the old
whole-history evidence identity. Continuing to calculate the V1 value would
retain the linear historical reread that segmentation is intended to remove.
A distinct, explicit identity is therefore required before append or cutover
can be evaluated.

## Decision

Introduce `opportunity-candidate-segmented-chain-identity/1.0` as a
non-authoritative identity proof with these rules:

- hash one ordered node per immutable Candidate session;
- bind every node to its ordinal, session, prior node fingerprint, exact
  segment logical fingerprint and physical SHA-256, record/scope counts,
  source Candidate audit identity, and the frozen Candidate/state calculation,
  parameter, and Universe contract fingerprint;
- use the final node fingerprint as the forward chain identity and separately
  fingerprint the complete assessment record;
- never place the chain identity into the V1
  `state_history_fingerprint` field or claim that the two identities are
  equivalent; and
- retain zero network, `/data`, scheduler, publication, Snapshot, or
  Production authority.

The chain identity is calculated only after the existing bounded reader has
validated exact custody and the current typed checkpoint. It is an input to
the next append/recovery proof, not a Candidate formula, score, rank, state,
or active contract change.

## Consequences

- A future append can bind the new immutable session to the prior chain tip
  without relabeling checkpoint evidence as V1 whole-history evidence.
- Candidate formulas and parameters remain unchanged. A later cutover still
  requires an explicit calculation/contract compatibility decision because
  evidence identity is part of the existing batch lineage.
- The real ten-session 2026-09-03 shadow produced source-contract fingerprint
  `903eb2c7bb16a673e6313825a5f978ca4176081470c789f0ed749312affcce37`,
  final chain fingerprint
  `bababd41348f3ab0a15f6ce7af5e5868fd3ef32a3c91734d19e142be8f1518e0`,
  and assessment logical fingerprint
  `5b495eb37a0dca9dbaf17c037218122ce62276cda8e43793f0f240bcb75e19ab`.
  The read completed in 16.4 seconds with zero external requests, canonical
  writes, or publication authority.
- Append construction, crash recovery, periodic cold equivalence, retention,
  downstream compatibility, and cutover remain unproven.

## Alternatives Considered

### Reuse V1's state-history field with a new value

Rejected because consumers could not distinguish a checkpoint chain from the
canonical hash of all historical V1 rows.

### Keep recomputing the cumulative V1 history fingerprint

Rejected as the segmented append identity because it preserves the linear
historical dependency. It remains available through periodic V1 cold
equivalence while V1 is authoritative.

### Bind only the prior chain tip and new segment hash

Rejected because calculation, parameter, Universe, provenance, and segment
scope changes must also alter the chain identity or fail validation.
