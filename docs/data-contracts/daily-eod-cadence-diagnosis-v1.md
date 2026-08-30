# Daily EOD Cadence Diagnosis V1

## Purpose

`daily-eod-cadence-diagnosis/1.0` classifies one already-read daily run-journal
chain when Pipeline Runtime 1.0 left a cadence reservation unresolved. It is a
pure diagnostic contract: it writes nothing and grants no recovery or replay
authority.

## Inputs

- one complete tuple of formally valid, same-session run-journal events;
- the exact target session; and
- a timezone-aware diagnostic observation time.

The event tuple must have contiguous sequence numbers and internal hash-chain
links. The cadence reservation, plan, evidence, and any nested action events
must pass their existing contract verification.

## Classifications

| Status | Meaning | Suggested next action |
| --- | --- | --- |
| `no_pending_wake` | No unresolved cadence reservation exists | None |
| `outcome_unknown` | Reservation exists but no supported nested action evidence follows | Operator confirms the invocation boundary; no replay |
| `action_recovery_required` | One nested action start is unresolved | Use its existing family-specific no-replay recovery |
| `known_result_review_ready` | One matching nested action terminal exists | Review a separate no-replay cadence disposition |
| `blocked` | Extra, unsupported, or conflicting evidence exists | Operator diagnosis |

Terminal classifications are candidates, not cadence outcomes:

- `advanced_candidate` for formal acquisition-package, canonical-Apply, or
  offline success evidence;
- `no_change_candidate` for formal provider not-ready, rate-limit, transient,
  or recovered-not-completed evidence; and
- `failed_candidate` for all other supported terminal failures.

The diagnostic report never invents a missing `next_eligible_at`, coordinator
result, current-state proof, or action outcome.

## Zero-authority boundary

Every report declares zero external requests, filesystem writes, and Production
writes. Action replay, automatic resolution, retry, and recovery are false.
There is no CLI, persistence, scheduler binding, or resolution action in V1.
