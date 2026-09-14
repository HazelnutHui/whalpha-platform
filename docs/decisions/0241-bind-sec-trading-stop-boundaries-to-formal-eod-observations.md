# ADR 0241: Bind SEC Trading-Stop Boundaries to Formal EOD Observations

## Status

Accepted.

## Context

The first-strategy lifecycle sample has 61 point-in-time common-equity links,
typed transaction completion dates, merger/acquisition termination reasons,
primary common-share consideration, and source-party topology. Item 3.01 text
often states when an exchange was asked to stop trading, but that statement is
not automatically a legal delisting-effective date or proof of the last actual
trade. Form 25 filing and signature dates describe regulatory notice timing and
cannot substitute for either concept.

Canonical Dell EOD partitions can prove whether the stable `instrument_id` has
a retained daily bar on a particular exchange session. A missing bar may mean
the security stopped trading, but it may also reflect no trade or upstream
provider absence. SEC text and EOD presence therefore need separate, explicit
comparison states.

## Decision

For the exact 61 source-hash-bound cases, retain a finite reviewed timing
registry with three profiles: before open, after close, or unresolved. For the
53 cases whose Item 3.01 text states an exact stop boundary:

1. preserve the bounded source clause and its hash;
2. derive the expected final EOD session using the canonical exchange-session
   index and the stated before-open or after-close boundary;
3. formally reread the immediately relevant canonical EOD and Identity-bound
   sessions by stable `instrument_id`; and
4. classify agreement as `matched` and disagreement as `conflicting`.

Cases without an exact stop-time statement remain `unsupported`. A conflict is
never coerced into a match. The provider delist-date candidate remains
comparison metadata only.

This report supplies bounded SEC stop-boundary and last-EOD-observation
evidence. It does not establish the first tradable date, the legal effective
delisting date, a complete first/last-tradability field, a complete suspension/
delisting field, or a canonical lifecycle fact.

## Consequences

The 61-case lifecycle population gains a reproducible comparison between
source-stated stop timing and formal daily-bar presence while preserving
unsupported and conflicting cases. Because neither sampled tradability field
is complete, the eight-field coverage matrix does not increase.

Terminal payoff, successor or consideration-issuer identity, OTC continuation,
and final lifecycle admission remain later gates. The operation is network-
disabled, reads `/data` without modifying it, and writes only one immutable
owner-only private evidence report.
