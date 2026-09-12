# ADR 0207: Build the first reconciled EOD edition through the last fully proven session

- Status: Accepted
- Date: 2026-09-12

## Context

ADR 0204 requires one exact Grouped Daily source package and exact same-session
Identity source custody for every session in a complete immutable corrected
EOD edition. The rolling 2021-09-13 through 2026-09-11 source census now has a
price package for every one of its 1,255 sessions, but original Identity source
responses were not retained for 2026-08-13 and 2026-08-19.

Later Identity responses exist for both dates, but they are genuine later
provider revisions. An isolated diagnostic used each later response only as a
case-sensitive symbol projection and did not write canonical or candidate
data. Both reconstructed sessions passed price quality gates and had no
economic-value changes, but the 2026-08-13 reconstruction omitted one canonical
business key and the 2026-08-19 reconstruction omitted five. Treating those
responses as equivalent would therefore require weakening ADR 0204's explicit
no-removal rule and would conceal unknown lifecycle or revision effects.

The exact interval from 2021-09-13 through 2026-08-12 contains 1,234 contiguous
XNYS sessions before the first unresolved Identity-source date. It has exact
price and Identity source custody for every session: 947 retained-original
Grouped Daily packages and 287 visibly later-reacquired packages. It is large
enough to construct and validate the corrected price family without making the
two later evidence gaps disappear.

## Decision

Construct the first real Reconciled EOD Edition V1 candidate for exactly
2021-09-13 through 2026-08-12.

1. The edition contains all 1,234 ordered XNYS sessions in that interval. It
   may not skip an internal session or append a later session across either
   unresolved Identity-source date.
2. Every session remains subject to ADR 0204's exact price-source,
   same-session Identity-source, case-sensitive mapper, quality, and
   reconciliation gates. Later-reacquired price packages retain their later
   observation time and provenance class.
3. Any absent canonical business key, economic-value change, unexplained
   addition, source mismatch, or quality failure stops that session and
   prevents the interval completion marker.
4. The first 20 sessions, 2021-09-13 through 2021-10-08, remain declared
   outcome-free feature warm-up under ADR 0206. The earliest possible signal
   or performance session is 2021-10-11, and longer-lookback experiments start
   later.
5. The two later Identity-source gaps, their later responses, both price
   packages, and all diagnostic evidence remain retained and quarantined. They
   are not deleted, imputed, bridged, or relabeled as contemporaneous source.
6. Completing this edition proves only an immutable corrected EOD price-family
   candidate. It does not grant Historical Coverage, Membership or lifecycle
   completeness, action/adjustment completeness, backtesting, performance,
   model activation, Candidate, Production, publication, or deployment
   authority.
7. Extending the edition beyond 2026-08-12 requires separately proven exact
   Identity evidence or a new versioned edition decision. An assembling first
   edition is never silently widened after construction begins.

## Consequences

- Corrected-price construction can proceed across nearly five years without
  weakening evidence gates or blocking on two later source gaps.
- The first edition is intentionally shorter than the rolling canonical source
  window and must be described by its exact dates, not as a complete five-year
  performance history.
- Current Production remains on canonical EOD V1. Research still cannot open
  outcomes until the independent point-in-time Membership, lifecycle,
  corporate-action, adjustment, cost, chronology, and holdout gates are met.
- A later complete edition may supersede this candidate only through an
  explicit immutable interval and admission decision; it does not overwrite
  this edition.

## Rejected alternatives

- **Use the later Identity responses as exact substitutes:** rejected because
  the isolated rebuilds omitted one and five canonical business keys.
- **Relax the no-removal gate for only two dates:** rejected because the absent
  rows may encode lifecycle or provider-revision facts that are not proven.
- **Build one interval with two internal holes:** rejected because feature and
  label paths could silently cross discontinuous evidence.
- **Stop all corrected-price construction:** rejected because the preceding
  1,234-session interval is fully source-bound and independently useful for
  validating the price edition while other research families remain blocked.
