# ADR 0178: Publish sparse split adjustments with exact Plan/Apply

- Status: Accepted
- Date: 2026-09-09

## Context

ADR 0177 produced and independently reconciled a publication-exact candidate
containing 101,321 stable-ID/session rows. Candidate custody below `/tmp` is
not canonical custody. The project needs a narrow publication boundary without
changing factor math, treating omitted rows as neutral, or promoting this
split-only outcome-reconciliation result into Historical Coverage.

The candidate already embeds its derivation revision and calculation time. A
later planner necessarily has a different implementation revision, so the two
revisions must remain distinct rather than rewriting the audited candidate.

## Decision

1. Publish the candidate unchanged to the content-addressed ADR 0177 target.
   The target contains exactly `part-00000.parquet` and `manifest.json`.
2. Record `planner_source_revision` separately from the candidate publication's
   `source_revision`. Bind both identities, the plan creation time, exact
   artifact paths, bytes, hashes, and whole `/data` pre-state.
3. Before a plan is trusted, formally reread the candidate and fully rederive
   all rows from its bound canonical split-action and EOD family evidence using
   the candidate's original revision and calculation time. Require an exact
   `already_present` result and identical publication object.
4. Apply only under the shared Dell data lock, with network prohibited and the
   exact current inventory required. Copy into a deterministic staging
   directory, fsync both files and directories, then atomically rename.
5. Formally reread the canonical target and prove the inventory outside it is
   unchanged. An exact completed target returns `verified_existing` with zero
   writes. Drift, tamper, symlink, partial target, or staging residue fails
   closed.
6. Keep absent-row neutrality, total-return coverage, full Adjustment Ledger
   coverage, Historical Coverage, research performance, analytics, Snapshot,
   bundle, deployment, and scheduler authority false.
7. Advance the current-context reader to contract 1.9. It must formally read
   canonical sparse split publications and report them as split-only outcome
   reconciliation while preserving `data_blocked`.

## Consequences

- The exact real candidate can become durable and recoverable canonical
  evidence without a second transformation or mutable pointer.
- Candidate and planner provenance remain truthful and independently auditable.
- Full row rederivation makes Plan/Apply stronger than a byte-copy workflow,
  while the sparse physical artifact keeps storage and canonical write small.
- The new family is useful for adjustment reconciliation but remains
  insufficient for research signals or performance claims.

## Execution evidence

The first Dell plan was built from clean planner revision
`bdb027a293a167962c24f4a8ec0bb28746e53b8e` while preserving candidate
revision `0c57560d44489c4170675cee086527d25e6daef4`. Plan SHA-256 is
`fef31be98d8ae6ebbae2a55e043a2eb7f210770acae1204a0972141fefdbaf06`
and plan logical fingerprint is
`99d657c78694db98659a6d4537f2a3192a308f774994279fba7234d3a8ce132c`.

The locked Apply added exactly two files / 80,308 bytes and published 101,321
rows with fingerprint
`7e08b8a8ee364cf215c1459645f76240368b50cc3d2cb4bc77db86d3ca7c3c2a`.
There was no overwrite, deletion, external request, or outside-target change.
An exact second Apply returned `verified_existing` with zero files and zero
bytes. Current-context contract 1.9 formally reread the publication while
retaining incomplete adjustment reconciliation and `data_blocked`.

## Rejected alternatives

- **Rewrite the candidate with the planner revision:** changes already audited
  bytes without changing the underlying facts.
- **Trust only candidate file hashes:** does not prove the bytes still derive
  from current bound canonical inputs.
- **Copy directly into the final directory:** exposes partial publication and
  weakens interruption recovery.
- **Add a latest pointer:** unnecessary for an outcome-only basis-specific
  evidence family and introduces mutable state.
- **Promote the sparse result to Historical Coverage:** omitted-row neutrality,
  dividends, source availability/revision completeness, and other research
  families remain unresolved.
