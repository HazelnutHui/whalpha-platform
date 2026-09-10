# ADR 0197: Separate Reconstructed Research Membership from Signal-Eligible Membership

- Status: Accepted
- Date: 2026-09-10

## Context

The five-year foundation needs one complete daily population series before
outcome-blind coverage and later chronological research can be evaluated.
Most historical Membership is rebuilt after the represented session from a
dated provider query and frozen methodology. It avoids replaying today's
constituent list, but Dell did not observe the original historical provider
vintage. ADR 0193 therefore labels it
`reconstructed_point_in_time_latest_vintage`, not `as_operated`.

Three prospective Membership sessions separately satisfy the next-open
knowledge-time boundary and are already published as signal-eligible
canonical Membership. Reusing that publication family for the weaker
historical reconstruction would make physical presence look like equivalent
evidence and could let a research-only partition enter a Production reader.

## Decision

Store completed latest-vintage historical reconstruction in a distinct
canonical **research custody** family:

`market-data/research-universe-membership/schema_version=1/evidence_tier=reconstructed-latest-vintage-v1/...`

The existing signal-eligible family and its publication marker remain
unchanged:

`market-data/universe-membership/...` and
`market-data/universe-membership-publications/...`

Every research partition must:

1. preserve the original Membership manifest and Parquet bytes;
2. bind their exact hashes, logical fingerprint, methodology, session,
   evaluated base, source fingerprints, source cutoff, and evaluation time in
   a marker written last;
3. require `origin=reconstructed_point_in_time` and an actual source cutoff
   later than the represented session close for this evidence tier;
4. declare `not_as_operated` and deny signal, validation, holdout, performance,
   Candidate, Production, and web-publication authority;
5. permit only coverage, missingness, lineage, and input-completeness analysis
   until a separate ADR 0195 admission decision grants a later development
   use;
6. use an exact no-overwrite plan/Apply/readback boundary and retain conflicts
   or failures instead of replacing evidence in place; and
7. remain discoverable separately in the five-year census. The census may
   report a union of research and as-operated dates only when it also preserves
   their distinct evidence tiers; it must never relabel reconstructed dates as
   signal-eligible.

The first five-year evaluation session remains 2021-09-09. Membership's
20-session trailing-liquidity input requires support sessions from 2021-08-11
through 2021-09-08. Those sessions are explicit warm-up custody outside the
evaluation interval and do not increase the 1,255-session evaluation count.

## Consequences

- Historical population construction can progress without weakening the
  Production next-open gate.
- A filesystem or reader error cannot silently expose reconstructed history as
  current signal-eligible Membership.
- The five-year census can distinguish research coverage from the stronger
  prospective evidence instead of treating three formal publications as the
  whole historical family.
- Completing research custody still does not authorize outcomes. Lifecycle,
  actions, adjustments, terminal evidence, the 100% complete-session rule, and
  the 252-session floor remain independent gates.
- The 20 support sessions may expose an entitlement gap before the nominal
  five-year endpoint. That exact measured gap is handled through another
  professional/free source or a bounded paid-depth change; the evaluation
  interval is never silently shortened.

## Alternatives considered

### Publish reconstruction through signal-eligible Membership Apply

Rejected because the existing contract correctly refuses outcome-only
knowledge-time evidence and Production readers trust its completion marker.

### Keep all reconstruction only under `/tmp`

Rejected because reboot-sensitive shadow output is not durable five-year
database custody and cannot support transitive coverage manifests.

### Call later-retrieved dated snapshots fully point-in-time

Rejected because requested effective date and original observation vintage are
different clocks. The remaining revision risk must stay visible.
