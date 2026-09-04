# ADR 0127: Bound Strategy input to current Candidate evidence

## Status

Accepted.

## Date

2026-09-04.

## Context

Strategy Channels calculate and publish only the two Candidate batches for one
requested as-of session. The CLI nevertheless used the complete Candidate
audit reader, reconstructing cumulative Candidate batches, states, raw facts,
and normalization rows before discarding every non-current value.

On the unchanged 2026-09-03 Dell audit, that complete read alone took 225.978
seconds and peaked at 8,737,108 KiB RSS. The already accepted finalized current-
batch projection took 12.534 seconds as part of the ADR 0126 measurement. It
first rehashes the complete immutable Candidate artifact set, then validates
the exact current typed batches, source panel, Universe order, and fingerprint
bindings without reconstructing unrelated historical business rows.

Candidate Visual Context was separately replayed before this decision. It
completed in 51.11 seconds, including 34.208 seconds for the governed Candidate
and state projections, 8.719 seconds for the exact panel-cache reread, and
4.573 seconds for calculation plus Oracle. Its current path is therefore not
changed here.

## Decision

- Strategy Channels must use `read_opportunity_candidate_current_batches()`
  for its exact as-of Candidate inputs instead of the complete cumulative audit
  contents reader.
- The existing Entry Geometry audit reread, Primary-first completeness check,
  independent Strategy Oracle, permutation gate, audit custody, and source-
  manifest binding remain unchanged.
- The CLI reports physical stage timings and peak RSS in stdout. Runtime
  evidence remains outside Strategy business artifacts and logical
  fingerprints.
- Full Candidate reconstruction remains mandatory wherever cumulative
  Candidate history, raw facts, normalization, audit creation/finalization, or
  periodic/code-change validation is actually required.
- Do not add a new current-Candidate artifact, mutable cache, or shared process
  merely to optimize this stage. Reconsider only after a complete daily-chain
  measurement shows the remaining bounded reads are material.

## Consequences

- Strategy Channels no longer pay the time and memory cost of reconstructing
  Candidate histories they do not consume.
- Strategy formulas, channel eligibility, ranks, explanations, parameters,
  Candidate and Entry source identities, Oracle behavior, publication, and
  Snapshot contracts do not change.
- Canonical `/data`, Production, OCI, scheduler authority, and network access
  do not change.
- The completed 2026-09-03 `/tmp` replay reduced Strategy Channels to 33.82
  seconds. Its four business artifacts were byte-identical, its logical
  fingerprint was unchanged, and the Oracle and permutation gates passed.

## Alternatives Considered

### Share live in-memory objects across daily actions

Rejected. It would couple independently custodied, recoverable actions and make
restart behavior depend on one long-lived process.

### Add a new current-only Candidate artifact now

Deferred. The existing finalized projection solves the measured Strategy
problem without changing the Candidate audit contract.

### Optimize Visual Context in the same change

Rejected. Its measured 51.11-second path is already bounded and changing two
different evidence consumers would weaken attribution.
