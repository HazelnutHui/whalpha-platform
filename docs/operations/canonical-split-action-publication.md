# Canonical Split Action Publication

This runbook publishes only the exact split-only fact set approved by ADR 0176.
It performs no provider request, raw EOD change, adjustment calculation,
analytics, Snapshot, bundle, deployment, or scheduler action.

## Preconditions

- run on `dell5820` as `hui` from a clean `main`;
- formally reread the canonical Corporate Action Source marker and the exact
  ADR 0175 split candidate;
- confirm the candidate date range, source fingerprint, 707/1 event admission
  split, 1,240 unresolved rows, and 43 possible-impact stable IDs;
- confirm no target, staging path, symlink, or unexplained `/data` drift; and
- never expose provider response bodies or credentials.

## Plan

Use `scripts/admin/plan-canonical-split-action-publication.sh` with the exact
data root, split-candidate root, new owner-only publication-candidate root, new
plan path, and UTC creation time. The command requires a clean revision and
prints only aggregate evidence.

Review the plan SHA-256, logical fingerprint, expected `/data` fingerprint,
content-addressed target, counts, bytes, and all false authority fields. Planning
writes only below `/tmp`.

## Apply

Use `scripts/admin/apply-canonical-split-action-publication.sh` with the exact
plan path, approved plan SHA-256, expected plan logical fingerprint, expected
whole-data fingerprint, and fixed data root. Apply is network-prohibited and
uses the shared Dell data lock.

Success must report exactly two published files, zero overwrite/delete, exact
outside-target pre-state, and a formal canonical reread. Run the same exact
Apply again as a zero-write recovery check; it must report
`verified_existing`.

## Fail closed and recovery

- Any source/candidate/hash/count/inventory mismatch stops before publication.
- An exact completed target is reused only after complete formal reread and
  outside-target reconciliation.
- A conflicting target or deterministic staging residue is not overwritten or
  guessed away. Inspect it against the exact plan before any separately
  authorized cleanup.
- Do not infer neutral adjustment factors from absent action rows.

## Postflight

Run the authoritative current-context report. It must show canonical
`split_only` custody while retaining `data_blocked`, incomplete Corporate
Action coverage, absent Adjustment Ledger, and false research/performance
authority. Confirm `/data` file/byte/fingerprint changes equal the exact two
artifacts and Production remains unchanged.
