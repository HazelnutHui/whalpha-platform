# ADR 0100: Adapt Current EOD and Identity Without Publishing Coverage

## Status

Accepted

## Date

2026-08-30

## Context

ADR 0099 established immutable family evidence and transitive Historical
Coverage custody, but all proof used temporary fixtures. Dell already retains
completed canonical EOD and same-session point-in-time Identity data. Treating
those bytes as absent wastes valid mechanics evidence; publishing them without
first proving a formal adapter would overstate research readiness.

The existing EOD reader fully validates each Parquet partition and its Identity
binding. Identity had strict writer and internal reread checks but no public,
non-mutating reader that validated the logical snapshot plus all three physical
families together.

## Decision

Add a formal read-only Identity snapshot inspection method. It validates the
logical snapshot identity, component counts and fingerprints, canonical
partition references, exact file sets, completion manifests, Arrow schemas,
row counts, and recalculated logical content for Instrument Master, provider
identity, and ticker resolver. It creates no missing root or partition.

Add `current-historical-mechanics-evidence/1.0` and the credential-free command:

```text
scripts/admin/assess-current-historical-mechanics-evidence.sh \
  --data-root <absolute-canonical-root>
```

The command socket-blocks network access, formally rereads all completed EOD
sessions and every referenced Identity snapshot, constructs deterministic
in-memory EOD and point-in-time Identity family evidence, binds every source
completion manifest and payload SHA-256, and transitively validates the
proposed evidence without publication. Its output contains only dates, counts,
fingerprints, status, and explicit blockers.

Identity evidence counts canonical Instrument Master rows. Provider identity
and resolver files remain physically bound payload evidence, but their counts
are not added to the family record count. Source exclusions outside canonical
rows are explicitly not claimed as zero quarantine.

No current bytes are upgraded to `research_ready`. Evidence publication,
Historical Coverage publication, provider acquisition, `/data` writes, model
development, performance claims, deployment, and scheduler changes remain
separate transitions.

## Real Dell Evidence

The 2026-08-30 socket-guarded run validated 31 sessions from 2026-07-17 through
2026-08-28:

- EOD: 31 artifacts, 306,539 rows, evidence fingerprint
  `d7def47ee1fba89760a016ba52d79313bf3729aed2fee421c4e05a2596299cd5`;
- point-in-time Identity: 31 artifacts, 307,466 canonical instrument rows,
  evidence fingerprint
  `a69530ea830f448ecb90949c3f2a4a871a87ae015d2c2d8e0e6ae0582e5d4e76`;
- report fingerprint
  `6ef8da023b0b92c96147e9e11f530c361a3c24a23ff4b6c8a39ec38d6bc12228`.

Both family results are `validated_not_published`. Before and after the run,
the canonical root remained 694 files and 503,568,026 bytes. Neither
`historical-coverage-evidence` nor `historical-coverage` exists under `/data`.

## Consequences

- Existing 31-day mechanics now enter the same physical trust chain intended
  for future backfill instead of requiring a parallel format.
- A future publication can use the exact deterministic evidence after separate
  review, without recomputing different semantics.
- Current readiness remains blocked by 221 sessions plus daily membership,
  canonical corporate actions, lifecycle, adjustment reconciliation, and final
  Historical Coverage publication.
- Full content validation is intentionally heavier than a manifest-only check;
  it is an audit command, not a per-request serving path.

## Alternatives Considered

### Publish the two family manifests now

Rejected because the current task authorizes repository implementation and
read-only validation, not a `/data` transition.

### Trust completion manifests without rereading Parquet

Rejected because it would not prove the physical bytes still match their
logical fingerprints.

### Count all three Identity table row totals as one family count

Rejected because those tables have different grains. Canonical instrument
count is the family observation count; all three tables remain exact bound
evidence.
