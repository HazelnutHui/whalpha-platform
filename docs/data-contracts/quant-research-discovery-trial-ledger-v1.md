# Quant Research Discovery Trial Ledger V1

## Purpose

This contract is the cumulative accounting boundary for outcome-reading factor
and factor-interaction research. It prevents a later discovery campaign from
forgetting failed attempts after Development outcomes have been seen.

Implementation:
`apps/api/src/tip_api/contracts/analytics/v1/quant_research_discovery_trial_ledger.py`.

## V1 frozen content

- ledger version: `whalpha.quant-research.discovery-trial-ledger/1.0.0`;
- one completed campaign: `whalpha.factor-discovery.price-volume-v1`;
- eight formal trials: five candidate Alpha and three risk guards;
- zero outcome-tested conditioner interactions;
- zero admitted candidate-Alpha factors;
- one retained risk guard: `rolling_maximum_drawdown_10s`;
- terminal campaign state: `closed_no_candidate_alpha`;
- logical fingerprint:
  `502834abe5bfc171f80206138b36c8bf973c9fcc84078592b8dc92ccd5bee368`.

Each trial binds the exact factor version and fingerprint, role, target,
related-factor group, primary horizon, Development access date, disposition,
and immutable result report identity. Runtime validation rejects removal,
reordering, relabeling, or identity drift even when a caller recomputes an
outer hash.

## Append-only rule

A new discovery campaign creates a new ledger version that carries every prior
campaign unchanged and appends all new formal trials before outcome access.
Formula variants and registered conditioner interactions are counted. A name
change does not reset research history.

Strong-Leader Pullback remains separately counted as a strategy-development
program. It is named as a prior contaminated outcome boundary but is not
misclassified as eight additional factor trials.

## Statistical meaning

Within-campaign multiplicity control does not make successive adaptive
campaigns globally independent. Development results select research inputs;
they are not a validated Alpha claim. The cumulative ledger must accompany a
future locked factor-model-expression lineage through Validation, Holdout,
reproduction, shadow review, and any separate Product activation decision.

## Authority boundary

This contract grants no new data access, outcome read, factor admission, Model
Construction, Strategy Expression, Validation, Holdout, Candidate,
publication, deployment, broker, or execution authority.

The immutable V1 content is carried forward unchanged by the
[V2 preregistration ledger](quant-research-discovery-trial-ledger-v2.md).
