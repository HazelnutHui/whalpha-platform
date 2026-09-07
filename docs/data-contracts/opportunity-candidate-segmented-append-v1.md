# Opportunity Candidate Segmented Append V1

## Status and purpose

`opportunity-candidate-segmented-append/1.0` and
`opportunity-candidate-segmented-append/1.1` are offline Dell-local proofs that
one Candidate session can extend an exact ADR 0155 parent chain without
rewriting its segments. Neither is an active Candidate audit, publication,
Snapshot source, research result, or Production input.

## Required inputs

- one formally valid `opportunity-candidate-segmented-shadow/1.0` parent;
- its distinct `opportunity-candidate-segmented-chain-identity/1.0`; and
- one formally valid Candidate Audit V1 whose ordered session ledger is the
  parent ledger plus exactly one session.

Version 1.1 additionally requires the exact
`opportunity-candidate-segmented-session-candidate/1.0` emitted from the daily
objects and a physically completed incremental V1 audit whose validation
ledger binds that candidate and the parent.

For a later generation, the parent is supplied as one base shadow plus an
explicitly ordered sequence of already completed append packages. Every append
is validated against the immediately preceding manifest and chain tip before
the new direct candidate or successor may be accepted. Absolute paths are not
part of logical identity.

Candidate/state calculation versions, parameter identities, and Universe
order must match. When the source is V1 incremental, its validation ledger
must bind the exact parent V1 audit and session.

## Prefix and current-session equivalence

The writer compares the parent and later V1 audit by exact per-session
projections for source panels, Candidate batches, states, transitions, raw
facts, and normalization records. This is explicit because V1's global
raw-fact ordering can change old global ordinals after a later session is
added. The new contract never relabels its session-major projection as the V1
global-order fingerprint.

The only new segment contains the new source panel, two Universe batches,
current states and transitions, raw facts with their source V1 ordinals,
normalization records, six risk results, and current Oracle evidence. Its
contract is `opportunity-candidate-segmented-append-session/1.0`.

Version 1.1 instead copies the exact
`opportunity-candidate-segmented-session/1.0` bytes. It records
`session_local_canonical` raw-fact ordinals and binds its prefix through the
exact parent versioned chain. It does not recreate V1's cumulative global
ordinal positions or a redundant whole-prefix projection. All eight current
business projections must nevertheless match the 1.0 cold reference exactly.

## Identity and custody

The completion manifest binds:

- parent manifest SHA/logical identity, session count, calculation-contract
  fingerprint, and chain tip;
- source V1 manifest SHA/logical identity and incremental-parent status;
- new segment logical fingerprint, physical SHA-256, byte and record counts;
- prefix and current projection fingerprints; and
- the chain node extending the exact prior tip.

Version 1.1 also binds the direct-candidate manifest/payload identity, exact
physical completion of the intended V1 audit, and the manifest-committed
incremental validation record. Its final chain is intentionally distinct from
1.0 because segment contract and ordinal semantics are part of chain identity.
`parent.shadow_contract_version` identifies the base shadow contract across the
lineage; the adjacent parent manifest SHA/logical fingerprint always identifies
the immediate parent package.

The output is a new owner-only direct child of `/tmp`; directory mode is
`0700` and completed files are `0400`. A deterministic completed staging
directory can be formally verified and atomically delivered after an
interruption. Partial or ambiguous evidence fails closed and is not deleted.

## Explicit non-authority

The package performs no network or canonical write and grants no publication,
scheduler, research-performance, or Production authority. Candidate V1 remains
authoritative. ADR 0158 composes the ADR 0157 sidecar only after verifying its
exact V1 physical completion. Governed chain-head custody, retention,
downstream compatibility, periodic audit, and cutover require later decisions.

## Real Dell proof

The 2026-09-03 ten-session parent extended through 2026-09-04 with one
86,610,428-byte segment and a 3,248-byte manifest. The append logical
fingerprint is
`dd3563f48370c81242f87f376f7156ed67a06e16a6dafdd82ffe786902cae630`,
and the new chain tip is
`f68d55c17160ab4db98d26f4da0a0742568143e79e2910c804d9c04e306a793d`.
Independent cold equivalence found zero mismatches and produced fingerprint
`0416ec637c00812e5d99d29e5e2745277d32bb3460db2c035bed836b5d64a202`.

The two heavy passes took 8 minutes 37 seconds and 8 minutes 30 seconds with
about 13.1 GiB peak RSS because they intentionally reread the cumulative V1
audit. They prove correctness rather than hot-path performance. ADR 0157 later
reduced direct session emission to 38.907 seconds.

ADR 0158 composed those exact direct bytes into version 1.1 in 36.70 seconds
with 1,203,960 KiB peak RSS. The output payload is 86,608,577 bytes; its logical
fingerprint is
`a62455909c0436ad07e4024c329c961dfec8e8cd85b9aa507f0b1144037cb515`
and SHA-256 is
`9c9af6fa03357f6135e83568d48c5c6f4355df7e9a903d5db8547e2a9642f967`.
Its manifest logical fingerprint is
`e7b0efce9a0e24d4ac242d10ec6c944c793f621c5bf568177b49d8b545bce7d6`
and the new chain tip is
`b0a43cd1affa3241562f424b67b32bb306ebc1be8c0213636ece27dfedf79ea1`.
An independent read took 40.36 seconds; a two-package comparison found all
eight current fields exact and confirmed the direct/composed payload bytes are
identical.

ADR 0159 separately proves two ordered append generations with fixture data.
The general cold reader validates the base and every supplied append, so this
is a correctness boundary rather than a constant-time hot-path claim. A
governed exact chain-head/checkpoint and periodic full-lineage policy remain
required before cutover.
