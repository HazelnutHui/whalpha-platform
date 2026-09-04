# ADR 0138: Bind Historical Identity Source Apply Planning

- Status: Accepted
- Date: 2026-09-04

## Context

ADR 0137 defines a normalized, `/tmp`-only source-observation partition for
each of the 279 profile-bound historical Identity packages. The complete real
candidate is substantially smaller than the retained response packages and
formally reconstructs the accepted same-day Identity families, but candidate
completion does not authorize a durable write.

A bulk copy based only on a directory name or session count could publish a
partial, changed, or stale candidate. It could also race a change elsewhere in
`/data`, overlap an existing target, or lose the exact profile-map and source
evidence that made the candidate acceptable.

## Decision

Add `historical-identity-source-apply-plan/1.0` as the single combined
candidate census and prospective Apply plan. Plan creation must:

- formally read every profile-bound candidate partition and require an exact
  one-to-one session match with the validated profile map;
- bind ordered session summaries, both files for every session, their sizes
  and SHA-256 values, the candidate inventory fingerprint, and the profile-map
  fingerprint;
- bind aggregate record, request, source-response, Parquet, manifest, file,
  and byte counts;
- map every candidate file to the fixed provider-neutral `/data` layout and
  require every target partition to be absent;
- reject symlinks, relaxed candidate permissions, unexpected files, profile
  drift, duplicate sessions, path escape, and changed candidate bytes;
- bind a fresh whole-`/data` inventory fingerprint; and
- write only one owner-readable plan below `/tmp`, then formally reread it.

The plan contains no Apply executor. Its operation status is
`ready_for_separate_review`, while `apply_authorized`, Historical Coverage,
membership, research performance, publication, deployment, and scheduling
remain false. A future Apply implementation must reread an explicitly pinned
plan, revalidate all source bytes, target absence, and the current `/data`
inventory immediately before any write. It must publish immutable partitions
atomically and handle partial-state recovery separately.

The plan is intentionally also the aggregate census. A second report carrying
the same 279 session and 558 artifact bindings would add maintenance surface
without adding evidence.

## Consequences

- A reviewed plan can answer exactly what would be added to `/data` without
  changing `/data`.
- Candidate drift, target overlap, or any unrelated canonical inventory change
  invalidates the plan rather than being silently accepted.
- The 24 unbound historical sessions remain outside this plan and retain their
  explicit missing-source status.
- Durable source custody remains distinct from daily Universe Membership and
  Historical Coverage publication.

## Alternatives Considered

### Copy the candidate tree directly

Rejected because a path and file count do not bind source bytes, target
absence, profile provenance, or the canonical pre-state.

### Create a census report and a separate Apply plan

Rejected because both would repeat the same ordered sessions, artifacts,
hashes, and aggregates. One strictly validated plan is the smaller source of
truth.

### Add the Apply executor at the same time

Rejected because proof of a no-write plan should precede authorization and
implementation of a bulk canonical transition.
