# Authoritative Current Context

Operational state verified at: 2026-08-30 UTC

Repository development context updated at: 2026-08-30 UTC

This is the authoritative compact handoff for new Codex tasks and new devices.
It records current facts and their evidence boundary. Product history remains
in the [changelog](changelog.md) and dated audits. Proposed sequencing remains
in the [roadmap](roadmap.md).

## Repository

| Field | Verified value |
| --- | --- |
| Workstation | `dell5820` |
| User | `hui` |
| Source-of-truth repository | `/home/hui/projects/trading-intelligence-platform` |
| Branch | `main` |
| Deployed bundle source commit | `83f9b629279c0e7e949cf01b454ebfda60b35900` |

Codex-created worktrees may be detached at the same commit. Always verify the
main repository separately before treating a worktree as the source of truth.
The repository HEAD is intentionally not frozen in this document because a
documentation or code commit legitimately advances it. The read-only report
must show the current HEAD and cleanliness separately from the immutable commit
recorded by a deployed bundle.

## Formal local state

The 2026-08-30 reconciliation used the project readers after the separately
authorized complete 2026-08-28 Identity/EOD, analytics, publication, Snapshot,
bundle, and OCI deployment round. It reread the full local inventory and active
custody/contracts after deployment.

| Boundary | Active verified value |
| --- | --- |
| Canonical EOD | 31 sessions, 2026-07-17 through 2026-08-28 |
| Latest EOD | 2026-08-28, 9,942 rows |
| EOD content fingerprint | `d02dd3bca07331087934b947bc3e724f6d1ca64113615515f08951e46bb5c803` |
| EOD Parquet SHA-256 | `f3d57d29a947bcf4ed11b14f8c2ee3686b84f5eaa9f8d3b6762c3b93c5005a18` |
| Latest canonical Identity | 2026-08-28: 9,981 instruments / 13,151 provider identities / 9,981 resolvers |
| Latest Identity logical fingerprint | `becf17b05b22a9f89de0d8f96094d83cabb568eaf0c32121eaf2c0daba21189b` |
| Latest-EOD-bound Identity | 2026-08-28: 9,981 instruments / 13,151 provider identities / 9,981 resolvers |
| EOD-bound Identity logical fingerprint | `becf17b05b22a9f89de0d8f96094d83cabb568eaf0c32121eaf2c0daba21189b` |
| Identity/EOD alignment | `aligned` |
| Activation analysis session | 2026-08-19 |
| Activation pointer fingerprint | `dbe6056e1ed4b87ebce88b356c346831ce67431a263066cd283b9ad7e8067168` |
| Activation logical fingerprint | `6ea818cb3079bb77fd5fe1b8000530d2c8e2d1127fcccd40be68ac590678c7a5` |
| Primary | 1,718 CS; fingerprint `c3665203965b96528c9be07db3c49d18023104e346da16050f1170d4fe148978` |
| Secondary | 1,831 = 1,718 CS + 113 ADRC; fingerprint `2dce08e728774510878c47dc80898e10236952dacd146990ad344c4dcb75a295` |
| Market Intelligence | `2026-08-28T135850Z-f483d6999a3e`, contract 1.3 |
| Market Intelligence payload SHA-256 | `bb58287454ddc79955e045f3341c35873961a16e692ee9146d9519f4837351fc` |
| Market Intelligence logical fingerprint | `7f1e6b9c065999939a2f43f397f8af4a94dc342f65ad6dc3624d4c6d6b507f74` |
| Candidate publication | 686 Primary / 744 Secondary records; fingerprint `96c37e7a1e35c55e67422a1b4638e7ad1f5a69d6edc5a8124344ae4a0f7cf758` |
| Dashboard Snapshot | `2026-08-28T141747Z-83f9b629279c` |
| Contracts | Snapshot 1.11 / Dashboard 2.8 |
| Snapshot pointer fingerprint | `cd78a18de7fe102b694fbf624315b37c7648f4d0034e59c6d130e6a965ed9468` |
| Active review metadata | none; ordinary fresh publication |
| Current post-close pipeline freshness | expected 2026-08-28; canonical EOD, analytics, active Snapshot, and deployed UI all analyze 2026-08-28; lag zero |
| `/data` inventory | 694 files / 503,568,026 bytes after MI 1.3 and the final Snapshot 1.11 publication |
| `/data` inventory fingerprint | `b32d70ae94098bf753282ff2eaa89f241bedc469995bfcd2ac97c2568ddb35ca` |
| `/data` symlink/staging/partial residue | zero |

Workstation listener review found no Python, Node, Vite, Uvicorn, or project
application process and no unexpected project listener. Normal SSH, DNS, and
Tailscale listeners were present.

