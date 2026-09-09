# Daily EOD Bounded Cadence V1

## Purpose

`daily-eod-bounded-cadence-plan/1.0` determines whether one later, distinct
pipeline wake may be reviewed. It is a pure repository planning contract. It
does not sleep, loop, schedule, persist evidence, invoke a coordinator, or run
an offline action.

## Required inputs

- timezone-aware UTC observation and explicit cadence-start times;
- one complete, semantically verified Pipeline Wake Plan 2.1 observed at the
  exact same time;
- zero or more contiguous `daily-eod-cadence-wake-evidence/1.2` records for the
  same target session; and
- the fixed default policy or a strictly narrower policy.

Each evidence record binds its sequence, target, immutable cadence start,
start/completion time, exact cadence-plan and pipeline-plan fingerprints,
invocation action, formal outcome, one-invocation count, and result
fingerprint. A formal readiness `next_check_at` is retained and takes
precedence over the five-minute floor. Failed or unknown outcomes terminate the chain. ADR 0083 retains
known evidence plus the complete enabled cadence plan in the existing
owner-only run journal. ADR 0084 advances that journal to 1.8: an unknown
reservation is written before invocation and is closed only by a matching
known result. The planner itself still creates no file.

## Candidate limits

| Limit | Default and maximum | Meaning |
| --- | ---: | --- |
| Transition wakes | 16 | Includes all distinct data/offline invocation wakes for one target session |
| Cadence window | 4 hours | Measured from the explicit immutable cadence start |
| Completion-to-next-start interval | 5 minutes minimum | Prevents an in-process or rapid cross-process loop |
| Invocations per planner/process | 0 | The planner only proposes; Runtime 1.0 may perform at most one in a separate process boundary |

The original transition ceiling was derived from the five-attempt provider
policy, separate canonical Apply, and ten offline actions. The pipeline now has
an eleventh Visual Context action, but the ceiling remains 16 rather than being
silently widened. A worst-case session may therefore stop for later review
before every offline action completes. It is conservative review capacity, not
expected workload or approved Production timing.

## Outcomes

| Current condition | Plan action |
| --- | --- |
| Pipeline waiting | Wait until the later pipeline or minimum-interval boundary |
| Ready, candidate disabled at either layer | Review one transition |
| Ready, both candidates enabled | Propose one transition invocation |
| Manual publication/Snapshot/deployment review | Stop |
| Blocked pipeline state | Stop |
| Prior known failure | Stop; no automatic retry |
| Prior unknown outcome | Stop; no replay or automatic recovery |
| Wake-count or elapsed-time limit reached | Stop |

`no_change` means a prior invocation returned formally without advancing state.
It permits only a later fresh observation; it is not authority to replay the
same side effect. `advanced` must also be followed by a fresh Pipeline Wake
Plan before another proposal.

## Fail-closed verification

The plan exposes and fingerprints its exact limits, used/remaining budget,
window, next wake, current pipeline identity, evidence-chain identity, both
candidate enablement flags, and zero-authority fields. Re-fingerprinted but
semantically incompatible Pipeline V2 or cadence state is rejected.

## Repository-only runtime boundary

`daily-eod-pipeline-runtime/1.0` is default-off and accepts both exact plan
fingerprints. Explicit invocation requires both enabled candidates and exactly
one matching data/offline capability. Cadence custody 1.1 first writes and
rereads an unknown reservation, then invokes once, then closes the reservation
with a formally validated known result. An exception, malformed result, crash,
or retention failure leaves the reservation open and blocks replay and later
sessions.

## Not implemented or authorized

- real filesystem provisioning;
- a CLI or installed entry point for the runtime bridge;
- automatic diagnosis or closure of an unresolved reservation;
- process locking beyond the existing short journal/action custody;
- a repeated systemd service/timer;
- credentials, provider/OCI access, canonical writes, publication, deployment,
  automatic retry, or automatic recovery.
