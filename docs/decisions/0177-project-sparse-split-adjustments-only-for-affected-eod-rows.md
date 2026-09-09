# ADR 0177: Project sparse split adjustments only for affected EOD rows

- Status: Accepted
- Date: 2026-09-09

## Context

ADR 0176 published 709 canonical split-only fact rows while explicitly leaving
full action coverage and neutral-factor inference false. The next step must
validate target-basis split transformations against real canonical EOD without
creating a dense ledger that silently treats every absent action as proven
neutral.

The canonical EOD family has 304 sessions and roughly three million rows. Only
622 stable IDs appear in active split facts, the one quarantined action group,
or the unresolved possible-impact set. A dense all-security/session projection
would mostly contain unsupported factor-one placeholders and would obscure the
remaining coverage gap.

## Decision

1. Build an immutable sparse projection at stable `instrument_id`, source
   session, basis session, methodology, and revision grain.
2. Fix the first basis to the last session of one exact canonical EOD family-
   evidence publication. Bind that evidence and the exact canonical split-
   action publication physically and logically.
3. Emit a clear row only when an observed EOD bar crosses one or more active
   canonical split events satisfying
   `source_session < effective_date <= basis_session`.
4. Calculate the price multiplier from the product of exact `from / to` ratios
   and the volume multiplier from the reciprocal `to / from` ratios. Quantize
   only after exact composition. Never use the provider cumulative factor.
5. Emit a quarantined row with no factor whenever the EOD path crosses the
   multiple-action canonical group or an unresolved possible-impact event.
   Quarantine takes precedence over otherwise clear actions.
6. Omit rows that cross neither active nor quarantine evidence. Omission means
   "outside this sparse affected-path projection," not a neutral factor of one.
7. Keep total return unavailable. All rows remain outcome-reconciliation only;
   fixed-basis adjusted values cannot enter point-in-time signal, raw-dollar,
   price-floor, volume, or liquidity features without a separate review.
8. The first implementation writes a publication-exact owner-only candidate
   below `/tmp`, prohibits network access, and formally rereads its Parquet and
   manifest. Canonical `/data` publication requires a separate exact Plan,
   Apply, recovery, and postflight boundary.

## Consequences

- Real split math can be reconciled on affected price paths without claiming
  complete action coverage.
- Quarantine is localized to the exact source-session paths it can affect.
- Storage is proportional to affected paths rather than the full EOD panel.
- The sparse ledger remains insufficient for research readiness until missing-
  row neutrality, broader actions/revisions, Membership, lifecycle, costs, and
  final Historical Coverage are proven.

## Read-only sizing evidence

The design census formally read ADR 0176 and the canonical 304-session EOD
evidence. All 622 selected stable IDs had at least one EOD row. It scanned
175,033 selected rows and projected 101,321 rows: 98,291 clear rows across 575
IDs and 3,030 quarantined rows across 31 IDs. The other selected rows cross no
known or possible split event and are intentionally omitted, not filled with
one.

## Rejected alternatives

- **Dense factor-one ledger:** current bounded source coverage cannot prove
  absent-event neutrality.
- **Only store one row per event:** consumers need an explicit source-session
  to basis transformation and cannot infer same-date inclusion rules safely.
- **Cancel the reciprocal quarantine group:** arithmetic cancellation is not
  event authority.
- **Drop possible-impact IDs:** converts unresolved identity into false clean
  history.
- **Mix dividend total return into this stage:** its currency, ordering, and
  special-distribution semantics remain unresolved.
