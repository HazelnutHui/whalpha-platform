# ADR 0201: Admit bounded quarantined historical Identity alias collisions

- Status: Accepted
- Date: 2026-09-10

## Context

The exact five-year EOD/Identity continuation stopped before publishing
2025-01-22 Identity. The immutable package passed pagination and custody
validation, but its snapshot failed ADR 0116's 0.1% stable-identifier
collision ceiling.

Offline reproduction found 11,166 raw rows and 9,356 eligible observations.
Twenty-nine Share Class FIGIs each appeared under two distinct tickers, for 58
collision observations or 0.6199% of eligible rows. Every pair was already
classified ambiguous and excluded from Instrument and Resolver output. The
remaining 8,467 eligible observations resolved independently, with 90.4981%
eligible identity coverage.

The conflicts are consistent with later-vintage ticker-alias revisions, not
proof that both tickers were simultaneously valid. Their provider
`last_updated_utc` values are later than the requested historical date, and
some pairs contain names or tickers known only from a later provider revision.
Choosing either member would invent point-in-time ticker lifecycle evidence.
Rejecting the whole session would also discard thousands of unrelated,
deterministic stable-ID resolutions and stop adjacent price acquisition.

## Decision

Keep ADR 0116's 0.1% ceiling for prospective/current Identity snapshots.
Introduce a separate historical-reconstruction profile with a maximum 1.0%
stable-identifier collision-observation ratio.

Under that profile:

- every conflicting observation remains `ambiguous`;
- neither ticker receives an Instrument or Provider Ticker Resolver row from
  the conflicting evidence;
- collision observations remain in the eligible denominator;
- the actual collision count, actual ratio, and applied ratio ceiling remain
  in immutable quality/plan evidence;
- EOD bars depending on an unresolved alias remain absent from canonical bars
  and visible in coverage/missingness evidence; and
- any session above 1.0%, below the existing 80% eligible-identity coverage
  gate, or failing another unchanged quality gate still stops.

The 1.0% ceiling is a bounded reconstruction tolerance selected to contain the
observed 0.6199% revision anomaly without converting row quarantine into an
unbounded acceptance rule. It is not evidence that the provider reference
endpoint is a historical ticker-lifecycle authority.

## Consequences

- One localizable historical alias batch cannot block unrelated stable-ID and
  EOD construction.
- Prospective Identity quality remains stricter than later-observed historical
  reconstruction.
- The affected rows cannot become Membership-, signal-, validation-, or
  performance-eligible until independent lifecycle evidence resolves the
  applicable ticker interval.
- A later lifecycle reconciliation may repair an alias interval append-only;
  it must not rewrite this source observation or silently select a winner.
- The five-year Identity family remains latest-vintage reconstructed evidence,
  not `as_operated` point-in-time truth.

## Supersession scope

This decision supersedes ADR 0116 only for the explicitly selected historical
reconstruction profile. It does not change stable identifier priority,
prospective/current gates, corporate-action logic, lifecycle authority,
historical research admission, or Production behavior.
