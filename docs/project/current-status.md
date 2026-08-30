# Current Status

Status date: 2026-08-30

This document is the concise current-state summary. Exact publication IDs,
fingerprints, verification scope, and cross-device handoff are maintained in
the [authoritative current context](current-context.md). Historical execution
detail belongs in the [changelog](changelog.md) and dated audits, not here.

## Current product

WH Alpha is a Session-protected, bilingual U.S. equity market-intelligence
dashboard for discretionary research. Its intended decision chain is:

```text
market state -> strength direction -> sector/theme -> stock candidate
-> trade preparation -> entry/invalidation -> position management
```

The current production-capable source slice covers market overview, breadth, movers,
Trading Activity Map, benchmark and sector-ETF context, a transparent five-
dimension Market Regime, 16 preregistered ETF relationships, and a bounded
Stock Candidate research workspace. English is
the first-visit default; English and Simplified Chinese render the same
language-neutral analytics.

Repository source now presents Market Regime & Opportunities
(`市场风向与机会`), Market Structure & Activity, and Stock Candidates
(`个股候选`) as first-level workspaces with persistent desktop
left navigation and one shared Universe/language/Session utility header. Market
Regime & Opportunities is the first item and default workspace; Market
Structure & Activity is second and begins with a factual “what is happening
now” summary.
It explains Universe membership versus same-session comparable coverage. A
Daily Decision Brief adds one- and five-session Composite changes, distances
to both state boundaries, and an explicit broad Risk-on stance. Six fixed
economic decision lanes precede the collapsed complete 16-pair audit table;
each highlight shows current-versus-prior relationship state, persistence,
one-/five-session change, and a bounded ten-point state path; the short-history
warning is consolidated. These changes and equal-capability guest entry are
deployed in the current OCI release.

The public data-free entry now uses the dark WH mark in a mature full-page
brand experience. Credential and guest entry remain immediately available in
the first viewport and open the same workspace. Below them, a bilingual
alternating capability path distinguishes four live capabilities, four planned
capabilities, and one later position-management capability; planned work is
never presented as available functionality. Product principles and the full
market-to-position decision chain are visible before Session entry.

The post-entry workspace now uses the same deep-navy, cyan, and restrained
green identity across the shared sidebar, utility header, first-screen briefs,
cards, tables, drawers, and mobile navigation. The WH mark is present in the
persistent product lockup. Guest and credential Sessions render this exact
same application shell and retain identical data and capabilities.

The interface supports human decisions. It does not issue orders, model option
returns, or claim causality. Price and volume analytics are participation or
relative-performance proxies, never actual fund flow.

## Active data and publications

- Canonical EOD and canonical Identity are both completed through 2026-08-28
  and formally aligned.
- Latest EOD contains 9,942 rows. Latest Identity and the Identity snapshot
  bound to EOD contain 9,981 canonical instruments, 13,151 provider
  observations, and 9,981 resolver rows.
- Activation V2 is active with Common Shares as the sole default:
  - Primary: 1,718 CS.
  - Secondary: 1,831 = 1,718 CS + 113 ADRC.
- Active Market Intelligence publication is
  `2026-08-29T080431Z-785ab49dfedd`, contract 1.2, with 686 Primary and 744
  Secondary bounded Candidate research records across the fixed entry lanes.
- Active Dashboard Snapshot is
  `2026-08-30T092455Z-1894b9c9b95e`, contract 1.10 / Dashboard 2.7.
- The locally retained OCI bundle and live-verified deployed release are
  `2026-08-30T092455Z-1894b9c9b95e` from source commit `1894b9c9b95e`.

The active analytics and Snapshot are ordinary fresh publications for
2026-08-28: actual and expected session match, lag is zero, review mode is
false, and no stale-review exception was used. Snapshot
`2026-08-30T085601Z-6c732e9cd602` is the exact planned rollback reference. The
2026-08-30 post-deployment reader found 608 files / 404,002,859 bytes under
`/data`, inventory fingerprint
`be0846beeee56bbac1856056ab23b2c03c26c4972d479d7fcc44e2e2e64a3db6`,
zero symlinks, and zero publication residue.

### Daily automation development state

The repository daily planner/executor now governs ten ordered offline daily
stages: Phase 1a, incremental Phase 1b, Candidate, Entry Geometry, ETF
Relationships, Market Preview, Strategy Channels, Market Intelligence
approval-plan preparation, Dashboard Snapshot approval-plan preparation, and
exact active-Snapshot serving-bundle construction.
Every invocation still performs at most one transition. The latter stages
require the exact target session and upstream logical fingerprints. The MI
Plan action additionally binds an explicit UTC
creation time and expected `/data` inventory fingerprint, writes only two new
`/tmp` artifacts, formally rereads them, and stops at publication review.
After a separately invoked MI Apply makes that exact publication active, the
Snapshot Plan action binds an explicit UTC time, exact active MI and same-
session Strategy Channel audit, writes only new `/tmp` artifacts, formally
rereads Plan 2.4, and stops at Snapshot publication review. After separately
invoked Snapshot Apply proves the planned pointer active, the bundle action
requires an explicit UTC time and clean matching Dell source, builds only
beneath a new `/tmp` candidate root, formally rereads every file and exact
Snapshot binding, and stops at deployment review. `analytics_ready` therefore
describes a reviewed boundary, not write authority; it grants no MI Apply,
Snapshot Apply, OCI deployment, `/data`, credential, or scheduler authority.
No data-transition scheduler or unattended Production publication/deployment
chain has been enabled. The separately installed timer runs only the read-only
planner described below.

ADR 0076 adds the first read-only scheduler-wake plan. It validates every
small canonical EOD completion manifest, fully rereads only the latest
Parquet/Identity binding, and uses the XNYS calendar to select the oldest
missing session and next close-plus-stabilization review time. A real Dell
review at 2026-08-29T14:30:00Z completed in about 2.8 seconds, reported current
EOD through 2026-08-28, next target 2026-08-31, and next check 20:30 UTC.
Default and explicitly enabled-candidate reviews both invoked no coordinator,
read no credential, used no network, and wrote no file or Production state.
All 1,701 backend tests pass. No service or timer was installed at that ADR
0076 boundary; repeated distinct-wake handling is recorded in ADR 0077 and the
later host installation in ADR 0079 below.

ADR 0077 adds the default-off bridge from one exact enabled-candidate wake plan
to at most one supplied coordinator call. It recomputes both the full plan
content fingerprint and the returned coordinator-result fingerprint, rejects
content/target/authority drift, retains the accepted result identity, and never
retries, routes recovery, or delivers an alert in-process. The credential-free
synthetic rehearsal
covered current, oldest-missing, retry-wait, unresolved-interruption, and
alert-required wakes. It made four fake coordinator calls across five separate
scenarios, never more than one per wake, and zero real credential, network,
filesystem, or Production activity.

ADR 0078 now adds the exact non-installed user-systemd candidate. It binds
Dell/hui, clean `main`, an exact Git revision, canonical `/data`, the read-only
planner entrypoint, two New York calendar expressions, and future service/timer
SHA-256 identities. It fixes and rechecks the project Python interpreter rather
than inheriting runtime overrides. The proposed service independently rechecks
host, user, branch, clean revision, and uses the system UTC clock; it cannot
invoke the coordinator or load capabilities. At that review boundary Dell had
systemd 255 and a running user manager but `hui` had `linger=no`; no installation
or host change had yet occurred.

