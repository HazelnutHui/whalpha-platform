# ADR 0060: Reuse Candidate Completion Evidence for Publication

## Status

Accepted

## Date

2026-08-28

## Context

The Candidate calculation path is incremental, streamed, and independently
checked, but Market Intelligence publication still treated publication as a
new research audit. Candidate construction, approval-plan construction, and
Apply each invoked the full audit reader. That reader hashes every artifact,
parses every historical JSON row, rebuilds typed objects, and repeats Oracle
and business-fingerprint checks. A real 2026-08-26 comparison had already
shown a 197.20-second formal business-projection read, and the Candidate
process peak was 3,343,112 KiB. Repeating that work at publication boundaries
made deployment latency materially larger than calculation improvements
suggested.

The completed Candidate manifest is already the audit completion marker. It
freezes the ordered artifact set, byte sizes, SHA-256 values, logical
fingerprints, parameters, Oracle identity, zero-mismatch result, and replay
equivalence gates. The writer validates calculation inputs before writing and
performs the full semantic reread when finalizing the audit. Publication needs
the bounded current-session product, not a second research validation.

## Decision

Separate Candidate research validation from publication custody validation.

The publication reader must:

- require the same owner-only, direct-`/tmp`, non-symlink, mode-0400 custody;
- canonically validate the completion manifest and current parameter contract;
- stream SHA-256 over every declared artifact and check exact byte sizes and
  file order;
- require the zero-mismatch Oracle and all declared replay-equivalence gates;
- parse and type only the current publication inputs needed for the bounded
  Candidate product; and
- preserve the exact Candidate and Entry Geometry source identities already
  embedded in MI 1.1/1.2.

MI candidate construction returns an in-process validation evidence object.
MI 1.1/1.2 plan creation requires that exact object, so a caller cannot submit
an unrelated prebuilt Candidate and obtain a plan through the supported path.
The plan continues to freeze the immutable MI candidate, Candidate manifest
SHA/logical identity, Entry Geometry identity, final Candidate publication
fingerprint, Production inventory, and pointer state.

Apply and verify-then-link re-stream the artifact hashes and validate the
frozen plan, MI candidate files, current formal EOD/Identity/Activation,
freshness, target absence, and pointer compare-and-swap. They do not recreate
all historical Candidate typed objects. Any artifact, manifest, parameter,
Oracle gate, Entry Geometry binding, MI candidate, plan, Production state, or
pointer change still fails closed.

This decision does not change Candidate formulas, scores, ranks, business
bytes, MI/Snapshot contracts, review authorization, or rollback behavior.

## Consequences

- Research validation remains complete once, at Candidate audit finalization.
- Publication performs strong byte custody and bounded product validation
  without repeating historical business reconstruction.
- A real 2026-08-26 custody-only read completes in 1.55 seconds with 145,632
  KiB peak RSS. The complete bounded Candidate 1.1 projection with Entry
  Geometry completes in 11.29 seconds with 1,097,512 KiB peak RSS and retains
  logical fingerprint
  `286d4eebcb2e0489f33b03894bec8c7c58c1641f113719a014f296db42c2f07a`
  and 496/532 records.
- Periodic cold-reference validation and independent Oracle work remain in the
  calculation/research tier; publication cannot turn a failed audit into a
  deployable product.

## Alternatives Considered

### Skip artifact hashing and trust modification time

Rejected because timestamps and mode bits do not prove byte identity.

### Cache Python objects across commands

Rejected because process-local memory is not a durable approval boundary.

### Keep three full semantic rereads

Rejected because it adds no new decision evidence after immutable completion
and makes daily publication operationally impractical.
