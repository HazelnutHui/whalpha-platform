# ADR 0220: Cross-Census Residual Corporate-Action Evidence Without Assignment

- Status: Accepted
- Date: 2026-09-13

## Context

The ADR 0219 Identity extension reduced the five-year unresolved Corporate
Action population to 112,943 typed rows / 13,780 tickers. ADR 0218 preserves
2,387 history-wide ticker-to-instrument candidate relations, but none proves
event-date ownership. Dell also retains two Massive inactive-listing anchors
and a complete official FINRA OTC Daily List range. Their possible connection
to the residual population must be measured before another source is acquired
or any identity is promoted.

A bounded read-only pre-census found three materially different evidence
shapes:

- 19 unresolved-row/candidate occurrences fall inside an actually observed canonical
  Instrument span;
- 2,386 occurrences fall only between the last canonical observation and an unverified
  provider delisting-date candidate;
- 1,449 occurrences conflict with observed boundaries, while remaining
  unresolved-row/candidate occurrences have no lifecycle evidence;
- FINRA has 20,679 exact date/symbol candidate matches and 10,261 exact
  numeric matches against unresolved rows; and
- inactive-provider ticker evidence touches 9,445 unresolved rows, including
  4,942 rows whose ticker has no candidate in the bound Identity history.

Combining these as if they had equal authority would be misleading. Provider
delisting dates do not prove last tradable dates, FINRA covers OTC events only,
and ticker agreement never proves stable identity.

## Decision

Create one owner-only residual-evidence cross-census with these rules:

1. Formally reread the exact Corporate Action Resolution Shadow, unresolved
   census, both inactive-lifecycle shadows, and sealed FINRA range before
   materialization.
2. Preserve one result row for every unresolved typed source action and bind
   the immutable input manifests and FINRA package chain.
3. Classify each history-wide candidate relation separately as inside the
   canonical observed span, in the unverified terminal gap, before first
   observation, after the delisting candidate, mixed across anchors, or
   lacking lifecycle evidence.
4. Record inactive-provider ticker/type and stable-identifier shape only as
   source-scope evidence. It never resolves an action through ticker.
5. Record FINRA exact-date/symbol occurrence counts, exact numeric occurrence
   counts, and explicit add/delete/symbol-change/bankruptcy flags. Dividend
   currency and gross/net/fee basis remain unverified.
6. Keep stable-ID assignment, canonical writes, adjustments, Historical
   Coverage, analytics, Candidate, publication, deployment, scheduler, and
   external-request counts literally zero.
7. Write one immutable Parquet result plus one manifest beneath an explicitly
   supplied direct child of owner-only Dell custody. Refuse overwrite and
   formally reread the output.

## Consequences

The project gains a reproducible investigation map without turning candidate
agreement into history. The census can prioritize official or paid evidence by
measured residual class and prevents the small observed-span subset from being
conflated with the much larger unverified terminal gap.

The output cannot become canonical Corporate Action or Lifecycle input. A
future promotion requires independent effective-dated security/lifecycle
evidence, explicit source-availability and revision semantics, and a separate
reviewed Apply decision.

## Acceptance boundary

Tests must prove all lifecycle states, FINRA candidate/numeric separation,
inactive-source classification, one-to-one row accounting, immutable custody,
tamper rejection, aggregate-only CLI output, and zero authority. The real run
must account for all 112,943 unresolved typed rows without network or `/data`
writes.
