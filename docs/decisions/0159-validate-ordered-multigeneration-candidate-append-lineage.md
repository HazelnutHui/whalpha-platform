# ADR 0159: Validate Ordered Multi-Generation Candidate Append Lineage

## Status

Accepted

## Date

2026-09-07

## Context

ADR 0158 proved one `opportunity-candidate-segmented-append/1.1` successor over
an ADR 0155 base shadow. A daily segmented design also needs to use yesterday's
successor as today's parent. Treating every append as though it directly
extended the original shadow would lose the exact parent manifest, session
ordinal, source-audit lineage, and forward-chain tip.

A multi-generation correctness proof must not introduce path-dependent logical
identity or a mutable current pointer. It must also avoid claiming constant-
time daily performance: an independent reader that starts from the base and
validates every supplied append is intentionally linear in the append lineage.

## Decision

Add a `CandidateSegmentedParentEvidence` reader over one exact base shadow and
an explicitly ordered sequence of append package paths.

The reader formally validates the base, then each append against the immediately
preceding validated parent. Every step must preserve:

- the base shadow contract version;
- exact parent manifest physical SHA-256 and logical fingerprint;
- parent as-of session and session count;
- source calculation-contract and Universe fingerprints;
- exact prior and current forward-chain fingerprints; and
- the current append's typed session payload, counts, hashes, current
  projections, and non-authority gates.

After each step, the parent evidence advances to the append manifest, increments
the session count, exposes the new chain tip, and carries the current source V1
logical identity needed by the next verified-prior validation ledger.

The existing direct-session writer/reader and ADR 0158 composer accept an
optional ordered `parent_appends` sequence. Their default empty sequence retains
the original single-generation behavior and identities. For a later generation,
the direct candidate binds the immediate prior append manifest and chain tip;
the composer requires the same sequence and exact completed V1 source.

The existing `parent.shadow_contract_version` field continues to identify the
lineage's base shadow contract. The adjacent parent manifest SHA/logical
fingerprint identifies the actual immediate parent, which may be the base or a
prior append. No filesystem path becomes part of logical identity.

## Consequences

- A three-session fixture now constructs a base V1/shadow, append-1, and
  append-2 from two consecutive verified-prior V1 audits and direct session
  candidates.
- Append-2 binds append-1's exact manifest SHA and chain tip, increments the
  session ordinal once, preserves all eight direct-session projections, and is
  idempotently reusable.
- Omitting or reordering an intermediate append fails on exact parent-chain
  identity. The root shadow remains unchanged and all evidence reports zero
  external request, Production write, and publication authority.
- The generalized reader accepted the real 2026-09-03 base plus ADR 0158's
  2026-09-04 append as an 11-session/one-append parent in 39.79 seconds with
  2,078,752 KiB peak RSS. Its manifest SHA and final chain tip exactly matched
  the existing append.
- No new append or direct-session contract version is needed because existing
  parent fields already distinguish base contract identity from immediate
  parent content identity.
- The full parent reader validates the base and every append. This proves
  correctness and recovery from a cold process, not an O(current-session) hot
  path. A separately governed immutable chain-head/checkpoint with exact
  expected-parent identity, CAS, recovery, and periodic full-lineage audit is
  required before daily cutover.
- No real second-generation Dell append was created because no later exact
  retained V1/current-object pair was used for this proof. No `/data`, network,
  executor, coordinator, scheduler, publication, OCI, or Production state
  changed.

## Alternatives Considered

### Read append-2 directly against the base

Rejected because it would omit append-1 from both parent-manifest identity and
the forward hash chain.

### Embed absolute append paths in manifests

Rejected because paths are operational locations, not portable logical
identity, and would make otherwise identical evidence location-dependent.

### Trust only the latest manifest without an expected parent checkpoint

Rejected for the cold reader. A later hot reader may be bounded only when an
independently governed exact head identity supplies the missing trust anchor.
