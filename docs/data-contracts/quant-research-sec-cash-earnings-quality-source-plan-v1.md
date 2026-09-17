# SEC Cash-Earnings-Quality Source-Engineering Plan V1

## Purpose

`quant-research-sec-cash-earnings-quality-source-plan/1.0` freezes a future,
outcome-blind SEC source-engineering path while the U.S. successor intake
remains closed at `closed_source_blocked`. It is a plan, not a feature, source
result, coverage report, factor admission, or experiment.

## Exact source semantics

| Role | Exact concept | Shape | Forms / fiscal periods |
| --- | --- | --- | --- |
| Operating cash flow | `us-gaap:NetCashProvidedByUsedInOperatingActivities`, USD | duration | 10-K/10-K/A/10-Q/10-Q/A; FY/Q1/Q2/Q3 |
| Net income | `us-gaap:NetIncomeLoss`, USD | duration | 10-K/10-K/A/10-Q/10-Q/A; FY/Q1/Q2/Q3 |
| Total Assets | `us-gaap:Assets`, USD | instant | 10-K/10-K/A/10-Q/10-Q/A; FY/Q1/Q2/Q3 |

No concept, extension, namespace, IFRS, or currency fallback is permitted.
Unsupported evidence remains quarantined.

## TTM derivation

Discrete fiscal quarters are frozen as:

```text
Q1 = reported Q1 duration
Q2 = Q2 year-to-date - Q1 year-to-date
Q3 = Q3 year-to-date - Q2 year-to-date
Q4 = fiscal-year duration - Q3 year-to-date
```

TTM CFO and TTM net income sum the latest four consecutive discrete quarters
known by the signal cutoff. Average Assets is:

```text
(Assets at the opening TTM boundary + Assets at the closing TTM boundary) / 2
```

The planned measurement is:

```text
(TTM operating cash flow - TTM net income) / average Assets
```

Average Assets must be positive and finite. Missing or ambiguous fiscal chains
remain unavailable and are never filled.

## Knowledge time and amendments

- availability uses SEC acceptance time followed by the first XNYS open
  strictly after acceptance;
- only accessions available by the completed signal-session close may enter;
- a later clean amendment affects only cutoffs at or after its own availability;
- earlier snapshots are never rewritten by later original or amended filings;
- CFO and net income at a cumulative endpoint require the same clean
  accession; and
- value, availability, period-shape, fiscal-chain, or amendment-basis conflict
  quarantines the complete chain.

## Identity and applicability

Projection requires stable `instrument_id`, an admitted unique CIK link, and
exactly one admitted common security for that CIK/session. Ticker, name, CIK
broadcast, and multi-common-security projection are forbidden. Strict
`as_operated_next_open` and
`reconstructed_latest_vintage_development_only` evidence must be counted
separately and cannot be promoted.

An effective-dated point-in-time nonfinancial classification is mandatory.
Financial and unknown applicability are quarantined. Current classification
cannot be backfilled.

## Outcome-blind coverage hard stops

A separately authorized future census uses the exact 106 closed-campaign
Development dates and point-in-time Primary Membership without labels. It
stops if:

- the session index differs from 106;
- fewer than 96 sessions are complete;
- either 53-session chronological half has fewer than 48 complete sessions;
- any admitted complete session has fewer than 500 complete instruments;
- joint exact-formula availability is below 75%;
- point-in-time nonfinancial applicability is absent;
- strict and reconstructed tiers are combined; or
- only raw concept counts, rather than exact joint formula coverage, exist.

## Replay and authority

One owner-private coverage report and one independently produced,
byte-identical replay are required before any later source qualification may
be reviewed. The report must bind the closed intake, SEC source/query/filing
clock, identity, Membership, applicability, session-index, formula,
implementation, and physical/logical report identities.

The current plan authorizes no source execution, network request, feature,
coverage report, outcome read, Validation, Holdout, formal trial, model input,
Candidate use, canonical write, or Production write. ADR 0298 remains closed.

See [ADR 0299](../decisions/0299-freeze-sec-cash-earnings-quality-source-engineering-plan.md).
