# ADR 0136: Bind Historical Identity Rebuild Profiles by Fingerprint

- Status: Accepted
- Date: 2026-09-04

## Context

ADR 0135 proved that the 279 retained Identity packages are covered exactly
once by two reconstruction profiles: 58 by `current_v1` and 221 by
`pre_etv_governance_v1`. The profile placement is not monotonic by session
date because the historical backfill crossed a code-policy change while
running in descending order. A date threshold, filesystem order, or retry
order therefore cannot safely choose the reconstruction rule.

The existing membership-shadow commands still use the current profile
implicitly. They cannot consume the 221 valid legacy-profile sources without
an explicit, reviewable binding, and allowing a free-form profile flag would
move the choice from evidence into operator judgment.

## Decision

Materialize an owner-only, immutable profile-map report below `/tmp` from the
two completed full-index census reports. The map builder must formally parse
both reports and fail closed unless:

- the first report is contract 1.0's implicit current profile or contract
  1.1's explicit `current_v1`, and the second is contract 1.1's explicit
  `pre_etv_governance_v1`;
- both reports cover the complete, identical canonical session index and the
  identical discovered-package inventory;
- canonical family fingerprints and package custody identifiers agree for
  every session;
- missing sessions are identical in both reports;
- every retained session is exact under one and only one profile, while the
  other profile differs only in Provider Identity and still matches Instrument
  Master and Resolver.

Each retained-session binding records the chosen profile, the package locator,
manifest and content fingerprints, the package observation time, all accepted
Identity-family fingerprints, and its own logical fingerprint. The map records
the physical SHA-256 of both source reports, profile counts, the 24 missing
sessions, and a logical fingerprint over the complete mapping.

Historical membership-shadow builders must receive a binding selected from a
formally reread profile map. They must revalidate the actual package locator,
package custody fingerprints, observation time, session, and accepted
Identity-family fingerprints before calculating membership. A command-line
profile override is not allowed. Single-session and bounded-batch output must
retain the selected profile and binding/map fingerprints in provenance.

Contract 1.0 census reports are recognized only as `current_v1` because that
contract predates selectable rebuild profiles and used the current builder
unconditionally. No other missing profile field may be inferred.

## Consequences

- Membership reconstruction can use all 279 retained packages without any
  session-date heuristic or manual profile choice.
- Moving a retained package changes its locator fingerprint and requires a new
  census and map. This is intentional; durable source custody remains a
  separate governed migration rather than an invisible path substitution.
- The 24 missing sessions remain unbound and cannot enter a batch.
- The map proves source-to-profile routing only. It does not create Universe
  Membership, Historical Coverage, research readiness, or Production data.
- All work remains network-disabled and `/tmp`-only; `/data` and OCI are
  unchanged.
