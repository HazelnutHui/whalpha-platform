# Strong-Leader Pullback Reconstructed Development Dataset

This Dell-only operation materializes the admitted reconstructed-development
observations and independent 1/3/5-session labels. It is a versioned research
operation, not a daily product path.

Run from a clean canonical Dell repository. Bind every source to one exact
absolute root, use the checked-in implementation revision, and create the
owner-only output custody directory before execution:

```bash
scripts/admin/build-strong-leader-pullback-reconstructed-development-dataset.sh \
  --data-root /data/trading-intelligence-platform \
  --membership-shadow-root /absolute/reconstructed/membership \
  --development-census-root /absolute/development/census \
  --split-action-publication-root /absolute/canonical/split/actions \
  --split-adjustment-publication-root /absolute/canonical/split/adjustments \
  --method-launch-root /absolute/private/method-launch/review=VERSION \
  --method-launch-custody-root /absolute/private/method-launch \
  --diagnostics-root /absolute/private/diagnostics/report=VERSION \
  --diagnostics-custody-root /absolute/private/diagnostics \
  --admission-root /absolute/private/admission/review=VERSION \
  --admission-custody-root /absolute/private/admission \
  --terminal-boundary-root /absolute/private/terminal-boundary/census=VERSION \
  --terminal-boundary-custody-root /absolute/private/terminal-boundary \
  --terminal-gap-v3-root /absolute/private/terminal-gap-v3/census=VERSION \
  --terminal-gap-v3-custody-root /absolute/private/terminal-gap-v3 \
  --fixed-cash-root /absolute/private/fixed-cash/adjudication=VERSION \
  --fixed-cash-custody-root /absolute/private/fixed-cash \
  --listed-consideration-root /absolute/private/listed/adjudication=VERSION \
  --listed-consideration-custody-root /absolute/private/listed \
  --residual-listed-consideration-root /absolute/private/residual-listed/adjudication=VERSION \
  --residual-listed-consideration-custody-root /absolute/private/residual-listed \
  --terminal-population-listed-reference-root /absolute/private/population-listed/adjudication=VERSION \
  --terminal-population-listed-reference-custody-root /absolute/private/population-listed \
  --terminal-gap-v4-root /absolute/private/terminal-gap-v4/census=VERSION \
  --terminal-gap-v4-custody-root /absolute/private/terminal-gap-v4 \
  --final-terminal-root /absolute/private/final-terminal/review=VERSION \
  --final-terminal-custody-root /absolute/private/final-terminal \
  --output-root /absolute/private/development-dataset/dataset=VERSION \
  --output-custody-root /absolute/private/development-dataset \
  --created-at 2026-09-15T00:00:00Z \
  --implementation-revision EXACT_40_CHARACTER_GIT_COMMIT
```

The builder disables network access, rereads and reproduces the complete
outcome-blind diagnostic population, checks it against the admitted report,
and retains only usable chronological development assignments. It does not
construct validation or holdout labels.

Interpretation boundaries:

- entry is next-session open and exit is the registered horizon close;
- no next-session open is unexecutable and never replaced by signal close;
- exact and interval terminal references remain separate;
- MFE/MAE require a complete observed path;
- labels are raw underlying-stock price outcomes, not total returns or option
  returns; and
- transaction costs are not embedded in the immutable source labels.

Before acceptance, verify the exact manifest and logical fingerprints, row and
state counts, owner-only `0700/0400` custody, one manifest plus two Parquet
files, and zero symlink, staging, canonical-data, Candidate, publication,
deployment, and Production writes. Replaying the exact same version and
creation time must return `already_present`; changed source bindings must fail.
