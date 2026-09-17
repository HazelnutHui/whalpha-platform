# SEC Cash-Earnings-Quality Query Registry V1

## Scope

`quant-research-sec-cash-quality-query-registry/1.0` is the declarative,
plan-only registry for ADR 0299. It registers exact Company Facts inputs but
does not run a query, choose an occurrence, derive TTM values, materialize a
feature, or read any research outcome.

## Registered queries

| Query | Concept | Shape | Forms and fiscal periods |
| --- | --- | --- | --- |
| Assets boundary | `us-gaap:Assets`, USD | instant; null start | 10-K/10-K/A FY; 10-Q/10-Q/A Q1/Q2/Q3 |
| Net income cumulative | `us-gaap:NetIncomeLoss`, USD | duration from fiscal-year origin | 10-K/10-K/A FY; 10-Q/10-Q/A Q1/Q2/Q3 |
| Operating cash flow cumulative | `us-gaap:NetCashProvidedByUsedInOperatingActivities`, USD | duration from fiscal-year origin | 10-K/10-K/A FY; 10-Q/10-Q/A Q1/Q2/Q3 |

For duration queries, FY requires a fiscal-year duration and Q1/Q2/Q3 require
cumulative fiscal-YTD durations. Period ends must be reported fiscal-period
ends. Extensions, IFRS, alternative concepts, currency conversion, and missing
value fills are not registered.

## Time, revision, and coherence

- Availability begins at the first XNYS open strictly after SEC acceptance.
- A later clean amendment affects only cutoffs from its own availability.
- Exact duplicates may collapse only within one accession.
- Competing values quarantine; no value is selected.
- CFO and net income for one cumulative endpoint require the same clean
  accession.
- Opening and closing Assets are both required; interpolation is forbidden.

## Binding and authority

The registry binds the ADR 0299 plan fingerprint and the unchanged
`sec-issuer-fundamentals-first-set-v1` fingerprint. Its own deterministic
logical fingerprint covers membership, semantics, bindings, and authority.

The registry authorizes no source execution, external request, occurrence
selection, TTM derivation, feature materialization, outcome access, Validation,
Holdout, trial, Candidate, canonical write, or Production use.

See [ADR 0300](../decisions/0300-register-separate-sec-cash-quality-source-queries.md).
