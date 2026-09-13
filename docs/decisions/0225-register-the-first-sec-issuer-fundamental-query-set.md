# ADR 0225: Register the First SEC Issuer Fundamental Query Set

- Status: Accepted
- Date: 2026-09-13

## Context

The normalized SEC Company Facts source contains many taxonomies, concepts,
units, forms, fiscal-period shapes, duplicate states, and later revisions. The
completed semantic census measures that population, while ADR 0224 prohibits
broadcasting filer facts to securities without an explicit projection class
and knowledge-time tier.

A broad concept fallback or a fact-by-security-by-session panel would hide
semantic differences before their coverage is understood. The first query set
therefore needs to be deliberately small, exact, and issuer-grained.

## Decision

Register four source queries under
`sec-issuer-fundamentals-first-set-v1`:

1. latest reported `us-gaap:Assets`, USD;
2. latest reported `us-gaap:StockholdersEquity`, USD;
3. fiscal-year `us-gaap:NetIncomeLoss`, USD; and
4. fiscal-year `us-gaap:OperatingIncomeLoss`, USD.

Balance-sheet queries require an instant fact with null start date and accept
10-K/10-K/A `FY` or 10-Q/10-Q/A `Q1`/`Q2`/`Q3`. Annual income-statement
queries require a duration fact, 330–400 inclusive calendar days, 10-K or
10-K/A, and `FY`.

Every query requires an admitted exact numeric occurrence, a non-null period
end, and a non-null source-available timestamp. A caller must supply the
historical decision cutoff. Source availability and period end may not follow
that cutoff. Exact duplicates within an accession may collapse; competing
values are quarantined rather than selected. Among clean facts, the eventual
reader selects the latest period end and then the latest available accession.
An amendment changes state only from its own availability time.

The economic grain remains issuer. Security projection may use only ADR
0224's `single_common_security_per_cik_v1` class and must preserve either
`as_operated_next_open` or
`reconstructed_latest_vintage_development_only`. Missing evidence remains
quarantined.

The registry is source-query authority only. It does not authorize a daily
panel, security feature, strategy outcome, performance result, Candidate, or
Production use.

## Deliberate exclusions

- Revenue is deferred because `RevenueFromContractWithCustomer...`,
  `Revenues`, and `SalesRevenueNet` are not interchangeable fallbacks.
- `StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest` is
  not substituted for `StockholdersEquity`.
- EPS, shares outstanding, market capitalization, and other per-share or
  class-sensitive facts require class-level evidence.
- IFRS facts, 20-F, 6-K, quarterly-flow derivation, trailing-twelve-month
  construction, and stub fiscal years require separate registered semantics.
- Missing operating income for an issuer or business type is coverage
  evidence, not permission to impute a value.

## Consequences

- The first coverage scan can measure exact joint semantics instead of relying
  on separate aggregate concept/unit/form counts.
- Coverage may be lower than a vendor-normalized fundamental feed; the missing
  population remains visible and can motivate a later explicit normalization
  decision.
- No query may be added or broadened merely because a backtest benefits. A
  material semantic change creates a new registry version.

## Rejected alternatives

### Combine synonymous concepts by first non-null value

Rejected because taxonomy concepts can differ economically and across filer
history.

### Start with quarterly income values

Rejected for the first set because 10-Q facts mix quarter-only and cumulative
year-to-date durations. Quarterly derivation needs a separate, tested rule.

### Materialize all facts for every security and session

Rejected because it is unnecessary for source readiness, expensive, and would
prematurely imply projection and feature authority.
