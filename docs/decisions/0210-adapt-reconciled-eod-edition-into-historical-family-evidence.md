# ADR 0210: Adapt one named reconciled EOD edition into historical family evidence

- Status: Accepted
- Date: 2026-09-12

## Context

The first Reconciled EOD Edition is a complete immutable price-family edition
for 1,234 sessions, but Historical Coverage cannot consume it through the
legacy current-EOD adapter. That adapter represents rolling EOD V1 partitions
and its EOD artifact model is one completion manifest per session. Treating the
edition as another current-EOD partition would lose the edition boundary and
could mix its exact interval with later rolling sessions.

Historical Coverage also requires the point-in-time Identity family to cover
the identical ordered sessions. The edition session manifests already bind the
same-session Identity snapshot fingerprints, so an adapter can verify those
bindings without granting any of the four still-missing family authorities.

## Decision

Add a read-only, edition-scoped historical-mechanics adapter with these rules:

1. A caller must name the exact `edition_id` and expected interval logical
   fingerprint. There is no latest-edition discovery or directory scan as an
   authority decision.
2. The EOD family evidence contains one artifact. Its completion manifest is
   the edition `interval-manifest.json`; its payload is the exact sorted set of
   every declared session manifest and Parquet file.
3. Before proposing evidence, the adapter formally rereads the complete
   edition. The Historical Coverage physical validator additionally accepts
   only the typed Reconciled EOD interval contract, verifies the exact edition
   file set, reconciles the interval record count, validates every sealed
   session manifest, and binds every declared Parquet SHA-256.
4. Point-in-time Identity evidence covers exactly the edition sessions. Every
   snapshot receives its existing formal reread and must equal the Identity
   snapshot fingerprint and provider bound by that edition session.
   Full edition-session and Identity-snapshot rereads may use a bounded local
   process pool. Results remain input-ordered and deterministic, and the
   worker count does not alter any logical fingerprint.
5. The result remains mechanics-only unpublished evidence. It does not publish
   family evidence or Historical Coverage and does not grant research,
   performance, Candidate, Production, website, or deployment authority.
6. Universe Membership, corporate actions, lifecycle, and adjustment-ledger
   evidence remain independent blockers. Price and Identity completion must
   not be described as a completed five-year research database.

The legacy current-EOD adapter and its already published evidence remain
unchanged and readable.

## Consequences

- Historical evidence can preserve the reconciled edition as one explicit
  immutable price source rather than flattening it into rolling current state.
- The Identity evidence interval cannot silently differ from the price
  interval or use a later snapshot.
- The evidence manifest remains small while transitively binding all source
  bytes; no EOD rows are copied.
- Full initial validation is deliberately more expensive than a manifest-only
  scan because it reopens the edition and Identity snapshots. Publication and
  subsequent rereads can rely on the immutable physical hashes bound here.
- A separately reviewed exact publication plan is still required before any
  new family-evidence files may be written to canonical `/data`.

## Rejected alternatives

- **Reuse the current-EOD adapter:** rejected because its rolling session scope
  and per-session completion semantics do not represent an immutable edition.
- **Reference only the interval manifest:** rejected because it would not bind
  the session manifests and Parquet bytes transitively.
- **Publish a partial Historical Coverage manifest now:** rejected because four
  required research families remain incomplete.