Development, canonical data, research, replay, and heavy recomputation use
Dell as the source of truth. OCI is the static web-serving, Session-auth, and
public-read boundary; Windows and future Mac clients are remote work entry
points, not independent compute/data authorities. Dell has a Xeon W-2145 with
8 physical cores / 16 threads. The Candidate pipeline now shares overlapping
immutable panel reads, uses stable-ID state indexes, and supports a verified-
prior one-session append with an additive audit schema. Real append/cold
comparison exposed a legacy Phase 1b rolling-window state-prefix defect;
repository source corrects it with state calculation V1.0.1 and a stable
canonical left boundary. Phase 1b audit schema 1.1 now formally rereads the
current Phase 1a and immediately prior Phase 1b audits, appends one session,
and runs an independent current-session state Oracle without reopening
`/data`. On real 2026-08-26 inputs it matched the V1.0.1 cold state,
explanation, transition, summary, and history outputs exactly: 0.237 seconds
before writing versus 302.736 seconds cold, with zero Oracle mismatch. This is
development-only and has not changed active Production. Repository source now
also implements optional content-addressed reuse of the formally validated
Phase 1a panel in the daily Candidate append. On real 2026-08-26 development
inputs it reduced panel loading from 217.409 to 8.837 seconds and total time
before writing from 310.008 to 101.792 seconds; all nine business/Oracle files
were byte-identical and both paths had zero Oracle mismatch. Repository source
now also streams and resumes source-bound Candidate artifacts under ADR 0026.
The final real 2026-08-26 development run recorded 111.636 seconds before
writing, 17.921 seconds for ten streamed artifacts, a 3,343,112 KiB process
peak, and an approximately 164-second work-directory-to-delivery boundary.
Its nine source/business/Oracle files were byte-identical to the earlier
panel-cache audit, all four equivalence gates were true, and Oracle mismatch
was zero. Repository source now explicitly enforces `daily`, `periodic`, and
`code_change` validation tiers under ADR 0027. A real same-version
2026-08-26 periodic cold reference took 597.70 seconds and the formal
incremental-versus-cold comparison took 197.20 seconds; all eight comparable
business projections matched and both audits had zero Oracle mismatch.
Repository source now also applies ADR 0028's bounded process parallelism only
to independent cold-replay session Oracles. Four workers reduced the same cold
Oracle stage from 117.09 to 76.23 seconds and end-to-end time from 597.70 to
560.02 seconds; all nine business/Oracle files and both aggregate fingerprints
were exact. A measured inner-daily parallel prototype was slower, so daily
keeps one effective Oracle worker. ADR 0029's exact-session, read-only daily
planner is now implemented. A real 2026-08-26 rehearsal formally reconciled
the corrected incremental chain and selected `calculate_entry_geometry` as its
sole next action, with zero external requests and Production writes. A
single-action executor and durable Dell run-custody implementation now consume
only an exact unchanged plan for one of eleven offline daily actions. Eight
are analytics actions, including Candidate Visual Context; the ninth prepares
an MI approval plan, the tenth prepares a Dashboard Snapshot approval plan,
and the eleventh constructs and formally rereads an exact active-Snapshot
serving bundle. All remain without a
Production write or network authority. The executor holds a global lock, journals start/terminal
events in an immutable
cross-session hash chain, validates output evidence, and re-plans before
recording success. Interrupted-attempt recovery only classifies formal state
and never re-executes. Before the first controlled 2026-08-27 rehearsal, this
boundary was repository-tested only; no scheduler is enabled. Session-
readiness/retry policy and provider acquisition/apply standing
authorization were the next boundary. ADR 0031 now implements the first half
as a pure, network-free readiness plan with actual XNYS close/early-close
handling, a provisional 30-minute stabilization window, and bounded
15/30/60/120-minute retry,
five-attempt and six-hour limits, explicit alert state, and oldest-missing-
session recovery. It never asserts provider completeness or performs a fetch,
apply, notification, or scheduler action. Durable acquisition-attempt custody
now shares the global lock and cross-session journal with offline execution,
reserves only a fresh exact readiness fingerprint, records bounded outcomes,
formally binds completed package evidence, and recovers interruption without a
request. Before the first controlled rehearsal, journal 1.2 had not been
provisioned for a real run and no fetch had executed. Provider fetch/canonical-apply
standing authorization is now defined by ADR 0033 as an expiring, exact-
revision, externally SHA-pinned contract for only Identity/EOD fetch and
canonical apply. Its reader and transition verifier were initially repository-
tested only; the later controlled state is recorded below. Publication and
public-serving operations stay outside this scope.
ADR 0067 extends the ordered offline calculation boundary after Entry Geometry
through ETF Relationships, Market Preview, and Strategy Channels. Each new
stage formally binds the exact same-session upstream logical fingerprints and
uses the existing one-transition journal, lock, postcondition, and recovery
semantics. ADR 0068 adds the exact-inventory, exact-UTC MI Plan preparation
action after those seven artifacts. `analytics_ready` now requires the formal
MI plan and immutable candidate as well. These development changes do not
enable a scheduler and do not authorize MI Apply, Snapshot, bundle,
deployment, credentials, or `/data` writes.
ADR 0069 adds a default-off, one-shot MI Apply port under coordinator 1.7 and
backward-readable daily journal 1.4. It requires the exact plan SHA, expected
Production inventory, host-runtime pin, and any exact plan-bound stale-review
acknowledgement; it is mutually exclusive with other execution modes and keeps
networking prohibited. Success requires the exact active publication/pointer
to formally reread. Recovery never applies or links. At that implementation
boundary the port was repository-tested only; later controlled publication is
recorded in the active-state table and deployment audit below.
ADR 0070 advances the planner/executor/coordinator contracts to 1.3/1.3/1.8
and adds Snapshot Plan preparation only after the formal daily MI plan matches
the exact active MI publication. It binds explicit UTC, new direct-child
`/tmp` output/plan paths, the same-session Strategy Channel audit, and exact MI
payload/logical fingerprints. A strict public Plan 2.4 reader verifies
canonical owner-controlled read-only custody and the complete candidate
lineage. Completion stops at `review_snapshot_publication`; Snapshot Apply,
bundle, OCI deployment, and scheduler activation remain separate and
unauthorized. At that implementation boundary it had not created or activated
a real Snapshot; later controlled use is recorded below.
ADR 0071 advances the coordinator, backward-readable daily journal, and
recovery router to 1.9/1.5/1.1 and adds a default-off, one-shot Snapshot Apply
port. It requires the
exact Plan 2.4 SHA, expected active Snapshot state, host-runtime pin, unchanged
Activation pointer, target/staging absence, and any exact plan-bound stale-
review acknowledgement. Success requires the exact active release and planned
pointer to formally reread. Recovery never applies or links. The same change
preserves `snapshot_generated_at` when routing an interrupted Snapshot Plan
recovery. At that implementation boundary the port was uninstalled and
uninvoked; later controlled Snapshot publication is recorded below. It still
grants no standing or unattended publication authority.
ADR 0072 advances the offline planner/executor/coordinator/recovery contracts
to 1.4/1.4/1.10/1.2 and
adds exact active-Snapshot serving-bundle construction as the tenth action. It
requires a clean matching Dell `main` revision, explicit UTC and `/tmp`
candidate root, exact Snapshot aggregate/manifest and source-byte bindings,
complete file checksums, fixed locale and equal Session capability, preserved
bundle build-time recovery identity, and a
strict Serving Bundle 1.0 formal reader. It removes the ambiguous legacy
Snapshot-release shortcut and stops at `review_bundle_deployment`. At that
implementation boundary it had not built a real candidate or made an OCI
request; later controlled bundle construction and deployment are recorded
below. One-shot OCI deployment custody was the next missing control boundary
at that commit.
ADR 0073 advances coordinator/recovery/journal contracts to 1.11/1.3/1.6 and
implements that boundary behind a separately SHA-pinned, owner-only, default-
disabled deployment config. One invocation binds the exact Serving Bundle and
fresh remote pre-state, reserves before mutation, invokes Apply once, and
requires a separate structured post-state inspection. The report contains no
credential values and explicitly records that password login was not tested.
Recovery performs one read-only inspection and never invokes Apply; unchanged,
exactly completed, and partial/ambiguous states remain disjoint. The deployer
also rejects changed current release, staging/failed residue, and a preexisting
target stage immediately before mutation. At that implementation boundary the
capability was uninstalled and uninvoked; the later separately authorized OCI
deployment and independent inspection are recorded below. No scheduler or
standing deployment authority was enabled.
The composed coordinator/capability/custody/journal path now also has a complete
fake-transport rehearsal with exact healthy pre-state, one simulated Apply,
independent exact post-state, and the expected start/success hash-chain events.
A separate review CLI renders an exact external deployment runtime candidate
and future-file SHA entirely in memory. It defaults disabled; even its explicit
enabled-candidate mode records zero installation, authorization, credentials,
networking, or writes. Because every source commit invalidates the candidate's
revision pin, the final candidate must be rendered after the final clean commit
and must not be persisted or activated without separate review.
All 1,653 backend tests pass for this final repository implementation; no
frontend source changed.
ADR 0074 subsequently adds a repository-only, additive relationship-change
view derived from the retained Phase 2 history. It exposes state-run duration
and exact rolling relative-return changes without modifying source payloads,
formulas, thresholds, rankings, or source Market Intelligence.
All 1,654 backend tests and 95 frontend tests pass for this additive boundary,
and the frontend production build succeeds. This boundary is now deployed in
release `2026-08-29T133847Z-1490b37f25b3`.
ADR 0075 subsequently adds a repository-only ten-point relationship state path
with explicit retained-history boundaries and selected-window relative returns.
It does not alter Phase 2, formulas, rankings, or source Market Intelligence.
All 1,656 backend tests and 96 frontend tests pass, the frontend
production build succeeds, and the formal active-publication reader reconciles
all 16 pairs against 21 retained 2026-08-28 relationship sessions without a
write. This boundary is deployed in release
`2026-08-29T133847Z-1490b37f25b3`.
The first write-free publication preflight then caught a backend compatibility
defect when rereading the active pre-projection Snapshot. Repository source now
accepts missing additive fields while newly rendered responses still include
them. The failed preflight stopped with only a `/tmp` candidate and made no
`/data`, OCI, or Production change. The correction was then applied before the
successful Snapshot and OCI deployment.
ADR 0076 subsequently adds a credential-free, read-only scheduler-wake plan.
It binds a lightweight completion-manifest index to a full formal reread of the
latest EOD partition, selects only the oldest missing XNYS session, and reuses
the existing stabilization policy. On current Dell state at
2026-08-29T14:30:00Z it completed in about 2.8 seconds and returned
`up_to_date`, latest 2026-08-28, next target 2026-08-31, and next check
2026-08-31T20:30:00Z. Both disabled and explicitly enabled-candidate reviews
recorded zero coordinator invocation, credential access, networking, file
write, or Production write. All 1,701 backend tests pass. No scheduler service
or timer was installed at the ADR 0076 planning boundary; ADR 0079 records the
later host installation below.
ADR 0077 subsequently adds the default-off one-transition wake bridge. It
recomputes the complete ADR 0076 plan fingerprint before a call, accepts only
an explicitly enabled ready candidate plus a separate invocation flag, and
recomputes and retains the coordinator-result fingerprint before rejecting any
result content, target, or authority drift. A synthetic five-wake report
fingerprint `4b533e1ab3b6bff01767e0a574a7f7dc3c7c3e0d49512f4072a2bee1a817b6d8`
records four total fake coordinator calls, maximum one per wake, no automatic
retry/recovery or alert delivery, and zero credential, network, filesystem, or
Production activity. It installs no service or timer.
ADR 0078 subsequently adds an exact, non-installed Dell/hui user-systemd
candidate for the read-only planner only. It pins clean `main`, Git revision,
canonical data root, entrypoint, New York 13:30/16:30 weekday calendars, and
both future unit hashes. It clears inherited Python overrides and pins/rechecks
the project interpreter. Runtime must reprove the exact Dell source and current
UTC clock before planning. At that candidate boundary Dell systemd 255 and the
user manager were available, but `linger=no` remained prerequisite-missing.
ADR 0079 now records the separately authorized installation: `hui` linger is
enabled and the owner-only read-only user timer is installed. An initial
`218/CAPABILITIES` start proved three proposed directives incompatible with the
Dell user manager; the timer stayed stopped while `PrivateNetwork`,
`PrivateDevices`, and explicit capability bounding were removed. The retained
read-only/`NoNewPrivileges`/`AF_UNIX` unit then passed a controlled start in
about three seconds and reported current 2026-08-28 state with zero coordinator,
credential, external request, filesystem write, or Production write. No real
data transition, publication, or deployment is scheduled.
ADR 0080 now separates operation evidence from host state. Current planner,
scheduled-wake, and rehearsal 1.1 outputs report
`scheduler_installation_performed=false`, meaning that the invocation made no
unit change. They no longer emit `scheduler_installed`. The installed/enabled
timer and `hui` linger state remain separately established by read-only host
inspection. The updated five-wake rehearsal fingerprint is
`51133b39e01eeb5aacdc0686eb00b612180a7a4ba45a448802de99b859759412`.
ADR 0081 adds a repository-only Pipeline Wake Plan 2.0 and deterministic
Dell-local per-session workspace derivation, so current canonical EOD no longer
conceals unfinished offline analytics. ADR 0082 adds the non-installed bounded
cadence above it: at most 16 distinct transition wakes over four hours with a
five-minute completion-to-next-start floor. Known failure, unknown outcome,
manual review, blocked state, and budget exhaustion all stop. These layers
create no workspace or evidence store, invoke nothing, and do not alter the
installed read-only timer. A natural timer wake and separate owner-only runtime
custody remain prerequisites before any activation decision.
All 1,731 backend tests pass with the two existing dependency warnings at this
boundary.
ADR 0083 subsequently reuses run journal 1.7 as the single owner-only cadence
evidence store. It retains complete enabled cadence plans and known Evidence
1.2, so cadence start and budgets cannot reset across tasks or restart.
Coordinator 1.12 now maps provider waiting to waiting and provider/offline
failure to blocked instead of calling every return an executed transition.
Exact adapters project results but invoke nothing; no real cadence event or
runtime integration exists yet. All 1,746 backend tests pass with the two
existing dependency warnings at this boundary.
ADR 0084 advances the journal to 1.8 and cadence custody to 1.1. A full unknown
wake reservation is now retained before one action; only a matching known
result closes it. Crash, invalid result, or retention ambiguity leaves it open
and blocks replay plus later-session custody. Repository-only Pipeline Runtime
1.0 composes this with exactly one scope-matched data/offline capability and
remains default-off, non-looping, and uninstalled. Old journal 1.2–1.7 evidence
remains readable. No real reservation, capability, CLI, timer binding, request,
`/data` write, publication, deployment, or Production invocation occurred. All
1,754 backend tests pass with the two existing dependency warnings.
ADR 0085 adds pure Cadence Diagnosis 1.0 over a supplied exact-session journal
chain. It separates an unknown invocation boundary, existing no-replay action
recovery, a formal terminal that is only ready for later disposition review,
and conflicting evidence. It performs and authorizes no read outside the
supplied tuple, write, replay, retry, recovery, or automatic resolution. No CLI,
real journal access/event, timer binding, request, `/data` write, publication,
deployment, or Production operation occurred. All 1,764 backend tests pass
with the two existing dependency warnings.
ADR 0034 now implements the repository-only coordinator core: it joins exact
planning, journal recovery, readiness, authorization review, one opt-in offline
action, diagnosis, and the publication-review stop while never looping.
Provider/apply capability ports are absent by default; that coordinator slice
introduced no CLI, authorization activation, request, or write.
ADR 0035 adds exact canonical-Apply reservation, success proof, and no-write
recovery under a third disjoint journal family. It binds completed acquisition
hashes, the formal plan, current inventory, absent targets, and exact paths;
unknown or partial outcomes remain unresolved or blocked. No real Apply
reservation, recovery, or `/data` write occurred through this layer.
ADR 0036 now supplies repository-tested, explicitly installed fetch/Apply
adapters that compose the external authorization SHA, acquisition/Apply
custody, real Massive boundaries, and formal terminal evidence. Request 1.1
binds Apply to `canonical_apply_started`; ADR 0036's coordinator 1.1 accepts
Identity's actual bounded 1–20 HTTP requests; and the authorized canonical root
is `/data/trading-intelligence-platform`. That implementation slice created no
real authorization artifact, host pin, credential read, provider request,
reservation, Apply, CLI, or scheduler entry; later controlled use is recorded
below.
ADR 0037 now adds the repository-tested one-transition CLI and external
host-runtime config contract. Authorized ports stay absent unless an externally
SHA-pinned owner-only config enables them and the invocation opts in. Runtime
derives the actual Dell hostname, executing source root, clean Git HEAD, and
current readiness-policy fingerprint rather than trusting asserted strings.
That implementation slice created no real Host artifact or transition. No
service, timer, alert, or scheduler exists. ADR 0038 now routes one explicitly
requested unresolved acquisition, canonical-Apply, or offline-action event to
its existing recovery boundary after an exact locked journal reread. Recovery
keeps networking disabled, never performs Apply or replays calculation, and
never loops. This is
repository-tested only; no real recovery or run-journal transition occurred.
ADR 0039 now carries alert-required state through coordinator 1.3 and can emit
one stable, channel-neutral alert intent with a deterministic deduplication key.
It explicitly records that delivery was not attempted. No alert outbox,
transport, channel credential, retry, receipt, or real notification exists.
Because host and standing authorization bind exact Git revision, external
artifacts remain deliberately unprovisioned until control-plane code is stable.
ADR 0040 now adds repository-tested, at-most-once alert delivery custody under
a separate immutable journal. It records `delivery_started` before an explicit
transport call, deduplicates formally delivered intents, and blocks automatic
retry after known failure or crash-ambiguous outcome. ADR 0041 now supplies a
repository-tested, default-disabled SMTP adapter behind that custody boundary.
It uses whole-file SHA-pinned external config, exact Dell/runtime/root binding,
owner-only two-key credential custody, verified implicit TLS or STARTTLS, and a
deterministic bilingual message. No external email config, credential, alert
root, network request, delivery, service, timer, or scheduler exists. ADR 0042
now adds a repository-tested read-only joint preflight command for the host,
standing-authorization, and email artifacts. It prohibits networking and
reports configuration consistency without credential access, writes, or
rehearsal authority. ADR 0043 now composes the intent, immutable delivery
custody, and SMTP adapter after one formal coordinator result when the CLI has
an explicit delivery flag and exact Host/email SHA pins. Normal states perform
no credential access or alert write. No real external artifact has been
created or preflighted, and no delivery route has been invoked.
ADR 0044 advances external preflight to 1.1 with an explicit
`daily_data_only` mode because SMTP is deferred. The mode never reads email
config and retains the complete Host/Identity/EOD authorization checks.