ADR 0079 records the separately authorized host change. `hui` linger is now
enabled and the owner-only read-only user service/timer are installed. The
first controlled start failed before the process with `218/CAPABILITIES`:
`PrivateNetwork`, explicit capability bounding, and capability-changing
`PrivateDevices` are unsupported by this user manager. The timer remained
stopped during diagnosis. The compatible unit retains the exact revision and
Python bindings, read-only system/home, `NoNewPrivileges`, `AF_UNIX`, socket
guard, and timeout. Its controlled start then succeeded in about three seconds,
reporting EOD current through 2026-08-28 and zero coordinator, credential,
network, filesystem-write, or Production-write activity. The timer is enabled
only for read-only planning; no data transition, publication, or deployment is
scheduled.

ADR 0080 removes the remaining semantic ambiguity from current contracts.
Planner, scheduled-wake, and rehearsal 1.1 now report only
`scheduler_installation_performed=false`; this proves that the invocation did
not change unit state and is not a claim that the host timer is absent. The
systemd candidate review 1.1 likewise reports operation facts only. Actual
installed/enabled state remains a separate read-only host inspection.

ADR 0081 now adds the repository-only Pipeline Scheduler V2 planning boundary.
It combines scheduler plan 1.1 with a fully fingerprinted same-session
Automation Plan 1.4, so current canonical EOD cannot conceal an unfinished
offline pipeline. A deterministic persistent-workspace contract derives
per-session artifacts plus shared journal/cache roots outside `/tmp`, `/data`,
and Git while preserving legacy `/tmp` plan compatibility. This code performs
no creation, migration, invocation, installation, activation, publication, or
deployment; the installed timer remains on the read-only 1.1 planner. All
1,718 backend tests pass with the two existing dependency warnings.

ADR 0082 now adds a repository-only bounded distinct-wake cadence above V2.
The widest candidate permits at most 16 transition wakes in four hours and
requires five minutes from one completion to the next start. It consumes a
fingerprinted evidence chain, requires both candidate layers before proposing
one invocation, and stops at known failure, unknown outcome, manual review,
blocked state, or either budget. V2 verification now also rejects
re-fingerprinted semantic or authority conflicts. No evidence store, runtime
bridge, unit, timer change, invocation, credential, request, `/data` write,
publication, or deployment is part of this repository boundary. The installed
timer remains the unchanged read-only planner. All 1,731 backend tests pass
with the two existing dependency warnings.

ADR 0083 now reuses the existing owner-only daily run journal as the sole
cadence evidence store. Journal 1.7 retains the complete enabled cadence plan
and known Evidence 1.2 in a standalone event only when no action is unresolved;
old 1.2–1.6 events remain readable. Coordinator 1.12 distinguishes successful,
waiting, and failed provider/offline outcomes, and strict adapters project them
without inferring progress. No real journal event, directory, runtime bridge,
unit/timer change, request, `/data` write, publication, or deployment occurred.
All 1,746 backend tests pass with the two existing dependency warnings.

ADR 0084 closes the remaining invoke-then-record crash gap without a second
store or lock hierarchy. Journal 1.8 and cadence custody 1.1 reserve one exact
enabled wake before its side-effect boundary, allow the existing action custody
to run once, and close only with a formally known matching result. Exceptions,
invalid results, interruption, or retention failure leave an unresolved
reservation that blocks replay and later sessions. Pipeline Runtime 1.0 is
default-off and repository-only; it requires both exact plan fingerprints and
one scope-matched capability, and never loops, retries, recovers, publishes, or
deploys. Old journal 1.2–1.7 and direct cadence 1.7 evidence remain readable.
No CLI, real cadence event/root, capability, unit/timer change, request, `/data`
write, publication, deployment, or Production invocation occurred. All 1,754
backend tests pass with the two existing dependency warnings.

ADR 0085 now adds the read-only Cadence Diagnosis 1.0 contract for an open
runtime reservation. It verifies the supplied same-session hash chain and
distinguishes no nested evidence, an unresolved action routed only to existing
no-replay recovery, a formal terminal exposed only as a later disposition
candidate, and blocked conflicting evidence. It never infers a coordinator
result or retry time and has zero request/write/replay/retry/recovery/resolution
authority. No CLI, real journal read/event, timer change, request, `/data`
write, publication, deployment, or Production operation occurred. All 1,764
backend tests pass with the two existing dependency warnings.

ADR 0069 now adds the next repository-only control boundary: MI Apply can be
performed by exactly one explicit, host-pinned CLI invocation with the exact
plan SHA, Production-state fingerprint, and any plan-bound review
acknowledgement. The default path still stops at publication review. A separate
journal 1.4 event family reserves before Apply, formal active-state reread is
required for success, and interruption recovery never writes or links. At that
implementation boundary it had not been invoked against Production. Snapshot
Apply, bundle, OCI deployment, and scheduler activation remained outside that
daily transition; later controlled publication is recorded above.

ADR 0070 extends the repository-only offline chain to a ninth action after MI
Apply: prepare Dashboard Snapshot Approval Plan 2.4 from the exact active MI
publication and same-session Strategy Channel audit. It uses explicit UTC and
new `/tmp` paths, formally rereads the full Snapshot candidate/plan, and stops
at `review_snapshot_publication`. At that implementation boundary the action
had not generated or applied a real Snapshot; later controlled use is recorded
above.

ADR 0071 adds the next repository-only write boundary: an explicit,
host-pinned, default-off one-shot Dashboard Snapshot Apply port under
coordinator 1.9 and backward-readable journal 1.5. Reservation binds the exact
unchanged Snapshot-review plan, Plan 2.4 whole-file SHA, current Snapshot
state, Activation pointer, target/staging absence, current freshness or exact
review acknowledgement hash, and all paths. Success requires the exact active
Snapshot, immutable target, contracts, aggregate, manifest, session, and
planned pointer to formally reread. Recovery never applies or links; it only
reconciles exact success, proves untouched state, or blocks partial/changed/
ambiguous state. At that implementation boundary the port was uninstalled and
uninvoked. The later separately authorized Snapshot publication is recorded
above; the port grants no standing or unattended authority.

ADR 0072 advances the planner/executor/coordinator/recovery contracts to
1.4/1.4/1.10/1.2
and adds the tenth offline action only after exact Snapshot activation. The
Serving Bundle 1.0 reader binds the clean source commit, Snapshot aggregate and
manifest hashes, MI/Candidate/Strategy lineage, complete checksum inventory,
English/Chinese policy, equal guest/credential capability, and prohibited-
content flags. It rejects symlinks, source maps, unchecksummed or unexpected
files, partial staging, changed Snapshot bytes, and source/release drift.
Completion stops at `review_bundle_deployment`; no network path or OCI
capability is installed by this action. The legacy `--snapshot-release`
builder shortcut is removed in favor of an exact immutable absolute Snapshot
path. At that implementation boundary it had not built a real candidate or
changed `/data`, the active Snapshot, local retained bundles, OCI, or a
scheduler. Later controlled bundle construction and deployment are recorded
above; one-shot OCI deployment custody and scheduler activation remained
separate authorization boundaries.

ADR 0073 advances coordinator/recovery/journal contracts to 1.11/1.3/1.6 and
adds a default-off one-shot OCI deployment port after exact bundle review. It
binds an owner-only external config SHA, clean Dell `hui`/`main` revision,
exact local bundle fingerprints and source commit, a fresh approved remote
pre-state, and the expected current release. The deployer repeats the current-
release and residue gates immediately before mutation; success is recorded
only after a separate structured inspection proves the exact remote manifest/
checksum identities, service/listener health, protected routes, role-free guest
access, and zero staging/failed residue. Recovery performs one read-only
inspection and never replays Apply. At that implementation boundary the
capability was uninstalled and uninvoked. The later separately authorized OCI
deployment and independent inspection are recorded above; no scheduler or
standing deployment authority was enabled. All 1,647 backend tests passed at
this boundary; no frontend source changed in it.

