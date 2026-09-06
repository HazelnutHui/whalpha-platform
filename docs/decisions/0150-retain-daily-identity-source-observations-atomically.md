# ADR 0150: Retain Daily Identity Source Observations Atomically

## Status

Accepted

## Date

2026-09-06

## Context

The canonical Identity and EOD families contain 304 completed sessions through
2026-09-04. Normalized provider Identity source custody contains 301 sessions.
Two older dates, 2026-08-13 and 2026-08-19, are intentionally unbound because
the reacquired provider observations do not exactly reconstruct the accepted
Identity. The remaining 2026-09-04 gap is operational: its sanitized daily
Identity package and exact canonical Identity exist, but the ordinary daily
Identity plan publishes only Instrument Master, Provider Identity, Resolver,
and the logical completion marker.

Repairing only 2026-09-04 would allow the same omission to recur every day.
Reusing the historical profile-map binding would also be misleading. A daily
package is directly bound to the canonical Identity it creates; it is not one
member of the complete historical profile-map census. ADR 0142 explicitly
rejects constructing a synthetic partial profile map.

## Decision

Extend normalized Identity source custody with a backward-compatible daily
manifest variant. It retains the unchanged row contract and physical dataset
layout, but identifies `same_day_identity_plan` as its binding origin and uses
one deterministic direct-binding fingerprint over the package, observation
time, rebuild profile, session, and accepted canonical Identity fingerprints.
It does not contain or imitate historical profile-map fields.

The ordinary daily Identity approval plan will advance to schema 1.1 and add
the normalized source partition immediately before its logical completion
marker. The plan therefore binds all prospective bytes, their immutable
targets, and the pre-Apply `/data` inventory in one compare-and-swap boundary.
Apply remains network-prohibited and recoverable: already completed physical
components must match the approved bytes exactly, and the logical marker stays
last.

Schema 1.0 daily plans remain readable under their original four-target,
seven-file contract. New plans use the five-target, nine-file contract. The
version is never inferred from file cardinality.

A source-only schema 1.1 repair operation may append one absent normalized
source partition for a session whose canonical Identity already exists. It
must rebuild the package under `current_v1`, prove exact Instrument Master,
Provider Identity, Resolver, and logical Snapshot fingerprints, bind an exact
inventory pre-state, publish atomically, and formally reread the result. It
cannot overwrite or relabel any completed target.

Daily observations use their actual package `fetched_at` as knowledge time.
They are eligible only at or after that observation time; a later fetch never
creates a claim that the source was known at the session close. Historical
profile-map manifests retain their existing
`outcome_reconciliation_only` eligibility.

## Consequences

- Future successful daily Identity publication cannot silently omit normalized
  source custody.
- The 2026-09-04 operational gap can be repaired without changing canonical
  Identity, EOD, Universe, analytics, Snapshot, or Production serving state.
- Existing 301 historical partitions and their profile-map evidence remain
  byte-for-byte immutable and readable.
- The deliberately unbound 2026-08-13 and 2026-08-19 observations remain gaps;
  this decision does not weaken their mismatch boundary.
- Source custody still grants no Historical Coverage, Universe Membership,
  research-performance, model, publication, deployment, or scheduler
  authority.

## Alternatives Considered

### Patch 2026-09-04 manually

Rejected because the omission would recur and a manual copy would lack the
same approval, inventory, recovery, and reread guarantees as the daily path.

### Add 2026-09-04 to a synthetic historical profile map

Rejected because it would misrepresent a direct daily binding and contradict
ADR 0142's complete-map rule.

### Store the raw response package in `/data`

Rejected because normalized typed rows already retain the governed source
facts without persisting response URLs, request identifiers, or transport
envelopes.
