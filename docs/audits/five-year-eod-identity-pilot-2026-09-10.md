# Five-Year EOD and Identity Pilot — 2026-09-10

## Outcome

The frozen-interval executor extended canonical EOD and same-session Identity
from 306 to 310 contiguous XNYS sessions. The new left boundary is 2025-06-16;
the frozen last session remains 2026-09-09.

| Batch | Sessions completed | Provider requests reported by final run | Result |
| --- | --- | ---: | --- |
| one-session recovery | 2025-06-20 | 1 | Identity package reused after formal validation; EOD acquired and both families applied/read back |
| three-session pilot | 2025-06-18, 2025-06-17, 2025-06-16 | 39 | 12 Identity pages plus one EOD request per session; all applied/read back |

Before the final one-session recovery, one persistent Identity fetch made 12
requests and retained a valid package, then stopped while validating a newly
introduced persistent plan-artifact path. A separate diagnostic made 12
requests and proved the same Identity page set could be acquired at the
selected pace. Together with the successful runs, the bounded pilot activity
made 64 requests. No response body, URL credential, or secret was logged.

The failed artifact candidate was never bound by an Apply plan and no target
existed in `/data`. Direct deletion was refused by the execution environment;
it was moved to the exact recoverable name
`failed-identity-plan-artifacts-attempt-1` inside that session's owner-only
runtime directory. It is not referenced by a plan or canonical manifest.

## Postflight

The network-disabled foundation census formally observed:

- EOD: 310/1,255 sessions, 945 missing;
- Identity: 310/1,255 sessions, 945 missing;
- normalized Identity source: 308/1,255 sessions and 3,772,364 rows, 947
  missing;
- Membership: unchanged at 3/1,255 sessions; and
- overall state: `quarantined`, logical fingerprint
  `f4d08089d1525fa092028038d992dd0338d9cd9d88ddd8fc2deee4e203e8a837`.

No analytics, Historical Coverage, OCI publication, deployment, or scheduler
action occurred.

## Performance decision

The three-session run took 179.47 seconds and peaked at 434,532 KiB RSS, about
59.8 seconds per session. A standalone current-state fingerprint took 5.39
seconds. The same-day plan/apply path performs that full-content inventory scan
six times per newly paired session, accounting for roughly half the observed
duration and reading the unchanged canonical corpus repeatedly.

The 0.25-second serial provider interval was not the bottleneck and produced no
rate or entitlement error. Scaling the unchanged path across 945 sessions
would waste many hours on repeated full-root hashing. One bounded optimization
is therefore required before the long run: preserve the exact pre-state and
locked recheck, but eliminate duplicate scans within each Identity/EOD plan and
record a measured post-change pilot. This is an execution-efficiency change,
not a relaxation of canonical readback or conflict rules.

The bounded change then passed its focused compatibility suite and a second
three-session real batch. That batch completed 2025-06-13, 2025-06-12, and
2025-06-11 with 39 requests, no retry or failure, in 158.52 seconds at 436,088
KiB peak RSS. This is 20.95 seconds (11.7%) faster than the original
three-session batch while retaining every locked full-content recheck. The
bounded optimization is closed; additional performance work is deferred unless
the finite long run breaches its explicit operational bound.

After the measurement, EOD and Identity contain 313 sessions and miss 942;
normalized Identity source contains 311 sessions and misses 944.
