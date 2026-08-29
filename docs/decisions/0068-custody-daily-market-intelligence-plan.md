# ADR 0068: Custody the Daily Market Intelligence Plan

## Status

Accepted

## Date

2026-08-29

## Context

ADR 0067 places all seven offline analytics artifacts under the daily
one-transition coordinator. The next manual step still required an operator to
assemble a long Market Intelligence `--plan` command, supply the exact
Production inventory fingerprint, and then reconnect the generated candidate
and approval package to the daily run.

Market Intelligence planning is already an offline, no-network operation that
writes only a new explicit `/tmp` candidate directory and approval package. It
does not activate a publication. Leaving it outside daily custody nevertheless
creates avoidable path-selection, source-lineage, interruption, and handoff
risk.

## Decision

Add `prepare_market_intelligence_plan` as the eighth ordered daily action,
after Strategy Channels and before `review_publication`.

The action delegates to the existing Market Intelligence `--plan` mode and
requires two explicit execution bindings:

- an aware UTC `publication_created_at`; and
- the exact expected `/data` inventory fingerprint.

It also receives explicit, new direct-child `/tmp` paths for the MI output root
and approval-plan file. These paths become part of the locked execution-input
fingerprint and interruption-recovery identity.

After the administrator exits, the daily planner formally rereads the
canonical approval plan and immutable candidate. It requires MI plan 1.2, the
exact target session and data root, exact Phase 1a/1b/2, preview, Candidate,
and Entry Geometry paths, and the matching upstream logical fingerprints.
Missing output and plan select the one preparation action. A partial pair,
invalid plan/candidate, different path, session, or lineage blocks.

The completed plan exposes whether normal freshness allows activation. The
coordinator then stops at `review_publication` regardless of eligibility.
Freshness-blocked output is evidence for catch-up or explicit review; it is
never treated as Apply permission.

No standing authority is added. MI Apply, verify-then-link, Snapshot,
Snapshot Apply, bundle, OCI deployment, rollback, notification, and scheduler
activation remain separate operations.

## Consequences

- The full route from canonical data through a reviewable MI approval package
  now uses one exact-session, hash-chained Dell control plane.
- Planning remains reproducible and recoverable without granting Production
  write authority.
- A crash before both plan artifacts complete cannot be silently retried or
  mistaken for readiness.
- Operators review one formal approval package rather than reconstructing its
  source command manually.
- The daily system is still not unattended because Apply and all public-serving
  transitions remain outside this action.

## Alternatives Considered

### Keep MI planning as an unjournaled manual command

Rejected because it duplicates path selection and loses the daily run's exact
input and interruption custody.

### Generate and immediately Apply the MI plan

Rejected because plan creation is evidence preparation, while Apply changes
Production state and requires separate authorization.

### Infer the inventory fingerprint without binding it to the action

Rejected because the resulting approval package must identify the exact
Production state reviewed by the operator.
