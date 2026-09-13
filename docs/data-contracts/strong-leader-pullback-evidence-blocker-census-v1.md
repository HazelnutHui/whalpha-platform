# Strong-Leader Pullback Evidence Blocker Census V1

## Purpose

`strong-leader-pullback-evidence-blocker-census/1.0` intersects retained
Corporate Action and inactive-lifecycle evidence with the first experiment's
fixed reconstructed Primary paths. It prioritizes the next evidence and source
work without opening outcomes or selecting a better-covered cohort.

It is not Historical Coverage, development admission, a strategy result, or a
Candidate model.

## Fixed strategy scope

- signal interval: 2025-06-23 through 2026-08-12, exactly 287 XNYS sessions;
- Universe: `provider_classified_common_shares_v1`;
- Membership: `provider-form-complete-base-point-in-time-v3` at
  `reconstructed_point_in_time_latest_vintage`;
- included path denominator: the exact outcome-blind development census;
- feature action window: `t-19` through `t` inside the 21-session input panel;
- entry: next-session open;
- label-event windows: `t+1` through 1, 3, and 5 XNYS sessions; and
- outcome basis: underlying-stock price return, never option return or total
  return.

The action window starts at `t-19` because an action effective on the oldest
`t-20` bar has no earlier pre-event bar inside that feature panel. This rule
does not itself prove any adjustment factor or event neutrality.

## Action exposure rows

One row is one source-action/instrument relation that intersects at least one
included feature or label window. It preserves:

- source action ID, revision, ticker metadata, effective date, and action type;
- either exact event-date resolution or an explicitly unassigned history-wide
  candidate ID;
- one/multiple candidate classification and the exact resolution failure for
  unassigned relations;
- feature and 1/3/5-session path counts;
- retained inactive-source and FINRA leads for unresolved rows; and
- the semantic distinction between cash-dividend event context and a
  price/share adjustment requirement for split-like actions.

A `candidate_instrument_id` on an unassigned row is not a stable-ID assignment.
No unique or multiple candidate may be promoted through this contract.

## Lifecycle exposure rows

One row is one deduplicated inactive-source review-candidate window for a
stable ID that appeared in at least one included path. It preserves all source
anchors, canonical first/last observed dates, the provider delisting-date
candidate, total included paths, feature-span conflicts, and 1/3/5-session
label paths that cross the last observation or contain the delisting candidate.

These dates remain corroboration evidence. They are not canonical last-trade,
successor, consideration, or terminal-return facts.
A provider delisting-date candidate may equal the last canonical observation;
the contract preserves that equality rather than inventing a later date.

## Completeness and non-authority

The manifest binds the rejected admission decision, the original development
census, every reconstructed Membership partition, the Corporate Action
Resolution Shadow, unresolved-candidate census, residual-evidence census, and
inactive-lifecycle anchors. It also retains the global unresolved denominator.
Rows without a history candidate are explicitly not proven irrelevant merely
because they cannot be mapped to the declared cohort.

Strategy triggers, forward outcomes, performance metrics, parameter or cohort
selection, stable-ID assignment, canonical writes, Historical Coverage,
research admission, Candidate writes, publication, deployment, scheduler
changes, and external requests are all fixed to zero or false.

## Physical custody

The immutable owner-only package contains:

- `action-exposures.parquet`;
- `lifecycle-exposures.parquet`; and
- `manifest.json`.

The manifest binds physical SHA-256, byte size, record logical fingerprints,
source identities, aggregate reconciliation, implementation revision, and
calculation time. Directories are mode `0700`, files are mode `0400`, creation
is exclusive and atomic, and completed output is fully reread without reopening
outcomes.
