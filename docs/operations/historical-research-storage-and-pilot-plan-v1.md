# Historical Research Storage and Pilot Plan V1

## Status

Fixture-only research-family repositories and Coverage publication mechanics
are implemented. The representative Pilot and 300-session EOD/Identity
acquisition are complete; the remaining research families are not.

This plan turns ADR 0051 into a bounded Dell physical direction and retains the
historical acquisition design. Reading it does not authorize another provider
request, `/data` write, publication, research run, or standing operation.

## Read-only Dell capacity evidence

Measured on 2026-08-28 from the existing canonical root:

| Existing family | Sessions/snapshots | Bytes |
| --- | ---: | ---: |
| EOD Price Bars | 29 | 30,461,337 |
| Instrument Master | 30 | 27,172,419 |
| Provider Instrument Identity | 30 | 23,463,061 |
| Provider Ticker Resolver | 30 | 16,453,442 |
| Entire current market-data root | current state | 158,652,120 |

Observed EOD storage is approximately 1.05 MB/session. The three Identity
families together are approximately 2.24 MB/snapshot. Straight-line physical
estimates before new membership/action/lifecycle fields are:

| Target | EOD + three Identity families |
| --- | ---: |
| 252 sessions | approximately 0.83 GB |
| 504 sessions | approximately 1.66 GB |

The new schemas, revisions, manifests, membership decisions, actions, lineage,
and adjustments will increase this. Reserve 10 GiB for a 504-session canonical
foundation and another bounded 10 GiB for staging/audit work until a pilot
provides real measurements. This is small relative to the 700 GiB Dell data
volume; capacity is not the binding constraint.

## Proposed physical families

All paths remain under the approved Dell root and use explicit schema versions:

```text
market-data/
  provider-corporate-action-observation/
    provider_id=<provider>/schema_version=1/event_year=YYYY/
  corporate-actions/
    schema_version=1/event_year=YYYY/
  instrument-lifecycle/
    schema_version=1/as_of_date=YYYY-MM-DD/
  universe-membership/
    schema_version=1/methodology_version=<version>/session_date=YYYY-MM-DD/
  adjustment-ledger/
    schema_version=1/methodology_version=<version>/basis_session=YYYY-MM-DD/
  historical-coverage/
    schema_version=1/coverage_id=<immutable-id>/
```

The source-observation, lifecycle, membership, and adjustment fixture
repositories now implement this layout under caller-provided temporary roots.
Exact production paths must still be frozen in the pilot approval plan.
Completed partitions are immutable, symlinks are rejected, and conflicting
reruns fail closed. Provider corporate-action observations remain distinct from
the future canonical Corporate Action family.

## Layer ownership

- Provider observations preserve normalized source facts and source revision;
  no raw response body is retained by default.
- Corporate Action and Lifecycle datasets resolve canonical stable IDs and
  preserve contradiction/quarantine state.
- Universe Membership is a WH Alpha methodology decision, never a provider
  membership claim.
- Adjustment Ledger is derived from canonical actions and independently
  reconciled; it does not mutate EOD Price Bars.
- Historical Coverage binds exact family fingerprints and reports readiness;
  it does not contain signal features or outcomes.

## Request model

The current Basic public limit is five calls/minute. Existing controlled
workflows use a conservative fixed 15-second serial interval. Provider calls
remain serial; Dell CPU parallelism applies only after immutable packages are
available offline.

For a history ending at the existing 2026-08-26 EOD session:

| Target | Missing sessions | Grouped Daily calls/time at 15s | Active Identity observed estimate (14 pages/session) | Identity existing ceiling (20 pages/session) |
| --- | ---: | ---: | ---: | ---: |
| 252 | 223 | 223 / 55m45s | 3,122 / 13h00m30s | 4,460 / 18h35m |
| 504 | 475 | 475 / 1h58m45s | 6,650 / 27h42m30s | 9,500 / 39h35m |

These are transport-duration estimates, not completion promises. They exclude
inactive ticker pages, corporate-action pagination, error stops, staging,
mapping, formal rereads, and quality review. Basic's exact two-year boundary
may not cover 504 sessions.

Per-ticker Custom Bars would require thousands of calls and is rejected as the
primary full-market backfill route. Ticker Events is experimental and should be
queried only for a small set of unresolved stable IDs, never the entire base.

## Implementation sequence before a real pilot

1. **Complete:** add provider-neutral logical/Pydantic contracts for corporate-action source
   observations, lifecycle, adjustment ledger, and coverage manifests.
