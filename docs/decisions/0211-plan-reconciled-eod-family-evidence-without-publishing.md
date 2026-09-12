# ADR 0211: Plan reconciled EOD family evidence without publishing

- Status: Accepted
- Date: 2026-09-12

## Context

ADR 0210 produced exact, read-only EOD and Identity family-evidence candidates
for one named Reconciled EOD Edition. The existing publication plan is bound to
rolling `current` EOD/Identity semantics and already governs a separate
304-session publication. Reusing that contract name for the corrected edition
would make the source scope ambiguous, while copying the complete planning and
Apply implementation would create unnecessary parallel machinery.

## Decision

Add a backward-compatible edition-specific plan contract that reuses the
existing two-family item, target, custody, target-absence, ordering, and
recovery semantics. The new plan additionally binds:

- operation `publish_reconciled_eod_historical_family_evidence`;
- the exact source `edition_id`; and
- the exact source interval-manifest fingerprint.

Its EOD evidence must contain one artifact whose completion path and logical
fingerprint match those two source fields. EOD and Identity sessions must
remain identical and ordered. The old current-plan contract remains unchanged
and each read entry point rejects the other plan type.

Building the plan may perform the ADR 0210 formal source validation and write
one owner-readable immutable plan only in direct `/tmp` custody. Rereading the
plan verifies its exact SHA-256, canonical bytes, every bound source file, all
target absences, and absence of target staging residue.

This decision does not extend the existing Apply entry point. Canonical
publication support, execution authorization, Historical Coverage, research,
Production, and website changes remain separate decisions.

## Consequences

- One plan can bind the two exact unpublished candidates without confusing
  them with the legacy 304-session evidence.
- Existing safe planning helpers are shared rather than duplicated.
- The plan is reviewable but grants no write authority.
- A later Apply extension can accept the new contract only after explicitly
  checking its distinct operation and source bindings.
