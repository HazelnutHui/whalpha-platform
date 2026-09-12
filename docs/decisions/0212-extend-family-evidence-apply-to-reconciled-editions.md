# ADR 0212: Extend Family-Evidence Apply to Reconciled Editions

- Status: Accepted
- Date: 2026-09-12

## Context

ADR 0211 sealed a distinct, edition-bound two-family evidence publication
plan. ADR 0166 already provides proven exact-plan, ordered-prefix, recoverable
Apply mechanics for the older rolling-current plan. The mechanics are equally
appropriate for the edition plan, but the existing reader and operation check
intentionally reject that different source scope.

Copying the executor would create two mutation implementations whose recovery,
locking, inventory-drift, staging, and formal-reread behavior could diverge.
Weakening the current reader to accept both contracts implicitly would remove
the deliberate source-scope boundary.

## Decision

Keep two explicit public Apply entry points and share one private execution
mechanism:

- the existing current entry requires the current-plan reader and operation
  `publish_current_historical_family_evidence`;
- the new reconciled-edition entry requires the edition-plan reader and
  operation `publish_reconciled_eod_historical_family_evidence`.

Both entries require the exact plan file SHA-256, plan logical fingerprint,
family-set fingerprint, and approved Dell data root. The plan-specific reader
validates its contract and source bindings before the shared executor can take
the canonical lock. The shared executor preserves ADR 0166's EOD-first ordered
prefix, immutable targets, target and staging custody, network prohibition,
outside-target inventory drift check, atomic directory rename, formal reread,
and verify-then-complete semantics.

The administrator CLI adds an explicit `reconciled-eod` source-scope choice;
its default remains `current` for backward compatibility. Selecting a scope
cannot cause the other reader or operation to accept the plan.

This decision implements capability only. It does not execute the real plan,
grant Apply authority, publish family evidence, create final Historical
Coverage, authorize research, or change Production.

## Consequences

- There remains one mutation mechanism rather than two implementations.
- The old current plan and new edition plan cannot be confused at either the
  reader or operation boundary.
- Temporary-root tests prove edition-plan publication, current-entry refusal,
  formal reread, and completed zero-write recovery while the full inherited
  ADR 0166 fault suite continues to cover the shared mechanics.
- The focused family-evidence suite passed 32 tests and the complete API suite
  passed 2,533 tests with only the two existing dependency deprecation
  warnings.
- Real execution requires separate approval bound to the exact ADR 0211 plan
  SHA, logical fingerprint, and family-set fingerprint.
