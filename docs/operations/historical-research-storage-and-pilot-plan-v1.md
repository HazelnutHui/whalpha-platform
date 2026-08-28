# Historical Research Storage and Pilot Plan V1

## Status

Design complete; provider pilot not authorized.

This plan turns ADR 0051 into a bounded Dell physical direction. It does not
create a dataset, call a provider, inspect credentials, write `/data`, or grant
standing authorization.

## Read-only Dell capacity evidence

Measured on 2026-08-28 from the existing canonical root:

| Existing family | Sessions/snapshots | Bytes |
| --- | ---: | ---: |
| EOD Price Bars | 29 | 30,461,337 |
| Instrument Master | 30 | 27,172,419 |
| Provider Instrument Identity | 30 | 23,463,061 |
| Provider Ticker Resolver | 30 | 16,453,442 |
| Entire current market-data root | current state | 158,652,120 |

Observed EOD storage is approximately 1.05 MB/session. The three Identity
families together are approximately 2.24 MB/snapshot. Straight-line physical
estimates before new membership/action/lifecycle fields are:

| Target | EOD + three Identity families |
| --- | ---: |
| 252 sessions | approximately 0.83 GB |
| 504 sessions | approximately 1.66 GB |

The new schemas, revisions, manifests, membership decisions, actions, lineage,
and adjustments will increase this. Reserve 10 GiB for a 504-session canonical
foundation and another bounded 10 GiB for staging/audit work until a pilot
provides real measurements. This is small relative to the 700 GiB Dell data
volume; capacity is not the binding constraint.

## Proposed physical families

All paths remain under the approved Dell root and use explicit schema versions:

```text
market-data/
  provider-corporate-action-observation/
    provider_id=<provider>/schema_version=1/event_year=YYYY/
  corporate-actions/
    schema_version=1/event_year=YYYY/
  instrument-lifecycle/
    schema_version=1/as_of_date=YYYY-MM-DD/
  universe-membership/
    schema_version=1/methodology_version=<version>/session_date=YYYY-MM-DD/
  adjustment-ledger/
    schema_version=1/methodology_version=<version>/basis_session=YYYY-MM-DD/
  historical-coverage/
    schema_version=1/coverage_id=<immutable-id>/
```

This is a proposed layout for fixture implementation. Exact production paths
must be frozen in the pilot approval plan. Completed partitions are immutable,
symlinks are rejected, and conflicting reruns fail closed.

## Layer ownership

- Provider observations preserve normalized source facts and source revision;
  no raw response body is retained by default.
- Corporate Action and Lifecycle datasets resolve canonical stable IDs and
  preserve contradiction/quarantine state.
- Universe Membership is a WH Alpha methodology decision, never a provider
  membership claim.
- Adjustment Ledger is derived from canonical actions and independently
  reconciled; it does not mutate EOD Price Bars.
- Historical Coverage binds exact family fingerprints and reports readiness;
  it does not contain signal features or outcomes.

## Request model

The current Basic public limit is five calls/minute. Existing controlled
workflows use a conservative fixed 15-second serial interval. Provider calls
remain serial; Dell CPU parallelism applies only after immutable packages are
available offline.

For a history ending at the existing 2026-08-26 EOD session:

| Target | Missing sessions | Grouped Daily calls/time at 15s | Active Identity observed estimate (14 pages/session) | Identity existing ceiling (20 pages/session) |
| --- | ---: | ---: | ---: | ---: |
| 252 | 223 | 223 / 55m45s | 3,122 / 13h00m30s | 4,460 / 18h35m |
| 504 | 475 | 475 / 1h58m45s | 6,650 / 27h42m30s | 9,500 / 39h35m |

These are transport-duration estimates, not completion promises. They exclude
inactive ticker pages, corporate-action pagination, error stops, staging,
mapping, formal rereads, and quality review. Basic's exact two-year boundary
may not cover 504 sessions.

Per-ticker Custom Bars would require thousands of calls and is rejected as the
primary full-market backfill route. Ticker Events is experimental and should be
queried only for a small set of unresolved stable IDs, never the entire base.

## Implementation sequence before a real pilot

1. Add provider-neutral logical/Pydantic contracts for corporate-action source
   observations, lifecycle, adjustment ledger, and coverage manifests.
2. Refine Universe Membership V1 into an explicit included/excluded/
   quarantined physical decision with evaluated-base lineage.
3. Add PyArrow schemas, deterministic fingerprints, temporary-root writers,
   formal readers, and tamper/conflict tests.
4. Implement Massive response mapping against saved synthetic fixtures only.
5. Implement independent split/dividend factor fixtures and reverse-to-raw
   invariants.
6. Add a read-only pilot planner that calculates exact sessions, request
   ceilings, expected paths, and current inventory without credential access.
7. Re-review terms/account entitlement and obtain exact pilot authorization.

Steps 1–6 are repository work and can proceed without provider access or
`/data` writes. Step 7 is a separate external transition.

## Proposed first live pilot after gates clear

The first pilot should cover three historical sessions and representative
action/lifecycle cases discovered from the approved date range. Proposed hard
ceiling: 80 serial requests, zero automatic retry.

- at most 3 Grouped Daily requests;
- at most 60 active All Tickers pages using the existing 20-page/session cap;
- at most 6 inactive All Tickers pages across bounded anchor dates;
- at most 2 Splits pages and 4 Dividends pages at limit 5,000;
- at most 5 targeted Ticker Events requests;
- no Custom Bars unless one separately named repair case replaces another
  request inside the same ceiling.

Fetch writes only a hashed package below `/tmp`. Offline plan and validation
must complete before any separately approved canonical Apply.

## Pilot success gates

- exact request count and endpoint allowlist match the approved plan;
- every page completes without pagination loops or host drift;
- no response body, URL credential, header, or request ID enters Git/logs;
- Grouped Daily confirms unadjusted semantics and same-session Identity binding;
- stable-ID ambiguity and duplicate canonical business keys are zero;
- source observations preserve all required dates and revision fields;
- known split/dividend fixtures reconcile within exact Decimal rules;
- disappearing IDs resolve to governed evidence or explicit quarantine;
- raw OHLC files remain unchanged;
- formal reread reproduces logical and physical fingerprints;
- no current constituents are projected backward;
- no performance, total-return, alpha, or option-return claim is produced.

## Known pilot limitations

Even a successful pilot cannot prove complete merger, spinoff, successor, or
terminal-outcome coverage. It cannot activate performance evaluation. Those
gaps require an additional source or a formally accepted quarantine boundary.

## Current blockers

- Massive individual-use/derived-use and guest/friend compatibility is not
  cleared.
- Current account entitlement for historical/corporate-action endpoints is not
  live-verified.
- Merger/spinoff/successor and terminal-outcome source remains missing.
- Physical contracts, readers, and fixture validation do not yet exist.
