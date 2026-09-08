# ADR 0175: Bind split-action candidates to canonical source custody

- Status: Accepted
- Date: 2026-09-08

## Context

ADR 0172 proved split-ratio mechanics from an owner-only resolution shadow.
ADR 0174 subsequently published the exact normalized source observations and
their Identity binding under a formal marker. Continuing to depend on the old
`/tmp` shadow would preserve two competing operational inputs.

The first candidate also composed one TTSH same-date reciprocal pair to a net
factor of one. That arithmetic is reproducible, and the raw EOD series has no
corresponding 3000-fold discontinuity, but neither fact proves that two source
rows are one authoritative neutral event. A net factor of one must not bypass
an event-conflict gate.

A dense global ledger at the existing `instrument_id` / source-session / basis-
session grain would also repeat the same sparse event state across many rows.
More importantly, absent rows cannot yet be converted to neutral factors
because the current source marker proves only a bounded query snapshot, not
complete historical action availability or revision coverage.

## Decision

1. The next split-action candidate reads the canonical ADR 0174 source marker
   and transitively validates all referenced Parquet and Identity evidence. It
   does not accept the resolution-shadow path as an input.
2. Exact-event-date stable-ID resolution remains the only positive admission
   path. Historical ticker presence is only a conservative quarantine aid and
   never assigns an unresolved action.
3. A single active resolved source action at one stable-ID/date is a
   `clear_candidate`. Multiple actions on the same stable-ID/date remain
   `quarantined` even when their ratios compose to one.
4. The candidate remains a sparse event set. Canonical split actions will be
   published before an Adjustment Ledger, and a later ledger projection will
   expand only the exact admitted research panel and basis requested by a
   governed consumer. Missing events do not imply a neutral factor until an
   action-coverage boundary proves that conclusion.
5. Provider cumulative factors remain audit-only. Raw EOD remains immutable,
   total return remains unavailable, and all source rows remain
   `first_observed_only` / `outcome_reconciliation_only`.
6. The first implementation writes only one owner-only artifact below `/tmp`,
   prohibits network access, binds the clean implementation revision, and
   performs a formal reread. `/data` publication requires a separate exact
   Plan, review, Apply, recovery, and postflight boundary.

## Consequences

- The formal source marker becomes the one operational input; the earlier
  temporary candidate remains historical audit evidence only.
- The reciprocal TTSH pair is visible and mathematically reproducible without
  being silently admitted as a clear ledger factor.
- Storage remains proportional to real events and explicit quarantines rather
  than to a security/session Cartesian product.
- Research readiness remains blocked by canonical action publication, action
  coverage/revision evidence, the ledger, lifecycle, Membership, costs, and
  final Historical Coverage.

## Execution evidence

The first real run completed on clean Dell main
`c46cc3f4ee883ed7ef4c850ca146b6e3807f87bb`. It formally reread source
publication
`7b13691e22b7e815a773ed1d575ed580bbee897eb0dbf10c41e4e0862a95b1d1`
and produced 708 event groups from 709 resolved active split observations:
707 single-action clear candidates and one multiple-action quarantined group.
The 1,240 quarantined source rows still produce 43 possible-impact stable IDs.

The 602,491-byte candidate has SHA-256
`8ef0f95dce94a041be7e5c18d69bb959ae037e52e6f22d41c2401ab92f160c83`
and logical fingerprint
`026e9087ad4ef7ec891036cbe84ee4b3bde47cb1b1349fa858fc2e090b74f132`.
Its event and unresolved-impact projections exactly match the earlier
resolution-shadow candidate after excluding the new admission-status field.
The postflight report found unchanged `/data`, zero residue, absent canonical
actions/ledger, and unchanged `data_blocked` research status.

## Rejected alternatives

- **Keep reading the old resolution shadow:** leaves a temporary precursor in
  the active lineage after its exact bytes have formal canonical custody.
- **Treat a reciprocal pair as proven neutral:** arithmetic cancellation is
  not authoritative event reconciliation.
- **Write neutral factor one for every absent event:** bounded observation is
  not proof of complete action coverage.
- **Materialize every instrument/session combination now:** creates large
  repetitive custody without removing any research-readiness blocker.