At 2026-08-27T20:18:05Z, a fresh network-free Dell report still showed latest
Identity/EOD 2026-08-26 and a clean repository at `353b5d1`. The exact
2026-08-27 automation plan selected `prepare_identity_catchup`. Readiness was
`stabilizing` until 20:30Z with zero attempts, requests, or writes. The proposed
daily run and alert roots were absent and no matching user timer was active.
An in-memory seven-day Host/standing-authorization candidate was reviewed but
not written; its revision became intentionally obsolete when ADR 0044 work
began.

After ADR 0044 was committed as `e4fdee0`, a fresh network-free readiness check
at exactly 2026-08-27T20:30:00Z returned `ready_for_fetch_review` with
`next_action=review_fetch_authorization` for the same 2026-08-27 Identity
catch-up. It recorded zero attempts, external requests, and Production writes;
no provider fetch or authorization followed.

The user subsequently authorized the controlled data-only rehearsal. External
owner-only Host Runtime, standing authorization, and daily run roots were
installed at exact revision `c3af030`, valid through
2026-09-03T20:49:28Z. Preflight 1.1 returned
`configuration_consistent` / `daily_data_only` with zero credential reads,
network requests, and Production writes. The 2026-08-27 Identity fetch then
made 14 requests; its offline plan validated 13,148 provider-identity rows and
9,982 instrument/resolver rows, and canonical Identity Apply completed with one
Production transition.

