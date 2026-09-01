# ADR 0117: Reuse finalized Candidate evidence and parse Snapshots once

## Status

Accepted.

## Date

2026-09-01.

## Context

The daily Candidate append re-opened the immediately prior completed audit by
fully reconstructing canonical JSON and re-deriving every historical logical
fingerprint. The same audit had already passed that complete reconstruction
before immutable finalization. On the real 2026-08-31 audit, this repeated
read/validation stage took 133.871 seconds.

Dashboard Snapshot construction also validated each newly written JSON file
before immediately validating the complete staging directory. Within each
complete directory validation, large Candidate summary/detail artifacts were
then decoded and contract-validated a second time for cross-file checks.

These repetitions did not add independent evidence after exact immutable-byte
custody had already been re-established.

## Decision

Add a dedicated prior-audit projection for the daily Candidate append. It must
first validate the completed directory, manifest, exact file set, owner/mode,
byte counts and SHA-256 of every artifact. It then parses those exact verified
bytes once and preserves typed contracts, embedded-to-manifest fingerprint
bindings, record-fingerprint ledgers, session and Universe bindings, Oracle
gates, and finalized incremental lineage checks.

Do not use this projection to create, finalize, periodically compare, or
approve an audit. Full canonical reconstruction and historical fingerprint
derivation remain mandatory at audit finalization and at periodic/code-change
validation tiers.

For Dashboard Snapshots, validate the complete staging directory before
completion and the completed directory after atomic rename, but remove the
redundant per-file validation immediately after writing. A complete directory
validation must decode and contract-validate each file once, then reuse that
validated value for cross-file binding checks. File-set and SHA-256 checks are
unchanged.

## Consequences

- The real 2026-08-31 prior-Candidate read fell from 133.871 seconds to 28.18
  seconds, about a 79% reduction.
- The optimized real read preserved session 2026-08-31, 14 batches, 24,843
  state rows, 12,793 raw rows, 24,795 normalization rows, and audit logical
  fingerprint
  `8f68aa780a5a066d070238584a2b49e8f0bc1a637f3a79f517d9bed96014e3fe`.
- A complete read-only validation of the active 32-shard Snapshot took 5.40
  seconds after the single-parse change.
- No formula, parameter, rank, state, Universe, publication, Snapshot contract,
  `/data` content, scheduler, or OCI release changes.
- If immutable-byte custody or any retained binding differs, the daily append
  still fails closed; a cold/full validation remains the recovery boundary.
