# Factor Catalog V2 Development Screening Audit — 2026-09-15

## Verdict

`closed_no_candidate_alpha`

Factor Catalog V2 completed its one frozen Development report and one complete
exact replay. None of the four candidate-Alpha hypotheses passed every frozen
gate. Both risk guards passed their own gates, but neither may become a model
input because the campaign admitted no candidate Alpha. Model Construction
therefore remains closed.

## Frozen boundary

- Protocol: `quant-research-factor-screening/2.0.0`
- Protocol fingerprint:
  `5441468ef8b392f555aac5a4e9cc8c6d50a9fb064349b6da342ccc2540dc193b`
- Implementation revision: `60f0038b5238567985c24a5769e1782638e9d619`
- Development signals: 106 sessions, 2025-07-22 through 2026-01-07
- Cohort: 167,860 factor observations and 167,860 nuisance controls
- Labels: 503,580 independently constructed 1/3/5-session rows
- Formal trial budget: four candidate-Alpha plus two risk-guard hypotheses
- Primary horizon: three sessions; one and five sessions are decay diagnostics
- Inference: deterministic five-session block bootstrap with 10,000
  replications and separate Holm families
- Costs: 0/10/25/50 basis points per side as diagnostics, not calibrated
  execution costs or portfolio returns

The setup conditioner and applicability input consumed no standalone outcome
trials. Validation and Holdout were not opened.

## Registered decisions

| Factor | Role | Robust effect | 90% lower bound | Holm p | Failed gates | Decision |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| `medium_term_relative_momentum_126s_skip5` | candidate Alpha | 0.0113 | -0.0256 | 1.0000 | 6 | rejected |
| `short_term_relative_reversal_5s` | candidate Alpha | 0.0096 | -0.0216 | 1.0000 | 4 | rejected |
| `intraday_relative_pressure_reversal_5s` | candidate Alpha | 0.0071 | -0.0188 | 1.0000 | 6 | rejected |
| `overnight_relative_persistence_5s` | candidate Alpha | -0.0162 | -0.0433 | 1.0000 | 10 | rejected |
| `single_index_residual_volatility_60s` | risk guard | 0.3438 | 0.3209 | 0.0002 | 0 | qualified risk evidence; not selected |
| `relative_downside_semideviation_60s` | risk guard | 0.3259 | 0.3041 | 0.0002 | 0 | qualified risk evidence; not selected |

The two risk results describe downside sensitivity. They are not stock-return
Alpha, a long/short portfolio, or an option-return prediction.

## Reproduction

- Report contract: `quant-research-factor-screening-report/2.0`
- Logical fingerprint:
  `caf88beb14434f60d4cf018dc6bc5c33b2c788b6504b1db93107faecdd313f42`
- Report SHA-256:
  `c900ce46f1685e140e3ef9f309bf0d1cda34b1838df7f4741678b9170d4f0733`
- Full replay result: `already_present` with identical logical and physical
  identities
- External requests: 0
- Canonical-data writes: 0
- Production writes: 0

The immutable owner-only report remains outside `/data`. The repository and
Product projection expose only reviewed aggregates and reproducibility
identities.

## Limits and next decision

This is Development-only, reconstructed latest-vintage evidence over 106
signal sessions. Historical classification is absent, Membership is not
as-operated, split-neutral absence is unproven, market-state diversity is not
proved, and cost scenarios are not observed execution estimates.

V2 closes without retuning. The next permitted research action is to design a
new, finite, outcome-unread Factor Discovery campaign. It should test whether
economically distinct factor behavior changes across point-in-time market
structure, rather than reopening V2 or preselecting a named strategy. Every
new outcome-reading trial must first be appended to a new cumulative ledger.

