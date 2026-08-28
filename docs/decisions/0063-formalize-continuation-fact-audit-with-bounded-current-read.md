# ADR 0063: Formalize Continuation Fact Audit with a Bounded Current Read

## Status

Accepted

## Date

2026-08-28

## Context

ADR 0062 introduced deterministic descriptive continuation facts, but the
first real review calculated them in memory. A daily research stage needs an
immutable, formally rereadable artifact with exact Candidate, Entry Geometry,
panel-cache, parameter, and Oracle custody.

The existing general Candidate audit reader reconstructs cumulative raw facts,
normalization, score history, state history, transitions, risks, and Oracle
objects. That is appropriate for append and deep validation, but unnecessary
for a downstream fact stage that needs only the exact latest Candidate batches.
The Candidate score-history artifact is about 196 MB on the current real audit,
so repeated full semantic replay would reintroduce avoidable latency and memory
pressure.

## Decision

Add a bounded current-batch Candidate reader. It must first run the existing
publication-evidence reader, which verifies the immutable manifest, exact file
set, owner/mode, byte count, physical SHA-256, parameter contract, and all
completion/Oracle/equivalence gates. It then parses only:

- the Candidate score-history artifact to select the audit's exact as-of
  batches; and
- the source-input manifest to bind the exact current panel.

It validates the selected typed rows, row and batch logical fingerprints,
Primary-first Universe order, manifest fingerprint ledger, and panel-history
lineage. It does not reconstruct raw facts, normalization, state history,
transitions, risks, or the historical Oracle.

Do not canonically re-encode the 196 MB score-history object at this downstream
boundary. The immediately preceding custody reader has already matched its
exact bytes to the immutable completed manifest. Re-encoding those same bytes
does not add independent evidence; the selected current objects still receive
full typed and logical-fingerprint validation.

Add a tmp-only `candidate-continuation-facts-audit/1.0` writer, formal reader,
and offline CLI. The audit:

- binds Candidate, Entry Geometry, and content-addressed panel-cache manifests;
- freezes the fact parameter contract and both fact-batch fingerprints;
- requires zero independent-Oracle mismatch and input-permutation equivalence;
- records that it is shadow-only, not a strategy-score input and not a
  performance claim; and
- writes three immutable artifacts plus the completion manifest by atomic
  directory rename, with directory mode `0700` and file mode `0400`.

Keep performance timings outside the logical audit identity. Two runs with the
same governed inputs must have the same fact, Oracle, and audit logical
fingerprints even if their runtime differs.

Do not add a new current-batch artifact to the Candidate main audit yet. The
optimized current projection is no longer the dominant stage, and changing the
upstream schema would affect append, resume, validation-tier, publication, and
compatibility readers. Reconsider a shard only after repeated daily profiles
show a material end-to-end need.

## Consequences

- Continuation facts now have a reproducible offline custody path rather than
  relying on an ad hoc in-memory review.
- On real 2026-08-26 inputs, the optimized end-to-end stage completed in 24.15
  seconds versus 33.59 seconds before removal of duplicate re-encoding. The
  current Candidate projection fell from 16.48 to 7.16 seconds; fact plus
  independent-Oracle computation took 6.65 seconds and audit write plus formal
  reread took 0.52 seconds.
- Both runs produced audit fingerprint
  `3e1226c676f19d95876c8bda96a4739ec551d4be83cfe83cbc1854cf5fafe976`
  and the same two fact-batch fingerprints.
- The remaining largest measured stage is the formally validated price-panel
  cache read at 8.83 seconds. That is real required input work, not unexplained
  strategy-calculation latency.
- No `/data`, Strategy Preview, publication, Snapshot, Dashboard, deployment,
  provider, credential, scheduler, or Production state changes.

## Alternatives Considered

### Use the cumulative Candidate audit reader

Rejected for this downstream stage because it semantically rebuilds unrelated
historical objects.

### Add a new Candidate current-batch shard immediately

Deferred because the measured optimized projection is seven seconds and no
longer dominates the 24-second stage. The upstream compatibility cost is not
currently justified.

### Store runtime timings inside the audit logical fingerprint

Rejected because identical business evidence would receive different content
identities on every run.
