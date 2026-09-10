# Strong-Leader Pullback Development Coverage Census V1

## Purpose

This contract implements ADR 0193's first outcome-blind gate. It determines
what historical evidence exists for the fixed latest-vintage reconstruction
interval before any strategy trigger, forward return, performance metric,
coverage threshold, cohort, or parameter is selected.

It is a development-admission diagnostic, not a backtest, readiness approval,
Historical Coverage publication, model result, or Candidate activation.

## Fixed scope

| Field | Value |
| --- | --- |
| Contract | `strong-leader-pullback-development-coverage-census/1.0` |
| Policy | `strong-leader-pullback-development-admission/1.0.0` |
| Calendar | XNYS, version retained in every report |
| Interval | 2025-06-23 through 2026-08-12 |
| Sessions | exactly 287 contiguous sessions |
| Universe | `provider_classified_common_shares_v1` |
| Membership | `provider-form-complete-base-point-in-time-v3` |
| Evidence tier | `reconstructed_point_in_time_latest_vintage` |
| As operated | false |
| Feature path | signal session plus its prior 20 XNYS sessions |

The interval, Universe, methodology, and evidence tier are contract constants.
A missing, duplicated, reordered, or out-of-scope session rejects the entire
report.

## Accepted evidence

Every Membership partition is formally reread from the completed owner-only
historical shadow. Its manifest and rows must prove:

- reconstructed, not as-operated, origin;
- identical complete evaluated bases for every included Universe;
- explicit included, excluded, or quarantined disposition for every stable
  `instrument_id`;
- exact session, methodology, source-fingerprint, and base-fingerprint
  binding; and
- direct lineage to the same session's formally reread canonical normalized
  Identity source custody.

An included Primary row counts as raw-feature-path complete only because this
specific Membership methodology already requires current and previous bars,
20 complete trailing sessions, minimum price/liquidity gates, and absence of
material EOD quality flags. This inference cannot be transferred to another
Membership methodology.

The canonical split-action and sparse split-adjustment publications are read
only as partial, outcome-reconciliation evidence. A clear split exposure is
counted only when an active split effective date lies inside the contemporaneous
21-session feature window and the window has a clear sparse adjustment row.
Later split events cannot mark an earlier window. A quarantined action,
unresolved possible impact, missing clear row for a known in-window action, or
source-coverage gap marks the path quarantined.

Sparse omission never proves a neutral factor. Canonical instrument lifecycle
and terminal-outcome evidence is unavailable. Consequently every included
path retains both `absent_row_neutrality_unproven` and
`instrument_lifecycle_unavailable`, and V1 requires
`all_required_evidence_complete_count = 0`.

## Output

The report retains:

- exact code revision, calculation time, calendar version, fixed policy scope,
  and report fingerprint;
- one evidence status and logical/physical binding for each of EOD, Identity,
  Membership, corporate actions, adjustment ledger, and lifecycle;
- per-session Primary disposition totals and feature-path coverage counts;
- per-stable-ID evaluated/absent/included/excluded/quarantined session counts,
  first/last boundaries, feature-path coverage counts, and reason counts; and
- cross-aggregates that must reconcile between the report, all sessions, and
  all instruments.

Reason counts include both original Membership decision reasons and explicit
coverage limitations. Tickers are not accepted as identity keys.

The output is one canonical JSON file in a new owner-only direct child of
`/tmp`. The writer uses exclusive creation, atomic rename, exact canonical-byte
and Pydantic reread, `0700` directory mode, and `0400` file mode. It cannot
overwrite an existing report or write `/data` or Production.

## Explicit non-authority

Every report fixes these fields to false or zero:

- strategy triggers, forward outcomes, and performance metrics;
- parameter selection and coverage-threshold selection;
- admitted-cohort selection;
- development, validation, holdout, and Candidate activation;
- external requests; and
- canonical-data and Production writes.

The next stage must inspect this census without opening outcomes and either
freeze one immutable missingness-based cohort/threshold decision or reject the
latest-vintage development path. This contract does not make that decision.

## Implementation

- typed contract:
  `tip_api.contracts.analytics.v1.candidate_strategy_development_coverage`;
- pure aggregation and validation:
  `tip_api.services.candidate_strategy_development_coverage`;
- owner-only report custody:
  `tip_api.persistence.development_coverage_census`; and
- network-disabled administrator entry point:
  `scripts/admin/census-strong-leader-pullback-development-coverage.sh`.
