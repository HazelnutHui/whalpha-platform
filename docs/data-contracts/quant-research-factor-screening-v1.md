# Quant Research Factor Screening V1

## Purpose

`quant-research-factor-screening-protocol/1.0` is the immutable,
before-outcomes development-screening contract for Factor Catalog V1. It
authorizes only the registered Development read and does not authorize
Validation, Holdout, model construction, a strategy, Candidate ranking, or
Production.

The immutable protocol logical fingerprint is
`222b14dd358f5d4e6e260c77226b11f3ac2130f8850f96abe5ae5d48a07a8a60`.

## Population

The cohort is the intersection of:

- the ADR 0275 complete 12-factor vector population;
- usable Development assignments in chronological plan
  `e793471617c35de7596aee27950e3f5ded0bcd51cf4370ac8b20742cb9b24515`;
  and
- the reconstructed latest-vintage Primary Membership evidence already bound
  to the qualification report.

It contains 106 signal sessions from 2025-07-22 through 2026-01-07 and 167,860
expected paths. One failed complete cross-section excludes the whole session.

## Formal screens

Five candidate-Alpha factors use 3-session SPY-relative return. Three risk
guards use 3-session maximum adverse excursion. All labels start at the next
session open. Horizons 1 and 5 measure decay only. Lower and upper terminal
endpoint worlds must agree for Alpha; incomplete excursion paths remain
excluded for risk guards.

Every session is the unit of inference. Factor and target values use
same-session average ranks. The protocol retains daily IC, partial IC against
the 20-session relative-return baseline, circular block inference,
chronological halves, bucket monotonicity, concentration, decay, and fixed-cost
diagnostics. Exact thresholds and the Holm families are frozen in ADR 0276 and
the typed protocol.

The four setup conditioners remain registered but outcome-unscreened. Any
shape, threshold, or interaction requires a new finite model-development
protocol.

## Selection and authority

At most two Alpha candidates and one risk guard, with at most one factor per
related group, can be forwarded to a later model protocol. A factor forwarded
by this screen is not validated Alpha. At least one Alpha survivor is required
before Model Construction may be proposed.

One report and one exact replay exhaust this version. The report must preserve
every pass, rejection, unavailable result, source and code fingerprint, and
explicit absence of historical classification neutralization. It may write
only immutable owner-private evidence outside canonical `/data` and has zero
network, canonical-data, publication, deployment, Candidate, broker, or order
authority.
