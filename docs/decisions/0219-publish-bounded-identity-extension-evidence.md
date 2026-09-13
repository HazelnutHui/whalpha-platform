# ADR 0219: Publish Bounded Identity Extension Evidence

- Status: Accepted
- Date: 2026-09-13

## Context

The five-year corporate-action resolution shadow is bound to published
point-in-time Identity evidence through 2026-09-04. Canonical, formally
readable Instrument/Identity/Resolver snapshots also exist for 2026-09-08 and
2026-09-09. A read-only exact-date audit found that these two snapshots can
resolve 206 of the 343 corporate-action rows whose event dates fall after the
currently bound Identity range.

The existing current and reconciled-EOD family-evidence plans always publish
an EOD and Identity pair over identical sessions. Reusing either contract for
this tail would create redundant EOD evidence and would misstate the narrow
reason for extending Identity evidence.

## Decision

Add a distinct bounded Identity-only family-evidence plan and Apply entry with
these constraints:

1. The plan accepts one to 16 explicit, unique, ordered sessions. Every
   session must have a complete canonical Instrument/Identity/Resolver
   snapshot that passes the existing formal reader.
2. The only allowed family is `point_in_time_identity`. Its artifacts bind the
   snapshot completion manifest and all six partition manifest/payload files
   by physical hash.
3. The plan is deterministic, owner-controlled in direct `/tmp` custody,
   requires an absent immutable target, performs no network request and writes
   no canonical data.
4. Apply requires the exact plan SHA-256, logical fingerprint, family-set
   fingerprint, approved Dell data root, absent target and operation name. It
   reuses the existing lock, outside-inventory check, atomic target publication
   and formal reread mechanics.
5. The first operational scope is exactly 2026-09-08 and 2026-09-09, for the
   declared purpose `corporate_action_exact_date_resolution_support`.
6. The evidence remains a source-bound outcome-reconciliation input. It does
   not authorize Historical Coverage, research development, performance
   claims, Candidate changes, Production analytics or deployment.

## Consequences

- The 206 measured exact-date matches can be admitted to a later, new-version
  corporate-action resolution shadow without ticker fallback.
- Existing rolling-current and reconciled-EOD evidence objects remain
  immutable and unchanged.
- A new Identity extension is never inferred from whatever sessions happen to
  be latest; its session list is explicit and bounded.
- Unresolved rows outside these two sessions remain unresolved and continue to
  require lifecycle or external evidence.

## Acceptance boundary

Tests must prove exact family/session binding, source-drift refusal, absent-
target planning, exact Apply binding, atomic one-target publication, formal
reread, idempotent recovery, offline execution and compatibility with both
existing two-family plan types. The real plan must be reviewed by its exact
hash before any `/data` publication.
