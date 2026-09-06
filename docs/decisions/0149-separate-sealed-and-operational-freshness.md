# ADR 0149: Separate sealed and operational freshness

- Status: Accepted
- Date: 2026-09-06

## Context

Dashboard Snapshot freshness is evaluated when an immutable static release is
created. That assertion remains historically true for the release, but its
label can be misread later as a live statement about the current clock. A
Snapshot that was fresh on Friday can still display `fresh` on Saturday even
when the canonical store has advanced or the next completed exchange session
has become due.

Rewriting immutable Snapshot metadata would destroy publication provenance.
Treating the sealed assertion as current operational state would conceal a
real lag. The two meanings therefore require separate names and independent
evidence.

## Decision

Keep Snapshot freshness immutable and explicitly label it as the publication-
time check. The durable browser reference remains `Data as of`.

Advance the network-free current-context report to contract 1.5 and expose
three distinct views:

1. `canonical_operational` evaluates the latest canonical EOD session against
   the XNYS calendar at report time;
2. `active_snapshot_operational` evaluates the active Snapshot data session
   against that same current clock; and
3. `snapshot_publication_sealed` preserves the exact expected session, actual
   session, lag, status, calendar, and checked-at timestamp sealed in the
   immutable Snapshot.

Both operational views are derived read-only and never mutate a publication.
Malformed active-Snapshot session dates fail the report closed. The browser
continues to render only static Snapshot data and must not imply live runtime
monitoring; English and Chinese labels explicitly say the visible freshness
was checked when published.

## Consequences

- Historical publication truth remains reproducible.
- Operators can detect canonical or serving lag from the current report
  without interpreting sealed Snapshot metadata as a live assertion.
- The public site still has no dynamic market-data dependency and remains
  fail-closed.
- A future live operational status surface must consume a separately governed
  current source rather than relabeling static Snapshot fields.

## Validation evidence

Focused backend tests prove Friday-to-weekend separation and malformed-session
rejection. The real Dell report on 2026-09-06 independently classified
canonical EOD, the active 2026-09-04 Snapshot, and its sealed publication
assertion as lag-zero against the completed XNYS session. Focused frontend
tests and the production build prove the revised bilingual labels.
