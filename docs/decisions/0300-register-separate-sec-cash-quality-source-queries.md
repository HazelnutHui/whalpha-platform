# ADR 0300: Register Separate SEC Cash-Quality Source Queries

## Status

Accepted

## Date

2026-09-17

## Context

ADR 0225 made `sec-issuer-fundamentals-first-set-v1` immutable. Its fingerprint
is bound into point-in-time selection, readiness censuses, and ADR 0299's
cash-earnings-quality source plan. Its duration-query type deliberately admits
only 330–400-day annual income-statement flows. It cannot represent quarterly
cumulative cash flow or net income without changing historical semantics and
invalidating those bindings.

ADR 0299 permits exact source-query registration as the first plan-only source
engineering stage, but does not authorize querying, occurrence selection, TTM
derivation, feature materialization, outcomes, or trials.

## Decision

Create the independent registry
`sec-cash-earnings-quality-exact-source-queries-v1`, bound to both the ADR 0299
plan fingerprint and the immutable first SEC registry fingerprint.

It registers exactly three issuer-grained, USD, `us-gaap` queries:

1. `Assets`, as instant facts at FY/Q1/Q2/Q3 fiscal boundaries;
2. `NetIncomeLoss`, as FY duration and Q1/Q2/Q3 cumulative fiscal-YTD
   durations; and
3. `NetCashProvidedByUsedInOperatingActivities`, on the same duration basis.

The admitted forms are 10-K/10-K/A for FY and 10-Q/10-Q/A for Q1/Q2/Q3.
Duration starts must equal the fiscal-year origin; instant facts must have no
start date. Period ends must equal the reported fiscal-period end. No concept,
namespace, currency, missing-value, or cross-security fallback is registered.

Availability begins at the first XNYS open strictly after SEC acceptance. A
clean amendment applies only from its own availability. Conflicts quarantine
rather than select a value. CFO and net income for the same cumulative endpoint
must use one clean accession. Opening and closing Assets are both required and
cannot be interpolated.

The registry is declarative source-query authority only. Every execution and
downstream authority flag remains false, including external requests,
occurrence selection, TTM derivation, feature materialization, outcomes,
Validation, Holdout, trials, Candidate use, and canonical or Production writes.

## Consequences

The historical first SEC registry and all consumers bound to its fingerprint
remain unchanged. The new registry expresses the exact raw inputs needed by
ADR 0299 without pretending that the queries have run or that coverage exists.
A separately reviewed later stage would be required to execute the registered
queries or select occurrences.

## Rejected alternative

Appending CFO and quarterly net-income semantics to
`sec-issuer-fundamentals-first-set-v1` was rejected because it would mutate an
accepted registry, change its fingerprint, broaden its duration type, and
silently invalidate historical contracts and census evidence.
