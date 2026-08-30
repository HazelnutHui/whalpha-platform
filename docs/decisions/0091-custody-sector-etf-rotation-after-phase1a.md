# ADR 0091: Custody Sector ETF Rotation After Phase 1a

## Status

Accepted

## Date

2026-08-30

## Context

ADR 0090 made the Sector ETF Rotation calculation effectively instantaneous,
but a standalone formal panel load took more than 200 seconds on Dell. Adding
that scan as another daily stage would repeat work already performed by Market
Regime Phase 1a and recreate the data-ingestion bottleneck the project has
already removed elsewhere.

The result also needs immutable source and Oracle custody before it can be
considered for Market Intelligence or Snapshot projection.

## Decision

Add `sector-etf-rotation-audit/1.0` as an atomic, direct-child `/tmp` audit. The
writer receives the already loaded `MarketRegimeInputPanel`; it performs no
canonical scan or external request. It formally rereads the completed Phase 1a
audit, binds the exact Phase 1a calculation and input manifest hashes/logical
fingerprints, and requires the panel history fingerprint and session ledger to
match that source.

The audit contains one source manifest, the typed rotation product, the typed
independent Oracle report, and a completion manifest. Product/parameter/source
fingerprints, all 11 record fingerprints, file hashes, Oracle zero-mismatch,
Theme-unavailable status, shadow-only status, and zero Production writes are
frozen. Files are canonical JSON, owner-only mode `0400`, and the completed
directory is created only through an atomic staging rename.

Daily integration must calculate and write this audit while the Phase 1a panel
is already available in process. A separate reload from canonical EOD is not an
accepted runtime design.

This ADR does not add the calculation to the installed scheduler, Market
Intelligence publication, Dashboard Snapshot, API, navigation, or Production.

## Consequences

- The real 2026-08-28 audit bound all 11 records to formal Phase 1a with Oracle
  mismatch zero and no partial residue.
- The measured standalone panel load was 200.729 seconds; calculation and
  independent Oracle took 0.012 and 0.008 seconds. Panel reuse is therefore a
  correctness-preserving performance requirement, not a later optimization.
- Publication consumers can later accept only a formally reread audit instead
  of an unbound JSON product.

## Alternatives Considered

### Reload canonical history in a new daily stage

Rejected because it adds about 200 seconds of redundant work for a millisecond-
scale calculation and creates another independent source-reconstruction path.

### Publish the in-memory product without an audit

Rejected because downstream consumers could not prove exact Phase 1a lineage,
parameters, per-record identity, or Oracle success.

### Write directly under `/data`

Rejected because this is still a shadow research artifact and no publication
or activation has been authorized.
