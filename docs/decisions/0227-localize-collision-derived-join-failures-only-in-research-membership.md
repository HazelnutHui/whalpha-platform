# ADR 0227: Localize Collision-Derived Join Failures Only in Research Membership

- Status: Accepted
- Date: 2026-09-13

## Context

The five-year research Membership continuation completed 913 of 950
source-available sessions under the unchanged V3 evidence policy. The remaining
37 sessions failed both `stable_identifier_collision_nonzero` and
`identity_join_ratio_below_gate`. They had no ambiguous mapping or canonical
business-key conflict. Their linkage ratios range from
0.9922589725545391 through 0.9988058275614998 and collision counts from 10
through 66.

The Membership path already treats stable-identifier collision as localizable:
every affected canonical stable ID is passed into the complete-base builder as
an explicit source quarantine. The builder emits two decisions for every
same-session Instrument Master ID, and any ID without usable provider form
evidence becomes `INVALID_INPUT` / quarantined. No affected security can be
silently included.

V3 nevertheless treats the ratio failure derived from those same collisions as
non-localizable and rejects the whole session. That duplicates the collision
control at a coarser level and creates a missing daily cross-section instead of
retaining complete decisions with explicit local quarantine.

The 0.999 provider-evidence threshold remains appropriate for current or
signal-eligible evidence. A general threshold reduction would hide ambiguity
and is rejected.

## Decision

Introduce research-only methodology
`provider-form-complete-base-localized-collision-v4`.

V4 may treat `identity_join_ratio_below_gate` as localizable only when all of
these conditions hold:

1. the complete quality-failure set is exactly
   `stable_identifier_collision_nonzero` plus
   `identity_join_ratio_below_gate`;
2. canonical mapped rows and collision rows are both nonzero;
3. ambiguous mappings and canonical business-key conflicts are zero;
4. the linkage denominator equals canonical mapped rows plus collision rows,
   proving that the ratio shortfall is entirely collision-derived;
5. all source categories reconcile exactly to the raw record count; and
6. at least one canonical stable ID has an explicit retained collision
   quarantine.

Every original quality flag remains in the Membership source lineage and
logical fingerprint. V4 changes only whether the derived ratio failure blocks
the whole research session; it does not convert a collided or missing-security-
evidence instrument into an eligible member.

Any other failure combination remains session-blocking. V3 remains immutable.
V4 writes only distinct missing dates under its own methodology directory. The
five-year census may union approved V3 and V4 research dates but must reject a
date present under both methods and must continue to report the whole family as
reconstructed latest-vintage evidence.

This exception is unavailable to provider Security Evidence publication,
current Identity, signal-eligible Membership, Candidate, Production, web
publication, validation, holdout, or performance.

## Consequences

- The 37 measured source-available gaps can be tested without weakening the
  numeric gate or changing 1,213 immutable V3 partitions.
- A complete research cross-section is preferable to whole-session absence
  when all uncertainty is explicit and instrument-local, but it remains
  `not_as_operated` and development-only.
- The two unavailable Identity source sessions, 2026-08-13 and 2026-08-19,
  remain absent and cannot be filled by this policy.
- The five-year database remains blocked by historical knowledge time,
  lifecycle/terminal outcomes, actions/adjustments, costs, and final Historical
  Coverage even if all 37 V4 candidates pass.

## Alternatives considered

### Lower the 0.999 threshold globally

Rejected because a numeric relaxation would affect unrelated ambiguity and
current/signal evidence and would not prove that missing joins were localized.

### Rewrite the V3 partitions under V4

Rejected because V3 is immutable, 1,213 sessions already passed its stricter
gate, and rewriting adds no research information.

### Leave all 37 sessions absent

Rejected because the observed failure is fully explained by an already
quarantined collision category. Whole-session absence loses otherwise explicit
cross-sectional decisions without adding safety.
