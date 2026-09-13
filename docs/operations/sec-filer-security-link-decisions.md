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

An isolated row conflict must not abort unrelated rows. Source lineage drift,
missing same-session inputs, duplicate canonical Instrument Master keys,
schema/hash mismatch, session-index drift, or incomplete denominator
reconciliation stops the build.

## Post-build review

Record exact admitted/missing/conflicting/mismatch counts, one-to-many CIK
distribution, session coverage, bytes, hashes, logical fingerprint, tests, and
the unchanged zero-authority boundary in a dated audit. Only then may a
separate canonical publication decision be considered.
