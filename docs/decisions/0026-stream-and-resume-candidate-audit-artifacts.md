# ADR 0026: Stream and Resume Candidate Audit Artifacts

## Status

Accepted

## Date

2026-08-27

## Context

The verified-prior Candidate calculation now finishes in about 102 seconds
before audit writing, but the cumulative audit contains a roughly 196 MB score
history plus several other large JSON artifacts. The legacy writer encoded an
entire artifact into one string and then copied it into bytes. Formal reread
simultaneously retained raw bytes, parsed objects, and a second canonical
encoding. A prior real run was observed near 6.3 GiB RSS during this boundary.

The final audit is already an accepted compatibility and publication input.
Changing it to JSON Lines, Parquet, deltas, or pointer chains would expand the
consumer and custody contract. The first correction should therefore remove
avoidable memory copies and make final-artifact delivery recoverable without
changing any completed artifact bytes or logical fingerprints.

## Decision

Keep Candidate audit schemas 1.0 and 1.1 and their exact completed file sets.
Replace whole-object canonical serialization with a deterministic streaming
encoder that emits the same sorted, compact, ASCII JSON plus one trailing
newline. Physical hashes, byte counts, and logical fingerprints are calculated
incrementally. Formal reread hashes files in bounded chunks and compares the
parsed object with a streaming canonical hash instead of retaining duplicate
raw and re-encoded copies.

Add an optional explicit `--audit-work-dir`, restricted to a separate
owner-controlled direct child of `/tmp`. Each final audit artifact becomes one
ordered recovery stage. The work directory contains:

- a canonical recovery journal bound to the exact final output path, contract,
  source-derived artifact logical fingerprints, typed record fingerprints,
  Oracle, equivalence gates, and prior-audit identity;
- a contiguous prefix of completed final artifact files;
- at most the next exact `.partial` artifact during an atomic write; and
- a pending final manifest only after every artifact stage is complete.

Every resumed completed artifact is formally checked for owner/mode/symlink custody,
canonical encoding, physical SHA-256, byte count, and logical fingerprint.
Unexpected files, gaps, changed inputs, malformed journals, and present corrupt
stages fail closed. A valid interrupted `.partial` may be adopted; an invalid
known partial is discarded and rewritten. Unknown files are never removed.

Completion writes and fsyncs a pending manifest, removes the recovery journal,
atomically renames the manifest, formally rereads the exact completed file set,
and atomically renames the entire work directory to the requested final output.
A restart can finish a fully prepared or fully completed work directory before
opening Phase 1b, Candidate, panel, or `/data` sources. An interruption earlier
in artifact writing reuses the verified artifact prefix but still reconstructs
missing in-memory projections; calculation-stage checkpoints are later work.

The ordinary no-work-directory path remains supported and receives the same
streaming serializer and reader-memory improvement. Runtime timings, writer
mode, written count, and resumed count are physical evidence excluded from the
aggregate logical fingerprint.

## Consequences

- Completed Candidate business artifacts remain byte-compatible with existing
  audits, readers, publication, Snapshot, and rollback paths.
- Large temporary strings and bytes are removed from writer and reread custody,
  while the typed parsed objects required for validation remain in memory.
- A crash during final delivery no longer requires Candidate recalculation;
  an earlier writer crash preserves and reuses its formally verified prefix.
- The recovery directory intentionally remains after failure for inspection or
  explicit resume. Retention and cleanup require a later bounded policy.
- This does not yet checkpoint score, state, risk, and Oracle calculations, and
  it does not replace later daily/periodic/code-change validation tiers.
- No `/data`, provider, publication, Snapshot, OCI, credential, or scheduler
  state is introduced or changed.

## Alternatives Considered

### Replace completed artifacts with JSON Lines or Parquet

Deferred because it would change the accepted audit and downstream consumer
contract before the existing memory copies and final-delivery failure mode are
addressed.

### Write partial files directly into the final output directory

Rejected because the final path would become ambiguous after interruption and
could be mistaken for a completed immutable audit.

### Silently overwrite a mismatched recovery stage

Rejected because a changed input or corrupted stage must be investigated or
restarted under a new exact work directory, not hidden by cache-like fallback.
