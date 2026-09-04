# ADR 0141: Fetch Historical Identity Source Gaps Without Canonical Writes

## Status

Accepted

## Date

2026-09-04

## Context

Canonical EOD and completed same-day Identity snapshots cover 303 contiguous
XNYS sessions, while normalized Identity source custody covers only 279. The
remaining 24 sessions from 2026-07-17 through 2026-08-19 have accepted
canonical Identity outputs but no retained reference package or normalized
source-observation partition.

The existing Historical Backfill Runner cannot safely close this gap. Its
resume authority is canonical Identity/EOD presence, so it correctly skips all
24 dates. Reusing it would either do nothing or require weakening a proven
canonical-state boundary. Direct single-date fetch commands would also reset
the process-local limiter between dates and provide no one-run checkpoint or
bounded resume record.

## Decision

Add one narrow Dell-local source-gap fetch operation that:

- accepts one explicit, unique, ascending set of at most 24 historical dates;
- preflights every date against the canonical EOD index and completed
  same-day Identity snapshot before the first provider request;
- rejects any date that already has canonical normalized source custody;
- uses the existing credential loader, sanitized package writer, endpoint
  validation, 20-page/25,000-record ceilings, and complete package reader;
- shares one 15-second serial limiter across every page and date;
- writes only immutable, owner-only packages below one explicit `/tmp` root;
- reuses only a package that passes the existing complete custody reread;
- retries only transport timeout/unavailable failures, at most twice after 30
  and 90 seconds, while counting every provider attempt;
- emits safe per-session checkpoints and never emits request URLs, response
  bodies, exception text, credentials, or Authorization material; and
- reports zero canonical, normalized-custody, membership, analytics,
  publication, and deployment writes.

This acquisition does not select a reconstruction profile. Every new package
must next be compared independently under both `current_v1` and
`pre_etv_governance_v1`. A session may proceed only after exactly one profile
reconstructs all three accepted Identity families and that result is bound by
package and canonical fingerprints.

Normalized candidate construction, a canonical Apply plan, canonical Apply,
daily point-in-time membership, Historical Coverage, strategy research, and
public serving remain separate transitions.

## Consequences

- The physical 24-session package gap can be closed without replaying or
  rewriting accepted canonical Identity/EOD data.
- A stop is resumable from formally readable package custody, not from a
  mutable progress file.
- Provider calls remain serial because the external rate limit, not Dell CPU,
  controls acquisition speed. Later offline equivalence and normalization may
  use bounded local process parallelism.
- A package obtained now is a retained observation of the provider's
  point-in-time date query; it is not assumed equivalent to the accepted
  historical output until exact dual-profile comparison passes.

## Alternatives Considered

### Reuse the canonical Historical Backfill Runner

Rejected because canonical Identity presence is intentionally its resume
authority, so every source-only gap is skipped.

### Launch 24 independent single-date commands

Rejected because the shared limiter and one bounded checkpoint/resume record
would be lost at process boundaries.

### Fetch and write normalized canonical custody in one operation

Rejected because network acquisition, offline equivalence, profile binding,
normalization, planning, and canonical Apply must remain independently
verifiable transitions.
