# Historical Corporate Action Source Repeat Diff V1

Contract: `historical-corporate-action-source-repeat-diff/1.0`.

This contract compares two complete observations of one Massive split or
dividend endpoint over the same inclusive range. It is temporary revision
evidence, not canonical Corporate Action or an Adjustment Ledger.

## Inputs and order

Both packages must pass the ADR 0169 formal reader and have identical provider,
action kind, start date, and end date. The repeat package must start strictly
after baseline completion. Every row must contain a unique nonempty provider
action ID; no ticker/date/amount heuristic may replace it.

## Comparison grain

Canonical JSON payload hashes are compared by provider action ID, independent
of page boundaries and row order:

- `unchanged`: the same ID and payload hash exist in both packages;
- `changed`: the same ID exists with different payload hashes;
- `added`: the ID exists only in the repeat package; and
- `removed`: the ID exists only in the baseline package.

Only non-unchanged records appear in `changes.json`. They retain the provider
action ID, before/after payload hashes, changed field names for same-ID
changes, and optional event-date/ticker locators. No raw provider payload is
copied from the formally retained source packages.

## Output and interpretation

The owner-only output contains exactly `diff.json` and `changes.json`, with
directory mode `0700` and file mode `0400`. The manifest binds both source
manifest hashes and logical fingerprints, page/row counts, order-independent
content fingerprints, every aggregate delta, the changes artifact, and its own
logical fingerprint. Completed output must pass formal reread.

The only permitted interpretation is `observed_snapshot_delta_only`.
Added/removed records are not automatically event additions/cancellations;
same-ID changes are not assigned provider revision numbers; and a no-change
result does not prove historical immutability or availability. Point-in-time
eligibility remains `outcome_reconciliation_only`.

The diff itself performs zero external requests, canonical writes, Adjustment
Ledger writes, analytics, publications, deployments, or scheduler changes.
