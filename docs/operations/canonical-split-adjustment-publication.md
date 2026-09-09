# Canonical Split Adjustment Publication

This runbook publishes only the exact ADR 0177 candidate approved by ADR 0178.
It performs no provider request, EOD mutation, factor retuning, total-return
calculation, analytics, Snapshot, bundle, deployment, or scheduler action.

## Preconditions

- run on `dell5820` as `hui` from clean `main`;
- formally reread the exact owner-only candidate and its canonical split-action
  and EOD family evidence;
- confirm the basis, row counts, factor audit, quarantine counts, and all false
  authority fields against the dated candidate audit;
- confirm no target, staging path, symlink, or unexplained `/data` drift; and
- never expose provider response bodies or credentials.

## Plan

Use `scripts/admin/plan-canonical-split-adjustment-publication.sh` with the
fixed data root, exact candidate root, new owner-only plan path, and current UTC
plan time. The command requires a clean planner revision, fully rederives the
candidate from its bound sources, and prints aggregate evidence only.

Review the plan SHA-256, logical fingerprint, candidate and planner revisions,
expected `/data` fingerprint, content-addressed target, row counts, two-file
inventory change, bytes, and every false authority field. Planning writes only
the plan below `/tmp` and reuses the immutable candidate.

## Apply

Use `scripts/admin/apply-canonical-split-adjustment-publication.sh` with the
exact plan path, approved plan SHA-256, expected plan logical fingerprint,
expected whole-data fingerprint, and fixed data root. Apply is network-
prohibited and takes the shared Dell data lock.

Success must report exactly two published files, zero overwrite/delete, exact
outside-target pre-state, and a formal canonical reread. Run the same exact
Apply again as a zero-write recovery check; it must report
`verified_existing`.

## Fail closed and recovery

- Any source rederivation, candidate, plan, artifact, count, hash, or inventory
  mismatch stops publication.
- An exact completed target is reused only after full formal reread and
  outside-target reconciliation.
- A conflicting target or deterministic staging residue is not overwritten or
  guessed away. Inspect it against the exact plan before separately authorized
  cleanup.
- Do not infer factor one for an omitted row or use these factors for
  point-in-time signals.

## Postflight

Run the authoritative current-context report. Contract 1.9 must show
`canonical_sparse_split_only_outcome_reconciliation`, exact rows and
fingerprint, incomplete adjustment reconciliation, `data_blocked`, and false
Historical Coverage/research authority. Confirm the `/data` file, byte, and
fingerprint change equals the exact two artifacts and Production is unchanged.
