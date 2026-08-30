# ADR 0085: Diagnose Unresolved Cadence Wakes Without Replay

## Status

Accepted

## Date

2026-08-30

## Context

ADR 0084 deliberately leaves a wake reservation open when the runtime process
exits, a capability raises, its result is invalid, or result retention fails.
This prevents silent replay, but an operator still needs a precise explanation
of what durable evidence exists after the reservation. Treating every open
reservation alike would conceal the difference between no nested action
evidence, an unresolved action attempt, and an action with formal terminal
evidence.

Automatically closing the cadence record from journal event names would be
unsafe. A waiting acquisition also needs an exact future eligibility boundary,
and successful side effects may require current-state revalidation beyond the
terminal event. Diagnosis therefore must not become implicit recovery.

## Decision

Add the pure, read-only `daily-eod-cadence-diagnosis/1.0` contract. It consumes
an already-read, exact-session journal chain and produces one fingerprinted,
zero-authority report. It makes no filesystem, credential, network, or
Production access and performs no replay, retry, recovery, or resolution.

The report classifies five states:

- no unresolved cadence wake;
- reservation with no nested action evidence, whose outcome remains unknown;
- one supported unresolved acquisition, canonical-Apply, or offline action,
  routed only to its existing no-replay recovery name;
- one matching formal nested terminal event, exposed only as an
  `advanced_candidate`, `no_change_candidate`, or `failed_candidate` for later
  operator review; or
- unsupported, extra, or conflicting evidence, which is blocked for diagnosis.

The classifier verifies every event contract, exact-session identity,
contiguous sequence and hash-chain links, the full cadence custody projection,
reservation timing, supported nested family, matching attempt identity, and
zero-authority result semantics. A known terminal candidate is not permission
to append cadence evidence. No-change candidates in particular must not infer
a retry time that is absent from the retained cadence result.

No CLI, journal event, persistent report, resolution action, capability,
service/timer change, request, `/data` write, publication, deployment, or
Production operation is added. Natural timer evidence remains a prerequisite
before runtime installation or activation review.

## Consequences

- Operators can distinguish an action-recovery problem from a cadence-result
  retention problem without inspecting raw event files informally.
- Existing action recovery remains the only route for unresolved nested action
  attempts and still never replays side effects.
- Formal terminal evidence becomes reviewable but cannot silently turn into a
  completed cadence wake.
- A separate reviewed disposition contract is still required before an open
  cadence reservation can be closed safely.

## Alternatives Considered

### Automatically infer and append a cadence result

Rejected because terminal action evidence alone does not always reconstruct
the coordinator result, next eligibility boundary, or current-state proof.

### Treat every open reservation as the same unknown state

Rejected because it would hide existing family-specific recovery and formal
terminal evidence that materially changes operator diagnosis.

### Add diagnosis directly to the installed timer

Rejected because the natural read-only trigger has not yet been observed and
diagnosis must be validated independently before any host binding.
