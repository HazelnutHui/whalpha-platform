# Opportunity Candidate Segmented Chain-Head Apply V1

## Purpose and authority

This boundary executes and reviews one ADR 0161 publication plan only in a
disconnected `/tmp` simulation. It introduces:

- `opportunity-candidate-segmented-chain-head-recovery-review/1.0`; and
- `opportunity-candidate-segmented-chain-head-simulated-apply-result/1.0`.

It has no Production Apply authority. The implementation explicitly refuses
`/data/trading-intelligence-platform`, makes no external request, and is not a
CLI, coordinator, scheduler, serving, rollback, or pruning boundary.

## Exact execution binding

The caller must provide all of the following independently:

- immutable plan path and physical SHA-256;
- plan logical fingerprint;
- source chain-head logical fingerprint;
- expected bounded-family inventory fingerprint;
- expected current-pointer-state fingerprint; and
- the exact owner-controlled `0700` simulated root under `/tmp`.

The plan and source are physically and semantically reread. The derived target,
pointer bytes, pointer SHA-256, source descriptor, authority flags, and root
must exactly reproduce the plan before a write is possible.

## Recovery review

The read-only review reports exactly one of three states:

| State | Required evidence |
| --- | --- |
| `not_started` | Target release absent; original target-absence and family/pointer plan reread passes. |
| `release_published_pointer_pending` | Target release is exact; after excluding only that verified target, family and pointer equal the planned pre-state. |
| `complete` | Full family reader validates every retained release and the current pointer exactly equals the planned pointer. |

The review always reports zero filesystem, canonical, Production, and external
effects. Staging residue, malformed or corrupt custody, unexpected files,
conflicting releases/pointers, source drift, or CAS drift raises an error
instead of assigning a recoverable state.

## Apply ordering and durability

Execution repeats recovery review under a root-specific `fcntl` lock. It then
uses this order:

1. build an owner-only same-parent release staging directory;
2. copy and fsync the exact source manifest as `0400`;
3. verify, atomically rename, and fsync the immutable release parent;
4. repeat the outside-target family and pointer CAS;
5. write and verify the exact planned pointer as an owner-read-only staging
   file; and
6. atomically replace `current.json`, fsync its parent, and formally reread the
   complete state.

The execution phase prohibits socket creation. Immutable release replacement,
automatic cleanup, deletion, pruning, and rollback are forbidden.

## Idempotency and recovery command

- Normal Apply accepts only `not_started`.
- Normal Apply refuses release-only partial state and complete state.
- `verify_then_complete=true` accepts only an exact release-only state or an
  already complete state.
- Release-only recovery reuses the release and writes the pointer only.
- Completed recovery reuses both objects and writes zero files/bytes.
- Recovery never restarts a not-started Apply.

## Result semantics

The result includes plan and expected-state identities, post-family and
post-pointer fingerprints, active head identity, release/pointer
published-versus-reused flags, simulated file/byte counts, and explicit zeros
for external requests, canonical/Production writes, overwrite, deletion, and
rollback.

`simulated_write_count` and `simulated_written_bytes` describe only the
immutable manifest and pointer payload. They are not canonical write or
Production publication metrics.
