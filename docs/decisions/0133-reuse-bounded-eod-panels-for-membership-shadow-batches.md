# ADR 0133: Reuse Bounded EOD Panels for Membership Shadow Batches

## Status

Accepted.

## Date

2026-09-04.

## Context

ADR 0132 proved one complete-base historical Universe Membership shadow, but
the single-session path took about 150 seconds on the Dell workstation. A
function-level profile of the unchanged 2026-09-03 replay showed that EOD
partition validation dominates the path. The same 20 historical partitions
were first inspected to describe the window and then reopened for the formal
calculation read, producing 41 EOD partition validations for one analysis
session. The accepted Identity families were also reread once for logical
snapshot inspection and again to build provider-identity indexes.

Repeating that path independently for 279 retained source packages would waste
hours on overlapping immutable partitions. Loading the entire 303-session
history into model objects at once would reduce I/O but create an unnecessarily
large memory and failure boundary.

## Decision

- Build a bounded shared EOD panel for at most five adjacent analysis sessions.
  Use the completion index only to discover available dates, then fully read,
  validate, fingerprint, and join every current or trailing partition consumed
  by the batch exactly once.
- Derive each session's 20-session descriptor from the formally read panel and
  the same XNYS calendar contract. Missing pre-history remains explicit; a date
  present in the completion index but absent from the formal panel is an error.
- Permit the single-session shadow to use the same panel path so window
  inspection no longer reopens all 20 partitions.
- After a sanitized package exactly rebuilds all three accepted same-day
  Identity-family fingerprints, build provider-identity indexes from those
  equivalent in-memory records instead of reopening the same Identity and
  Resolver Parquet partitions.
- Formally read the provider type catalog once per bounded batch. It remains a
  code dictionary, not point-in-time issuer-structure evidence.
- Accept only an explicit session-to-package mapping. Reject duplicates,
  out-of-range sessions, source/output overlap, non-`/tmp` output, and batches
  larger than five sessions.
- Write and formally reread each successful shadow partition independently
  under `/tmp`. A package-specific custody or Identity-equivalence failure
  blocks only that session and remains visible in the batch result. A shared
  EOD, catalog, output-custody, or unexpected programming failure stops the
  batch.
- Keep execution serial for this phase. Shared formal reads remove the major
  duplication without multiplying peak memory; CPU parallelism requires a
  separate measured design after the bounded implementation is proven.

## Consequences

- Five adjacent analysis sessions need roughly 25 unique EOD partitions rather
  than five independent 41-partition validation paths.
- The batch remains resumable through immutable per-session outputs and does
  not create a mutable cache, daemon, canonical index, or second source of
  truth.
- Every output retains its own exact source cutoff, source envelope, evaluated
  base, three-state decisions, and Primary-subset-of-Secondary invariant.
- The optimization changes no formula, threshold, Universe, active pointer,
  Production payload, scheduler, or research-readiness status.
- The retained packages remain ephemeral mechanics evidence. Efficient batch
  execution does not solve durable source custody or the exact 24-session gap.

## Alternatives Considered

### Run all 279 single-day commands independently

Rejected because it repeats immutable EOD and Identity validation thousands of
times and turns a correctness proof into avoidable operational delay.

### Load all 303 EOD sessions into one process

Rejected for this phase because millions of Python model objects would create
an oversized memory and restart boundary.

### Parallelize multiple full single-day builds

Rejected until shared-read performance and peak memory are measured. It would
repeat the same I/O while multiplying memory pressure.

### Trust completion manifests without rereading Parquet

Rejected because the completion index is a discovery boundary, not evidence
for data that feeds a calculation.
