# ADR 0174: Publish bounded corporate-action source observations before canonical events

- Status: Accepted
- Date: 2026-09-08

## Context

ADRs 0169–0172 produced two complete same-scope Massive split/dividend
observations, a zero-delta repeat comparison, exact-event-date stable-ID
resolution, and a split-adjustment candidate. The resolved output is still an
owner-only `/tmp` shadow. A derived Adjustment Ledger must not depend on a
temporary tree, but the available evidence also does not justify calling the
rows complete canonical Corporate Actions or historical point-in-time facts.

The existing provider-neutral Corporate Action Source Observation 1.1
contract and Parquet repository already preserve every source row, its local
observation revision, resolution disposition, action fields, observation
time, and quarantine reasons. Rebuilding another nearly identical data family
would add complexity without adding authority.

## Decision

Publish the exact, formally reread source-observation shadow as a bounded
canonical **source-observation** dataset, not as canonical Corporate Actions.

1. Publish both immutable event-year partitions below
   `market-data/provider-corporate-action-observation/` and publish a separate
   marker-last source-coverage record below
   `market-data/provider-corporate-action-observation-publications/`.
2. The publication marker binds the two complete baseline source packages,
   both later repeat-diff reports, the exact Identity evidence, the resolution
   shadow, every target partition byte, aggregate resolution/quarantine
   counts, and the inclusive 2025-06-23 through 2026-09-04 query scope.
3. Coverage means only that the two named provider endpoints completed natural
   pagination for the exact range as observed. It is not a claim that the
   provider exposes every corporate-action type, that old provider revisions
   are reconstructable, or that absence of a row proves no action outside the
   declared query scope.
4. Preserve `first_observed_only`, `local_observation_baseline_only`, and
   `outcome_reconciliation_only`. The published data is not signal eligible
   and does not authorize performance claims.
5. Require an immutable no-write plan that formally rereads all temporary
   inputs, binds the full current `/data` inventory, verifies absent targets,
   and records exact source/target hashes and byte counts.
6. Apply under the existing Dell data lock, with network disabled, physical
   partitions first, publication marker last, atomic directory renames,
   outside-target drift detection, exact recovery states, and a separate
   zero-write formal postflight.
7. Keep unresolved observations quarantined. No current/nearest ticker, name,
   Universe, or heuristic fallback may promote an action.
8. A later canonical Corporate Action adapter and family-level Historical
   Coverage publication remain separate decisions. The split Adjustment
   Ledger may consume only the published source-observation partitions plus
   explicit unresolved-impact quarantine; it may not infer general
   corporate-action completeness.

## Consequences

- The adjustment pipeline gains durable, reproducible source facts without
  overstating their semantic authority.
- The 28,043 unresolved rows remain visible and auditable instead of being
  silently dropped.
- The same rows are not duplicated into an invented canonical-event schema.
- Research readiness remains blocked on canonical action/lifecycle scope,
  Membership, costs, complete adjustments, and sealed evaluation.
- Temporary raw source packages and repeat observations remain acquisition
  evidence; the durable normalized observations and publication marker become
  the operational source boundary.

## Rejected alternatives

- **Build the Adjustment Ledger directly from `/tmp`:** makes a canonical
  derivative depend on an ephemeral source.
- **Promote only resolved rows:** hides unresolved exposure and can create
  false neutral factors.
- **Call the snapshot canonical Corporate Actions:** invents provider revision
  history and overstates point-in-time availability and action-type coverage.
- **Retain a second permanent copy of all sanitized provider pages:** adds
  roughly 24 MB of duplicate private payload custody without improving the
  normalized operational contract.