The following 2026-08-27 EOD fetch made exactly one request and terminated
`permanent_failure`. It left the package, staging path, approval plan, and
canonical EOD target absent. The original acquisition-custody 1.0 event did not
retain the numeric HTTP status; local code proves only that it was neither 404
nor 429. No retry or later stage was run. ADR 0045 adds safe status/request-
count evidence for future attempts without changing retry policy. Any new
commit also invalidates the installed exact-revision controls until they are
separately reviewed and reprovisioned.

ADR 0046 corrects the handoff view exposed by context report 1.0. Report 1.1
now shows latest canonical Identity 2026-08-27 separately from latest EOD
2026-08-26 and its bound Identity 2026-08-26, with
`identity_eod_alignment=identity_ahead_of_eod`.

ADR 0047 now makes readiness explicitly plan-aware. The active default profile
is `massive_stocks_basic_end_of_day`; Identity retains the provisional
30-minute first-review point, while a first current-session Basic EOD request
requires an immutable operator review and bounded `not_before`. Journal 1.3's
reader is repository-tested against immutable 1.2 event bytes and can append a
standalone review bound to the exact prior terminal fingerprint. This repository-only
path performs and authorizes no fetch, Apply, scheduler, publication, or
deployment. At 2026-08-27T22:24:36.997840Z, the offline command appended one
real terminal-failure review bound to event fingerprint
`cb8cf64d212fe5da269e7936eb18b7f2a354962db27dfd8fd127760f7cfee297`.
The review event fingerprint is
`83b641f17c3897544f6c1a962add51f27d7e63b9097825618a7c70db2de01489`
and its logical review fingerprint is
`61a5c1b559b83d10f15dd675910eee7f657980d1523e50fedae9dde03ca1a499`.
It records `authorize_one_fetch_after` with `not_before=2026-08-28T16:00:00Z`.
A subsequent offline reread returned `waiting_to_retry` / `wait`, reason
`operator_review_not_before_pending`, one attempt, one review, no alert, zero
external requests, and zero Production writes. The time is a conservative
operator boundary inferred from public plan/endpoint documentation and the
provider's separate next-day flat-file completion guidance; it is not a
Grouped Daily REST release guarantee or a provider-completeness assertion.
The review does not itself authorize a fetch. The old `c3af030` Host Runtime
and standing authorization also remain inactive by exact-revision mismatch.

At 2026-08-28T17:06:00Z, the user separately authorized exactly one
2026-08-27 EOD fetch-only retry. Short-lived owner-only controls permitted only
`fetch_eod` at exact revision `dd314db`; the coordinator made one request and
returned `fetch_package_ready` with zero Production writes. The frozen package
formally contains 12,552 results and has manifest/content SHA-256 values
`bd9a664e4a3df54cb4b39344893d6662d8fa8b51055b31d02af1ce6a02807d06`
and `17545f3479fe532b425419c5a83f2fa0e54c58693d1d61e5c5ec5a5751088ae6`.
The `/data` inventory remains unchanged at fingerprint
`7d66bc02fe88410a4ed6f000f74875aa135e11d10318ff010a148d03ba08a0de`;
at that fetch-only boundary, the 2026-08-27 canonical EOD target and Apply plan
were absent. Readiness advanced to `ready_for_apply_review`. See
[the exact retry audit](../audits/daily-eod-fetch-retry-2026-08-28.md).

The later offline Apply Plan is now complete and formally reread at file
SHA-256
`76ac1c50a016b82772ce8ac391f8d67e107c8433caae0e1f6364b311deb23bc5`.
It binds the same package, 2026-08-27 Identity, and unchanged current inventory;
it yields 9,945 canonical rows, zero duplicate business keys, zero orphan
references, and exactly two planned files totaling 1,056,432 bytes. Independent
Parquet inspection confirms 9,945 unique business keys, zero null instrument
IDs, and only the target session. At that plan-review boundary, the canonical
target was absent and no Apply authority had been granted. See
[the exact plan audit](../audits/daily-eod-apply-plan-2026-08-28.md).

The first authorized Apply invocation then failed closed before reservation:
the coordinator passed journal operator reviews into readiness, while canonical
Apply custody omitted them during its independent recheck. At that rejected-
invocation boundary, the journal still ended at `acquisition_package_ready`,
the target remained absent, and `/data` was unchanged. The minimal fix projects
the same immutable reviews in both layers and adds a permanent-failure/review/
successful-retry reservation regression. It changes neither policy nor Apply
scope. Fresh exact-revision controls were still required to exercise the
user's existing one-Apply authority.

Fresh controls bound only `apply_eod` at fix revision `6256bf3`. The second
invocation completed one canonical transition with zero external requests and
formal reason `canonical_stage_completed_and_replanned`. The 2026-08-27
partition contains 9,945 rows and matches the approved Parquet, manifest, and
content hashes. The journal ends in `canonical_apply_succeeded` with no
unresolved event. `/data` is now 392 files / 203,931,663 bytes at fingerprint
`ddbe1ab03d5b945e9c3e2be975218c830f10e1ca615571e9616e131c847c7749`,
with zero symlink/staging/partial residue. The next exact automation action is
offline `calculate_phase1a`; no downstream action had run at that Apply
boundary. See
[the canonical Apply audit](../audits/daily-eod-canonical-apply-2026-08-28.md).

The next explicitly continued one-transition action completed offline Phase 1a
for 2026-08-27. Its formal audit fingerprint is
`887024c4847ef74a28a713c439359f3a4d8d93e49269ab58f2f0177c61159c53`,
with zero Oracle mismatch, zero missing metrics, and 100% configured weight
available. Primary/Secondary composites are 67.4134 / 67.5471. Trend,
volatility, and leadership/dispersion support the composite, while breadth and
liquidity/participation conflict. These are not final state labels; Phase 1b
hysteresis remains pending. The 257,202-bar formal panel cache is available at
key `5dfa32ea7b447feef752f490b7141aefe9ace53b20bb62e76631cf8eee142cca`.
Phase 1b then appended 2026-08-27 from the corrected V1.0.1 2026-08-26 audit.
Its audit fingerprint is
`6a3a530280dbe9eea6617d76e980ed453b47e087d9e35fe588e8f7b6fe630801`.
Both Universes remain confirmed Balanced at composites 67.4134 / 67.5471;
the independent Oracle has zero mismatch and all prefix/restart/source gates
pass. An initial invocation correctly rejected the legacy Production-bound
V1.0.0 prior path and created no target; the corrected lineage then completed
normally. At that Phase 1b boundary, the planner selected only
`calculate_candidate_daily`. `/data` and all active serving artifacts remained
unchanged. See
[the Phase 1a audit](../audits/daily-eod-phase1a-2026-08-28.md).
See also [the Phase 1b audit](../audits/daily-eod-phase1b-2026-08-28.md).

The 2026-08-27 daily Candidate append is now also complete at audit fingerprint
`0fa85ae742ef47e7278c444c12f05f2082e38a5071068a5787655a11271eb4e4`.
It reused four sessions, added one session across both Universes, used the
formal panel-cache hit, and passed the independent Oracle and every incremental
equivalence gate. Current score batches contain 1,714 Primary and 1,827
Secondary comparable securities; the complete state ledger preserves all
1,718 / 1,831 active members with four unavailable in each. The journal ends
normally and the formal next operational action is
`calculate_entry_geometry`. The 422,786,554-byte cumulative audit exposed a
material control-path inefficiency: the 152.944168-second pre-write business
path became a 576.027031-second journaled action because multiple layers fully
reconstruct historical JSON. Optimize those redundant rereads without
weakening the append-input or Oracle gates before running the next large
postcondition chain. See
[the daily Candidate audit](../audits/daily-eod-candidate-2026-08-29.md).

