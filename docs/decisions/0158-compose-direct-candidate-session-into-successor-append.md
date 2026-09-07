# ADR 0158: Compose the Direct Candidate Session into a Successor Append

## Status

Accepted

## Date

2026-09-07

## Context

ADR 0156 proved an exact one-session Candidate append by reparsing the complete
cumulative V1 audit. Its two correctness passes each took about 8.5 minutes and
peaked near 13.1 GiB. ADR 0157 then emitted the current session directly from
the daily calculation objects in 38.907 seconds, but deliberately stopped
before append authority because the intended V1 audit was not yet physically
complete.

The direct payload and the cold ADR 0156 payload have the same eight business
projections. They cannot be called the same byte contract. V1 stores raw-fact
ordinals against its globally canonical cumulative list; a self-contained
immutable session instead stores session-local canonical ordinals. Deriving
the former requires the cumulative history work this design is intended to
avoid.

## Decision

Introduce `opportunity-candidate-segmented-append/1.1` as a versioned,
non-authoritative successor append composed from:

- the exact formally read ADR 0155 parent chain;
- the exact ADR 0157 direct session candidate;
- the physically completed intended incremental Candidate Audit V1; and
- that V1 audit's manifest-bound incremental validation ledger.

The composer must verify all immutable V1 artifact custody and hashes without
reparsing cumulative business rows. It then verifies that the completed V1
logical identity, as-of session, Universe order, calculation contract,
immediate prior audit, and validation fingerprint are exactly those already
bound by the direct candidate and parent.

The append copies the already validated direct payload bytes into a new
owner-only `/tmp` stage, requires identical size and SHA-256, constructs the
new chain node, writes the completion manifest, verifies the exact file set,
ownership, modes, sizes, and hashes, and atomically delivers the stage. An
existing output or completed interrupted stage is independently read and must
match all requested inputs before reuse or recovery.

Version 1.1 records:

- `prefix_binding=exact_parent_versioned_chain`, rather than regenerating a
  redundant cumulative-prefix projection fingerprint;
- `raw_fact_order=session_local_canonical`;
- the exact direct-candidate manifest and payload identities;
- verified physical completion and incremental-validation binding for the
  intended V1 source; and
- all eight current-session projection fingerprints.

The generic append reader accepts both 1.0 and 1.1, applies the appropriate
session contract, recomputes all current projection fingerprints, and checks
the forward-chain node. The two versions intentionally have different final
chain fingerprints because their segment contracts and raw-fact ordinal
semantics differ. Neither may be relabeled as the other.

## Consequences

- Fixture tests prove that composition does not call the cumulative V1
  semantic reader, all eight current fields exactly equal the ADR 0156 cold
  append, wrong completed sources fail closed, and idempotent and interrupted-
  delivery recovery paths preserve the exact result.
- On the real 2026-09-03 parent and 2026-09-04 session, composition completed
  in 36.70 seconds with 1,203,960 KiB peak RSS. It copied the exact
  86,608,577-byte ADR 0157 payload with logical fingerprint
  `a62455909c0436ad07e4024c329c961dfec8e8cd85b9aa507f0b1144037cb515`
  and physical SHA-256
  `9c9af6fa03357f6135e83568d48c5c6f4355df7e9a903d5db8547e2a9642f967`.
- The 3,276-byte append manifest has logical fingerprint
  `e7b0efce9a0e24d4ac242d10ec6c944c793f621c5bf568177b49d8b545bce7d6`,
  physical SHA-256
  `57895b6fd22fbe9f44ce2041c05c7e4c11a0a76f72adec5f8add4227ad90fbf8`,
  and final chain fingerprint
  `b0a43cd1affa3241562f424b67b32bb306ebc1be8c0213636ece27dfedf79ea1`.
- A separate full read of the composed append took 40.36 seconds and peaked at
  2,078,136 KiB. A two-package cold comparison took 80.82 seconds, found all
  eight business fields and their fingerprints exact, and confirmed byte-
  identical direct/composed payloads and the exact same prior chain.
- Composition is now proven for one generation only. Repeated append,
  generalized parent reading, downstream compatibility, retention, periodic
  cold-audit policy, and cutover remain open.
- Candidate V1, executor, coordinator, scheduler, publication, MI, Snapshot,
  `/data`, OCI, and Production remain unchanged. The package grants no
  publication or canonical-write authority.

## Alternatives Considered

### Preserve the 1.0 chain fingerprint by rebuilding global raw ordinals

Rejected because it requires sorting or parsing the cumulative V1 raw-fact
history and would falsely preserve the performance problem behind a nominally
fast composer.

### Call session-local and global ordinal payloads equivalent

Rejected. Their business projections match, but their evidence contracts and
physical identities are intentionally different.

### Trust the prepared V1 manifest without physical completion

Rejected. The composer verifies every completed artifact's custody and hash
and the exact incremental validation ledger before creating a successor.