2. **Complete:** refine Universe Membership V1 into an explicit included/excluded/
   quarantined physical decision with evaluated-base lineage.
3. **Complete:** add PyArrow schemas, deterministic fingerprints, temporary-root writers,
   formal readers, and tamper/conflict tests.
4. **Complete:** implement Massive response mapping against saved synthetic fixtures only.
5. **Complete:** implement independent split/dividend factor fixtures and reverse-to-raw
   invariants.
6. **Complete:** add a read-only pilot planner that calculates exact sessions,
   request ceilings, expected paths, and caller-supplied current inventory
   without credential access or storage scanning.
7. **Complete:** add a default-deny approval review that binds the exact plan,
   repository evidence, unified data-governance policy, and external gates
   without creating an authorization.
8. **Complete:** add immutable family-evidence and Historical Coverage
   publication repositories whose formal reader transitively verifies source
   completion manifests and payload hashes under temporary roots.
9. **Complete:** adapt the current canonical EOD and EOD-bound Identity bytes
   into deterministic in-memory family evidence and transitively validate all
   source manifests/payload hashes without publishing to `/data`.
10. **Complete:** join current mechanics, full inventory,
   exact preceding sessions, repository evidence, and dated Massive permission
   conclusions into one blocked, network-prohibited pilot baseline.
11. **Complete:** add a provider-neutral, exact-plan-bound temporary source
   package with per-scope completion, request ceilings, artifact hashes,
   sensitive-field rejection, atomic publication, and full formal reread.
12. **Completed for the bounded EOD/Identity acquisition under ADRs 0120–0124:**
   bind user-directed Dell-local scope, prove the representative Pilot, and
   finish the resumable 300-session target. This did not complete or authorize
   the remaining research families.

Steps 1–11 were repository mechanics. Step 12 was the separately governed
historical EOD/Identity transition and is retained as execution history, not a
pending authorization instruction.

ADRs 0137–0138 add a later no-write custody step for the 279 retained
historical Identity reference packages. The complete typed `/tmp` candidate
contains 3,399,877 result rows in 558 files totaling 258,394,518 bytes. Its
combined census and prospective Apply plan binds the candidate bytes, all
absent targets, and whole-`/data` inventory, but contains no Apply executor and
does not change the blocked readiness state. The 24 missing source sessions
remain a separate gate.

The current `/data` root has no `market-data/historical-coverage` directory.
Strategy readiness therefore remains `data_blocked`; fixture-only publication
mechanics do not supply missing canonical facts.

ADR 0100's 2026-08-30 real read-only pass validated 31 current EOD artifacts
(306,539 rows) and 31 EOD-bound Identity artifacts (307,466 canonical
instrument rows) as proposed family evidence. Both remain
`validated_not_published`. The run preserved the exact 694-file / 503,568,026-
byte root and also confirmed that `historical-coverage-evidence` is absent.

ADR 0101's first real clean-main baseline binds that same mechanics evidence to
inventory `b32d70ae94098bf753282ff2eaa89f241bedc469995bfcd2ac97c2568ddb35ca`
and exact hypothetical targets 2026-07-14 through 2026-07-16. Plan fingerprint
is `ea6faae1d7f5cd3cd80ce349915a8094bc9e78e7e201f72638a06773f4e01899`;
baseline fingerprint is
`7a8ab595707844fb57f4e64651a9e2db16f16246984a945cce3897ee031d7f28`.
It is `blocked`, has no acknowledgement, and made zero requests/writes.

## Implemented read-only planner boundary

`historical-research-pilot-plan/1.0` is a pure function. It accepts an exact,
fingerprinted inventory summary from its caller; it does not read credentials,
scan `/data`, call a provider, or write a package. It validates one to three
ordered XNYS target sessions, subtracts already completed EOD and same-session
Identity partitions, and calculates six endpoint-class ceilings.

The reviewed maximum is exactly 80 requests: 3 Grouped Daily, 60 active All
Tickers, 6 inactive All Tickers, 2 Splits, 4 Dividends, and 5 targeted
experimental Ticker Events requests. Every line is serial, has zero automatic
retry, and uses no faster than the existing 15-second pace. At the maximum,
the transport-only estimate is 1,200 seconds; this is not an execution or
completion promise.

The output deterministically binds the inventory fingerprint, missing
sessions, request lines, source gaps, proposed canonical partition candidates,
and exact relative paths below a required future `/tmp` package root. Action
event years and the final Coverage ID remain explicit templates until validated
observations and formal reread exist. The planner always returns
`not_authorized`, `review_plan_only`, zero external requests, and zero data
writes. It has no transition that can grant acquisition, Apply, publication,
deployment, or scheduler authority.