ADR 0065 now closes that planner/postcondition repetition. Planning rehashes
every immutable Candidate artifact but reconstructs only the small lineage
ledger needed for the planning decision; Candidate calculation still performs
the one full typed prior-prefix read. On the exact 422,786,554-byte current
audit, formal planning takes 9.45 seconds and 221,640 KiB maximum RSS while
preserving plan fingerprint
`eb19d7790605fae6d2467f6996b9411fb5fc6653f28f27b6e60c9fdd6b41811f`
and sole next action `calculate_entry_geometry` at that boundary.

The resulting 2026-08-27 Entry Geometry shadow audit is now complete at
fingerprint
`3aa78cb694a4c06835f19fb6165cd721e62b7fe16f921240ce8a601fcd83c11a`.
It assesses all 1,714 / 1,827 current comparable Candidate rows, has zero
Oracle mismatch, preserves input-permutation equivalence, and makes zero
external requests or Production writes. Primary/Secondary technical-review-
ready counts are 70 / 73; monitor-for-trigger 1,303 / 1,393; wait-for-reset
104 / 110; and deprioritized 237 / 251. Journal event 21 closes normally. The
post-plan is `analytics_ready` at fingerprint
`f6fe6ddd5b4e561724088147d9dda361d270b548f2a7ff4d3df1b5b974958ff9`;
the next boundary is `review_publication`, not an authorized publication or
deployment. The action took 338.217438 seconds and exposed a remaining current-
batch read optimization opportunity, but its result and custody are valid.
See
[the planning optimization audit](../audits/daily-candidate-planning-optimization-2026-08-29.md).
See also
[the daily Entry Geometry audit](../audits/daily-eod-entry-geometry-2026-08-29.md).

The publication review then completed the missing 2026-08-27 Phase 2 and
preview chain. Phase 2 fingerprint
`1d0efadf75579c2487696fe5933bccfcdc56e40680433a790a9600b3776ec41f`
has zero Oracle mismatch and all replay/permutation/prefix gates. Preview
payload fingerprint is
`da5b9364ab4e84955c82d3c8666b125e293108dd0093c692830bfef2ccf3d52c`.
Two initial MI Plan attempts failed closed before plan creation because the
schema 1.1 daily Candidate evidence was still interpreted through duplicated
cold-only field access. ADR 0066 and commits `54b1d09` / `211c1a5` now make
Candidate construction and MI approval recheck use one explicit mode-aware
projection; the complete backend suite passes 1,573 tests.

The final formal MI 1.2 review plan SHA-256 is
`a5732db20555cc0e873fb184302e401e825fab9f65d81e7e6d6bbdecd472e2ea`.
It passes full source validation and projects 558 / 599 Candidate records at
fingerprint
`d81479e4e332865f5d4c6312033a66095febe3b018a8e54376668d3e8f36ac47`,
but returns `freshness_blocked`: actual 2026-08-27, expected 2026-08-28, lag
one, with no applicable review authorization. Apply did not run. No same-day
8/27 Strategy audit was generated; Snapshot 1.9 would require one, but the next
correct data boundary is 8/28 acquisition review rather than completing an
already non-activatable serving chain. See
[the publication review audit](../audits/daily-eod-publication-review-2026-08-29.md).

The subsequent network-free 2026-08-28 readiness review formally selected
`prepare_identity_catchup` at automation-plan fingerprint
`3bf65e5b57284b48df6fb6cfd26b983f035cdfd5505cb380877ad57cf94821c2`.
At `2026-08-29T06:12:50+00:00`, readiness was
`missed_session_recovery` / `review_fetch_authorization`, fingerprint
`4e26699abd653a611e3f2e1f4e117b099789dd6da92fd538da992ea6a7959e69`,
because the daily deadline had elapsed and 2026-08-28 was the oldest missing
session. Attempt and operator-review counts were zero; provider completeness
was not asserted. Every proposed 8/28 acquisition, Apply-plan, analytics, and
run-journal target was absent, and no matching timer, service, or residual
calculation process existed. Full readers reconfirmed the unchanged 392-file
`/data` fingerprint and then-active MI/Snapshot. No current-revision external
control was supplied or preflighted. At that historical boundary, the next
possible authorization was one exact 2026-08-28 Identity fetch followed by a
separate Apply review. The authorized round was subsequently completed as
recorded in the active-state table and
[complete audit](../audits/daily-eod-complete-deployment-2026-08-29.md). See
[the readiness audit](../audits/daily-eod-readiness-2026-08-29.md).

## Analytics and presentation

- Market Regime: Primary 47.3666 Balanced; Secondary 47.6047 Balanced. Both
  instantaneous candidates are Defensive, but the confirmed state remains
  Balanced under the frozen hysteresis rule.
- Fixed registry: 30 ETFs and 16 relationships with 5/10/20-session windows.
- Relationship history: 336 rows over 26 sessions; confidence is low.
- English and Simplified Chinese use one language-neutral payload. English is
  the first-visit default.
- Credential and equal-capability guest entry both create the same role-free
  protected Session and load the same product payload.
- Production bundles exclude synthetic Dashboard data and fail closed on API
  or Snapshot failure.
- Production contains Candidate publication 1.1, MI 1.2, Snapshot 1.10 /
  Dashboard 2.7, the independent Candidate, Entry Geometry, and Strategy
  Oracles, formally bound Visual Context, strict frontend parsing, lazy
  Candidate detail/strategy products,
  and the bilingual entry-location view. Leadership rank and entry location
  remain separate axes.
- The active formal Candidate audit is
  `/tmp/whalpha-candidate-phase5c-20260828`, fingerprint
  `39f26ded1dbdd5359eca9d6f3c49dc0b1286531f31a5a61845c0a955ad145412`.
  The bound Entry Geometry audit is
  `/tmp/whalpha-candidate-entry-20260828`, fingerprint
  `fb072d180744d951a052d8a48235a205258078effe7a53ec1d74ff3f5f96e63d`.
  Both formal rereads have zero Oracle mismatch and no external or Production
  writes; Entry Geometry input-permutation equivalence is true.
- Primary Entry Geometry assesses 1,714 securities: 59 technical-review-ready,
  1,173 monitor-for-trigger, 54 wait-for-reset, and 428 deprioritized. Its 52
  strong-but-extended results demonstrate that strong leadership does not
  automatically become an entry instruction. This is distribution evidence,
  not outcome validation.
- The active Candidate payload has 686 Primary and 744 Secondary records. Its
  Snapshot 1.10 first-load summary is 2,061,314 bytes and retains 32 on-demand
  detail shards. Repository source now adds ADR 0048's Snapshot 1.8 /
  Dashboard 2.5 lossless delivery projection: a 1,490,756-byte first-load
  summary plus 32 stable-ID detail shards of 474,940–1,028,834 bytes. A real
  `/tmp` 2026-08-26 build formally reconstructed the unchanged full Candidate
  1.1 publication with the same 496/532 counts. A separate lag-zero build
  produced and validated approval plan 2.3 without applying it. The later
  authorized 1.9/2.6 release publishes this lossless split; guest and
  credential Sessions remain capability-identical by contract.
- ADR 0060 separates full Candidate research validation from MI publication
  custody. The immutable completion manifest, every artifact SHA/size,
  parameters, zero-mismatch Oracle, equivalence gates, and Entry Geometry
  lineage remain mandatory, while Plan/Apply no longer recreate all historical
  typed rows. On the real 2026-08-26 audit, custody-only validation took 1.55
  seconds and the complete bounded Candidate 1.1 projection took 11.29 seconds
  with unchanged 496/532 counts and Candidate publication fingerprint.
