# ADR 0144: Consume Canonical Identity Source for Membership Shadows

## Status

Accepted.

## Date

2026-09-05.

## Context

The historical Membership shadow accepted by ADRs 0132 and 0133 still required
an explicit retained package below `/tmp` and an external Identity rebuild
profile map. ADRs 0137 through 0143 subsequently normalized 301 exact source
packages into immutable canonical source-observation partitions on the Dell
workstation. Continuing to make the primary shadow consumer depend on temporary
package custody would leave an unnecessary second operational source path and
make restart, batching, and provenance review harder.

The two non-equivalent provider revisions for 2026-08-13 and 2026-08-19 remain
intentionally absent. Canonical source custody is outcome-reconciliation
evidence observed after the represented session; it does not establish
historical knowledge-time availability or authorize research performance
claims.

## Decision

- Add a canonical-source Membership shadow path that formally rereads the
  normalized source partition, its manifest, Parquet hash, schema, row count,
  content fingerprint, row ordering, source observation time, and accepted
  Identity-family binding before calculation.
- Rebuild the accepted same-session Instrument Master, provider Identity, and
  ticker Resolver from the normalized rows under the profile stored in the
  canonical manifest. All three fingerprints must match; no date inference or
  operator-selected profile is permitted.
- Reuse the existing complete-base decision implementation after source
  validation. The retained-package V2 path remains available only for
  compatibility and equivalence review.
- Version canonical-source outputs as
  `provider-form-complete-base-point-in-time-v3` and add the canonical source
  custody logical fingerprint to each output's source lineage. Package hashes
  retained by the canonical manifest remain in the lineage as well.
- Keep batches bounded to one through five adjacent XNYS sessions, share the
  formal EOD panel and provider type catalog, write only below `/tmp`, and
  formally reread every successful output.
- Preserve the existing fail-closed provider-evidence gates. Localizable
  mapping conflicts remain quarantined, while a non-localizable gate such as
  `identity_join_ratio_below_gate` blocks that session and is now reported by
  its exact code.
- Declare `pytz` as an API runtime dependency. PyArrow's UTC timestamp
  conversion otherwise performs repeated unsuccessful optional-module lookups
  for each converted row in this environment; loading the supported timezone
  package once removes that runtime waste without weakening formal reads.

## Consequences

- A real 2026-09-03 V3 shadow produced 19,958 rows over 9,979 stable IDs. After
  excluding only the intentionally changed methodology, source-lineage, and
  execution timestamp fields, every V3 Membership decision matched the
  retained-package V2 output.
- The same V3 logical fingerprint and Parquet SHA-256 repeated before and after
  the timezone dependency fix. Measured single-session time fell from about
  100 seconds in the initial V3 run to 59.53 seconds. The five-session boundary
  run completed in 135.53 seconds versus 195.04 seconds for the earlier V2
  baseline, with no network request or canonical write.
- The canonical source recovered 2026-08-28, which the earlier unprofiled raw
  batch had rejected. The 2026-08-31 source exactly rebuilds Identity but still
  fails the unchanged global evidence gate: ten stable-identifier collisions
  yield a 0.998996689 linkage ratio, just below 0.999. This is an explicit
  policy result, not source corruption.
- The V3 path removes `/tmp` packages and an external profile map from normal
  Membership shadow execution. It does not delete the old audit path, fill the
  two missing sources, publish Membership into `/data`, change active
  Universes, or alter Production.

## Alternatives Considered

### Continue using retained `/tmp` packages

Rejected as the primary path because exact normalized source custody is now
canonical for 301 sessions and already carries the accepted profile and source
lineage. Temporary packages remain useful only for audit comparison.

### Treat normalized rows as trusted without rebuilding Identity

Rejected because source custody and accepted resolved Identity are different
record layers. Every consumed partition must continue to prove the exact
same-session three-family reconstruction.

### Lower the 0.999 linkage gate to admit 2026-08-31

Rejected in this decision. A near-threshold observation is evidence for a
separate policy review, not permission to change a preregistered quality gate
during implementation.

### Run all sessions in one in-memory batch

Rejected because the existing five-session bound contains memory and restart
risk while still sharing the dominant overlapping EOD reads.