The repository now includes a full coordinator-to-journal rehearsal using
only temporary custody and a fake OCI transport, plus a network- and write-free
runtime-candidate review command. The default candidate is disabled; an
explicit enabled-candidate review still installs nothing and grants no
deployment authority. At that implementation boundary no external candidate
had been installed and no real remote inspection or Apply had run. The later
one-shot deployment used separately reviewed exact runtime state and is
recorded above. All 1,653 backend tests passed at this boundary.

ADR 0074 now adds repository-only descriptive ETF relationship change views.
The retained Phase 2 history is projected into current-state run duration and
exact one-/five-session changes in rolling 5/10/20 relative returns. The
bilingual UI presents who leads and whether that advantage is strengthening,
weakening, reversing, emerging, or fading. No Phase 2 record, Market
Intelligence payload, state formula, threshold, ranking, or highlight selection
changes. All 1,654 backend tests and 95 frontend tests pass, and the frontend
production build succeeds. This addition is deployed in release
`2026-08-29T133847Z-1490b37f25b3`.

ADR 0075 now adds a repository-only bounded relationship state timeline. It
projects at most the latest ten frozen Phase 2 rows per pair, including state,
confidence, prior-session change, and existing 5/10/20 relative returns. The
bilingual detail view exposes retained-history boundaries and never recomputes
states in the browser. All 1,656 backend tests and 96 frontend tests pass, and
the frontend production build succeeds. A formal read-only construction from
the active 2026-08-28 Market Intelligence payload reconciles all 16 pairs,
showing 10 of 21 retained relationship sessions. This addition is deployed in
release `2026-08-29T133847Z-1490b37f25b3`.
The first write-free publication preflight found that the backend reader also
needed to accept prior Snapshots without the additive fields. That compatibility
is corrected and regression-covered; the failed preflight created only a
bounded `/tmp` candidate and changed neither `/data` nor Production. The fix
was applied before the successful Snapshot and OCI deployment.

### Historical 2026-08-27 recovery and pipeline evidence

The following details are retained as historical recovery and performance
evidence. They no longer describe the active publication or next operational
action.

The exact failed EOD terminal has one immutable offline operator review. After
its conservative 2026-08-28T16:00:00Z boundary, the user separately authorized
one exact EOD-only retry. At revision `dd314db`, one request succeeded and
produced a frozen 12,552-result 2026-08-27 package with zero Production writes.
The separately authorized canonical Apply is complete. The approved 9,945-row
partition matches its plan, has zero duplicate business keys and zero orphan
references, and advanced `/data` by the exact two files / 1,056,432 bytes.
At that Apply boundary, the next automation action was offline
`calculate_phase1a`; active analytics and the public Dashboard remained on the
2026-08-26 stale-review release.

Offline 2026-08-27 Phase 1a is now complete with audit fingerprint
`887024c4847ef74a28a713c439359f3a4d8d93e49269ab58f2f0177c61159c53`.
Primary/Secondary composites are 67.4134 / 67.5471, all configured weight is
available, no metric is missing, and the independent Oracle has zero mismatch.
Incremental Phase 1b is also complete from the corrected V1.0.1 prior lineage,
with audit fingerprint
`6a3a530280dbe9eea6617d76e980ed453b47e087d9e35fe588e8f7b6fe630801`.
Primary/Secondary remain confirmed Balanced at those composites, the
independent Oracle has zero mismatch, and every incremental prefix/restart/
source gate passes. The first attempt safely rejected a legacy V1.0.0 prior
path without creating a target; the corrected path completed normally. At that
Phase 1b boundary, the next exact action was `calculate_candidate_daily`.
`/data`, Market Intelligence, Snapshot, Dashboard, and OCI remained unchanged.

The 2026-08-27 verified-prior daily Candidate append is now complete with audit
fingerprint
`0fa85ae742ef47e7278c444c12f05f2082e38a5071068a5787655a11271eb4e4`.
It passed the current-session independent Oracle and every incremental
equivalence gate. Current batches contain 1,714 Primary and 1,827 Secondary
comparable securities; all active members remain represented in the state
ledger with four unavailable in each Universe. At that boundary the exact next
operational action was `calculate_entry_geometry`.
The 422.8 MB cumulative JSON audit made the performance boundary concrete:
business work before write took 152.94 seconds, while repeated full formal
rereads expanded the journaled action to 576.03 seconds and post-plan memory
to roughly 6.1 GB RSS. Removing redundant control-layer historical
reconstruction is the next engineering priority; it must retain one full
append-input validation, exact custody, typed current-session evidence, locked
plan identity, and fail-closed postconditions.

ADR 0065 implements that bounded optimization. The daily planner now rehashes
all Candidate bytes and validates the small incremental lineage ledger without
rebuilding cumulative historical business rows. Candidate calculation retains
its full typed prior-input validation. On the real current audit, planning now
takes 9.45 seconds at 221,640 KiB maximum RSS and returns the unchanged plan
fingerprint and `calculate_entry_geometry` next action. All 157 related tests
and all 1,571 backend tests pass.

The 2026-08-27 Entry Geometry action then completed with audit fingerprint
`3aa78cb694a4c06835f19fb6165cd721e62b7fe16f921240ce8a601fcd83c11a`.
All 1,714 / 1,827 current comparable rows were assessed; Oracle mismatch is
zero and input-permutation equivalence is true. Primary/Secondary technical-
review-ready counts are 70 / 73, while 104 / 110 strong-but-extended or other
rows are routed to wait-for-reset. The action is shadow-only and changes no
score/rank, `/data`, active publication, Snapshot, Dashboard, bundle, or OCI
state. Journal event 21 is successful, the post-plan status is
`analytics_ready`, and the next boundary is `review_publication`. Publication
and deployment remain separately unauthorized. The 338.217438-second action
also identifies current-batch Candidate reading as the next safe performance
target; the present audit remains formally valid. All 98 focused tests pass.

The missing same-session Phase 2 and preview are now complete for 2026-08-27.
Phase 2 fingerprint
`1d0efadf75579c2487696fe5933bccfcdc56e40680433a790a9600b3776ec41f`
passes zero-mismatch Oracle and all replay/permutation/prefix gates; preview
payload fingerprint is
`da5b9364ab4e84955c82d3c8666b125e293108dd0093c692830bfef2ccf3d52c`.
The final MI 1.2 review plan passes full source validation and projects 558 /
599 Candidate records, but is `freshness_blocked`: actual 2026-08-27,
expected 2026-08-28, lag one. No applicable exact review authorization exists,
so neither MI Apply nor Snapshot/bundle/deployment ran. ADR 0066 fixes two
duplicated cold-only Candidate evidence lookups discovered by the first real
daily-schema Plan attempts; both failed before plan creation or Production
write. All 1,573 backend tests pass. The network-free 2026-08-28 readiness
review is now complete. The planner selects only `prepare_identity_catchup`;
readiness is `missed_session_recovery` / `review_fetch_authorization`, with
zero attempts, requests, writes, or provider-completeness assertion. Every
proposed 8/28 target is absent, `/data` and active serving state are unchanged,
and no daily timer or service was installed at that historical boundary. No
current-revision external control was supplied or preflighted. The next possible boundary is a
separately authorized single 2026-08-28 Identity fetch, then its own canonical
Apply review. ADR 0067 later added Phase 2, preview, and Strategy Channels to
the offline coordinator. Publication, Snapshot, bundle, deployment, and
scheduler activation remain separate and still block unattended end-to-end
operation.

