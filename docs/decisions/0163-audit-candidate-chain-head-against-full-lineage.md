# ADR 0163: Audit Candidate Chain Head Against the Full Lineage

## Status

Accepted

## Date

2026-09-08

## Context

ADRs 0160–0162 provide a small expected-identity chain head, a governed
immutable-release/current-pointer plan, and a disconnected Apply/recovery
proof. Those boundaries make a daily fast path possible, but a checkpoint
cannot independently prove its omitted ancestry. Replaying every historical
segment every day would restore the linear cost that the checkpoint removes.

The missing boundary is a periodic cold audit that starts from the retained
base plus every ordered append and proves that they reconstruct the exact
currently selected head. It must also prevent a current-pointer change during
the cold read from producing a mixed-state success.

## Decision

Add a zero-write, network-prohibited, `/tmp`-only full-lineage audit. It requires
externally supplied expected identities for the bounded family inventory,
current-pointer state, active head logical fingerprint, and active manifest
SHA-256. The Production `/data` root is rejected before any root or plan I/O.

The audit performs this sequence:

1. fully read the bounded release family and pointer and require all four
   expected current bindings;
2. formally read the base shadow and every explicitly ordered append from the
   start of the lineage;
3. deterministically reconstruct the expected chain-head manifest in memory;
4. require exact active-parent identity, canonical manifest content, logical
   fingerprint, and physical SHA-256 equality; and
5. fully reread the family and pointer under the same expected bindings and
   require the complete before/after states to be identical.

Success returns
`opportunity-candidate-segmented-chain-head-full-lineage-audit/1.0` with
`status=exact_match`, `validation_tier=periodic`, zero mismatches, a
deterministic logical fingerprint, and explicit zero/false authority fields.
There is no success-with-warning state. Missing, reordered, corrupt, or changed
lineage/current evidence raises an error and returns no positive audit.

Adopt three distinct validation levels:

- **Daily:** expected-current/head fast read, one exact successor, pointer CAS,
  and postflight. It does not claim a full-lineage audit.
- **Periodic:** this cold audit at least once every five accepted Candidate
  append sessions or seven calendar days, whichever occurs first, and after
  any verify-then-complete recovery before a later head is accepted.
- **Code change:** the periodic audit plus the existing V1 `code_change` full
  semantic reconstruction, independent Oracle, and affected contract tests.
  This audit alone therefore reports `code_change_validation_complete=false`.

The cadence is policy only. No CLI, journal writer, coordinator, or scheduler
is added. On failure, freeze segmented advancement and retain the authoritative
V1 path; preserve evidence, do not automatically clean, repair, roll back, or
publish, and require diagnosis plus a later clean audit.

## Consequences

- The three-session fixture proves a two-append exact match, deterministic
  result fingerprint, two current-state reads, one full-lineage read, and zero
  writes. Missing generation, reordered generation, wrong expected current
  state, simulated mid-audit current change, and Production-root use fail.
- The retained real 2026-09-03 base plus 2026-09-04 composed append reconstructed
  the exact simulated active 11-session head. The run took 39.79 seconds with
  2,079,080 KiB peak RSS, produced zero filesystem output, and reported zero
  mismatches, requests, canonical writes, and Production writes.
- Real lineage fingerprint remains
  `33971a2e205afec07aeadfbdcf4d00161bb555dfbb8dc2557f1654c4d3ca55a2`;
  active logical fingerprint remains
  `653f6f3a47066094a32fbf5481e563eebb4a2c290344be7d5c6d20264c0400bc`;
  active manifest SHA-256 remains
  `47c8636305f3f89f9fa03855e705b9063763313603b95ee7dc404a720d8e4ee0`.
  The audit logical fingerprint is
  `8adc21deec2bda549f1bb142e482376d6c07183c997050fb008689affb761ca3`.
- The 39.79-second cold result is a periodic correctness cost, not a daily-path
  target or a complete daily-chain measurement.
- `/data`, authoritative V1 Candidate, formulas, parameters, ranks, states,
  publication, MI, Snapshot, bundle, OCI, executor, coordinator, scheduler, and
  Production remain unchanged. No canonical chain-head pointer exists.
- Candidate-focused coverage passed, and the complete API regression finished
  at `2136 passed, 2 warnings`; both warnings are unchanged dependency
  deprecations.
- The next gate is reviewed CLI/executor exposure and downstream compatibility;
  neither is authorized by this decision.

## Alternatives Considered

### Replay the complete lineage every day

Rejected because it defeats the bounded expected-head fast path. Daily and
periodic validation serve different risks and must stay visibly distinct.

### Trust only the active head's self-contained manifest

Rejected because a checkpoint can be internally valid while representing the
wrong or incomplete ancestry.

### Persist another independent audit database

Rejected for this phase. The existing immutable base, append, head, and pointer
contracts contain the required evidence. A future CLI may record the compact
result in the existing run-journal boundary without creating a second source
of truth.
