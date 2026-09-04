# ADR 0126: Reuse exact panel and current Candidate evidence downstream

## Status

Accepted.

## Date

2026-09-04.

## Context

The 2026-09-03 daily chain completed correctly, but downstream stages repeated
expensive reconstruction of inputs already validated earlier in the same
offline chain.

On the unchanged Dell inputs, the original ETF Relationship audit spent
605.725 of 611.256 pre-write seconds loading the same 26-session formal panel.
After ADR 0125, an isolated cold replay still spent 148.666 of 154.178 seconds
on that panel load. Its audit and history logical fingerprints, relationship
metrics, current summary, equivalence gates, and zero-mismatch Oracle all
matched the original output.

Entry Geometry also called the complete Candidate audit reader, then decoded
the 469 MB score history and 140 MB state history again. The completed output
directory appeared about 19 minutes after the prior Candidate stage. A
read-only benchmark of the existing finalized-evidence projections took 34.410
seconds for the exact two current batches plus the governed state ledger,
while retaining immutable file custody, hashes, source lineage, typed records,
and Candidate completion gates.

ADR 0025 already defines a content-addressed, source-bound formal panel cache.
ADR 0117 already defines when finalized Candidate evidence may be reused. The
missing step is to apply those accepted boundaries consistently to downstream
daily consumers.

## Decision

- Entry Geometry and ETF Relationships may consume the existing exact
  Market Regime panel cache when an explicit owner-controlled cache root is
  supplied.
- Cache selection must be derived from a formally reread upstream source
  ledger: the current Candidate source panel for Entry Geometry and the Phase
  1a input manifest for ETF Relationships.
- A cache hit must pass the complete cache custody, physical-hash, logical-
  fingerprint, schema, and reconstructed-source-boundary checks from ADR 0025.
  An unsafe, malformed, or mismatched entry fails closed.
- If no exact entry exists, the unchanged formal `/data` reader remains the
  fallback. Its reconstructed source boundary must equal the upstream ledger
  before an optional cache entry is written. No `latest` pointer or mutable
  lookup state is introduced.
- Entry Geometry must use the existing finalized Candidate current-batch
  projection and governed state-history projection instead of reconstructing
  the complete Candidate audit and then decoding the same large histories a
  second time. It still filters an exact as-of state set and preserves the
  current Primary-first completeness gate.
- The daily executor forwards its existing panel-cache root to both stages.
- Stage summaries may report physical cache status and elapsed time, but these
  runtime facts do not enter business logical fingerprints.
- Full Candidate reconstruction remains mandatory for creation, finalization,
  periodic/code-change validation, and any operation that consumes cumulative
  Candidate business history beyond the accepted projections.

## Consequences

- The daily chain should avoid two redundant formal panel scans and one
  redundant complete Candidate reconstruction.
- Entry Geometry, ETF Relationship, Candidate, Market Regime, publication, and
  Snapshot formulas, parameters, contracts, ranks, records, and business
  fingerprints do not change.
- The cache remains Dell-local and disposable under an explicit non-`/data`
  path. Canonical `/data`, scheduler authority, OCI serving, and network access
  do not change.
- The completed 2026-09-03 `/tmp` replay reduced Entry Geometry to 49.67
  seconds and ETF Relationships to 15.36 seconds. Entry's three and ETF's
  eight business artifacts were byte-identical to their prior audits; logical
  fingerprints and zero-mismatch Oracles were unchanged.

## Alternatives Considered

### Add another downstream database or mutable cache

Rejected. The existing content-addressed panel cache already carries the exact
source and custody evidence needed by these consumers.

### Add duplicate current-only Candidate artifacts immediately

Deferred. The accepted finalized-evidence projections reduce the measured
problem without changing the Candidate artifact contract. A new artifact is
justified only if a later profile shows the remaining bounded reads are still
material.

### Skip downstream source validation

Rejected. The optimization removes repeated reconstruction, not source,
custody, lineage, typed-record, Oracle, or equivalence gates.
