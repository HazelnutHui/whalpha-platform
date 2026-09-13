# Five-Year Corporate-Action Unresolved Census

This runbook builds and rereads the ADR 0218 owner-only diagnostic. It never
assigns a stable ID and performs no network request, `/data` write, canonical
event or Adjustment Ledger publication, research admission, analytics,
deployment, or scheduler change.

## Preconditions

- Run on Dell from clean `main` using the project Python wrapper.
- Bind the exact completed ADR 0217 persistent resolution shadow and its exact
  owner-only custody root.
- Create one separate owner-only mode-0700 census custody parent. The requested
  `build=...` target must be an absent direct child.
- Set a fixed UTC evaluation time and a bounded process count. Eight is the
  normal Dell setting; 32 is the hard maximum.

## Build and review

Invoke the unresolved-census CLI with `--resolution-shadow`,
`--resolution-shadow-custody-root`, `--output-root`,
`--output-custody-root`, `--evaluated-at`, `--process-count`, and `--execute`.
The CLI refuses a dirty repository and prints aggregate counts only.

Require every unresolved typed row in the bound resolution shadow to fall into
exactly one historical candidate class. Keep the shadow's unrepresentable rows
visible but outside this classification. Confirm the ticker and source-row
class denominators, the complete evidence-bound Resolver scan, candidate
relation count, owner-only modes, zero symlinks, zero partial residue, and
formal reread. Exact counts belong in the dated audit and current status, not
this runbook.

## Interpretation

- Zero candidates indicate that the current Identity history cannot connect
  the provider ticker at all.
- One candidate is an investigation lead, not an event-date assignment.
- Multiple candidates expose ticker reuse or identity ambiguity and require
  effective-dated lifecycle evidence.

Use the measured class distribution to choose a bounded next evidence source.
Do not update the Corporate Action shadow, canonical `/data`, Historical
Coverage, research panels, Candidate rankings, or Production from this census.
