# ADR 0069: Custody One-Shot Market Intelligence Apply

## Status

Accepted

## Date

2026-08-29

## Context

ADR 0068 brings Market Intelligence approval-plan preparation into the daily
Dell control plane and stops at `review_publication`. The existing publication
administrator already requires an exact plan SHA, expected Production
inventory, consumer-pointer compare-and-swap, current freshness, immutable
target, and atomic pointer update. It did not, however, share the daily run's
durable start/terminal custody. A process interruption could therefore leave a
complete inactive target or an unknown pointer outcome without preventing an
unsafe replay by a higher-level coordinator.

Publication authority must remain different from standing Identity/EOD data
authority. A timer must not acquire it merely because analytics are ready.

## Decision

Add a fourth disjoint daily-journal family under backward-readable journal
contract 1.4 and a one-shot MI Apply capability behind coordinator 1.7.

The default coordinator path is unchanged: `analytics_ready` returns
`review_publication`. Apply is reachable only when one invocation supplies:

- `--apply-market-intelligence`;
- the exact MI approval-plan whole-file SHA-256;
- the exact expected `/data` inventory fingerprint;
- the externally SHA-pinned, enabled Dell Host Runtime config; and
- for an approved stale-review plan only, the exact acknowledgement already
  embedded in that plan.

The MI mode is mutually exclusive with offline execution, unresolved recovery,
and standing Identity/EOD capabilities. Networking stays prohibited.

Before publication, custody holds the global daily lock and proves the exact
unchanged automation-plan fingerprint, `review_publication` state, canonical
MI plan and candidate, session/data-root/target/pointer identity, whole-file
plan SHA, current freshness or exact review exception, unchanged full
Production inventory, unchanged MI consumer pointer, absent target, and absent
staging residue. It appends `market_intelligence_apply_started` with hashes and
non-sensitive identities, then releases the journal lock. The review
acknowledgement itself is never journaled; only its SHA-256 is retained.

The explicit capability delegates the write to the existing lock-protected
`publish_and_activate` boundary. Success is recorded only after the formal
active reader, with source validation, proves the exact publication ID,
analysis session, target, aggregate, payload, and planned pointer fingerprint.
The bounded write evidence is exactly the plan's three files: payload,
manifest, and active pointer.

Any exception after the start remains unresolved. Recovery performs no Apply
and no `verify-then-link`. It records recovered success only for the exact
active state; recovered not-completed only when the target is absent and both
full inventory and consumer state equal the pre-Apply bindings; every inactive
target, staging residue, changed inventory/pointer, invalid plan, partial, or
ambiguous state blocks for diagnosis. A complete inactive target may later use
the existing separately explicit `verify-then-link` procedure after review.

This repository change does not create a Host Runtime artifact, execute a real
MI plan or Apply, write `/data`, build a Snapshot or bundle, deploy OCI, or
enable a service/timer/scheduler.

## Consequences

- MI publication now has the same no-replay crash semantics as canonical data
  Apply without sharing its standing authorization.
- A scheduler can observe `review_publication`, but cannot cross it without
  exact one-shot invocation inputs and an externally pinned Dell runtime.
- Unknown publication outcomes remain visible and serialized by the global
  journal.
- Snapshot publication, bundle construction, OCI deployment, rollback, and
  unattended scheduling remain separate future boundaries.

## Alternatives Considered

### Reuse standing Identity/EOD authorization

Rejected because it explicitly excludes publication and would turn a bounded
data-maintenance grant into a broader Product-state grant.

### Call MI Apply directly after plan preparation

Rejected because successful planning is review evidence, not publication
authority.

### Automatically link an inactive completed target during recovery

Rejected because recovery must classify state without performing a new
Production write.
