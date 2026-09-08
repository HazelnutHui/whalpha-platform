# ADR 0176: Publish canonical split actions before the Adjustment Ledger

- Status: Accepted
- Date: 2026-09-08

## Context

ADR 0174 placed the bounded provider observations in formal canonical source
custody, and ADR 0175 bound a sparse split candidate directly to that marker.
The next durable layer must separate provider-neutral action facts from the
derived factors later used to align prices and volumes to an explicit basis.

The current source scope is not complete Corporate Action coverage. It contains
only split and dividend endpoint observations from a bounded query snapshot,
has no defensible historical source-availability timestamp, and leaves 1,240
split observations unresolved. One resolved TTSH stable-ID/date group also has
two reciprocal provider rows. Although those ratios multiply to one, that does
not prove an authoritative neutral event.

## Decision

1. Publish a provider-neutral canonical fact layer for split-like actions only.
   Keep it separate from source observations and the Adjustment Ledger.
2. Preserve one canonical row for every resolved provider source action. Use a
   deterministic UUIDv5 of provider and source-action identity, stable
   `instrument_id`, effective date, exact Decimal ratio, source revision, and
   the source-action-set fingerprint.
3. Admit each of the 707 single-action groups as an active canonical fact.
   Preserve both rows in the one multiple-action group as quarantined facts;
   do not collapse, cancel, select, or delete them.
4. Keep all 1,240 unresolved split source observations outside canonical rows.
   Publish their 43 possible-impact stable IDs only as explicit quarantine
   evidence. Historical ticker presence never assigns an action.
5. Mark every row `first_observed_only` and
   `outcome_reconciliation_only`. The publication proves a split-only bounded
   source snapshot, not full action availability, point-in-time signal
   eligibility, neutral factors for absent rows, dividend total return, or
   research performance.
6. Store each publication as one content-addressed directory containing only
   `actions.parquet` and `manifest.json`. Publish the directory atomically with
   the shared Dell data lock, exact whole-inventory precondition, outside-target
   drift check, formal reread, and exact-existing recovery.
7. Keep source candidate construction and planning owner-only below `/tmp`.
   Applying to `/data` remains a distinct exact-plan operation. No network,
   overwrite, deletion, Adjustment Ledger, Historical Coverage, analytics,
   Snapshot, bundle, deployment, or scheduler authority is implied.

## Consequences

- A durable canonical event family can be referenced by later adjustment and
  Historical Coverage contracts without reusing a temporary shadow.
- Conflicting source rows remain visible rather than being hidden by arithmetic
  cancellation.
- Storage remains sparse and proportional to real action observations.
- Research readiness remains blocked until action-type/revision coverage,
  Adjustment Ledger reconciliation, lifecycle, Membership, costs, and final
  Historical Coverage are complete.

## Execution evidence

The first real Dell publication was planned from clean main
`cccbec4850736da90e24fc5277b4c8e61bffb3ab`. Plan SHA-256 is
`48dacad33ece6e855bf2f787086b763f6ce5cee6b0b877e419961e958ababe0c`
and plan logical fingerprint is
`d5b8633da94536817c1681fec192c580f154d695930017d7a5678c09ad1c0055`.

The locked Apply published 709 canonical rows: 707 active single-action rows
and two quarantined rows in one multiple-action group. It retained 1,240
unresolved source actions and 43 possible-impact stable IDs in manifest
quarantine evidence. Publication fingerprint is
`76f017a1547e20b997e40cd1e61497b71c749a94e88a8632a3898fe84c106218`.
Exactly two files / 118,592 bytes were added with no overwrite, deletion, or
outside-target inventory change. An exact second Apply was zero-write and
returned `verified_existing`.

## Rejected alternatives

- **Publish composed adjustment factors as canonical actions:** confuses facts
  with a basis-specific derived ledger.
- **Collapse the reciprocal TTSH rows:** creates unsupported event authority.
- **Assign unresolved rows from ticker history:** violates stable-ID evidence
  governance.
- **Write neutral rows for every security/session:** treats missing observation
  as proof of no event and creates unnecessary dense custody.
- **Overwrite one mutable latest directory:** removes immutable lineage and
  weakens recovery.
