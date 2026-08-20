# Full-Base Trailing Liquidity Scope Review V1

## Purpose

This shadow contract corrects the candidate-enumeration scope of Trailing Liquidity V1. It starts from the completed point-in-time canonical provider security evidence, not Legacy membership, Activation, a Dashboard snapshot, available tickers, or a one-session dollar-volume screen.

It remains `current_as_of_constituent_liquidity`, not a survivorship-free historical panel and not an activated production Universe.

## Policies

- `full_base_provider_classified_common_shares_v1`: every canonical `CS` evidence record.
- `full_base_provider_classified_common_shares_plus_adrs_v1`: every canonical `CS` or `ADRC` evidence record.

Primary must be a subset of Secondary. Secondary minus Primary may contain only `ADRC`.

## Components

The logical publication references five versioned Parquet components:

1. metric/status facts, one per Secondary-base stable `instrument_id`;
2. complete A/B decisions, one per `(policy_id, instrument_id)`;
3. selected membership rows;
4. current-production versus corrected set-diff rows;
5. sequential funnel rows.

All components use explicit Arrow schemas, deterministic business-key ordering, content fingerprints, physical Parquet SHA-256, same-filesystem staging, and formal reread. The logical manifest is renamed last.

## Sequential decision order

1. point-in-time provider evidence base;
2. target security form;
3. supported exchange;
4. current and previous canonical bars;
5. previous close at least USD 5;
6. complete 20-session history;
7. 20-session median dollar-volume proxy at least USD 20M;
8. material-outlier quarantine policy (no exclusion in this version; review signals remain overlapping);
9. reviewed eligibility overlay;
10. final shadow membership.

Every sequential row satisfies `input_count - excluded_count = remaining_count`, and each next input equals the preceding remaining count. Overlapping reason counts are reported separately.

## Liquidity semantics

The metric uses only the 20 completed XNYS sessions before the analysis session. Daily proxy is canonical close multiplied by canonical volume using Decimal. Exactly 20 observations are required; missing bars are not zero-filled or forward-filled. The even median is the exact mean of the tenth and eleventh ordered values. The analysis session never selects itself. A previous-session dollar-volume value is retained only as an audit field and is not a candidate gate.

## Reviewed overrides

Effective intervals are half-open and keyed only by stable instrument ID. `exclude` and `quarantine` fail closed. `allow` never bypasses type, exchange, comparable-bar, price, history, or trailing-liquidity gates. Future, overlapping, conflicting, duplicate, orphan, and ticker-keyed decisions are rejected.

## Non-goals

This contract does not prove issuer domicile or structure, activate Primary/Secondary, change the Dashboard or API, generate a private Dashboard snapshot, or deploy OCI.
