# Reconciled EOD Edition

## Purpose

This runbook covers construction review, exact Apply planning, and atomic
publication of ADR 0204's complete corrected EOD research edition. It does not
authorize source acquisition, model research, Historical Coverage, activation,
Dashboard publication, OCI deployment, or cleanup.

## Preconditions

1. The unique five-year EOD/Identity writer has stopped and both families are
   aligned across the frozen interval.
2. The source repository is clean and its exact revision is recorded.
3. Every required session has exact Grouped Daily and same-session Identity
   evidence, with later reacquisition visibly classified where unavoidable.
4. The candidate root is exactly one direct child of the fixed owner-only Dell
   base:
   `/home/hui/.local/state/trading-intelligence-platform/reconciled-eod-editions`.
5. No interval marker exists until every declared session has passed formal
   reconstruction and reconciliation.

Candidate construction is resumable per session. The persistent base,
candidate root, and all candidate subdirectories are 0700; candidate artifacts
are 0600. A completed candidate is still non-authoritative.

The internal batch builder accepts only an explicitly ordered source list,
processes 1–40 sessions with 1–4 spawned workers, disables network access, and
publishes only immutable candidate session partitions. An exact completed
session is formally reread and reused only when all selected source bindings
match. A failed session is reported without discarding other completed
partitions, and the batch never writes the interval marker or `/data`.

Do not construct the real edition until acquisition is quiescent and a formal
source-coverage plan has selected exactly one retained-original or visibly
later-reacquired package for every declared session. The batch service is an
implementation primitive, not permission to infer sources from directory
order or to build from an incomplete interval.

## Build and review source coverage

After the unique acquisition writer stops, build one immutable network-free
coverage artifact for the exact XNYS evaluation interval:

```bash
scripts/dev/run-project-python.sh -m tip_api.services.reconciled_eod_source_coverage_cli \
  --data-root /data/trading-intelligence-platform \
  --first-session 2021-09-09 \
  --last-session 2026-09-09 \
  --created-at <UTC-timestamp> \
  --coverage-path /home/hui/.local/state/trading-intelligence-platform/reconciled-eod-source-coverage/<coverage-id>.json \
  --workers 4
```

The artifact contains no home path or response body. It formally binds each
selected package by origin, provenance, observation time, package hashes,
canonical EOD/Identity fingerprints, and—when retained from canonical
construction—the original Apply-plan hash. It classifies missing, invalid,
unproven, or multiple sources rather than choosing the first directory match.
The daily workspace's generic acquisition directory is ignored when its
manifest declares an Identity package rather than Grouped Daily.
The census is limited to four spawned processes; this uses Dell parallelism
without turning source validation into an unbounded I/O workload.

Do not build candidate sessions unless status is
`ready_for_candidate_build`. Preserve the coverage file SHA-256. For a reviewed
ordered batch of at most 40 sessions, use no more than four workers:

```bash
scripts/dev/run-project-python.sh -m tip_api.services.reconciled_eod_edition_batch_cli \
  --data-root /data/trading-intelligence-platform \
  --coverage-path <exact-coverage-path> \
  --coverage-file-sha256 <coverage-file-sha256> \
  --candidate-root /home/hui/.local/state/trading-intelligence-platform/reconciled-eod-editions/<candidate> \
  --edition-id <edition-id> \
  --implementation-revision <clean-source-revision> \
  --created-at <UTC-timestamp> \
  --session <YYYY-MM-DD> \
  --workers <1-4> \
  --execute
```

The batch rereads the coverage hash and selected package bindings before
construction. `--execute` writes only owner-only candidate partitions; it
makes zero external requests, writes zero canonical files, and never writes
the interval completion marker.

## Completion and review

Publish the interval manifest only after the exact ordered evaluation and
warm-up session sets are present. The publisher formally validates one session
at a time, so memory use is bounded by one daily cross-section rather than the
whole five-year edition.

Before planning, confirm the final interval fingerprint, source-provenance
counts, accepted additions, zero quarantine/source gaps, exact file set, and
absence of the canonical edition target.

## Build the exact Apply plan

Run only after `/data` is quiescent. Substitute the reviewed edition ID,
candidate path, UTC completion time, and exact 40-character clean source
revision.

```bash
scripts/dev/run-project-python.sh -m tip_api.services.reconciled_eod_edition_apply_cli plan \
  --data-root /data/trading-intelligence-platform \
  --candidate-root /home/hui/.local/state/trading-intelligence-platform/reconciled-eod-editions/<candidate> \
  --plan-path /home/hui/.local/state/trading-intelligence-platform/reconciled-eod-editions/<candidate>/apply-plan.json \
  --edition-id <edition-id> \
  --planner-revision <clean-source-revision> \
  --created-at <UTC-timestamp>
```

Planning makes no provider request and no `/data` write. It formally rereads
the candidate, binds every artifact and the complete pre-state inventory, and
writes one 0400 plan. Record the emitted plan SHA-256, logical fingerprint,
expected state fingerprint, counts, and bytes. A plan with any unexpected
authority flag is invalid.

## Apply one complete edition

Apply requires the three exact values emitted by planning and an explicit
`--execute`. Do not run while any other canonical writer is active.

```bash
scripts/dev/run-project-python.sh -m tip_api.services.reconciled_eod_edition_apply_cli apply \
  --data-root /data/trading-intelligence-platform \
  --plan-path <exact-plan-path> \
  --approved-plan-sha256 <plan-file-sha256> \
  --expected-plan-logical-fingerprint <plan-logical-fingerprint> \
  --expected-current-state-fingerprint <pre-state-fingerprint> \
  --execute
```

Apply uses the shared Dell data-writer lock and prohibits network access. It
copies the complete edition to adjacent target-local staging, verifies exact
source bytes during the copy, places the interval marker last, and exposes the
edition with one atomic directory rename. It never overwrites an edition.

If an earlier Apply may already have completed the exact target, diagnose it
first and use `--verify-then-complete` only for byte-identical formal recovery.
Pre-existing staging residue is a stop condition and is never automatically
deleted.

## Postconditions

Success requires:

- target file count and bytes equal the plan;
- every target session passes schema, hash, row-contract, content-fingerprint,
  and interval-binding reread;
- the interval fingerprint equals the planned candidate fingerprint;
- canonical inventory outside the target is unchanged; and
- external requests, overwritten/deleted partitions, Production authority, and
  research-performance authority remain zero/false.

The next step is a separately versioned Historical Coverage and research-input
admission review. Merely publishing the corrected edition does not make it an
active model or website source.
