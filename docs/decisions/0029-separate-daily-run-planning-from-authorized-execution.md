# ADR 0029: Separate Daily Run Planning from Authorized Execution

## Status

Accepted

## Date

2026-08-27

## Context

The individual Identity, EOD, Phase 1a, Phase 1b, Candidate, and entry-geometry
steps already have formal readers and fail-closed calculation boundaries. A
scheduler that merely chains shell commands would still be unsafe: missing and
corrupt artifacts would look alike, an old audit could be selected by naming
convention, and acquisition, calculation, publication, and deployment could
silently share one authorization boundary.

Daily execution also needs a deterministic answer to one question before any
action: what is the only safe next step for one exact XNYS session?

## Decision

Add a credential-free, read-only daily planner with contract
`daily-eod-automation-plan/1.0`. The target session and every current/prior
audit path are explicit inputs; the planner never selects `latest`. It formally
rereads completed evidence in this order:

1. same-day Identity;
2. same-day canonical EOD, including the exact Identity fingerprint;
3. current Phase 1a, including Identity and EOD bindings;
4. immediately prior and current Phase 1b, requiring the verified-prior daily
   execution mode and exact Phase 1a/prior bindings;
5. immediately prior and current Candidate, requiring the explicit `daily`
   verified-prior mode and exact prior binding;
6. current Candidate entry geometry, including the exact Candidate binding.

An absent next artifact produces exactly one next action. A present artifact
that fails its formal reader, a session/fingerprint mismatch, a missing
verified prior, or an existing downstream artifact without a verified
prerequisite produces `blocked` and `operator_diagnosis`. Completed artifacts
are never overwritten or treated as retry targets.

The planner can report acquisition preparation, offline calculation readiness,
or analytics readiness for publication review. It does not fetch provider
data, calculate analytics, write `/data`, authorize publication, build a
Snapshot or bundle, deploy OCI, or enable a scheduler. Publication and
deployment remain separate explicit decisions. Its canonical report is
deterministic and records zero external requests and zero Production writes.

The current implementation is a control-plane checkpoint, not full unattended
operation. A later executor may consume one plan action at a time, but it must
re-plan after every completed action and retain the same formal readers and
authorization boundaries.

## Consequences

- A future timer only wakes the planner; it does not define business or safety
  semantics.
- Daily state is derived from immutable evidence rather than a mutable success
  flag or filename convention.
- Corruption and interrupted downstream residue stop the run instead of
  triggering an automatic overwrite.
- Strict formal rereads are intentionally suitable for one run transition,
  not high-frequency polling. A future lightweight index must be derived from
  and bound to the same completed evidence.
- Full automation still requires an explicit standing-authorization design for
  provider acquisition and canonical apply, plus a durable run-journal and
  scheduler activation decision.

## Alternatives Considered

### Chain all administrator scripts in a timer

Rejected because shell exit order alone cannot prove exact sessions, prior
lineage, fingerprints, or the difference between absence and corruption.

### Infer current and prior artifacts from `latest` links or names

Rejected because a daily state machine must bind immutable evidence, not
ambient naming conventions.

### Include publication and deployment in the first automatic action graph

Rejected because those operations have separate user-visible, rollback, and
public-serving consequences. The first control-plane slice ends at publication
review readiness.
