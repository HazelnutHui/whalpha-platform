# ADR 0022: Bind Daily Candidate Calculation to a Verified Prior Audit

## Status

Accepted

## Date

2026-08-27

## Context

The Candidate cold path formally rereads every source panel, recalculates every
historical Candidate batch and state row, reruns every session Oracle, and
rewrites the complete immutable audit. After shared source reads and indexed
state updates, the 2026-08-26 cold calculation still took about 462 seconds
before audit writing. Daily operation normally adds one completed trading
session, so repeating the already verified prefix is unnecessary work.

The existing audit stores one combined Oracle fingerprint rather than a
per-session Oracle ledger. A daily path therefore cannot reconstruct the old
combined Oracle container fingerprint without recalculating the prefix. It
must not claim that a current-session Oracle validated historical sessions it
did not recalculate.

## Decision

Keep the existing cold full-replay audit as the serial reference. Add a
separate `verified_prior_incremental` execution mode with an additive audit
schema minor version.

An incremental run must formally reread one completed prior Candidate audit
and fail closed unless all of the following hold:

- the prior audit has zero Oracle mismatch and all mode-appropriate
  equivalence gates pass;
- calculation, state, parameter, Universe order, Activation pointer, and
  membership fingerprints are unchanged;
- the prior Candidate sessions exactly equal the current Candidate-session
  prefix and the new as-of is the sole appended session;
- every prior Candidate batch still binds the matching Phase 1b state record;
- prior score, state, source, raw-fact, and normalization ledgers are retained
  byte-logically unchanged.

The incremental run formally loads the new 26-session panel, calculates the
two new Universe batches, appends one state row per current member, calculates
all current risk modes, and runs the independent score/risk Oracle plus an
independent state-append Oracle initialized from the prior state row. It writes
a complete immutable cumulative audit, not a pointer-only delta.

The incremental validation ledger binds the prior audit logical fingerprint,
prior business-output fingerprints, prior as-of, current as-of, reuse checks,
and current-session Oracle fingerprint. The incremental container fingerprint
is intentionally different from a legacy cold audit. Candidate batch, state,
risk, raw-fact, normalization, and source-panel business outputs must match a
cold reference for the same as-of when that periodic comparison is run.

Daily validation may use the incremental gate. Periodic validation and every
calculation, parameter, schema, source-governance, or state-machine change must
run the cold reference comparison before publication eligibility. Publication,
Snapshot, bundle, deployment, and scheduling remain separate authorization
boundaries.

## Consequences

- Ordinary daily work calculates only one new Candidate session while keeping
  a complete auditable result.
- A validated prior audit becomes an explicit input, never hidden mutable
  cache state.
- The first legacy audit used as a prefix is represented as one verified
  historical validation segment; later incremental runs append explicit
  current-session segments.
- A changed Activation, membership, parameter set, incompatible Phase 1b
  history, missing day, or failed prior gate forces a cold run rather than an
  unsafe incremental continuation.
- Audit writing still rewrites large cumulative JSON artifacts. Streaming,
  content-addressed resumable stages, and bounded retention remain separate
  performance work.

## Alternatives Considered

### Reuse prior state without recording the prior audit

Rejected because mutable or implicit cache state would weaken reproducibility
and make a daily result impossible to reconcile after restart.

### Reuse the legacy combined Oracle fingerprint

Rejected because it would falsely imply that the current process independently
recalculated the historical prefix.

### Require a cold full replay every day

Rejected as the permanent daily path because it repeats verified work and
delays stable post-close updates. It remains the reference and periodic gate.

### Store only a small daily delta

Deferred. A delta chain would reduce writes but adds compaction, retention,
recovery, and multi-file custody complexity. The first incremental version
keeps a self-contained cumulative audit.
