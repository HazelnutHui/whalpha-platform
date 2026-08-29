# ADR 0071: Custody One-Shot Dashboard Snapshot Apply

## Status

Accepted

## Date

2026-08-29

## Context

ADR 0070 brings Dashboard Snapshot Approval Plan 2.4 preparation into the
daily Dell control plane and stops at `review_snapshot_publication`. The
existing Snapshot publisher already validates the full candidate, exact plan
SHA, current active-state fingerprint, Activation pointer, freshness, target
absence, staged copy, immutable target, and atomic active pointer. It does not
share the daily run's durable start/terminal custody.

A process interruption can therefore leave an inactive completed target, a
staging directory, or an unknown pointer outcome. The coordinator must not
infer that Apply can be replayed from the plan-review state.

## Decision

Add a fifth disjoint daily-journal family under backward-readable journal
contract 1.5, recovery router 1.1, and a one-shot Dashboard Snapshot Apply
capability behind coordinator 1.9.

The default coordinator path remains unchanged:
`review_snapshot_publication` grants no write authority. Apply is reachable
only when one invocation supplies:

- `--apply-dashboard-snapshot`;
- the exact Snapshot approval-plan whole-file SHA-256;
- the exact current Snapshot state fingerprint;
- the externally SHA-pinned, enabled Dell Host Runtime config; and
- for an approved stale-review plan only, the exact acknowledgement already
  embedded in that plan.

Snapshot Apply is mutually exclusive with offline execution, MI Apply,
Identity/EOD capabilities, email delivery, and unresolved recovery. Networking
remains prohibited.

Before publication, custody holds the global daily lock and proves the exact
unchanged `review_snapshot_publication` automation plan, canonical current
Plan 2.4 and candidate, session/data-root/legacy-root/target/pointer identity,
whole-file plan SHA, current normal or exact review freshness, unchanged active
Snapshot state, unchanged Activation pointer, absent target, and absent
staging residue. It then appends `dashboard_snapshot_apply_started` with only
non-sensitive identities and fingerprints. A review acknowledgement is never
journaled; only its SHA-256 is retained.

The explicit capability delegates the write to the existing lock-protected
`publish_and_activate` boundary. Success is recorded only after the formal
active reader proves the exact release ID, session, target, Snapshot/Dashboard
contracts, aggregate, manifest, and planned pointer fingerprint. Bounded write
evidence is the approved immutable release file count plus the active pointer.

Any exception after the start remains unresolved. Recovery performs no Apply
and no `verify-then-link`. It records recovered success only for that exact
active state. It records recovered not-completed only when the target and all
matching staging paths are absent, active Snapshot state is unchanged, and the
Activation pointer is unchanged. An inactive target, staging residue, changed
pointer, changed Activation, invalid plan, partial state, or ambiguous result
blocks for diagnosis. A complete inactive target can only use the existing
separately explicit `verify-then-link` operation after a new review.

Also preserve the exact `snapshot_generated_at` value when routing recovery of
an interrupted offline Snapshot Plan action. This repairs the action identity
without broadening recovery authority.

This repository change does not execute a real Snapshot Apply, write `/data`,
build a bundle, deploy OCI, roll back, or enable a service/timer/scheduler.

## Consequences

- Snapshot publication gains durable no-replay crash semantics.
- A scheduler can observe Snapshot review but cannot cross it without an exact
  one-shot invocation and externally pinned Dell runtime.
- Journal 1.5 remains backward-readable for prior 1.2–1.4 events, including MI
  Apply events written under 1.4.
- Bundle construction, OCI deployment, rollback, and unattended scheduling
  remain separate future boundaries.

## Alternatives Considered

### Reuse Market Intelligence Apply authority

Rejected because MI and Snapshot change different active Product states and
have different plans, pointers, file sets, and recovery evidence.

### Call Snapshot Apply immediately after plan preparation

Rejected because a valid Plan 2.4 is review evidence, not publication
authority.

### Automatically link an inactive target during recovery

Rejected because recovery must classify state without performing a new
Production write.
