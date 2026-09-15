# Quant Research Factor Screening V2

This owner-only Dell operation executes the single ADR 0281 Development screen
under the evidence separation accepted by ADR 0282. Run it only from a clean
canonical repository after the complete implementation is committed. It
disables network access and never writes canonical `/data` or Production.

```bash
scripts/admin/run-quant-research-factor-screening-v2.sh \
  --data-root /data/trading-intelligence-platform \
  --membership-shadow-root /absolute/reconstructed/membership \
  --development-census-root /absolute/development/census \
  --split-action-publication-root /absolute/canonical/split/actions \
  --split-adjustment-publication-root /absolute/canonical/split/adjustments \
  --historical-split-candidate-root /absolute/private/split-candidate/candidate=VERSION \
  --historical-split-candidate-custody-root /absolute/private/split-candidate \
  --qualification-root /absolute/private/factor-qualification-v2/report=VERSION \
  --qualification-custody-root /absolute/private/factor-qualification-v2 \
  --cohort-diagnostics-root /absolute/private/factor-diagnostics/report=VERSION \
  --cohort-diagnostics-custody-root /absolute/private/factor-diagnostics \
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
  --output-root /absolute/private/factor-screening-v2/report=VERSION \
  --output-custody-root /absolute/private/factor-screening-v2 \
  --created-at 2026-09-15T00:00:00Z \
  --implementation-revision EXACT_40_CHARACTER_GIT_COMMIT
```

The runner performs these operations in order:

1. validates the committed implementation identity, frozen protocol,
   preregistered ledger, custody roots, canonical sources, Membership, census,
   chronology, exact qualification report, and the exact V1 diagnostics that
   define the reused 106-session complete-factor cohort;
2. reconstructs all 287 qualification sessions with the qualification-bound
   private split extension and requires a complete in-memory qualification
   replay before accepting factor observations;
3. constructs the 106-session Development nuisance controls from canonical
   split evidence only;
4. reads only the registered Development outcome paths and constructs new
   factor-bound 1/3/5-session labels from canonical split evidence and governed
   terminal references only;
5. executes exactly four candidate-Alpha and two risk-guard trials; and
6. writes one canonical JSON report under owner-only `0700/0400` custody.

Acceptance requires:

- 106 signal sessions, 167,860 observations, 167,860 controls, and 503,580
  labels;
- exactly 30 ordered horizon/endpoint summaries and six decisions;
- distinct factor/control/label source fingerprints and exact observation,
  control, and label collection fingerprints, plus the V1 cohort-diagnostics
  logical, physical, and internally bound Membership fingerprints;
- no selected risk guard unless at least one candidate Alpha survives;
- one exact full replay with unchanged logical and physical fingerprints;
- zero network, prior Pullback-result, canonical-data, Candidate, publication,
  deployment, Validation, Holdout, broker, or Production writes; and
- zero staging residue.

The report may identify at most two Alpha factors and one risk guard for a
later, separately preregistered Model Construction review. It never authorizes
that phase by itself.