- ADR 0060 also separates completed source-audit custody from calculation
  replay. The real 2026-08-26 MI source binding now rehashes all 26 declared
  EOD Parquet files, validates EOD/Identity manifests and immutable Activation
  membership, but does not rebuild the price panel or replay Activation's
  historical liquidity calculation. It fell from 53.74 to 2.98 seconds with
  unchanged Phase 1a history and preview fingerprints; Plan/Apply retain the
  whole-`/data` inventory CAS, and full source replay remains available through
  the read-only context report's explicit option.
- Repository source also contains ADR 0049's typed strategy-channel shadow
  taxonomy for momentum breakout, strong-stock pullback, trend continuation,
  technical reversal, fundamental value reversal, and defensive rotation.
  Scores/ranks are restricted to same-channel research priority; market fit,
  event context, entry geometry, and future option expression remain separate.
  ADR 0056 now adds a fixed, unvalidated Dell/offline preview for the first
  three technical channels and an eight-record-per-channel bounded consumer.
  The active 2026-08-28 offline calculation produced reconciled full-
  population counts
  and deterministic batch/consumer fingerprints. Its independent Oracle
  recomputed score, status, and rank without importing the Production
  calculator. The immutable `/tmp` audit fingerprint is
  `2f254623c9da96f36e57c9066bba406b688dee6c884cd3351fb8f5beaa517256`;
  both Universes have zero mismatches and input-permutation equivalence. It has
  no direct score/rank effect. ADR 0057 adds a separate
  lazy `candidate-strategy-channels.json` product and bilingual Strategy
  Channels workspace. A real temporary-root Snapshot 1.9 / Dashboard 2.6 build
  formally reread the product: 195,425 bytes, logical fingerprint
  `d4d8ea9a1ae7ae896d0569996810e2cabbca1f02641ee9193583db0ca29dee4b`,
  with 686/744 Candidate counts and 8/8/8/0/0/0 displayed records
  per Universe. ADR 0058 now adds Approval Plan 2.4, strict OCI bundle
  validation, and temporary-guest postflight validation. The authorized
  2026-08-28 release passed Plan 2.4, Apply, the 50-file OCI bundle checks,
  remote switch, and temporary-guest validation with the same product/audit
  fingerprints. The subsequent UI continuity pass preserves Candidate view and
  strategy channel in the URL, removes the unrelated risk-mode control from
  strategy mode, and makes evidence-incomplete channels explicit; 94 frontend
  tests and the Snapshot-mode build pass. Human visual acceptance remains
  pending. Repository source now also adds ADR 0087's bilingual Candidate
  decision-position map. It visualizes only the published close, SMA10/SMA20,
  prior-five-session high/low, reference support, threshold distances, and
  state-confirmation progress. It changes no model or payload and is not
  deployed. ADR 0088 now completes the separate source-bound Dell Visual
  Context 1.0 calculation, independent validator, and formal `/tmp` audit. The
  real 2026-08-28 result provides complete exact 20-session paths for all 3,541
  Candidate rows and left-censor-aware observed state age for 3,382; 159
  current unavailable/stale states remain empty. Its audit fingerprint is
  `3b8ddbf3cc7d35cf0ea2b8f257939d23cec6f1d463e0d16efce9b5fb1f23961f`.
  ADR 0089 now binds that audit into repository-only detail-shard 1.1,
  Snapshot 1.10 / Dashboard 2.7, and Approval Plan 2.5. The browser renders the
  exact path and left-censor-aware observed age through the existing one-request
  lazy detail flow. A real `/tmp` preview kept the 2,061,314-byte summary
  unchanged and added 3,724,116 bytes across the 32 lazy shards. It was later
  published through Snapshot 1.10 and remains included in active 1.11. The parameter-
  bound explanation and URL continuity changes are now
  deployed in OCI release `2026-08-29T133847Z-1490b37f25b3`. ADR 0059 now records
  the user's exact 2026-08-26 stale-review
  acknowledgement and adds a separate versioned authorization without
  changing historical 1.0 reads. The exact Apply and postflight are complete;
  the authorization is not reusable or standing. Technical reversal,
  fundamental value reversal, and defensive rotation remain explicitly
  unavailable rather than being synthesized from proxies.
- ADR 0061 adds an exact parameter-bound browser explanation for the three
  implemented technical channels: formula weights, underlying component
  definitions, entry-geometry mapping, status gates, ranking order, and per-
  security weighted contributions. The
  browser reconstructs each displayed score with fixed-point round-half-even
  arithmetic and fails closed on parameter or score drift. A separate Dell-
  side full-population diagnostic found that trend continuation contains every
  qualifying breakout and pullback row in both Universes (Primary union 425,
  Secondary union 451). It therefore remains a broad provisional trend filter,
  not a validated independent setup. The diagnostic compares membership sets,
  never channel scores or outcomes. These ADR 0061 source/UI changes are now
  deployed in OCI release `2026-08-29T133847Z-1490b37f25b3`.
- ADR 0062 adds a repository-only, descriptive continuation fact contract and
  pure Dell calculator for path continuity, trend persistence, recent/prior
  structure, volatility, high-position, and volume context. It produces no
  score, status, rank, threshold, or outcome claim, and an independent raw-
  panel Oracle does not import its calculator. A real read-only 2026-08-26 run
  covered 1,715/1,715 Primary and 1,828/1,828 Secondary Candidate rows with
  zero Oracle mismatch and permutation equivalence. Information discreteness
  and largest-day path share barely separated the existing continuation
  groups, while structure facts mostly restated the frozen filter. No current
  weight changed; Snapshot and the published strategy payload are unchanged.
  See the
  [dated review](../audits/candidate-continuation-facts-review-2026-08-28.md).
- ADR 0063 now gives those facts an immutable tmp-only audit, formal reader,
  and network-prohibited CLI. A bounded current Candidate projection retains
  complete file-custody and selected typed-row validation without rebuilding
  unrelated historical Candidate objects. The real optimized 2026-08-26 stage
  completed in 24.15 seconds, assessed 3,543 rows with zero unavailable and
  zero Oracle mismatch, and produced audit fingerprint
  `3e1226c676f19d95876c8bda96a4739ec551d4be83cfe83cbc1854cf5fafe976`.
  Candidate current projection took 7.16 seconds, panel reread 8.83 seconds,
  facts plus independent Oracle 6.65 seconds, and audit write/reread 0.52
  seconds. This profile does not justify changing the Candidate main-audit
  schema for a new current-batch shard. See the
  [formal audit](../audits/candidate-continuation-facts-formal-audit-2026-08-28.md).
- ADR 0064 advances the descriptive layer to Continuation Facts 1.1 with six
  t-1-normalized breakout-anatomy facts. The real 2026-08-26 formal audit
  assessed 3,543 rows with zero unavailable facts, zero independent-Oracle
  mismatch, exact permutation equivalence, and audit fingerprint
  `6e4b996cd7b75d49bf5f60fda94dfb6942da33d049c9b8589eb5f5fe455247a8`.
  The Production UI now labels Momentum Breakout records as confirmed,
  near-trigger, or extended/reset-first and explicitly states that Advance +
  Watch is not a completed-breakout list. The new facts remain shadow-only and
  do not change the published score, status, rank, or Snapshot payload.
- ADR 0050 adds the repository-only chronological evaluation boundary: source-
  dated signals are sealed without outcomes, and 1/3/5-session underlying-
  stock labels may be attached only later under a fixed no-random-split,
  five-session purge/embargo policy. Current-constituent replay is not
  performance-eligible. No evaluation dataset or result exists; 29 sessions,
  missing daily point-in-time membership, and incomplete corporate-action
  governance remain hard blockers.
- ADR 0097 names the future Quant Research Lab / 量化研究实验室 and adds the
  immutable first `strong-stock-pullback-research/1.0` preregistration. It
  compares pullback/recovery signals with same-session eligible-leader non-
  signal controls, fixes three sessions as the primary horizon, and bounds
  development to 24 combinations before locked validation and untouched
  holdout. Fingerprint
  `1b8752d67615d997f5bfa070c3222a7b036840063c2ccc46411a768265197d6f`
  is `preregistered_data_blocked`; no performance result, runtime, page, or
  Production authority exists.
