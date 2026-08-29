# ADR 0065: Reuse Candidate Completion Evidence in Daily Planning

## Status

Accepted

## Date

2026-08-29

## Context

ADR 0060 separated completed Candidate publication custody from full research
reconstruction. The daily automation planner still used the full Candidate
append reader for both the immediately preceding audit and the current audit.
The coordinator planned once, the executor planned again under its lock, and
the executor planned a third time for the postcondition.

The real 2026-08-27 daily Candidate audit is 422,786,554 bytes. Its business
path reached audit write in 152.944168 seconds and streamed the audit in
22.201208 seconds, but the journaled action took 576.027031 seconds. Before the
action started, the coordinator and executor also each fully reconstructed the
89-second prior audit. Postcondition reconstruction of the larger current
audit reached about 6.1 GB RSS. These repetitions did not create a new
research decision after the immutable audit had already passed full
finalization.

## Decision

Add a Candidate planning-evidence reader and use it for both prior and current
Candidate observations in the exact-session daily planner.

The planning reader:

- requires the same direct-`/tmp`, owner, mode, symlink, file-set, and
  completion-manifest custody as ADR 0060;
- canonically validates the completion manifest and parameter contract;
- streams SHA-256 across every declared Candidate artifact and checks exact
  sizes, order, zero Oracle mismatch, and all recorded equivalence gates;
- for schema 1.1, parses only the small incremental-validation ledger and
  checks its physical and logical fingerprints against the manifest;
- binds the ledger to the same prior/current sessions, prior audit fingerprint,
  calculation contracts, daily validation scope, current-session Oracle
  fingerprint, zero-mismatch Oracle segment, and all-true reuse gates; and
- retains backward reading of the pre-tier incremental audit where
  `validation_tier` is absent, while the current daily Candidate planner still
  requires explicit `validation_tier=daily` before advancing.

Candidate calculation continues to use the full audit-content reader for its
prior append input. Audit finalization remains a full research reread. The
planner does not use existence, timestamps, or a detached manifest as proof.
Entry Geometry continues to type and fingerprint the exact current Candidate
batches through its bounded reader.

This changes no Candidate formula, score, state, rank, parameter fingerprint,
artifact bytes, Oracle, automation-plan contract, publication behavior, or
deployment authority.

## Consequences

- The real completed 2026-08-27 planner now returns in 9.45 seconds at 221,640
  KiB maximum RSS instead of reconstructing both cumulative Candidate audits.
- Its plan fingerprint remains
  `eb19d7790605fae6d2467f6996b9411fb5fc6653f28f27b6e60c9fdd6b41811f`
  and its sole next action remains `calculate_entry_geometry`.
- Corrupt bytes, wrong file modes, extra files, manifest drift, parameter
  drift, failed equivalence/Oracle gates, lineage mismatch, missing daily tier,
  false reuse checks, and mismatched current Oracle segments still fail closed.
- The normal Candidate calculation still pays one full prior-input read
  because it needs the typed cumulative prefix. Removing that remaining cost
  requires a separately designed storage/schema change rather than weakening
  validation.

## Alternatives Considered

### Cache fully parsed Candidate objects in the coordinator

Rejected because process memory is not durable custody and would couple
planning to one runtime instance.

### Trust only the completion-manifest fingerprint

Rejected because the planner must still prove every declared artifact byte and
the incremental lineage required to advance.

### Remove the executor's locked re-plan

Rejected because the re-plan closes a real time-of-check/time-of-use boundary.
Making that re-plan cheap preserves the safety property.
