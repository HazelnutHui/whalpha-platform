# ADR 0134: Census Historical Identity Package Equivalence Before Reconstruction

- Status: Accepted
- Date: 2026-09-04

## Context

The Dell workstation has canonical same-day Identity snapshots for every
canonical EOD session and retained sanitized Identity reference packages for
most sessions. Package custody validation proves that a package is internally
complete and unchanged. It does not prove that rebuilding the package produces
the exact Instrument Master, provider Identity, and ticker Resolver families
accepted for the same session.

The bounded historical Universe Membership audit found this distinction in
real data: the custody-valid packages for 2026-08-28 and 2026-08-31 did not
reproduce their accepted same-day Identity fingerprints. Treating the retained
package count as reconstructable source coverage would therefore overstate the
historical foundation and could feed the wrong point-in-time base into later
membership work.

## Decision

Before broad historical Universe Membership reconstruction, run a dedicated
network-disabled, read-only equivalence census across the canonical EOD session
index and explicitly supplied retained-package roots.

For each canonical session the census must:

1. formally inspect the accepted same-day Instrument Master snapshot;
2. formally reread each discovered Identity package, including every response
   artifact and custody hash;
3. rebuild Instrument Master, provider Identity, and ticker Resolver records
   from the sanitized payloads with the package's original observation time;
4. compare all three logical content fingerprints with the accepted snapshot;
5. classify the session without silently selecting among duplicate sources.

The session classifications are:

- `missing_source`: no routed Identity package was discovered;
- `package_custody_failed`: the single routed source failed formal package
  validation;
- `identity_snapshot_mismatch`: the single custody-valid source did not match
  all three accepted Identity families;
- `exact_equivalent`: exactly one source passed custody and all three
  fingerprints matched;
- `duplicate_source_review_required`: more than one routed package exists for
  the session, regardless of whether one or more candidates are exact;
- `canonical_identity_unavailable`: the accepted same-day snapshot could not
  be formally inspected.

Candidate-level results retain only bounded non-sensitive evidence: source
locator fingerprint, package manifest/content fingerprints, observation time,
match flags, and rebuilt family fingerprints. Provider payload rows, tickers,
credentials, and response bodies must never be emitted.

Discovery is restricted to explicit existing, non-symlink directories below
`/tmp`. Invalid manifests that cannot be safely routed are counted separately.
Identity packages outside the canonical session index are also counted and do
not enter the session result set.

The census may write only one atomic JSON report below `/tmp`. It must not
write `/data`, publish Historical Coverage, construct membership partitions,
access the network, or change Production. Exact-equivalent results are source
readiness evidence only; they are not canonical Universe Membership or
research-performance authority.

The same implementation may run an explicitly labeled one-to-ten-session
`bounded_sample` before the full census. A sample report records both the full
canonical index size and its smaller evaluated-session count and can never be
represented as `full_canonical_index` evidence.

Serial execution is the default. After a serial sample and a bounded
multi-process repeat produce identical business evidence, the Dell-only census
may use at most four local processes. Each worker disables socket creation;
results are sorted by session before aggregation so completion order cannot
change the report.

## Consequences

- Broad reconstruction receives an exact source eligibility set instead of a
  misleading package-presence count.
- Missing, corrupted, mismatched, and duplicate sources remain separate repair
  queues.
- Duplicate packages can never be chosen by filesystem order.
- Full formal validation is intentionally more expensive than reading package
  manifests. The census is a one-time/periodic evidence operation, not part of
  the daily serving path.
- Parallel execution remains bounded by the serial-equivalence and measured
  Dell resource gates; it is not a general research-compute policy.
