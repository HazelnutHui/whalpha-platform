# Historical Split Adjustment Candidate V1

Contract: `historical-split-adjustment-candidate/1.0`.

This is the owner-only, non-canonical split stage selected by ADR 0172. It
turns the resolved subset of one formally reread ADR 0170 shadow into grouped
event ratios and separately records stable IDs that may be affected by
unresolved split rows. It is not a canonical Corporate Action family, an
Adjustment Ledger, Historical Coverage, or a website payload.

## Inputs and basis

- the exact owner-only corporate-action resolution shadow and its manifest
  SHA-256/logical fingerprint;
- the shadow's published point-in-time Identity evidence;
- every evidence-bound historical Resolver used only to find conservative
  stable-ID candidates for unresolved provider tickers; and
- one explicit basis session equal to the resolution range end.

Historical ticker presence never resolves or assigns an action. It only marks
all plausible stable IDs as possible impacts that a later ledger must keep
non-clear.

## Split event math

Resolved `stock_split`, `reverse_split`, and `stock_dividend` rows are grouped
by stable `instrument_id` and effective date. Within each group, exact Decimal
ratio numerators and denominators are multiplied before one final 18-decimal
quantization:

```text
price multiplier  = product(split_from) / product(split_to)
volume multiplier = product(split_to) / product(split_from)
```

This preserves exact cancellation for reciprocal same-date events. A later
ledger for source session `s` and basis `B` may compose only groups satisfying
`s < effective_date <= B`. Provider cumulative historical factors are
audit-only and cannot enter this calculation.

## Output

The single `candidate.json` file contains:

- exact source and Identity evidence bindings;
- split source/resolved/unresolved counts;
- one ordered resolved event group per stable ID/date, including source action
  IDs, source revisions, raw ratios, composed price/volume multipliers, and an
  action-set fingerprint;
- one ordered quarantine candidate per plausibly affected stable ID, including
  only the unresolved source IDs/tickers/dates that caused the possible impact;
- counts for unresolved rows with no historical Identity presence and rows
  with ambiguous historical candidates; and
- explicit `total_return_adjustment_status=unavailable` and
  `ledger_projection_status=not_built` boundaries.

The directory is mode `0700`, the file is mode `0400`, and formal reread checks
the exact file set, model invariants, ordering, uniqueness, composed math,
aggregate counts, and logical fingerprint. Exact reruns are idempotent;
conflicting content fails closed.

## Prohibited interpretation

The candidate performs no network request, `/data` write, unresolved action
assignment, canonical publication, Adjustment Ledger write, analytics,
Snapshot, deployment, or scheduling. All source observations remain
`first_observed_only` and the candidate remains
`outcome_reconciliation_only`. Fixed-basis factors must not enter raw-dollar,
price-floor, volume, or liquidity features until their leakage semantics are
reviewed.

