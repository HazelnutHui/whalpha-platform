# ADR 0161: Plan Segmented Candidate Chain-Head Publication

## Status

Accepted

## Date

2026-09-08

## Context

ADR 0160 reduced the exact expected-identity chain-head read to 1.08 seconds,
but the expected fingerprint still had no governed home. Trusting whichever
`/tmp` head happens to be newest would make the fast path self-selecting and
would lose concurrency, recovery, and rollback evidence.

Reusing the whole `/data` inventory fingerprint for a roughly 5 KB checkpoint
would be correct but unnecessarily broad. This family has a small, closed file
set that can carry its own exact state fingerprint while remaining inside the
same canonical root and source-of-truth rules.

## Decision

Add a no-write publication-plan boundary for a content-addressed immutable
chain-head release and one mutable `current.json` pointer.

The plan formally rereads the source under its externally supplied expected
logical fingerprint. It then binds:

- the exact source manifest path, byte count, physical/logical identity, base,
  Universe, source audit, lineage tip, session counts, and chain tip;
- one absent immutable target named by the chain-head logical fingerprint;
- the complete bounded family inventory and exact current-pointer state;
- deterministic prospective pointer bytes and SHA-256;
- immutable-release-first and pointer-last ordering;
- explicit recovery, rollback, retention, and zero-authority policies.

The family state reader rejects symlinks, special files, writable-by-group or
other directories, non-`0400` files, malformed paths, incomplete releases,
unreferenced pointer state, and unexpected file names. It hashes all accepted
family entries, but does not scan unrelated `/data` families.

A first publication has no rollback. When a current pointer exists, the new
head must be its exact one-session/one-append successor. The prospective
pointer preserves the old active reference as rollback and binds the prior
pointer-state fingerprint. All immutable releases are retained because their
bounded size makes pruning unnecessary and their evidence value is higher than
their storage cost. Automatic rollback and pruning remain prohibited.

No Apply, recovery mutation, rollback mutation, CLI, executor, coordinator,
scheduler, or downstream consumer is added by this decision.

## Consequences

- The three-session fixture now exercises bootstrap and successor plans over a
  simulated owner-only canonical root. The second plan preserves the first
  active reference as rollback.
- A non-successor, target collision, bounded-family drift, pointer CAS change,
  unsafe custody, and incorrect expected identity fail before any canonical
  write. Formal reread reproduces the complete plan exactly.
- The real 2026-09-04 11-session head produced a disconnected bootstrap plan
  at `/tmp/whalpha-adr161-candidate-chain-head-publication.plan.json`. It
  proposes a 4,962-byte immutable release and 1,712-byte pointer.
- The real plan SHA-256 is
  `d4785ff7526f65c4b91bc96d2e217f6b11ec21d4c6b86cbf99de4acb27f536c2`;
  its logical fingerprint is
  `fc155109b92a5b5e00f54ae9e2121f0330639866af3c26753534488d94c9797c`;
  and its planned-pointer fingerprint is
  `ad685e43eb5d12a07def67be53cc48497d6246e80fcdc8a6eba700f36dccc0db`.
- The real proof used only the retained `/tmp` Candidate evidence and a new
  empty `/tmp` simulation root. It made zero external requests and zero
  canonical or Production writes; `/data`, V1 Candidate authority, analytics,
  publication, Snapshot, bundle, OCI, scheduler, and formulas are unchanged.
- ADR 0162 subsequently implements and proves the exact-plan Apply/recovery
  mechanics only in a disconnected `/tmp` simulation. Periodic cold-lineage
  verification still remains required before daily CLI/executor integration or
  cutover.
- Candidate-focused coverage passed, and the complete API regression finished
  at `2135 passed, 2 warnings`. Both warnings are the unchanged Python `crypt`
  and Starlette/httpx deprecations.

## Alternatives Considered

### Store only one mutable expected-fingerprint file

Rejected because overwrite alone would not preserve the accepted prior head,
immutable evidence, or an exact rollback reference.

### Bind every plan to the whole `/data` inventory

Rejected for this small independent family because unrelated canonical writes
would create needless contention. The closed family inventory still fails on
every relevant byte, path, mode, and pointer change.

### Delete old heads after each pointer switch

Rejected. At approximately 5 KB per session, retaining immutable history is
cheap and materially improves recovery and auditability.
