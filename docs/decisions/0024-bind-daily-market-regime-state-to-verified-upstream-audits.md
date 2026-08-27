# ADR 0024: Bind Daily Market Regime State to Verified Upstream Audits

## Status

Accepted

## Date

2026-08-27

## Context

The corrected stable-prefix Phase 1b cold path preserves chronological state
semantics, but it reloads canonical EOD history and recalculates every prior
Phase 1a Composite each day. That duplicates the already completed and
independently validated current Phase 1a audit, and daily work grows with
retained history.

Phase 1b is a state transition over one current Composite plus the exact prior
persisted state. It does not need raw EOD partitions again when both inputs are
formal immutable audits with complete custody and zero-Oracle gates.

## Decision

Add Phase 1b audit schema 1.1 with
`execution_mode=verified_prior_incremental`. It formally rereads the current-
session Phase 1a audit and the immediately preceding corrected stable-prefix
Phase 1b audit.

The path accepts only calculation V1.0.1, the exact state parameter
fingerprint, an immediate XNYS successor, the same ordered public Universes,
unchanged Activation, and unchanged membership fingerprints. It appends
exactly one state and explanation row per Universe, repeats the append for
restart equivalence, and evaluates the new rows with the independent state
implementation initialized from the prior persisted record.

The cumulative audit adds `incremental-validation-ledger.json`. The ledger
binds the prior audit, prior history and explanation prefixes, prior source
manifest, current Phase 1a audit and Composite fingerprints, current one-
session Oracle fingerprints, reuse gates, and cumulative validation segments.
A mismatch fails closed and requires the V1.0.1 cold reference path.

The incremental path does not reopen `/data`. The cold stable-prefix replay is
retained for periodic and code/model-change validation and remains the
business-output equivalence reference.

## Consequences

- Normal daily Phase 1b work becomes constant with respect to retained state
  history, apart from formally rereading and rewriting the cumulative audit.
- Phase 1a remains responsible for raw EOD calculation and its Oracle; Phase
  1b does not duplicate that validated work.
- Incremental and cold container/Oracle fingerprints differ by design, while
  cumulative state, explanation, transition, current-summary, and history
  business outputs must match.
- Activation or membership changes, gaps, incompatible versions, unsafe audit
  custody, failed upstream Oracles, or prefix drift force a cold replay.
- Streaming audit output and validation tiers remain separate later work; the
  cumulative JSON writer can still become the dominant cost as history grows.

## Alternatives Considered

### Reload canonical EOD and recalculate every historical Composite

Rejected as the daily path because it repeats a formally completed upstream
calculation and grows with retained history. It remains the cold reference.

### Read the prior state row without formally rereading its audit

Rejected because a detached row cannot prove parameter, source, history-
prefix, Oracle, or completion custody.

### Accept non-adjacent or membership-changing inputs

Rejected because a state machine cannot silently bridge a session gap or
reinterpret historical state under a different Universe.
