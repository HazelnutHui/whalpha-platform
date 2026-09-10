# Five-Year Research Foundation Census V1

## Purpose

This contract turns ADR 0196 into a deterministic, network-free coverage
diagnostic. It compares formally reread Dell evidence with the exact rolling
five-calendar-year XNYS target ending at the latest canonical EOD session.

It is not a backtest, Historical Coverage publication, data acquisition plan,
model-readiness approval, performance result, Candidate activation, or
Production publication.

## Fixed scope

| Field | Value |
| --- | --- |
| Contract | `five-year-research-foundation-census/1.0` |
| Scope | `us-equity-five-year-point-in-time-v1` |
| Calendar | XNYS; installed calendar version retained |
| End | latest formally indexed canonical EOD session |
| Anchor | exactly five calendar years before the end |
| Start | first XNYS session on or after the anchor |
| External requests | always zero |
| Canonical and Production writes | always zero |
| Performance authority | always false |

Warm-up and outcome-tail sessions belong to separately registered experiments.
They never silently replace or shorten this target.

## Family policy

The report contains exactly one record, in fixed order, for each family:

1. EOD Price Bar;
2. point-in-time Identity;
3. normalized point-in-time Identity source observation;
4. Universe Membership;
5. corporate-action source observation;
6. canonical corporate action;
7. instrument lifecycle;
8. adjustment ledger;
9. point-in-time classification;
10. point-in-time fundamentals;
11. Historical Coverage Evidence; and
12. Historical Coverage.

The price-strategy foundation requires EOD, Identity, Membership, canonical
actions, lifecycle, adjustments, and Historical Coverage. The complete data
program also requires point-in-time classification and fundamentals. Source
observations and coverage evidence remain visible supporting families without
being mistaken for canonical completion.

Session-grained families retain exact target, covered, and missing session
counts plus observed bounds. Non-contiguous coverage is never approximated by
the first or last `N` sessions. Sparse event families retain record and
quarantine counts only when the formal reader measured them; an unmeasured
count is `null`, not zero.

## Status semantics

- `absent`: no accepted family custody exists;
- `partial`: some evidence exists, but family completion is not established;
- `coverage_unpublished`: every target session is present, but formal family
  coverage has not been published;
- `complete`: the authoritative family reader explicitly reports research
  readiness.

Top-level status is `complete` only when every program-required family is
complete. An incomplete required family with measured quarantined records
yields `quarantined`; otherwise the result is `source_incomplete`.

Every report carries ordered blocker lists and a deterministic logical
fingerprint. Typed validation rejects missing/reordered families, altered
required-family policy, inconsistent session arithmetic, reversed dates,
malformed counts, or fingerprint drift.

## Implementation and operation

- contract: `tip_api.contracts.market_data.v1.five_year_research_foundation`;
- formal assessment: `tip_api.services.five_year_research_foundation_census`;
- network-disabled CLI:
  `scripts/admin/census-five-year-research-foundation.sh`.

Run against the application data root, not the parent mount:

```bash
scripts/admin/census-five-year-research-foundation.sh \
  --data-root /data/trading-intelligence-platform
```

The command emits canonical compact JSON to standard output. It does not
persist a report, contact a source, read credentials, or mutate `/data`.

