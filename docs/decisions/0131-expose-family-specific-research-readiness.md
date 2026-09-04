# ADR 0131: Expose Family-Specific Research Readiness

## Status

Accepted.

## Date

2026-09-04.

## Context

Canonical Dell EOD and same-session Identity acquisition now covers 303
contiguous XNYS sessions. The existing strategy-readiness gate correctly
remains blocked until every required research family is transitively bound by
a Historical Coverage publication, but its all-or-nothing result does not show
the current physical progress of each family.

This creates two avoidable interpretation risks. Price depth may be mistaken
for backtest readiness, while the already acquired point-in-time EOD/Identity
foundation may be described as generally "missing". The historical Pilot
status prose also predates completion of the Pilot and 300-session acquisition.

## Decision

Advance the network-free authoritative current-context report to contract 1.3
and add a `research_readiness` section that:

- records the 252-session minimum and whether canonical price depth satisfies
  that narrow requirement;
- reports exact EOD and same-date Identity completion-marker coverage without
  promoting either family to published Historical Coverage evidence;
- inventories the fixed, provider-neutral research-family roots for source
  actions, canonical actions, daily membership, lifecycle, adjustments, and
  Historical Coverage evidence/final publications;
- distinguishes an absent root from observed partitions that still require a
  formal family reader and coverage publication;
- records costs/liquidity, availability/revision lineage, chronological
  evaluation, and holdout custody as separate supporting requirements; and
- emits explicit blocker codes while keeping development-review and
  performance-claim authority false.

Routine recovery continues to use the EOD completion index plus a full latest
partition inspection. An explicit full-history report still reconstructs all
EOD partitions. Identity coverage in the new section means exact completed
same-date manifests are present for the EOD session inventory; it does not
claim a full Parquet reread or research-ready family publication.

The report never treats directory presence or partition count as completion.
Any observed future research partition remains
`partitions_observed_not_coverage_validated` until the existing transitive
Historical Coverage reader validates the exact publication.

## Consequences

- A new task can see exactly which research inputs exist and which remain
  absent without rerunning a superseded Pilot review.
- The 303-session price acquisition is credited without weakening the
  point-in-time, action, lifecycle, adjustment, cost, or holdout gates.
- No new catalog, cache, database, persistent report, provider request, data
  write, research run, publication, deployment, or scheduler path is created.
- Historical storage documentation must label the Pilot and 300-session EOD /
  Identity acquisition as complete while preserving the still-missing
  research families.

## Alternatives Considered

### Reuse the historical Pilot baseline as the current readiness report

Rejected because it is an acquisition-era review that rebuilds deep evidence,
selects hypothetical preceding sessions, and evaluates permission gates that
do not describe current family implementation progress.

### Publish EOD and Identity family evidence immediately

Rejected because current-context reporting is read-only and publication is a
separate canonical transition.

### Treat 303 price sessions as sufficient to begin performance research

Rejected because that would introduce survivorship, action, terminal-outcome,
adjustment, cost, and evaluation leakage risks that the existing contracts
explicitly prohibit.
