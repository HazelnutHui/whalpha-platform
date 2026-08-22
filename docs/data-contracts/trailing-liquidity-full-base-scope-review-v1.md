# Full-Base Trailing Liquidity Scope Review V1

## Superseding reviewed-form revision

The completed V1 target is immutable. A reviewed security-form correction therefore uses publication manifest `2.0` and revision `authoritative-security-form-v1` under `trailing-liquidity-full-base-scope-review-v2`; it never overwrites the V1 analysis-session path. One atomic revision target contains reviewed-form evidence, metrics, complete two-policy decisions, memberships, diffs, funnels, and a last-written manifest.

The security-form evidence contract is frozen and forbids extra fields. Its key is stable `instrument_id` plus effective interval, with authoritative source type/date/official URL, reviewer, reason, and UTC audit timestamps. The corrected decision ledger contains every CS/ADRC union instrument for both policies, so an ADR/ADS has an explicit `target_security_form` disposition in Primary and can still proceed through all quantitative gates in Secondary. Physical Decimal tuple and context-independent arithmetic contracts are unchanged.

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

### Exact Decimal physical representation

`previous_close` retains the canonical price representation `decimal128(38,10)`. `median_dollar_volume_proxy_20s` uses an exact Decimal-tuple Arrow struct:

- `sign`: Boolean;
- `coefficient`: unsigned big-endian binary integer;
- `exponent`: signed 32-bit Decimal exponent.

This is not a string representation and does not round or quantize. The formal reader reconstructs the logical Decimal before Pydantic validation. Canonical close and volume can each use precision 38/scale 10, so a daily product can require precision 76/scale 20. Adding the two middle products can require 77 coefficient digits, and exact division by two can require scale 21. Because Arrow Decimal256 has a maximum precision of 76, no fixed Arrow Decimal type covers the full theoretical contract. The exact tuple is bounded to precision 77, scale 21, and 56 integer digits; anything larger fails closed with field and stable-instrument context.

The full-base target has never completed. This physical contract is therefore finalized within schema V1 before its first publication; no existing completed schema is rewritten and Trailing Liquidity V1 remains unchanged and readable by its original reader.

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

The metric uses only the 20 completed XNYS sessions before the analysis session. Daily proxy is canonical close multiplied by canonical volume using Decimal. Exactly 20 observations are required; missing bars are not zero-filled or forward-filled. The even median is the exact mean of the tenth and eleventh ordered values. The analysis session never selects itself. The previous-session product is compared at full Decimal precision for the audit-only `previous_dollar_volume_below_threshold` Boolean; the product itself is not persisted and is not a candidate gate.

The logical arithmetic is implemented with signed integer coefficients and explicit scales, not Decimal multiplication/addition/division under the ambient Python context. Canonical scale-10 inputs produce a scale-20 product; an odd middle-coefficient sum is represented at scale 21. Decimal objects are reconstructed only at the contract boundary. Comparisons are exact, no float/round/quantize path exists, and values outside the physical tuple limits fail closed. The calculation version remains V1 because this change enforces the already-declared exact arithmetic and the 2026-08-19 results reconcile numerically; immutable published Trailing Liquidity V1 is not rewritten.

## Reviewed overrides

Effective intervals are half-open and keyed only by stable instrument ID. `exclude` and `quarantine` fail closed. `allow` never bypasses type, exchange, comparable-bar, price, history, or trailing-liquidity gates. Future, overlapping, conflicting, duplicate, orphan, and ticker-keyed decisions are rejected.

## Non-goals

This contract does not prove issuer domicile or structure, activate Primary/Secondary, change the Dashboard or API, generate a private Dashboard snapshot, or deploy OCI.