The first authorized Apply invocation failed closed before reservation because
canonical Apply custody did not project the journal's ADR 0047 operator-review
events even though the coordinator did. No target or `/data` change occurred.
The minimal integration fix passes the exact reviewed-retry regression and
related 59-test suite. Fresh apply-only controls at `6256bf3` then completed
one canonical transition with zero provider requests. The journal ends in
`canonical_apply_succeeded`, no unresolved event remains, and no downstream
calculation or serving action has run.

## Market Regime

- Primary: 47.3666, Balanced; instantaneous candidate state Defensive.
- Secondary: 47.6047, Balanced; instantaneous candidate state Defensive.
- Fixed basket: 30 ETFs.
- Preregistered relationships: 16.
- Windows: 5, 10, and 20 XNYS sessions.
- Relationship-history rows: 336.
- History depth: 26 calculation sessions, so relationship confidence remains
  low and is implementation evidence rather than predictive validation.

The underlying active publication was formally reread after the 2026-08-29
deployment. Exact displayed scores are publication facts, not trade signals.

## Access and deployment boundary

- `/` is the branded credential-or-guest Session entry.
- `/dashboard/` and `/private-data/` share the server-side Session boundary.
- The Auth Service design is localhost-only on OCI.
- Production bundles contain no canonical Parquet, raw provider payload, or
  credentials.
- Synthetic Dashboard data is excluded from the production dependency graph.
  API and Snapshot failures fail closed and never fall back to demo data.
- Guest entry creates the same role-free opaque Session as credential login.
  Guest and credential Sessions expose the same data, functionality, language,
  Universe, precision, freshness, and analytics. No role-based difference is
  authorized.
- The user has reaffirmed that this is a hard shared-product rule. Source
  incompatibility must be resolved through permission or replacement, not an
  owner-only market-analysis tier. Future personal records require a separate
  identity boundary and do not change shared analytics parity.

The 2026-08-29 deployment passed remote preflight, Nginx configuration checks,
atomic apply, unauthenticated protection, and the temporary equal-capability
guest Session postflight defined by the deployment tool. Password-based and
visual browser behavior remains a manual user check because no password was
read or used.

## Current limitations and risks

- The active static payload is fresh through 2026-08-28, but freshness only
  establishes same-session custody; it does not validate predictive quality.
- The retained history is only 31 EOD sessions and the active calculations
  use 26 sessions. This is contract and implementation evidence, not enough
  history for predictive validation or stable threshold calibration.
- Provider security form does not prove issuer operating structure or
  domicile. Both public Universes remain explicitly provisional.
- SEC B2 published no completed source cache or issuer-structure evidence and
  remains paused.
- No point-in-time sector/industry taxonomy, market-cap dataset, fundamentals,
  valuation model, options chain, implied volatility, Greeks, open interest,
  true fund-flow data, automated daily ingestion, scheduler, database/catalog
  service, or general production API exists.
- The 2026-08-28 official Massive terms review found a material product/source
  conflict: individual-use data is described as owner-only, while the active
  equal-capability guest path serves the same provider-derived payload to other
  users. Session protection and non-commercial friend use do not establish
  permission. Owner-only non-display/derivative calculation and retention also
  require clarification. Product posture is resolved in favor of equal-
  capability Sessions; compatible source permission remains unresolved. The
  current review deployment does not resolve or waive that source-policy risk.
- The broader 2026-08-28 official-source review found no single source that is
  both complete for the historical foundation and cleared for the confirmed
  equal-capability product. SEC is suitable open filing/fundamental/event
  evidence; GLEIF and OpenFIGI are open identifier/crosswalk candidates; the
  Nasdaq Daily List is a licensed corporate-action candidate; and raw EOD still
  needs a separately display/derived/delivery-compatible provider. Twelve Data
  has an explicit redistribution add-on path but is not selected or currently
  cleared. Alpha Vantage, Alpaca customer data, and current Massive individual
  terms do not supply a cleared shared-product fallback.
- Historical analytics replay current-as-of membership and are not a
  survivorship-free backtest.
- The frontend production build still reports a JavaScript chunk above 500 KB.
  Production now serves the 1.49 MB Candidate first-load summary plus 32
  on-demand detail shards instead of the 20.4 MB monolith; workspace code
  splitting remains required before substantially expanding the UI.
- Repository source defines six distinct Candidate strategy research questions
  and
  now implements a fixed, unvalidated offline preview for momentum breakout,
  strong-stock pullback, and trend continuation. Each has a separate formula,
  reasons, counterevidence, invalidation, missing-data state, within-channel
  rank, and an eight-record bounded consumer. The 2026-08-26 offline review
  verified mechanics and exposed signal-volume counts, not performance. An
  independent implementation also recomputed score, status, and rank without
  importing the Production calculator. Its atomic `/tmp` audit formally reread
  both source audits and returned zero mismatch for both Universes with input-
  permutation equivalence.
  Technical reversal, fundamental value reversal, and defensive rotation
  remain explicitly unavailable. ADR 0057 now adds a separate 195,211-byte
  product payload, Snapshot 1.9 / Dashboard 2.6 review projection, strict web
  parser, and bilingual lazy-loaded Strategy Channels workspace. A real `/tmp`
  build formally reread the exact strategy-audit lineage and retained the
  496/532 Candidate counts. ADR 0058 adds Approval Plan 2.4 plus strict OCI
  bundle and guest-postflight validation. The authorized 2026-08-28 Plan,
  Apply, 50-file bundle, OCI switch, and temporary-guest postflight all passed;
  Snapshot 1.9 / Dashboard 2.6 introduced the strategy product now retained by
  the active additive 1.10 / 2.7 release.
  A subsequent UI continuity pass makes the Candidate subview and exact
  strategy channel URL-addressable, removes irrelevant risk-mode controls from
  strategy mode, uses the Advance + Watch population in its headline, and
  explicitly labels evidence-incomplete channels. All 94 frontend tests and a
  Snapshot-mode build pass. A Dell-local real-payload preview is available for
  human review; this is not user acceptance or deployment.
  The user has now supplied ADR 0059's exact 2026-08-26 stale-review
  acknowledgement. Repository source adds the separate
  `production-review-deployment/1.1` contract while preserving historical 1.0
  reads. The exact review publication and deployment completed on 2026-08-28;
  this remains a narrow stale-review authorization, not a standing permission.
  ADR 0061 now makes the exact technical-channel formulas, underlying input
  definitions, gates, ranking order, and per-security weighted contributions
  visible and independently
  reconstructs each displayed score in the browser. Its full-population set
  diagnostic found that the current trend-continuation qualifying population
  contains every qualifying breakout and pullback member in both Universes.
  Continuation is therefore explicitly a broad provisional trend filter, not a
  validated independent setup. New consolidation/contraction and trend-
  efficiency facts plus chronological validation are required before revising
  it under a new parameter version. These ADR 0061 explanation and diagnostic
  changes were later included in the deployed 2026-08-28 UI release and remain
  present in the active 2026-08-29 release.
  ADR 0062 now adds a separate source-bound descriptive fact layer for return-
  path continuity, trend persistence, recent/prior structure, volatility,
  closing-high position, and volume context. It has no score, status, rank, or
  threshold and is not a Strategy Preview 1.0 input. A real read-only
  2026-08-26 pass covered all 1,715 Primary and 1,828 Secondary rows with zero
  unavailable values, zero independent-Oracle mismatch, and permutation
  equivalence. The cross-section did not support promoting information
  discreteness, largest-day share, or volatility contraction into current
  weights. This fact layer is repository-only and not deployed.
  ADR 0063 adds its immutable tmp-only audit, formal reader, offline CLI, and a
  bounded current Candidate projection. The optimized real stage takes 24.15
  seconds end to end with the exact fact-batch fingerprints above, zero Oracle
  mismatch, and no partial residue. The remaining seven-second current-batch
  read does not justify changing the upstream Candidate audit schema yet.