## Implemented approval-review boundary

`historical-research-pilot-approval-review/1.1` binds the plan and inventory to
the exact implementation revision, synthetic mapping/adjustment evidence, the
Data Record Governance registry, equal-capability serving policy, Source
Permission Governance policy, `/tmp` package boundary, three caller-supplied
external gates, and one mechanically derived permission gate. It returns either `blocked` or
`ready_for_exact_user_authorization_review`; both have zero authority, requests,
and writes. An exact acknowledgement string exists only in the latter state and
still requires a separate user decision and a separately implemented custody
boundary. Satisfied inventory and account evidence expires after at most 24
hours, lifecycle-source review after 30 days, and source-permission review after
90 days; stale evidence fails closed. Permission requires exact same-time
assessments for EOD, point-in-time Identity, and corporate-action source
observations, with all six Dell/equal-capability uses covered by one source and
one review. The caller cannot submit a manual satisfied permission gate.

The deterministic first-window candidate is 2026-07-14 through 2026-07-16,
the three XNYS sessions immediately before the documented contiguous inventory
starts on 2026-07-17. With no named experimental Ticker Events, its preliminary
ceiling is 75 serial requests and 1,125 transport seconds at 15 seconds/request.
The unused five-request allowance cannot be filled later without regenerating
the plan and review binding.

At the original ADR 0101 checkpoint, no real approval package was complete:
the then-current inventory required a fresh exact fingerprint, while
equal-capability source permission, endpoint entitlement, and lifecycle-source
coverage were unresolved. The later user-directed Dell-local Pilot and
EOD/Identity acquisition proceeded under ADR 0120 without converting that
dated review into a general permission or completing lifecycle coverage.

The source-neutral `historical-source-package/1.0` custody mechanics are now
fixture-tested. They accept only already captured sanitized JSON, require every
non-empty Pilot scope to complete within its exact ceiling, bind permission,
entitlement, lifecycle-review, and authorization fingerprints, and atomically
freeze every byte below the exact `/tmp` plan directory. This code has no
transport, credential loader, CLI, default root, or canonical Apply authority.

## Exact 300-session backfill plan

ADR 0119 adds a separate non-authorizing bulk-plan boundary above the existing
three-session Pilot. Against the formally reread 2026-09-01 Dell inventory it
produces:

| Fact | Exact value |
| --- | ---: |
| Completed EOD/Identity sessions at plan creation | 32 |
| Target interval | 2025-06-23 through 2026-08-31 |
| Target / missing sessions | 300 / 268 |
| Three-session-or-smaller batches | 90 |
| First representative Pilot | 2026-07-14 through 2026-07-16 |
| Grouped Daily requests | 268 |
| Total requests at observed 14 Identity pages/session | 4,020 |
| Total requests at 20-page Identity ceiling | 5,628 |
| Serial transport at observed / ceiling pagination | 60,300 / 84,420 seconds |
| Estimated incremental canonical EOD/Identity bytes | 880,745,820 |
| Recommended staging reserve | 1,761,491,640 bytes |

The exact plan fingerprint is
`8bb9087fa1fa91b4f8754291d804e11e7a4c7d768093344952d8d9d38e4eb4aa`.
It orders batches from the current-history boundary backward, so every applied
batch extends one contiguous interval. It does not run the batches, and it
does not weaken the Pilot's source permission or lifecycle gates.

## Completed resumable batch operation

The representative Pilot is complete and ADR 0121's Dell-local batch runner
was the acquisition mechanism for the remaining EOD/Identity history. Each
invocation selects only the XNYS session adjacent to the canonical left
boundary, processes Identity before unadjusted EOD, freezes source packages,
binds plans to the exact inventory, applies atomically, and formally rereads
the result. Canonical state and formally readable packages are the only resume
authority.

ADR 0122 adds a narrowly bounded transient-failure policy to repository source.
Only transport timeout and transport-unavailable errors may retry, at most
twice for the same date after default 30- and 90-second delays. Every actual
provider attempt is counted. HTTP response errors including 429, data,
pagination, quality, custody, inventory, plan, Apply, and reread failures still
stop immediately. Exhaustion emits safe structured progress and the failed
session, then exits nonzero; it does not schedule another invocation.

