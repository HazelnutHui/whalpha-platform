# SEC Fundamental Query Registry V1

## Purpose

`sec-fundamental-query-registry/1.0` freezes the first exact issuer-level SEC
Company Facts queries before query-specific coverage or value materialization.
It is a deterministic code-owned registry, not a feature table.

## Query contract

Each query records:

- stable query ID, display name, issuer economic grain, and statement role;
- exact namespace, concept, unit, and accepted numeric value kinds;
- instant or duration period shape and start/end-date requirements;
- allowed form/fiscal-period combinations;
- inclusive duration bounds where applicable;
- caller-supplied availability and period-end cutoff policies;
- duplicate, revision, conflict, and missing-value behavior;
- ADR 0224 projection class and evidence tiers; and
- explicit false authority for concept fallback.

The registry fixes these queries in lexicographic ID order:

| Query | Exact source meaning |
| --- | --- |
| `assets_latest_reported_v1` | `us-gaap:Assets`, USD instant, admitted 10-K/10-Q family fact |
| `net_income_loss_fiscal_year_v1` | `us-gaap:NetIncomeLoss`, USD, FY 10-K family duration of 330–400 days |
| `operating_income_loss_fiscal_year_v1` | `us-gaap:OperatingIncomeLoss`, USD, FY 10-K family duration of 330–400 days |
| `stockholders_equity_latest_reported_v1` | `us-gaap:StockholdersEquity`, USD instant, admitted 10-K/10-Q family fact |

The logical fingerprint binds every field and query order. Typed validation
rejects query membership, ordering, period-shape, evidence-tier, or fingerprint
drift.

## Authority boundary

The registry authorizes only exact source-query definition. Daily Cartesian
panel creation, security feature materialization, strategy outcomes, research
performance, Candidate use, and Production use are all false. A later census
must measure exact joint-filter and conflict coverage before any projection or
feature decision.

Implementation:
`tip_api.providers.sec.fundamental_query_registry`.
