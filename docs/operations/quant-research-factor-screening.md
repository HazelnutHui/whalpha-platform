# Quant Research Factor Screening

This owner-only Dell operation executes the single ADR 0276 Development
screen. It reads no prior strategy result and cannot access Validation or
Holdout. Run it only from a clean canonical repository after the implementation
commit is fixed.

```bash
scripts/admin/run-quant-research-factor-screening.sh \
  --data-root /data/trading-intelligence-platform \
  --membership-shadow-root /absolute/reconstructed/membership \
  --development-census-root /absolute/development/census \
  --split-action-publication-root /absolute/canonical/split/actions \
  --split-adjustment-publication-root /absolute/canonical/split/adjustments \
  --method-launch-root /absolute/private/method-launch/review=VERSION \
  --method-launch-custody-root /absolute/private/method-launch \
  --factor-diagnostics-root /absolute/private/factor-diagnostics/report=VERSION \
  --factor-diagnostics-custody-root /absolute/private/factor-diagnostics \
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
  --output-root /absolute/private/factor-screening/report=VERSION \
  --output-custody-root /absolute/private/factor-screening \
  --created-at 2026-09-15T00:00:00Z \
  --implementation-revision EXACT_40_CHARACTER_GIT_COMMIT
```

The runner disables network access, verifies the immutable qualification
report and source fingerprints, recalculates only the 106 complete Development
sessions, constructs new factor-bound 1/3/5-session labels, applies the frozen
eight-hypothesis statistics, and writes one canonical JSON report under
owner-only `0700/0400` custody outside `/data`.

Acceptance requires:

- 106 signal sessions, 167,860 observations, and 503,580 labels;
- exactly 39 ordered horizon/endpoint summaries and eight decisions;
- one exact full replay with unchanged logical and physical fingerprints;
- no prior Pullback outcome, network, canonical-data, Candidate, publication,
  deployment, Validation, Holdout, broker, or Production access; and
- zero staging residue.

The report may select at most two Alpha factors and one risk guard for a later
model-protocol review. It cannot itself authorize Model Construction.
