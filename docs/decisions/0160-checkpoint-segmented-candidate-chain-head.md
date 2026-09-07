# ADR 0160: Checkpoint the Segmented Candidate Chain Head

## Status

Accepted

## Date

2026-09-07

## Context

ADR 0159 proved ordered multi-generation Candidate appends, but its independent
parent reader validates the base and every append. The real base-plus-one-
append read took 39.79 seconds. Replaying every immutable segment on every
future day would reintroduce linear history cost.

Skipping ancestry without a trust anchor is not acceptable. A latest manifest
can be internally consistent while still being the wrong lineage. The daily
path needs a small, immutable identity checkpoint whose exact logical
fingerprint is already expected, plus a separate periodic cold reader that can
reconstruct the same checkpoint from the full lineage.

## Decision

Introduce the non-authoritative contracts
`opportunity-candidate-segmented-lineage-identity/1.0` and
`opportunity-candidate-segmented-chain-head/1.0`.

The lineage identity begins with the exact base shadow manifest, source
contract, Universe, session count, and base chain tip. Each append advances it
with the prior lineage fingerprint, append manifest physical/logical identity,
session ordinal, source-audit identity, and new chain tip. Filesystem paths are
never part of the identity.

One immutable chain-head package contains:

- the exact base identity;
- the current parent manifest embedded canonically with its physical SHA-256;
- current session count, append count, Universe, source-contract, source-audit,
  and chain-tip identities; and
- the cumulative lineage fingerprint and explicit zero-authority fields.

There are two construction paths which must produce the exact same bytes:

1. cold construction fully validates the base and ordered append lineage;
2. incremental advancement requires the exact expected prior head logical
   fingerprint, validates the small prior head, fully validates only the new
   append against its embedded parent identity, and advances one node.

Reading a chain head always requires an externally supplied expected logical
fingerprint. The reader verifies custody, canonical bytes, physical and logical
hashes, embedded parent-manifest identity, counts, source/Universe/chain fields,
and non-authority gates. It does not accept an unanchored head and does not read
the underlying base or historical append files.

The direct-session and ADR 0158 composer APIs may consume this expected head as
an alternative to an explicit append list. The two parent modes are mutually
exclusive. CLI, executor, coordinator, scheduler, and canonical current-state
selection do not yet expose this path.

## Consequences

- A three-session fixture proved base head → head-1 → head-2 and full-lineage
  cold head produce exactly the same manifest. It also proved direct-session
  and append outputs from head-1 are exactly equal to those from explicit
  base-plus-append-1 validation while base/history readers are disabled.
- Wrong expected fingerprints, missing or reordered lineage, mixed parent
  modes, wrong successor append, unsafe custody, and incomplete recovery fail
  closed. Completed-stage recovery and idempotent reuse preserve exact output.
- On the real 2026-09-03 base and 2026-09-04 append, cold head construction
  took 39.82 seconds / 2,078,196 KiB. The base head took 16.53 seconds /
  858,796 KiB. Advancing it with only the new append took 24.78 seconds /
  1,733,656 KiB and produced byte-identical final head content.
- The final 4,962-byte head has logical fingerprint
  `653f6f3a47066094a32fbf5481e563eebb4a2c290344be7d5c6d20264c0400bc`,
  physical SHA-256
  `47c8636305f3f89f9fa03855e705b9063763313603b95ee7dc404a720d8e4ee0`,
  and lineage fingerprint
  `33971a2e205afec07aeadfbdcf4d00161bb555dfbb8dc2557f1654c4d3ca55a2`.
  Expected-fingerprint reading took 1.08 seconds / 152,104 KiB and returned the
  exact ADR 0158 11-session chain tip.
- Re-composing the real 2026-09-04 append from the expected 2026-09-03 base head
  took 21.18 seconds / 859,204 KiB, versus 36.70 seconds / 1,203,960 KiB for
  full base-parent validation. Both append files were byte-identical. This is
  about 42% lower elapsed time and 29% lower peak memory for this isolated
  composer path, not a complete daily-chain measurement.
- The expected fingerprint has no governed canonical home yet. A future
  immutable publication plus current pointer/CAS, rollback, recovery, and
  periodic full-lineage audit policy must be accepted before daily cutover.
- No network, `/data`, Candidate formula/parameter/rank/state, executor,
  coordinator, scheduler, publication, Snapshot, OCI, or Production state
  changed.

## Alternatives Considered

### Trust the latest head without an expected fingerprint

Rejected because a self-consistent local file is not evidence that the caller
selected the previously accepted lineage.

### Store the complete append path list in every head

Rejected because paths are operational and location-dependent, while a growing
list would undermine the bounded checkpoint design.

### Replace periodic full-lineage validation with checkpoints

Rejected. Incremental checkpoints bound daily work; periodic and code-change
verification must still reconstruct the exact full lineage independently.