- ADR 0050 now defines the anti-look-ahead evaluation contracts, but no signal
  or outcome dataset exists. The historical-readiness audit used 29 sessions;
  canonical retention is now 31 sessions versus the fixed 252-session research
  minimum. Daily point-in-time Universe membership and completed corporate-
  action governance are also missing. Current-constituent replay is explicitly
  ineligible for performance claims.
- The 2026-08-27 historical-readiness audit formally returns
  `NOT_READY_FOR_PERFORMANCE_EVALUATION`: 29 EOD sessions and same-date Identity
  binding are mechanically sound, and SPY covers 29/29 sessions, but daily
  Universe membership, corporate actions, adjustment reconciliation, and
  terminal/delisting identity are absent. Every one of 286,652 retained bars
  carries `adjustment_factors_unverified` and all adjustment factors are one.
- ADR 0051 defines the source-neutral historical foundation and retention
  boundary. Repository source now implements immutable provider-neutral typed
  rows for corporate-action observations, lifecycle evidence, three-state
  daily membership, adjustment entries, and bounded coverage/readiness.
  Explicit PyArrow schemas and immutable temporary-root Parquet repositories
  now pass synthetic round-trip, hash, conflict, corruption, and path-safety
  tests. ADR 0086 adds Membership manifest `1.1`, complete same-base coverage
  gates, and a formal reviewed-full-base reconstruction adapter. Its real
  2026-08-19 `/tmp` pilot contains 9,130 explicit rows over 4,565 stable IDs:
  Primary 1,718 included / 2,775 excluded / 72 quarantined and Secondary 1,831
  / 2,645 / 89. It is `reconstructed_point_in_time`, not `as_operated`.
  Its 2026-08-21 source cutoff follows the 2026-08-19 session, so all otherwise
  valid rows are warning-quality and the pilot is mechanics-only for
  chronological evaluation.
  Canonical multi-session rows and 252/504-session history remain physically
  absent; `/data` and Production were unchanged.
- Stock forward returns must not be described as option returns.
- Unknown, ambiguous, malformed, heuristic-only, or insufficient-evidence
  classifications remain quarantined.

Repository source now implements ADR 0054 Source Permission Governance V1.
Every source review must separately conclude Dell acquisition, raw retention,
derived analysis, equal-capability raw display, derived display, and machine
delivery. Missing, stale, separate-agreement, blocked, or unsupported use fails
closed, and even an eligible assessment carries zero operational authority.
Historical Pilot approval review 1.1 now binds this policy and derives its
permission gate from exact same-time assessments for EOD, point-in-time
Identity, and corporate-action observations. The caller can no longer provide
a standalone satisfied permission assertion or override a blocked review with
forged cleared assessments.
An immutable caller-root repository now provides atomic publish, formal reread,
idempotency, conflict/corruption/partial-target rejection, and symlink safety
for reviews and assessments. It has only been exercised under test temporary
directories; no `/data` permission package or active allowlist exists.

ADR 0055 now closes the planned general source-composition design pass. Source
Resolution Governance V1 binds exact data family/fact scopes, permission-
review fingerprints, evidence roles, precedence, and corroboration thresholds.
Ticker joins and first-non-null selection are disabled; any usable conflict
quarantines and missing required evidence stays unavailable. The provider
permission/coverage/pricing inquiry packet is prepared but has not been sent.
No concrete source policy, adapter, history, or operational authority exists.
Repository development has therefore returned to explainable Candidate
strategy channels. The fixed offline preview, bounded consumer, independent
Oracle, formal temporary-root audit, additive product projection, and
bilingual lazy consumer are implemented and the first Strategy Channels
product is active in the current ordinary-fresh 2026-08-28 analysis release.
Exact formula/contribution display and channel-overlap diagnostics are also
deployed. Real chronological validation remains blocked
on adequate point-in-time history; every future publication/deployment remains
a separate authorization.

ADR 0087 adds the first repository-only P4 decision-visualization slice to the
Candidate lazy detail drawer. It displays the published current close, SMA10,
SMA20, prior five-session close high/low, and selected reference support on one
shared scale, plus explicit threshold distances and Candidate-state
confirmation progress. It changes no model or payload. The view deliberately
does not fabricate a historical price path, call confirmation count signal age,
or call reference support a stop. All 98 frontend tests and the Production build
pass; this source change is not deployed.

ADR 0088 now implements the separate Candidate Visual Context 1.0 source layer:
exact 20-session canonical close paths, copied Entry Geometry reference levels,
and an observed Candidate-state age that stops at changes/missing/stale rows and
marks retained-history left truncation. The independent raw-source validator,
permutation gate, owner-read-only `/tmp` audit, and socket-guarded CLI are
complete. The real 2026-08-28 audit at
`/tmp/whalpha-candidate-visual-context-20260828` has fingerprint
`3b8ddbf3cc7d35cf0ea2b8f257939d23cec6f1d463e0d16efce9b5fb1f23961f`.
All 3,541 Candidate rows have complete paths; observed age is available for
3,382, while 159 unavailable/stale current states remain empty. Both Oracles
have zero mismatch. The optimized 38.81-second offline run made zero requests
and zero Production writes. ADR 0089 now completes the additive product
boundary in repository source. Detail-shard 1.1 carries each Visual Context row
beside its exact Candidate; Snapshot 1.10 / Dashboard 2.7 and Approval Plan 2.5
freeze audit, batch, row-lineage, and file identities. The bilingual drawer
renders the real path and honest `N`/`>=N` observed age without browser
recomputation.

A real Dell 1.10/2.7 build formally passed against the active 8/28 MI,
Candidate, Entry Geometry, Strategy, and Visual audits. The first-load summary
remained exactly 2,061,314 bytes; 32 lazy detail shards grew by 3,724,116 bytes
in total to a 671,118–1,432,204-byte range. Plan 2.5, Snapshot Apply, the
51-checksummed-file serving bundle, OCI atomic switch, temporary guest Session,
and independent remote inspection all passed. Visual Context and the dark WH
PNG favicon are active in Production.

## Next candidate work

ADR 0090 begins the next product layer as a strictly labeled Sector ETF proxy,
not a completed Sector/Theme workspace. Repository source now has a fixed
11-sector registry, independent 5/10/20-session return and relative-rank axes,
five-session relative acceleration, leadership-run duration, a four-quadrant
descriptive posture, and an independent raw-panel Oracle. It has no composite
score and does not claim constituent breadth, fund flow, alpha, causality, or
official sector membership. Theme output remains explicitly unavailable.

