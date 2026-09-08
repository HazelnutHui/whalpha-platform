# Corporate Action Source Publication V1

Contracts:

- `corporate-action-source-publication/1.0`
- `corporate-action-source-apply-plan/1.0`

## Purpose

This boundary promotes one exact, bounded provider corporate-action
source-observation snapshot from owner-only temporary custody into canonical
Dell storage. It does not promote the rows to canonical Corporate Actions and
does not make them signal eligible.

## Published facts

The physical family is Corporate Action Source Observation 1.1, partitioned
by provider and effective-event year. Every source row is preserved. Exact
event-date Identity resolution may attach a stable `instrument_id`; unresolved
rows remain explicitly quarantined with no nearest/current/name/Universe
fallback.

The marker-last publication binds:

- the exact inclusive query range and provider;
- split and dividend baseline source-package identities;
- later same-scope repeat-package and repeat-diff identities;
- zero changed, added, removed, or pagination-shape deltas;
- point-in-time Identity evidence and the resolution-shadow identity;
- every target manifest and Parquet hash, byte count, logical fingerprint,
  event year, and row count;
- resolved and quarantined totals; and
- the clean repository revision that produced the plan.

## Semantics

`complete_as_observed` means natural pagination completed for the named split
and dividend endpoints over the exact range at the observation times. It does
not prove:

- historical provider revision order;
- that an old event was knowable at its represented session;
- complete merger, symbol-change, spinoff, delisting, or lifecycle coverage;
- that a missing provider row proves no action outside the declared scope; or
- canonical Corporate Action or Historical Coverage readiness.

The fixed temporal labels are:

- source revision: `local_observation_baseline_only`;
- repeat stability: `short_interval_zero_delta_only`; and
- point-in-time eligibility: `outcome_reconciliation_only`.

## Plan and Apply

The no-write plan formally rereads the resolution shadow, both repeat diffs,
and canonical Identity evidence; binds all candidate and target bytes; binds
the complete current `/data` inventory; and requires every target absent.

Apply is network-prohibited and uses the shared Dell data lock. It publishes
immutable event-year partitions first and the publication marker last through
atomic directory renames. Recovery accepts only an exact completed physical
prefix. Outside-target inventory must remain unchanged, and a completed result
must pass the independent canonical reader.

The plan itself never authorizes Apply, canonical Corporate Actions, an
Adjustment Ledger, final Historical Coverage, or performance claims.

