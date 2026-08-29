# ADR 0070: Custody the Daily Dashboard Snapshot Plan

## Status

Accepted

## Date

2026-08-29

## Context

The daily Dell control plane now prepares and can separately publish Market
Intelligence under exact custody. It still stopped after MI publication, while
the operator had to reconstruct the Snapshot dry-run command, select the
active MI publication, bind the same-session Strategy Channel audit, choose a
timestamp/output root, and reconnect the resulting Approval Plan 2.4 to the
daily run.

Snapshot Apply must not be added until the planner can first prove that the MI
publication named by the daily plan is the exact active publication and that a
formal Snapshot plan was prepared from it.

## Decision

Extend the daily automation plan to 1.3 and add
`prepare_dashboard_snapshot_plan` as the ninth ordered offline action. It runs
after the exact MI planned pointer is active and before
`review_snapshot_publication`.

The planner first rereads the active MI release without repeating its already
completed full source reconstruction. It still validates the immutable active
release/reference and requires the exact publication ID, analysis session,
target path, and planned pointer fingerprint from the formally reread MI plan.
An absent or older active publication keeps the run at `review_publication`;
an inconsistent same-publication state blocks.

Snapshot planning requires two new, distinct direct-child `/tmp` paths for the
output root and approval-plan file plus an explicit aware UTC
`snapshot_generated_at`. The governed action delegates to the existing
Snapshot V2 dry-run administrator with:

- the exact target session;
- the exact active MI publication ID;
- the same-session Strategy Channel audit;
- the explicit timestamp; and
- the explicit output/approval paths.

It performs no network request and no Production write.

Add a public formal Snapshot-plan reader. It accepts only an owner-controlled,
regular, non-symlink, mode `0444`, canonical JSON file under `/tmp`, selects the
declared plan version, and runs the existing full candidate/plan validation.
The daily planner requires current Approval Plan 2.4, the exact session,
candidate parent, MI publication/payload/logical fingerprints, and Strategy
Channel audit fingerprint. Missing output and plan select the action; a partial
pair, invalid custody, old contract, or lineage/path mismatch blocks.

After successful formal reread, the planner stops at
`review_snapshot_publication`. This state grants no Snapshot Apply, bundle,
OCI deployment, rollback, or scheduler authority.

## Consequences

- The daily chain now reaches a reviewable Snapshot approval package without
  manual source/path reconstruction.
- Snapshot planning cannot run before the exact reviewed MI publication is
  active.
- The timestamp and both output paths join interruption identity and recovery
  custody.
- Snapshot Apply still requires a separate default-off write boundary with
  reservation, active-state proof, and no-write recovery.
- No real Snapshot candidate, approval package, `/data` write, bundle,
  deployment, service, timer, or scheduler was created by this change.

## Alternatives Considered

### Prepare Snapshot before MI Apply

Rejected because the Snapshot contract intentionally consumes a formally
active immutable MI publication, not a merely proposed candidate.

### Let Snapshot planning discover the newest MI directory

Rejected because directory recency is not publication identity or approval.

### Combine Snapshot Plan and Apply

Rejected because plan preparation is offline review evidence, while Apply
changes the active Product state and needs separate crash custody.