The first read-only 2026-08-28 Dell review produced all 11 records from the
formal 26-session Market Regime input. Panel loading took 215.446 seconds while
the new calculation took 0.012777 seconds. ADR 0091 now implements the required
reuse boundary and atomic `sector-etf-rotation-audit/1.0`: it formally binds
Phase 1a input/calculation custody, the product, all record fingerprints, and
the independent Oracle without scanning canonical data itself. The real audit
completed under `/tmp` with product fingerprint
`bce93211b6aec748d41db7a4c7f2e34226941e2a4f4ceee29b7a7d6adf51bbf7`,
audit fingerprint
`df02d96806a7681380f4c79c609771c26009b8f0e988c62c3af6da7a01947bbb`,
Oracle mismatch zero, four owner-only `0400` files, and no partial residue.
That run measured 200.729 seconds panel load, 0.012 seconds calculation, and
0.008 seconds Oracle. ADR 0092 now fixes the additive projection boundary:
Market Intelligence 1.3 carries one market-wide product and Snapshot 1.11 /
Dashboard 2.8 exposes a dedicated file fetched only when the Sector Rotation
workspace opens. The normal Phase 1a CLI and offline executor now require a
distinct Sector Rotation audit target and calculate it from the same in-memory
panel, reporting a single panel load. A real 2026-08-28 combined run formally
reread both audits with Phase 1a elapsed time 204.085 seconds, rotation
calculation 0.012778 seconds, rotation Oracle 0.008185 seconds, and zero
Oracle mismatches. The stable rotation product fingerprint remained
`bce93211b6aec748d41db7a4c7f2e34226941e2a4f4ceee29b7a7d6adf51bbf7`;
the source-bound audit fingerprint was
`060932af8da939d30f0c59482ed525387fc007b1fdde78a0f272eb2e04dfbce7`.
All files were owner-only `0400` and no partial residue remained. The next
bounded slice is Market Intelligence 1.3 contract integration. No publication
or deployment is authorized by the current repository work.

The Automation Plan does not yet expose Sector Rotation as its own observed
recovery stage. A process interruption after Phase 1a custody but before the
second audit would therefore stop later integration rather than automatically
repair or skip it. MI 1.3 must require the audit and fail closed; explicit
recovery custody remains a later automation-hardening slice.

Keep the currently deployed strategy formulas frozen. The first governed
continuation-specific descriptive facts, independent Oracle, and formal
temporary audit now exist.
Next, preserve them as shadow evidence and define preregistered competing
continuation hypotheses only after the point-in-time historical foundation can
support chronological evaluation. Do not reduce the observed overlap or
select contraction/path thresholds against the single 2026-08-26 cross-
section.

For P4, Visual Context product integration and deployment are complete. The
next step is human browser acceptance, followed by only evidence-driven visual
refinement. The unattended daily chain still does not generate Visual Context
as an automatic stage; do not silently make a missing visual audit block the
current daily pipeline.

ADR 0060 now also closes the publication-side repetition exposed during the
authorized 2026-08-26 deployment attempt. Candidate completion evidence is
rehash-validated without rebuilding historical typed objects at MI Plan and
Apply. On the real audit, custody validation took 1.55 seconds at 145,632 KiB;
the bounded Candidate + Entry Geometry projection took 11.29 seconds at
1,097,512 KiB and retained the exact Production Candidate fingerprint and
496/532 counts. The interrupted old Plan made no Production write; the later
optimized Plan/Apply and deployment passed and produced the active release
recorded above.

The second publication bottleneck is also closed in repository source. MI
source binding now rehashes the completed Phase 1a 26-session EOD ledger and
validates EOD/Identity manifest custody instead of reconstructing price rows;
it rereads immutable Activation membership without replaying that artifact's
historical liquidity calculation. On the same real inputs this step fell from
53.74 seconds and 365,016 KiB peak RSS to 2.98 seconds and 215,908 KiB with
unchanged history/preview fingerprints. Approval still freezes the complete
Production inventory, and `report-current-context.sh --full-source-validation`
remains the independent deep-reconciliation path.

The first Candidate performance slice is implemented without changing results:
physical per-stage runtime evidence, a worktree-safe Dell Python runner,
overlapping-panel shared reads, one stable-ID state bar index per panel, and
reuse of the already verified current risk ranking. On the same complete
2026-08-26 audit, time before the audit writer fell from 1840.44 to 461.88
seconds while the logical fingerprint remained
`34e97758863658bfd710e74b312481e5d9f0d170396882dcf2b9c5c63f7eb6d7`
with zero Oracle mismatch. Verified-prior Candidate append is now implemented
and matches a corrected stable-prefix cold reference across every business
artifact. Real validation exposed a legacy Phase 1b rolling-window defect that
reinitialized historical state when the 26-session window advanced. State
calculation V1.0.1 now preserves a stable canonical left boundary while each
Composite retains its trailing 26-session source window. Legacy V1.0.0 audits
remain readable; the active review publication uses the corrected chain while
retaining the exact Candidate publication fingerprint.

