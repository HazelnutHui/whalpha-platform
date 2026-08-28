# ADR 0058: Carry Strategy Bindings Through Publication and Bundle

## Status

Accepted

## Date

2026-08-28

## Context

ADR 0057 added repository build/read support for Snapshot 1.9 / Dashboard 2.6
and a lazy Candidate strategy-channel payload. The durable Snapshot publisher,
OCI bundle validator, and deployment postflight still stop at Snapshot 1.8.
Accepting 1.9 by version number alone would drop the exact strategy audit,
parameter, product, and decision-boundary evidence between Dell and OCI.

Guest and credential Sessions are deliberately role-free and capability-
identical. Deployment never reads a password, so public postflight proves the
guest path can retrieve the same role-free protected resources; manual
credential login remains a user check.

## Decision

Add Dashboard Snapshot Approval Plan 2.4 exclusively for Snapshot 1.9 /
Dashboard 2.6. It extends Plan 2.3 without weakening any freshness, Activation,
Candidate, Entry Geometry, split-shard, atomicity, recovery, or rollback gate.
It additionally freezes:

- strategy product filename and contract;
- strategy audit manifest SHA-256 and logical fingerprint;
- strategy parameter fingerprint; and
- strategy product logical fingerprint.

Plan construction, formal validation, apply, and verify-then-link must reject
any changed strategy binding. The CLI must parse Plan 2.4 explicitly; older
plans remain readable unchanged. Plan creation must also receive the exact
strategy audit through an explicit temporary-root CLI input; approved Apply
must rely only on the frozen Plan 2.4 and reject that build-time input.

The OCI bundle builder may accept the exact 1.9/2.6 pair only after validating
the strategy file and its manifest/source bindings, fixed Universe/channel
order, complete counts, contiguous bounded ranks, zero-mismatch independent
Oracle gates, research-only semantics, and identical guest/credential
capability flag. Its deployment manifest records the strategy identity.

Deployment postflight must obtain the 1.9 strategy resource through a temporary
guest Session and verify its core decision boundaries. Nginx and the Session
service continue to expose no role or capability distinction. No password,
credential Session, financial recalculation, publication, activation, upload,
or deployment is performed by this implementation task.

## Consequences

- Every immutable boundary carries the exact strategy identity rather than
  trusting a filename or version alone.
- Snapshot 1.5–1.8 and Approval Plans 2.0–2.3 remain rollback-compatible.
- A successful dry-run or local bundle proves mechanics only; it grants no
  Production authorization and no historical-performance validity.

## Alternatives Considered

### Reuse Approval Plan 2.3 without new fields

Rejected because a strategy file could change without changing the approved
split Candidate bindings.

### Trust the Snapshot manifest and skip bundle/postflight checks

Rejected because bundle construction and serving are separate custody
boundaries and must fail closed independently.

### Test a real credential Session automatically

Rejected because deployment verification must not read, transmit, or log the
user's password. The role-free Session design provides capability equality;
manual password login remains a separate user check.
