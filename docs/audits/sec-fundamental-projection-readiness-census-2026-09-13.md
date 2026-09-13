# SEC Fundamental Projection Readiness Census — 2026-09-13

## Scope

Build and formally verify the first cutoff-aware, outcome-free projection
coverage report for the four registered SEC issuer queries. The run used clean
main revision `9e8dedb54a372c2813bbe7bec06bac471da83195`, all 41,619,407 normalized
Company Facts occurrences, and the complete 1,255-session filer/security link
candidate from 2021-09-13 through 2026-09-11.

For each signal session the decision cutoff is the following XNYS session's
market open. A fact must have both source availability and filing-clock
eligibility by that cutoff. Projection is limited to a session-local CIK with
exactly one admitted common stock. The scan recomputes that common-stock
cardinality and does not mistake the link source's all-security CIK count for a
share-class decision.

The operation made no external request and wrote no canonical `/data`,
Membership, Candidate, feature, label, outcome, performance, publication,
deployment, or scheduler state. The private report contains aggregates only;
issuer values and security/fact rows were not retained.

## Structural projection result

The scan accounted for all 10,681,604 link row-sessions:

| Disposition | Row-sessions |
| --- | ---: |
| Common link not admitted | 5,977 |
| Multi-common-security CIK | 122,307 |
| Single common / strict as-operated next-open | 17,879 |
| Single common / reconstructed latest-vintage only | 6,104,572 |
| Link source custody missing | 19,879 |
| Not common stock | 4,410,990 |

The strict projection rows occur on only four sessions: 2026-09-04,
2026-09-08, 2026-09-09, and 2026-09-11. Reconstructed projection rows span
1,249 sessions. The two exact missing source sessions remain excluded.

This corrects the interpretation of the earlier timestamp-only scan. Its 11
sessions had source observation no later than the next open, but seven of those
sessions retained `outcome_reconciliation_only` source status. They are not
admissible `as_operated_next_open` evidence. Strict admission requires both a
timely timestamp and `eligible_at_source_observed_at` provenance.

## Query availability

The complete denominator is 24,489,804 query evaluations: every one of the
6,122,451 structurally projectable row-sessions evaluated against all four
registered queries.

| Query | Strict selected | Strict coverage | Reconstructed selected | Reconstructed coverage |
| --- | ---: | ---: | ---: | ---: |
| Assets | 15,518 / 17,879 | 86.79% | 5,186,997 / 6,104,572 | 84.97% |
| Fiscal-year net income/loss | 14,661 / 17,879 | 82.00% | 4,456,914 / 6,104,572 | 73.01% |
| Fiscal-year operating income/loss | 12,305 / 17,879 | 68.82% | 3,783,627 / 6,104,572 | 61.98% |
| Stockholders' equity | 14,993 / 17,879 | 83.86% | 4,976,189 / 6,104,572 | 81.52% |

Nonselection remains explicit as issuer query absent, issuer query not yet
available, or period ambiguity. Twelve strict and 1,834 reconstructed annual
net-income evaluations were quarantined for the registered
`same_period_end_multiple_starts` condition. No other query produced a
projected ambiguity under the current exact semantics.

Fact-age buckets were retained in the report. They are coverage diagnostics,
not freshness thresholds or feature authorization. Annual-flow facts naturally
concentrate in the 121–450 calendar-day buckets; that observation does not
authorize derived growth, value, or quality factors.

## Custody and verification

The completed owner-only package is:

`historical-source/sec-fundamental-projection-readiness-census/build=20260913-v1`

It contains one mode-`0400`, 1,836,393-byte `census.json` under a mode-`0700`
directory. File SHA-256 is
`ce7a30931ea71157d7ef4d116c4282eecc9085d7b9105ef312d39361838333f8`;
logical fingerprint is
`4e65cee8d4c1697dcd8e1b589b0a81297dc2722a1dfc5dc39f30b393f01a16bb`.
There is no sibling partial or residual process.

The eight-process build plus built-in transitive formal readback completed in
9 minutes 43.26 seconds, used 3,468.17 user CPU seconds at 598% aggregate CPU,
and reached 709,820 KiB maximum RSS. Formal readback reverified the exact query
source chain and all 1,255 link session files before returning success. A
second identical full reread was deliberately not run because it would repeat
the same immutable six-minute input verification without adding an independent
identity or boundary check.

The SEC-focused suite passed 260 tests before the real run. The complete API
suite then passed 2,622 tests with two unchanged dependency deprecation
warnings. The completed report also passed independent path, ownership, mode,
file-hash, package-member, process-residue, denominator, and authority-field
checks.

## Decision

The cutoff-aware issuer selector and exact security projection population are
now reproducible. The fundamental engineering lane has reached its bounded
exit criterion; no broad daily fact panel or security feature should be built.

The data gate did not pass for professional historical performance. Four strict
sessions cannot support five-year validation, sealed holdout, headline
performance, model activation, or Production Candidate use. Reconstructed
coverage remains useful only for labelled development sensitivity. The overall
five-year research foundation therefore remains `data_blocked` by historical
knowledge-time evidence and the separate Membership, lifecycle/terminal,
action/adjustment, cost, and final Historical Coverage gates.