ADR 0123 adds a finite continuous controller above that batch runner. One
external start can now chain healthy batches until the exact target is
complete. The 20-session ceiling remains inside the process, every completed
batch flushes a revision-bound checkpoint, and the same provider transport and
serial limiter are reused. A true failure still stops the process and requires
diagnosis; there is no unbounded daemon or automatic restart after exhaustion.

The last pre-ADR-0122 service completed normally at its 20-session ceiling.
Later continuous execution must start from a clean revision containing ADRs
0122 and 0123; running source is never changed in place.

The first continuous execution started at 2026-09-02T09:31:19Z from clean
revision `e7d3cf3bdf6ac4eda97a965133c3c4e84343dd7f` under transient user unit
`whalpha-historical-backfill-continuous-20260902-01.service`. Its exact target
is 300 sessions, internal batch size is 20, and its starting canonical boundary
is 147 sessions from 2026-01-30 through 2026-08-31 with 2026-01-29 next. It was
active/running at immediate post-start verification. The unit is collected
after completion; use its retained journal checkpoints and the canonical
reader rather than unit-file existence as completion evidence.

That first continuous process advanced to 245 sessions and then failed closed
at the 2025-09-09 Identity quality gate. ADR 0124 separates catalog-known ETV
from genuinely malformed missing-type records without inferring ETF or
changing the 1% gate. After full regression and offline replay, clean revision
`4d820c7205f090d4d8602435a4da41f400d87261` resumed the exact target under
`whalpha-historical-backfill-continuous-20260903-02.service` at
2026-09-03T17:28:30Z. Formal readers verified the formerly failing date's
Identity and 8,836-row EOD before the process continued to the remaining 54
sessions. The same canonical-resume, per-date atomicity, serial provider and
no-publication boundaries remain in force.

The resumed process subsequently completed the exact 300-session target
through 2026-08-31. Later ordinary daily runs extended the canonical sequence;
exact current range and inventory belong in
[current context](../project/current-context.md). No historical-backfill
transient process remains active.

## Historical Pilot proposal (superseded by the completed Pilot)

The following preregistered ceiling and gates are retained as the review basis
for the completed 2026-07-14 through 2026-07-16 Pilot. They are historical
evidence, not a statement that the Pilot is still awaiting authorization.

The proposed first Pilot was to cover three historical sessions and
representative action/lifecycle cases discovered from the approved date range.
Its proposed hard ceiling was 80 serial requests with zero automatic retry.

- at most 3 Grouped Daily requests;
- at most 60 active All Tickers pages using the existing 20-page/session cap;
- at most 6 inactive All Tickers pages across bounded anchor dates;
- at most 2 Splits pages and 4 Dividends pages at limit 5,000;
- at most 5 targeted Ticker Events requests;
- no Custom Bars unless one separately named repair case replaces another
  request inside the same ceiling.

Fetch writes only a hashed package below `/tmp`. Offline plan and validation
must complete before any separately approved canonical Apply.

## Historical Pilot success gates

- exact request count and endpoint allowlist match the approved plan;
- every page completes without pagination loops or host drift;
- no response body, URL credential, header, or request ID enters Git/logs;
- Grouped Daily confirms unadjusted semantics and same-session Identity binding;
- stable-ID ambiguity and duplicate canonical business keys are zero;
- source observations preserve all required dates and revision fields;
- known split/dividend fixtures reconcile within exact Decimal rules;
- disappearing IDs resolve to governed evidence or explicit quarantine;
- raw OHLC files remain unchanged;
- formal reread reproduces logical and physical fingerprints;
- no current constituents are projected backward;
- no performance, total-return, alpha, or option-return claim is produced.

## Known pilot limitations

Even a successful pilot cannot prove complete merger, spinoff, successor, or
terminal-outcome coverage. It cannot activate performance evaluation. Those
gaps require an additional source or a formally accepted quarantine boundary.

## Remaining limitations after the Pilot

- Massive individual-use/derived-use and guest/friend compatibility remains
  unverified and therefore limits publication claims, not the user-directed
  Dell-local acquisition allowed by ADR 0120.
- Grouped Daily and active point-in-time Tickers access has been demonstrated
  by the Pilot. Small exact probes also reached Splits and Dividends. Inactive
  Tickers pagination exceeded the six-page census ceiling and is incomplete.
- Merger/spinoff/successor and terminal-outcome source remains missing.
- The completed 300-session batch acquired only EOD and active Identity. It did
  not complete membership, corporate-action, lifecycle, adjustment, terminal
  outcome, or Historical Coverage families and therefore cannot activate
  strategy performance research by itself.
