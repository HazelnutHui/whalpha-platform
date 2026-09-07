# Opportunity Candidate Segmented Append V1

## Status and purpose

`opportunity-candidate-segmented-append/1.0` is an offline Dell-local proof
that one Candidate session can extend an exact ADR 0155 parent chain without
rewriting its segments. It is not an active Candidate audit, publication,
Snapshot source, research result, or Production input.

## Required inputs

- one formally valid `opportunity-candidate-segmented-shadow/1.0` parent;
- its distinct `opportunity-candidate-segmented-chain-identity/1.0`; and
- one formally valid Candidate Audit V1 whose ordered session ledger is the
  parent ledger plus exactly one session.

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

## Identity and custody

The completion manifest binds:

- parent manifest SHA/logical identity, session count, calculation-contract
  fingerprint, and chain tip;
- source V1 manifest SHA/logical identity and incremental-parent status;
- new segment logical fingerprint, physical SHA-256, byte and record counts;
- prefix and current projection fingerprints; and
- the chain node extending the exact prior tip.

The output is a new owner-only direct child of `/tmp`; directory mode is
`0700` and completed files are `0400`. A deterministic completed staging
directory can be formally verified and atomically delivered after an
interruption. Partial or ambiguous evidence fails closed and is not deleted.

## Explicit non-authority

The package performs no network or canonical write and grants no publication,
scheduler, research-performance, or Production authority. Candidate V1 remains
authoritative. ADR 0157 separately proves a direct current-session candidate,
but that sidecar is not an append until a later composer verifies its exact V1
physical completion and creates this contract's successor identity. Repeated
append generations, retention, downstream compatibility, and cutover require
later decisions.

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
reduced direct session emission to 38.907 seconds without changing this append
package or granting it authority; exact composition into a successor append is
the next open boundary.