On corrected 2026-08-26 development inputs, Candidate incremental time before
writing was 309.02 seconds versus 461.67 seconds cold. Repository source now
implements ADR 0025's optional immutable panel-stage reuse between Phase 1a
and Candidate. The final real-data comparison reduced current-panel load from
217.409 to 8.837 seconds and total time before writing from 310.008 to 101.792
seconds. Source, raw-fact, normalization, score, state, transition, risk,
parameter, and Oracle files were byte-identical; both Oracles had zero
mismatch. The cache is explicit, content-addressed, Dell-local, and fails
closed on a present invalid entry; it neither writes `/data` nor changes
Production.
Verified-prior Phase 1b append is now implemented. The final-version real
2026-08-26 incremental audit matched the V1.0.1 cold state history,
explanations, transitions, and current summary exactly with zero Oracle
mismatch; time before writing was 0.237 seconds versus 302.736 seconds cold.
Repository source now also implements ADR 0026's streaming and resumable
Candidate artifact boundary without changing completed audit schemas or
business bytes. The final real 2026-08-26 development run recorded 111.636
seconds before writing, 17.921 seconds for ten streamed artifacts, a 3,343,112
KiB process peak, and an approximately 164-second work-directory-to-delivery
boundary. Its nine source/business/Oracle files were byte-identical to the
earlier panel-cache audit, all four equivalence gates were true, and Oracle
mismatch was zero. Repository source now enforces daily verified-prior,
periodic cold-reference,
and code/model-change cold-full-replay modes under ADR 0027. A real 2026-08-26
periodic cold reference completed in 597.70 seconds; formal comparison with the
final incremental audit took 197.20 seconds and matched all eight comparable
business projections. Both audits had zero Oracle mismatch. Deterministic
process parallelism is now implemented only across independent cold-replay
session Oracles under ADR 0028. Four workers reduced the real cold Oracle stage
from 117.09 to 76.23 seconds and end-to-end time from 597.70 to 560.02 seconds;
all nine business/Oracle files were byte-identical. Daily remains one effective
Oracle worker because 2- and 4-worker inner-session prototypes were slower than
serial. ADR 0029 now adds an exact-session read-only daily state planner. A real
2026-08-26 rehearsal formally reread the corrected Phase 1b/Candidate
incremental development chain and returned `calculate_entry_geometry` as the
sole next action. It made zero external requests and Production writes and did
not enable a scheduler. ADR 0030 now adds the repository-tested single-action
offline executor and durable Dell run custody: exact plan/action binding, one
global lock, immutable hash-chained events, evidence validation, post-action
formal re-plan, and inspection-only crash recovery. It is limited to Phase 1a,
verified-prior Phase 1b, daily Candidate, and entry geometry. No durable real
analytics action has yet been executed through it; the run root was later
provisioned for the controlled acquisition/Apply rehearsal recorded below.
Session-readiness/retry policy and provider acquisition/canonical-apply
standing authorization were the next boundary. ADR 0031 now adds the
repository-tested, network-free readiness decision: actual XNYS close and
early-close handling, 30-minute provisional stabilization, bounded
retry/`Retry-After`, five-attempt
and six-hour limits, explicit alert state, and oldest-missing-session recovery.
It makes no provider-completeness claim and performs no fetch, apply,
notification, or scheduler action. Durable acquisition-attempt custody and
the standing-authorization decision were next. ADR 0032 now adds repository-
tested reservation/outcome/recovery custody under the shared global lock and
cross-session journal. It binds a fresh exact readiness fingerprint, package
path/type/session/request count/hashes/timing, persists bounded retry evidence,
and never loads credentials or executes a request. No real journal root or
fetch attempt was created. Provider fetch/canonical-apply standing
authorization is now repository-defined by ADR 0033 with a maximum 90-day
window, exact host/provider/path/code/readiness bindings, an external whole-
file SHA pin, and a four-operation Identity/EOD scope. No real authorization
directory, artifact, pin, or transition exists; current real operations still
require manual approval. ADR 0034 now adds the repository-tested coordinator
core with one-transition maximum, default-absent provider/apply capabilities,
explicit recovery stops, opt-in offline execution, and a hard stop at
publication review. That slice introduced no CLI, installed adapter,
authorization activation, request, or write.
ADR 0035 now adds repository-tested canonical Identity/EOD Apply custody under
journal 1.2. Reservation binds the completed acquisition, frozen plan SHA,
package hashes, expected inventory, absent targets, and exact paths; recovery
never writes and distinguishes formally complete, provably untouched, and
partial/ambiguous state. No real Apply reservation, recovery, or `/data` write
occurred through this layer.
ADR 0036 now adds repository-tested standing-authorized fetch/Apply capability
adapters. They preflight the external grant before reservation or credential
access, bind acquisition/Apply starts to request 1.1, preserve actual bounded
Identity HTTP request counts, and leave unknown fetch or any Apply exception
unresolved for recovery. The corrected authorized canonical root is
`/data/trading-intelligence-platform`; coordinator contract was then 1.1. The
ports remain absent unless explicitly installed, and that slice created no real
authorization, host pin, credential read, request, Apply, CLI, or scheduler
entry.
ADR 0037 now adds a default-disabled one-transition CLI and externally
SHA-pinned host-runtime contract. Capability installation requires an explicit
flag, enabled owner-only config, and independently derived actual Dell hostname,
executing source root, clean HEAD, and readiness-policy fingerprint. No real
host config, CLI invocation, service, timer, alert, or scheduler exists. The
CLI now has ADR 0038's explicit, mutually exclusive recovery mode. It rereads
one exact pending acquisition, Apply, or offline event and invokes only the
matching existing no-request/no-Apply/no-replay recovery boundary. Coordinator
contract is 1.2. This route is repository-tested only; no real recovery or
run-journal transition occurred.
ADR 0039 advances the coordinator to 1.3, preserves alert-required state, and
adds an explicitly emitted deterministic alert intent for blocked, interrupted,
or missed-session attention states. It never claims delivery: no channel,
outbox, credential, retry, receipt, or real notification is implemented.
External runtime/authorization provisioning remains deferred while exact-
revision-bound control code is still changing.
ADR 0040 adds a separate owner-only, immutable alert-delivery journal and one-
attempt custody port. It reserves before transport, requires bounded terminal
evidence, returns an already-delivered intent without another call, and blocks
known-failed or unresolved retries. ADR 0041 adds the first concrete channel:
a default-disabled SMTP adapter with exact-revision external config, separate
owner-only credentials, verified TLS, deterministic bilingual content, and
conservative unknown-outcome handling. It is repository-tested only: no email
config, credential, alert root, transport call, or delivery exists. ADR 0042
adds a read-only joint config preflight that verifies all three external
artifacts at one clean Dell revision while prohibiting credential access,
networking, writes, and activation. The command is repository-tested only; no
real external artifacts were provisioned or preflighted. ADR 0043 adds the
explicit post-coordination CLI composition from a non-null intent through
alert custody to SMTP. Default and normal-state paths remain zero-delivery;
only synthetic credentials and a fake sender have exercised this route. ADR
0044 advances joint preflight to 1.1 with an explicit no-email data-only mode;
the full four-operation data scope remains mandatory and email inputs must be
clearly included or omitted.
Publication, Snapshot generation, bundle construction, and OCI deployment
remain separate explicit approvals.

The 2026-08-27 20:18Z read-only Dell check found latest canonical Identity/EOD
at 2026-08-26 and selected `prepare_identity_catchup` for 2026-08-27. Readiness
was still in the post-close stabilization window until 20:30Z. A second
network-free check at exactly 20:30Z advanced only to
`ready_for_fetch_review` / `review_fetch_authorization`, with zero attempts,
requests, and writes. No daily run root, alert root, matching user timer,
external Host Runtime, or standing authorization was installed; no credential,
provider fetch, or write was performed.

That review was later explicitly authorized. At exact revision `c3af030`, the
installed seven-day data-only external controls passed preflight. Same-day
Identity fetched in 14 requests and canonical Identity 2026-08-27 formally
completed: 13,148 provider-identity rows and 9,982 instrument/resolver rows.
The next EOD fetch made one request but terminated `permanent_failure`; the old
terminal does not retain the numeric HTTP status, so its exact cause remains
unverified. A later separately authorized retry at revision `dd314db` made
exactly one request and produced a formally readable 12,552-result EOD package.
At that fetch-only boundary, no approval plan or canonical 2026-08-27 EOD
target existed. Canonical EOD was still 2026-08-26, while Identity and the
fetched EOD package were 2026-08-27.

The subsequent offline EOD Apply Plan formally rereads at file SHA-256
`76ac1c50a016b82772ce8ac391f8d67e107c8433caae0e1f6364b311deb23bc5`.
It binds the unchanged `/data` inventory and same-day Identity, produces 9,945
canonical rows with zero duplicate business keys and zero orphan references,
and proposes exactly two files under the then-absent 2026-08-27 EOD partition.

After the reviewed-retry custody fix at `6256bf3`, fresh apply-only controls
executed the user's exact authorization. Canonical EOD 2026-08-27 completed
with 9,945 rows; Identity/EOD alignment is now `aligned`. `/data` is 392 files
and 203,931,663 bytes at fingerprint
`ddbe1ab03d5b945e9c3e2be975218c830f10e1ca615571e9616e131c847c7749`,
with zero symlink or staging/partial residue. The next planner action is
`calculate_phase1a`.

ADR 0045 adds bounded request-count and numeric HTTP-status evidence for future
failures without retaining response content or changing failure classification.
The repository change invalidates the installed `c3af030` exact-revision
controls until separately reviewed and reprovisioned. Publication, deployment,
email, and scheduler authority remain absent.

ADR 0046 advances the credential-free context report to 1.1. It no longer
labels latest-EOD provenance as the overall Identity state; it separately
reports latest Identity, latest EOD's bound Identity, and their alignment.

ADR 0047 advances readiness to 1.1, acquisition custody to 1.2, the coordinator
to 1.4, and the backward-compatible run journal to 1.3. The active Basic EOD
profile now requires an immutable, bounded operator availability review before
a first current-session EOD request. A permanent/quality terminal can be
released for exactly one later bounded fetch review only by an event tied to
its exact terminal fingerprint. The review CLI is offline and grants no fetch,
Apply, scheduler, publication, or deployment authority. It has now appended
one real review tied to the exact 2026-08-27 terminal. The review did not itself
authorize a retry. After its boundary, the user's separate one-fetch approval
was exercised successfully and readiness advanced to `ready_for_apply_review`.
The legacy first-attempt HTTP status remains unknown.

The information-hierarchy and current-payload change layer are implemented in
repository source: first-level workspaces, shared controls, an opaque sticky
header, factual first-screen summaries, one-/five-session Regime deltas, both
threshold distances, relationship prior-state persistence, decision-lane
highlights, and the Universe/comparable explanation. Exact first-seen dates,
multi-session relationship persistence counts, and evidence acceleration need
an additive reviewed analytics-response contract; they are not inferred in the
browser.

