# SEC Filer/Security Projection Readiness — 2026-09-13

## Scope

This outcome-blind, network-free scan used only selected columns from the
completed five-year SEC filer/security candidate at logical fingerprint
`a71a6180f86228b7c80062c121da42e46a101d8f012e7f7a537147be0b609c71`.
It did not read Company Facts values, prices, strategy outcomes, or credentials
and wrote no data artifact.

## Security-form result

| Instrument / decision | Row-sessions |
| --- | ---: |
| Common stock / admitted unique CIK | 6,244,758 |
| Common stock / missing CIK | 5,977 |
| Common stock / missing source session | 9,129 |
| ETF / admitted unique CIK | 3,211,451 |
| ETF / missing CIK | 1,199,539 |
| ETF / missing source session | 10,750 |

Within admitted common stocks:

- 6,122,451 row-sessions belong to a session-local CIK with one common stock;
- 122,307 row-sessions belong to 59,440 CIK/session groups with multiple common
  stocks;
- the largest such group contains seven common stocks; and
- the conservative single-common-stock class covers about 98.0% of admitted
  common-stock row-sessions.

Counts are daily row/session relationships, not unique issuers or unique
securities. An instrument may appear under different states across history.

## Knowledge-time result

This scan found 11 sessions whose retained Identity source observation was no
later than the next XNYS open: 2026-08-21, 2026-08-24, 2026-08-26 through
2026-08-28, 2026-08-31, 2026-09-03 through 2026-09-04, 2026-09-08 through
2026-09-09, and 2026-09-11.

Correction after the complete projection contract was executed: this was a
timestamp-only count, not the final strict evidence-tier count. Seven of the
11 sessions retain `outcome_reconciliation_only` provenance. Requiring both a
timely timestamp and `eligible_at_source_observed_at` leaves four formal
`as_operated_next_open` sessions: 2026-09-04, 2026-09-08, 2026-09-09, and
2026-09-11. The completed aggregate census and authoritative interpretation
are recorded in
[SEC Fundamental Projection Readiness Census](sec-fundamental-projection-readiness-census-2026-09-13.md).

The remaining dated link reconstruction is not automatically historical
knowledge-time evidence. The scan therefore supports ADR 0224's separate
`as_operated_next_open` and
`reconstructed_latest_vintage_development_only` tiers.

## Runtime and boundary

The corrected session-streaming scan completed in 42.54 seconds at 182,808 KiB
peak resident memory and wrote zero bytes. One preceding exploratory scan used
an unnecessarily global in-memory CIK grouping and its output channel was not
retained; it completed without writing data and was immediately replaced by
the bounded session-local method. No third scan is required.

The result authorizes no security projection, feature, research admission,
performance claim, Candidate write, canonical Apply, publication, deployment,
or scheduler change.
