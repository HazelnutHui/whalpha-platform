# ADR 0208: Admit only source-proven case-sensitive legacy removals

- Status: Accepted
- Date: 2026-09-12

## Context

The first real ADR 0207 candidate build completed 275 sessions before stopping
on five dates in October 2022. Every failed rebuild had accepted
case-sensitive additions and no economic-value change, but omitted one EOD V1
business key, so ADR 0204's original no-removal gate correctly prevented
publication.

The same stable instrument and source pattern explained all five omissions.
The retained Grouped Daily package contains the exact symbol `ALpA`, while EOD
V1 records `ALPA` because the legacy mapper upper-cased the provider symbol.
Same-session retained Identity source proves that `ALPA` is a common stock and
`ALpA` is an excluded preferred stock. The old normalized Resolver therefore
attached the preferred-stock bar to the common-stock instrument. The exact
mapper correctly emits neither that false common-stock bar nor an eligible
preferred-stock bar.

Keeping the old record would preserve a known false instrument attribution.
Allowing arbitrary removals would be worse: it could hide provider revisions,
lifecycle events, source gaps, or mapper regressions. The distinction must be
represented explicitly in the immutable contract.

## Decision

Version the Reconciled EOD session, interval, and Apply-plan manifests to 1.1
and distinguish expected from unexpected absent base records.

An absent EOD V1 business key is accepted as a source-proven legacy
case-sensitive misbinding only when every condition below is true:

1. the selected Grouped Daily package has retained-original provenance;
2. exactly one bar exists in its normalized-symbol group and its exact provider
   symbol contains a case distinction;
3. same-session retained Identity source proves a case-colliding symbol group
   and classifies that exact bar symbol as excluded;
4. the canonical normalized Resolver maps the upper-case symbol to the exact
   stable `instrument_id` on the absent EOD V1 key;
5. the old record's normalized source ID and timestamp reproduce that exact
   source row;
6. the old record's observation time equals the retained package observation
   time; and
7. open, high, low, close, volume, adjusted close, and neutral adjustment
   factors reproduce the source row and legacy record.

The session manifest records total, expected, and unexpected absence counts.
Only unexpected absences block the diff, while economic changes, unexpected
additions, and unexpected retained-source provenance changes remain blocking.
A distinct `accepted_case_sensitive_reconciliation` disposition identifies a
session containing at least one proven removal. Interval and Apply-plan
manifests aggregate accepted absence counts rather than reporting only
additions.

Later-reacquired price packages are never eligible for this removal exception;
they lack the exact original price observation required by condition 1. A
later source with any absent base key remains quarantined.

The stopped 1.0 candidate has no interval completion marker and remains
ineligible execution evidence. It is not mixed with 1.1 partitions. A new
edition ID, clean implementation revision, fixed creation time, and empty
candidate root are required for the next complete build.

## Consequences

- The corrected edition can remove a bar proven to belong to an excluded
  case-distinct security instead of preserving a false common-stock price.
- A generic missing row still cannot pass. The proof depends on exact retained
  source custody, stable identity, security-form classification, source-row
  binding, and economic reproduction.
- Addition and removal totals remain visible at the session, interval, build,
  and Apply-plan boundaries.
- Canonical EOD V1 remains unchanged and reproducible. This decision changes
  only the new corrected edition candidate contract and grants no research,
  performance, `/data` Apply, Production, publication, or deployment authority.

## Supersession scope

This decision narrows ADR 0204's no-removal rule only for the seven-condition
source-proven legacy misbinding class above. ADR 0204 remains authoritative for
all unexplained absences and economic-value changes. ADR 0203 remains the exact
provider-symbol mapping authority.

## Rejected alternatives

- **Keep the false EOD V1 common-stock bar:** rejected because retained source
  proves that the traded row belongs to an excluded case-distinct preferred
  stock.
- **Accept every absence when additions are present:** rejected because an
  unrelated source loss could be hidden by a valid case-sensitive addition.
- **Use later-reacquired packages for the same exception:** rejected because a
  later provider revision cannot prove the original price observation.
- **Patch only the five dates:** rejected because evidence conditions, not
  hard-coded dates or tickers, must govern future reproducible reconstruction.
