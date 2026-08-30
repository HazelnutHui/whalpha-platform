# Daily EOD Bounded Cadence V1

## Purpose

`daily-eod-bounded-cadence-plan/1.0` determines whether one later, distinct
pipeline wake may be reviewed. It is a pure repository planning contract. It
does not sleep, loop, schedule, persist evidence, invoke a coordinator, or run
an offline action.

## Required inputs

- timezone-aware UTC observation and explicit cadence-start times;
- one complete, semantically verified Pipeline Wake Plan 2.0 observed at the
  exact same time;
- zero or more contiguous `daily-eod-cadence-wake-evidence/1.0` records for the
  same target session; and
- the fixed default policy or a strictly narrower policy.

Each evidence record binds its sequence, target, start/completion time, exact
pipeline-plan fingerprint, invocation action, formal outcome, one-invocation
count, and result fingerprint. Failed or unknown outcomes terminate the chain.
The future runtime must persist these records under separate owner-only
custody; the current planner creates no file.

## Candidate limits

| Limit | Default and maximum | Meaning |
| --- | ---: | --- |
| Transition wakes | 16 | Includes all distinct data/offline invocation wakes for one target session |
| Cadence window | 4 hours | Measured from the explicit immutable cadence start |
| Completion-to-next-start interval | 5 minutes minimum | Prevents an in-process or rapid cross-process loop |
| Invocations per planner/process | 0 | The planner only proposes; a future bridge may perform at most one |

The transition ceiling is derived from the current five-attempt provider
policy, separate canonical Apply, and ten offline actions. It is conservative
review capacity, not expected workload or approved Production timing.

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

## Not implemented or authorized

- evidence persistence or filesystem provisioning;
- data/offline result adapters or an execution bridge;
- process locking beyond existing action-level custody;
- a repeated systemd service/timer;
- credentials, provider/OCI access, canonical writes, publication, deployment,
  automatic retry, or automatic recovery.
