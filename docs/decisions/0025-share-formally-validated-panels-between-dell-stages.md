# ADR 0025: Share Formally Validated Panels Between Dell Stages

## Status

Accepted

## Date

2026-08-27

## Context

The Candidate incremental path still spent about 217 seconds reopening and
validating the same 26 canonical EOD partitions already read by the current-
session Phase 1a calculation. Repeating that source work adds latency without
adding an independent calculation check: Candidate and Phase 1a intentionally
consume the same immutable source panel.

An ordinary mutable cache would weaken custody if a stale or mismatched panel
could be selected by date or filename. The optimization must preserve the
exact EOD, Identity, Activation, membership, and source-session bindings and
must never turn cache availability into a correctness requirement.

## Decision

Add an optional Dell-local, content-addressed formal panel cache. Phase 1a may
write the complete already validated panel after its canonical source read.
Candidate incremental execution may read it only when the Phase 1b source
ledger projects to the exact same 26-session cache key.

Each immutable cache entry contains:

- the exact 26-session source ledger and history fingerprint;
- EOD, Identity, Activation, ordered Universe, count, and membership bindings;
- complete typed panel and stable-ID membership metadata;
- canonically ordered bars in a fixed Parquet schema;
- physical and logical bar fingerprints plus a last-written canonical
  manifest.

The cache root and entries must be caller-owned, non-symlink directories with
fixed permissions. Entries are append-only and selected by a SHA-256 key, not
by `latest`. An absent exact entry is a cache miss and uses the unchanged full
formal reader. A present but unsafe, malformed, or mismatched entry fails
closed and is never silently replaced or bypassed.

The cache root is always explicit through `--panel-cache-root`. The repository
does not hard-code a workstation path, and this decision does not authorize a
Production or `/data` cache location. OCI never reads or creates these entries.

## Consequences

- Phase 1a and Candidate can share one validated daily panel instead of
  independently parsing the same 26 partitions.
- Candidate outputs, source ledgers, Oracles, and cold-reference semantics do
  not change. Cache status and logical fingerprint enter physical runtime and
  incremental-validation evidence.
- Cache misses remain correct but slower. Cache corruption is a hard failure,
  not a reason to trust another entry.
- The cache duplicates a bounded normalized panel on Dell; retention and
  cleanup require a later explicit operational policy.
- This removes repeated source parsing but not Candidate calculation, Oracle,
  prior-audit reread, or cumulative JSON writer cost.

## Alternatives Considered

### Trust canonical Parquet manifests without retaining the parsed panel

Rejected because Candidate would still repeat large Parquet and historical
Identity joins, leaving much of the measured latency in place.

### Put the cache inside `/data` automatically

Rejected because `/data` is governed canonical state and no cache publication
or retention operation has been authorized there.

### Store only derived Candidate raw facts

Deferred because rolling score formulas need the underlying ordered bar
history and future formula changes should not depend on an incomplete feature
state.