- ADR 0098 adds the deterministic Dell-local Strategy Research Readiness 1.0
  check. Its 2026-08-30 socket-guarded formal reread covers 31 canonical
  EOD/Identity sessions through 2026-08-28 and returns `data_blocked`, logical
  fingerprint
  `4d3b5a1b472f710638f024443e2ad6c1dea1f4dd25920c2cd9eb1d3a51802116`.
  The 252-session minimum and complete membership/action/lifecycle/adjustment/
  matured-window evidence remain unmet. Even a future complete result permits
  only a separate development review, never automatic tuning or performance
  claims.
- ADR 0099 adds the missing physical-evidence boundary. Immutable per-family
  evidence binds exact source completion manifests and payload files; the final
  Historical Coverage reader verifies safe paths, self-fingerprints, file sets,
  counts, logical identities, and every physical SHA before returning a typed
  manifest. The readiness CLI accepts an exact coverage ID only. A 252-session
  six-family temporary-root fixture reaches review-only readiness, but real
  `/data` has no Historical Coverage directory and remains `data_blocked`.
- ADR 0100 bridges the current real bytes into that boundary without a data
  transition. The socket-guarded 2026-08-30 command formally reread 31 EOD and
  31 EOD-bound Identity artifacts, then transitively validated deterministic
  unpublished evidence fingerprints
  `d7def47ee1fba89760a016ba52d79313bf3729aed2fee421c4e05a2596299cd5`
  and
  `a69530ea830f448ecb90949c3f2a4a871a87ae015d2c2d8e0e6ae0582e5d4e76`.
  It counted 306,539 EOD rows and 307,466 canonical Identity instrument rows.
  `/data` stayed exactly 694 files / 503,568,026 bytes; evidence/Coverage
  directories remain absent and readiness remains 31/252 `data_blocked`.
- ADR 0101 produces the first current, clean-main Historical Pilot baseline.
  It binds revision `017ab5657edaa4bf3bd90ac2437448a7486f7b4b`, the exact
  inventory fingerprint
  `b32d70ae94098bf753282ff2eaa89f241bedc469995bfcd2ac97c2568ddb35ca`,
  and proposed sessions 2026-07-14 through 2026-07-16. The 75-request plan
  fingerprint is
  `ea6faae1d7f5cd3cd80ce349915a8094bc9e78e7e201f72638a06773f4e01899`;
  the baseline fingerprint is
  `7a8ab595707844fb57f4e64651a9e2db16f16246984a945cce3897ee031d7f28`.
  It is blocked by account entitlement, equal-capability permission, and
  lifecycle/terminal coverage; acknowledgement is null and no action occurred.
- ADR 0102 now implements the provider-neutral temporary source-package seam
  that a future authorized Pilot transport must use before canonical mapping.
  It freezes already captured sanitized JSON below the exact `/tmp` Pilot plan,
  binds permission, entitlement, lifecycle-review, and authorization evidence,
  enforces every planned scope and request ceiling, and formally rereads every
  byte. The implementation is synthetic-fixture-only and has no transport,
  credential loader, CLI, default root, `/data` Apply, publication, deployment,
  or scheduler authority. A concise Massive inquiry is prepared but not sent.
- A credential-free 2026-08-27 historical-readiness audit returns
  `NOT_READY_FOR_PERFORMANCE_EVALUATION`. It verified 286,652 bars, 29/29 SPY
  coverage, and same-session Identity binding, but found no daily Universe
  membership or corporate-action dataset, all bars flagged with unverified
  all-one adjustment factors, and no retained inactive/delisted Identity rows.
  It established source/retention design—not formula tuning or a physical
  backtest dataset—as the next safe work at that audit point.
- Repository source now also accepts ADR 0051 and Historical Research Data
  Foundation V1. The design separates raw EOD, point-in-time Identity, daily
  membership, corporate actions, lifecycle/terminal evidence, and explicit
  adjustment ledgers; 252 sessions is the acquisition floor and 504 is
  preferred. Provider-neutral Pydantic row/manifest contracts now enforce
  three clocks, stable-ID lineage, tri-state membership, distinct split/total-
  return factors, and a 252-session research-ready floor using synthetic
  fixtures. Explicit Arrow schemas and immutable temporary-root Parquet
  repositories now cover source action observations, lifecycle, membership,
  and adjustments with formal reread and tamper/conflict gates. Provider source
  observations cannot substitute for canonical Corporate Action coverage.
  This adds no canonical dataset, provider verification, `/data` write,
  formula, publication, or deployment.
- ADR 0086 now advances Daily Universe Membership from fixture-only persistence
  to a complete physical partition contract. Manifest `1.1` proves one exact
  stable-ID evaluated base, complete Primary/Secondary three-state ledgers,
  uniform point-in-time provenance, and source fingerprints. A real read-only
  Dell pilot formally reread the completed 2026-08-19 reviewed full-base source
  and wrote only `/tmp`: 4,565 evaluated IDs per Universe, 9,130 rows, Primary
  1,718 included / 2,775 excluded / 72 quarantined, and Secondary 1,831 /
  2,645 / 89. Its origin is `reconstructed_point_in_time`; no other date was
  inferred. The reviewed source completed on 2026-08-21, after the analysis
  session, so every non-quarantined row carries a later-known-source warning
  and the pilot is mechanics-only for anti-look-ahead evaluation. Canonical
  `/data`, active analytics, and Production were unchanged.
- That 2026-08-28 public-source/storage review is now complete. Massive Basic's
  documented EOD, point-in-time reference, split, and dividend shapes are
  technically plausible, and projected Dell storage is small. A real pilot is
  not authorized: current account entitlement is unverified, complete merger/
  successor/terminal evidence is missing, and official individual-use terms
  conflict with equal-capability friend/guest access and raise a separate non-
  display/derived-use question. No access, data, or deployment state changed.
  Saved synthetic current-endpoint split/dividend mapping and independent
  Decimal adjustment invariants are now also implemented. Missing or ambiguous
  stable IDs and incomplete evidence quarantine; unanchored rows become
  explicit safe issues. Provider cumulative adjustment evidence is never
  treated as a single-event factor without a declared common basis. The next
  safe slice is now complete as `historical-research-pilot-plan/1.0`: a pure
  caller-inventory planner that enforces one-to-three exact XNYS sessions, the
  reviewed 80-request ceiling, zero retry, serial pacing, deterministic future
  `/tmp` package paths, and permanent `not_authorized` output. It does not scan
  `/data`, access credentials, call a provider, or write data. A real pilot
  remains blocked on equal-capability source permission, account entitlement,
  lifecycle source coverage, and separate exact authorization. The user has
  resolved product posture: guest and credential shared content remain
  identical; incompatible sources are not converted into an owner-only tier.
- ADR 0052 and Data Record Governance V1 now define one executable family
  registry plus separate layer, disposition, evidence, quality, coverage,
  point-in-time, retention, content-scope, and serving dimensions. Existing
  domain states remain authoritative and no dataset was rewritten.
- ADR 0053 adds the pure historical Pilot approval review. The deterministic
  preliminary window is 2026-07-14 through 2026-07-16, immediately before the
  documented retained boundary, with 75 serial requests and no unnamed Ticker
  Events. The current review remains blocked and produces no acknowledgement;
  no provider, credential, `/data`, `/tmp`, publication, or deployment changed.
- The broader dated official-source review now returns
  `NO_SINGLE_SOURCE_CLEARED` and `HYBRID_SOURCE_PATH_RECOMMENDED`. SEC is the
  preferred open filing/fundamental/event evidence lane; GLEIF and OpenFIGI
  are identifier crosswalk candidates; Nasdaq Daily List is a licensed action/
  listing candidate; and EOD requires a separately licensed raw/derived/
  delivery-compatible source. Twelve Data has a possible paid redistribution
  path but is neither selected nor cleared. ADR 0054 and executable Source
  Permission Governance V1 now make six uses independent: Dell acquisition,
  raw retention, derived analysis, equal-capability raw display, derived
  display, and machine delivery. Any missing, stale, blocked, or unresolved use
  fails closed and every result has zero operational authority. No provider,
  data, deployment, or `/data` state changed.
