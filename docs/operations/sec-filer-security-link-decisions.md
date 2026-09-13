# SEC Filer-to-Security Link Decisions

## Boundary

Build only after the selected EOD/Identity interval is quiescent and its exact
session index is frozen. This is a network-free, credential-free Dell
computation. The first run writes only to an owner-only candidate root outside
canonical `/data`.

The operation must formally read all three same-session Identity inputs and
verify their transitive fingerprints before deriving a row. It must not read a
current ticker table as historical repair evidence.

## Required behavior

- Preserve one explicit decision for every Instrument Master row.
- Normalize CIK only as ten decimal digits; missing or malformed values
  quarantine the affected instrument.
- Quarantine same-instrument multi-CIK or source/Instrument-Master mismatch.
- Treat same-CIK multi-instrument links as visible one-to-many relationships,
  not as automatic primary-security selection.
- Preserve source observation time and eligibility without backdating.
- Reconcile all input resolution states and exact duplicates in the manifest.
- Write partial directories first and publish the completed candidate through
  atomic rename only after a full formal reread.
- A formal reader may use one to eight explicitly requested worker processes.
  Each session must still independently validate its canonical snapshots,
  source custody, physical hashes, Arrow schema, row order, stable-ID
  cardinality, knowledge time, and status counts. The parent must then
  reproduce the exact ordered session index and aggregate denominators.

An isolated row conflict must not abort unrelated rows. Source lineage drift,
missing same-session inputs, duplicate canonical Instrument Master keys,
schema/hash mismatch, session-index drift, or incomplete denominator
reconciliation stops the build.

## Post-build review

Record exact admitted/missing/conflicting/mismatch counts, one-to-many CIK
distribution, session coverage, bytes, hashes, logical fingerprint, tests, and
the unchanged zero-authority boundary in a dated audit. Only then may a
separate canonical publication decision be considered.

## Current full candidate

The retained 2026-09-13 five-year candidate covers 1,255 sessions from
2021-09-13 through 2026-09-11. Its two allowed missing source sessions are
exactly 2026-08-13 and 2026-08-19. The build uses at most eight workers for
session materialization and now passes that same bounded count to its strict
formal reread. Direct readers remain single-process by default so callers must
choose higher concurrency explicitly. The parallel path preserves all
transitive hash, schema, denominator, time-eligibility, and quarantine checks;
it is not a lightweight or manifest-only verification mode.