The Phase 5 stock-candidate pipeline and Phase 6 consumer integration are
active: strict fact/component/confidence/batch contracts, a fingerprinted
seven-component parameter set, pure 26-session scoring, missingness and anomaly
quarantine, separate Conservative/Balanced/Aggressive eligibility/ranking,
chronological Watch/Prepare/Enter/invalidated replay, independent Oracles,
canonical `/tmp` audit/reread boundaries, Candidate publication 1.1, MI 1.2,
Snapshot 1.9 / Dashboard 2.6, and strict frontend parsing. Earlier contracts
remain readable rollback boundaries.

Candidate Entry Geometry V1 remains separate from leadership score/state/rank.
It uses fixed SMA/ATR/return/gap/range/volume facts to distinguish bounded
breakout, breakout watch, orderly pullback, strong-but-extended, and no viable
setup. The active UI selects fixed review-now, watch-trigger, wait-reset, and
other-research lanes from the complete hard-risk-qualified population; it does
not convert stock-price structure into an option-return claim.

The formal 2026-08-28 Candidate audit is
`/tmp/whalpha-candidate-phase5c-20260828`, fingerprint
`39f26ded1dbdd5359eca9d6f3c49dc0b1286531f31a5a61845c0a955ad145412`;
the bound entry audit is `/tmp/whalpha-candidate-entry-20260828`, fingerprint
`fb072d180744d951a052d8a48235a205258078effe7a53ec1d74ff3f5f96e63d`.
Both formal rereads passed with zero Oracle mismatch and zero network or
Production writes; entry input-permutation equivalence is true. Primary has
59 technical-review-ready, 1,173 monitor-for-trigger, 54 wait-for-reset, and
428 deprioritized records. It has 52 strong-but-extended setups, so strength
does not automatically become an entry instruction.

ADR 0049 now defines a repository-only six-channel Candidate shadow contract:
momentum breakout, strong-stock pullback, trend continuation, technical
reversal, fundamental value reversal, and defensive rotation. It requires one
explicit result per security/channel, within-channel ranking only, visible
market fit, source-dated evidence, first rejection, counterevidence,
reviewability conditions, and invalidation. Event evidence is auxiliary;
price-derived relationships remain proxies; stock results remain distinct
from option returns. No formula, threshold, real-data assessment, Market
Intelligence/Snapshot field, UI, publication, or deployment was added.

The next evaluation boundary is also repository-defined: one sealed signal
record contains only contemporaneously available source sessions and exact
point-in-time membership, while 1/3/5-session stock outcomes mature in separate
records later. The fixed policy prohibits random splits, uses chronological
50/25/25 development/validation/holdout boundaries, purges/embargoes the
overlapping five-session label window, quarantines corporate-action ambiguity,
and never labels a stock outcome as option performance. This is a typed
contract only; no real signal/outcome row or performance statistic exists.

The read-only historical-readiness audit confirms that the short retained
panel cannot close those gaps. It contains 10,048 unique bar instruments and
9,672 present in every session, but adjacent sessions add 520 and lose 411
rows without governed lifecycle causes. The first/latest Identity snapshots
contain only `active` records; 84 first-snapshot IDs disappear and 187 latest-
snapshot IDs are new, with zero inactive/delisted rows or terminal trade dates.
With a 26-session feature window, the panel can mature at most 3 one-session,
1 three-session, and 0 five-session signal dates. Use it only for mechanics.

ADR 0051, Historical Research Data Foundation V1, and its repository-evidenced
source capability matrix are now accepted. They require separate raw EOD,
point-in-time Identity, daily membership, corporate-action, lifecycle, and
adjustment families; preserve effective/source-available/ingested clocks; and
set 252 sessions as the acquisition floor with 504 preferred.

The 2026-08-28 public-source review and Dell storage/request plan are now
complete. Basic publicly advertises five calls/minute, two years of EOD,
reference, and corporate-action history with the required Grouped Daily, All
Tickers, Splits, and Dividends shapes. A 504-session EOD+Identity projection is
about 1.66 GB before new families, so disk is not the blocker; historical
Identity pagination would take roughly 28–40 serial hours from the current
29-session base. Provider permission, live endpoint entitlement, and missing
merger/successor/terminal sources block a real pilot. Repository-safe work now
includes saved synthetic Massive split/dividend mapping, independent Decimal
adjustment invariants, and `historical-research-pilot-plan/1.0`. The planner
accepts only caller-supplied fingerprinted inventory, subtracts existing exact
sessions, enforces the 80-request/zero-retry/15-second-serial boundary, and
derives deterministic future `/tmp` package paths. It performs no storage scan,
request, credential access, or write and permanently returns `not_authorized`.
ADR 0052 and Data Record Governance V1 now add one executable cross-family
registry and orthogonal disposition, evidence, quality, coverage, point-in-time,
retention, content-scope, and serving dimensions. They do not rewrite existing
records. ADR 0053 now adds a default-deny approval review 1.1 and deterministic
preceding-window selector. The preliminary dates are 2026-07-14 through
2026-07-16 with a 75-request ceiling and no unnamed Ticker Events. It emits no
acknowledgement while source permission, entitlement, lifecycle coverage, and
a fresh exact inventory fingerprint remain unresolved. The next transition is
written external permission evidence, not acquisition.

The source MI Candidate product is about 20.4 MB. Production Snapshot delivery
now uses the Snapshot 1.8 / Dashboard 2.5 summary/on-demand-detail projection
without changing Candidate publication 1.1: the real 8/26 first-load file is
1.49 MB (92.68% smaller), with 32 detail shards and exact full-publication
reconstruction. Snapshot 1.9 / Dashboard 2.6 adds the independently audited
strategy product as one lazy 195,211-byte file without changing the default
Candidate transfer. Snapshot 1.10 / Dashboard 2.7 further adds the formally
bound Candidate Visual Context rows. The authorized 2026-08-28 analytics now
serve through the active 1.10 release with all three projections; Dell remains
the sole heavy-compute, historical-storage, and data-governance authority;
OCI is only the static serving/Session boundary. The optimized full and
incremental Candidate calculations retain serial state/order custody. Cold
replay alone may use the bounded session-Oracle process pool; daily append uses
one effective Oracle worker. Provider requests retain their fixed serial
request gates.

ADR 0064 now separates Momentum Breakout stage language from strategy status.
The deployed UI renders confirmed, near-trigger, and extended/reset-first
records distinctly and explicitly says that Advance + Watch is not a list of
completed breakouts. The frozen Strategy Preview score, status, rank, and
published payload are unchanged. Continuation Facts 1.1 adds six t-1-normalized
breakout-anatomy facts for preceding range, ATR contraction, broader-high
position, current close/intraday move, and current-session path concentration.
The formal 2026-08-26 shadow audit at
`/tmp/whalpha-candidate-continuation-breakout-facts-20260826` assessed 3,543
rows with zero unavailable facts, zero Oracle mismatch, exact permutation
equivalence, and logical fingerprint
`6e4b996cd7b75d49bf5f60fda94dfb6942da33d049c9b8589eb5f5fe455247a8`.
These facts do not enter Strategy, publication, Snapshot, or Dashboard pending
chronological validation.

## Verification entry point

Run the local, credential-free report from the repository root:

```bash
scripts/admin/report-current-context.sh
```

The report is read-only, performs no network request, and validates the local
repository, `/data`, active EOD/Identity/Activation/Market Intelligence/
Snapshot state, inventory, and publication residue. Use
`--full-source-validation` when a slower complete Market Intelligence source
reread is required.