- Historical Pilot approval review is now contract 1.1. Its permission gate is
  derived from exact EOD, point-in-time Identity, and corporate-action source-
  observation assessments covering all six uses, from one source/review at the
  exact approval time. Callers cannot submit a manual satisfied permission
  gate. The package remains blocked and grants no acquisition or write.
- Source permission reviews and assessments now also have an immutable,
  content-addressed caller-root repository with atomic publish, formal reread,
  idempotency, corruption/conflict/partial-target rejection, and symlink
  safety. It has no default `/data` root, CLI, active pointer, provider client,
  page bodies, or credentials; only temporary-directory fixtures exist.
- ADR 0055 and Source Resolution Governance V1 now make source composition
  mechanical per family and fact scope. Policies bind exact permission-review
  fingerprints, source roles, precedence, and matching thresholds while
  structurally disabling ticker joins and first-non-null selection. Any usable
  contradiction quarantines without majority vote; missing required evidence
  remains unavailable. Only synthetic facts were resolved and every decision
  has zero operational authority.
- The exact Source Selection and Permission Inquiry Packet V1 is prepared but
  not sent. It covers equal-capability display/browser delivery, Dell
  retention/derivation, termination deletion, history/lifecycle coverage,
  adjustments/corrections, availability, attribution, and pricing. General
  pre-feature data-governance design is now closed; source selection, real
  adapters, acquisition, and evaluation remain separately gated.
- Production contains the tested first-level workspace
  shell and user-facing `Market Regime & Opportunities` / `市场风向与机会` name.
  Market Regime & Opportunities is the first navigation item and default
  workspace; Market Structure & Activity is second.
  It centralizes Universe/language/Session controls, adds a factual first-screen
  market-structure summary, Daily Decision Brief, decision-lane relationship
  selection, prior-state markers, consolidated reliability warning, and
  collapsed 16-pair audit table.
- The public data-free Session entry is now a bilingual product introduction,
  not only an authentication panel. It uses the dark WH mark, keeps credential
  and equal-capability guest entry in the first viewport, presents the complete
  decision chain, and in active Production separates five live capabilities
  from three planned and one later capability along a central visual path.
  Sector ETF Rotation is now one of those live capabilities.
  The page makes the
  explain-before-ranking, counterevidence, context, fund-flow terminology, and
  stock-versus-option-return guardrails visible before entry.
- Repository source now carries the score-free 11-record Sector ETF Rotation
  product through Market Intelligence 1.3, Snapshot 1.11 / Dashboard 2.8, and
  OCI bundle validation. Approval Plans 1.3 and 2.6 bind the exact audit,
  product, history, Strategy, and Visual Context lineage. A dedicated browser
  workspace lazily loads the checksum-bound file and keeps 5/10/20-session
  relative leadership, acceleration, and persistence separate. A real
  2026-08-28 tmp-only MI 1.3 rehearsal and Snapshot 1.11/Plan 2.6 build passed
  with zero Production writes. Automation Plan 1.6 and Executor 1.5 now add a
  strict Candidate Visual Context stage and pass its exact audit into Plan 2.6;
  a real 3,541-row `/tmp` executor rehearsal reproduced the prior fingerprint
  with zero Oracle mismatch. ADR 0095 now shares one exact `/tmp`/persistent
  custody policy across every analytics writer and reader. A real 2026-08-28
  persistent Dell rehearsal completed all nine analytics directories with
  owner-only custody, no residue, zero Oracle mismatch, zero request, and zero
  Production write. The separately authorized MI 1.3 and Snapshot 1.11 / Plan
  2.6 Applies then formed one exact active lineage. Both the standard and
  persistent 52-checksummed-file bundles formally reread with identical bundle
  fingerprint `6e2e08f1e3e9c3d06c3c069e751fce1b9ac2433837952aa2f95186f27c1721e0`;
  persistent directories are `0700` and files `0400`. ADR 0096 advances the
  read-only planner to Plan 1.8 and removes only the superseded ADR 0094 stop.
  Two real 2026-08-28 replays reread all 18 current/prior observations and
  deterministically reached deployment review with fingerprint
  `0782f8793a8564b7b17f354eb81e602afe49c1fe8154bcc371e39ebacee51d83`,
  zero requests/writes, and no publication, deployment, or scheduler authority.
  Active Production is MI 1.3 and Snapshot 1.11 / Dashboard 2.8.

## OCI production state

The active remote release and matching local immutable bundle are
`2026-08-28T141747Z-83f9b629279c`, built from deployed source commit
`83f9b629279c0e7e949cf01b454ebfda60b35900` and bound to Market Intelligence
`2026-08-28T135850Z-f483d6999a3e`. A later repository HEAD does not
invalidate this immutable lineage; the report exposes whether the two commits
match rather than hiding the bundle.

The 2026-08-30 Sector Rotation deployment passed formal Snapshot Plan 2.6,
ordinary-fresh Snapshot Apply, exact 52-checksummed-file serving-bundle reread, remote
preflight, Nginx configuration checks,
atomic apply, unauthenticated protection, and the deployment tool's temporary
guest Session postflight against the exact Snapshot 1.11 payload, Candidate,
Strategy, Sector Rotation resources, and root PNG favicon.
No credential or cookie content was printed or retained.
The independent remote-state report also matched local manifest/checksum
hashes, found zero failed units or staging/failed residue, and recorded state
fingerprint
`50781e2bb39fa6ec56667c34b3455a9c9c60fcfe0c40ad323a1fb1397509bfcf`.
Password-based and visual browser
behavior remains a manual user check. The local report remains network-free
and cannot replace this separately authorized OCI check.

## Product guardrails

- Decision support, not automated trading, execution, or prediction.
- Conclusion first, with raw values, parameters, contributions, evidence,
  counterevidence, and market-state adjustment available for inspection.
- Never call price/volume proxies actual fund flow.
- Never call underlying-stock forward return an option return.
- Keep security form, issuer structure, listing scope, evidence, and Universe
  disposition separate and effective-dated by stable `instrument_id`.
- Quarantine unknown, ambiguous, malformed, heuristic-only, and insufficient-
  evidence records.
- Core remains the future policy goal and Broad the future secondary policy,
  but active provider-form Universes remain provisional until authoritative
  issuer evidence satisfies the documented gates.

## Explicitly not authorized by this context

The completed 2026-08-28 acquisition, canonical Apply, publication, Snapshot,
bundle, and deployment actions are evidence, not
continuing authority. This handoff does not authorize further provider or SEC
access, credential inspection, EOD or Identity acquisition, another canonical Apply,
scheduler changes, Activation, publication,
Snapshot creation, bundle generation, OCI deployment or rollback, guest
access, further UI implementation, another quantitative feature, or guest/
source licensing remediation. The
completed 2026-08-28 publication and deployment described above are evidence,
not continuing authorization.

ADR 0102's fixture-only source-package writer is repository development, not a
new authorization. It does not change the blocked Pilot result or permit the
prepared Massive inquiry to be sent automatically.

## Cross-device continuity

- Windows already has its own dedicated passwordless SSH key and saved Dell
  remote project.
- For Mac, first join the same Tailscale network, then generate a new Mac-only
  SSH key. Never copy the Windows private key.
- Add only the Mac public key to Dell, configure the `dell5820` SSH alias, save
  `/home/hui/projects/trading-intelligence-platform` in Codex Desktop, and run
  the read-only context report before continuing work.
- Never place literal server addresses, private-key paths, or credentials in
  repository documentation.

## Recovery procedure for a new task

1. Read `AGENTS.md`, `README.md`, `docs/README.md`, this document, and
   `current-status.md`.
2. Run `scripts/admin/report-current-context.sh` from the source-of-truth
   repository.
3. Compare repository, deployed-source commit, EOD, Identity, Activation,
   Market Intelligence, Snapshot, inventory, and residue fields with this
   baseline. A newer clean repository HEAD is not itself a deployment mismatch.
4. Classify differences before making changes. Do not silently rewrite an
   active pointer, rerun acquisition, or deploy.
5. Read only the product, architecture, operation, ADR, and audit documents
   relevant to the selected single objective.
