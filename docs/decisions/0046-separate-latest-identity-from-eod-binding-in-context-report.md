# ADR 0046: Separate Latest Identity From EOD Binding in Context Report

## Status

Accepted

## Date

2026-08-27

## Context

After canonical Identity advanced to 2026-08-27 while EOD remained at
2026-08-26, the authoritative read-only context report still displayed
Identity 2026-08-26. The report had intentionally read the Identity snapshot
bound into the latest EOD session, but labeled it as the general `identity`
state. That was accurate for EOD provenance and inaccurate for the latest
canonical Identity boundary.

## Decision

Advance the report to `tip-current-context-report/1.1` and expose both facts:

- `identity` is the latest completed canonical Identity snapshot discovered
  from exact dated snapshot directories and validated through its manifest;
- `eod.bound_identity_snapshot_date` is the Identity snapshot bound into the
  latest completed EOD session; the existing `eod.identity_snapshot_date`
  remains as a compatibility alias; and
- `identity_eod_alignment` explicitly reports `aligned`,
  `identity_ahead_of_eod`, or `identity_behind_eod`, together with all three
  dates.

An EOD session whose bound Identity date differs from its own session is
rejected as inconsistent. The report remains credential-free, network-
prohibited, and read-only.

## Consequences

- Handoffs can see partial daily progress without mistaking EOD provenance for
  the latest Identity state.
- The current state is represented as Identity 2026-08-27 ahead of EOD
  2026-08-26, while the latest EOD remains correctly bound to Identity
  2026-08-26.
- Existing consumers of `eod.identity_snapshot_date` remain compatible.

## Alternatives Considered

### Keep Identity tied to latest EOD

Rejected because it hides a formally completed same-day Identity transition.

### Replace the EOD Identity field with latest Identity

Rejected because that would corrupt EOD provenance and imply the 2026-08-26
bars were joined to a later snapshot.

### Expose only a textual warning

Rejected because exact dates and a machine-readable alignment state are needed
for reliable automation and handoff.
