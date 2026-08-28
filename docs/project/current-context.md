# Authoritative Current Context

Operational state verified at: 2026-08-27 UTC

Repository development context updated at: 2026-08-28 UTC

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
| Deployed bundle source commit | `6c60502e4473a7ee7512b720f71a135a665f2f34` |

Codex-created worktrees may be detached at the same commit. Always verify the
main repository separately before treating a worktree as the source of truth.
The repository HEAD is intentionally not frozen in this document because a
documentation or code commit legitimately advances it. The read-only report
must show the current HEAD and cleanliness separately from the immutable commit
recorded by a deployed bundle.

## Formal local state

The 2026-08-27 reconciliation used the project readers after the separately
approved 2026-08-26 Identity/EOD publication and ordinary lag-zero analytics,
Snapshot, bundle, and OCI deployment. It reread the full local inventory and
active custody/contracts after deployment.

| Boundary | Active verified value |
| --- | --- |
| Canonical EOD | 29 sessions, 2026-07-17 through 2026-08-26 |
| Latest EOD | 2026-08-26, 9,953 rows |
| EOD content fingerprint | `60de33ca6d37501387cc1d233d999a16f176197c185cb844dcc0fa3bee592466` |
| EOD Parquet SHA-256 | `50d19945be381d845ad9b2badad9a433797d242ca4388de73a880f6f16357db3` |
| Latest canonical Identity | 2026-08-27: 9,982 instruments / 13,148 provider identities / 9,982 resolvers |
| Latest Identity logical fingerprint | `a4db78888d19799f7e38485cfceeb3e6d4611ab2f1cb3d6785a8fc90e6f295ad` |
| Latest-EOD-bound Identity | 2026-08-26: 9,974 instruments / 13,141 provider identities / 9,974 resolvers |
| EOD-bound Identity logical fingerprint | `3f9fe19f4f57cb16552443d5bdd45d5ca6367409dddf5e675d2a32d08fad7acf` |
| Identity/EOD alignment | `identity_ahead_of_eod` |
| Activation analysis session | 2026-08-19 |
| Activation pointer fingerprint | `dbe6056e1ed4b87ebce88b356c346831ce67431a263066cd283b9ad7e8067168` |
| Activation logical fingerprint | `6ea818cb3079bb77fd5fe1b8000530d2c8e2d1127fcccd40be68ac590678c7a5` |
| Primary | 1,718 CS; fingerprint `c3665203965b96528c9be07db3c49d18023104e346da16050f1170d4fe148978` |
| Secondary | 1,831 = 1,718 CS + 113 ADRC; fingerprint `2dce08e728774510878c47dc80898e10236952dacd146990ad344c4dcb75a295` |
| Market Intelligence | `2026-08-26T050254Z-6c60502e4473`, contract 1.2 |
| Market Intelligence payload SHA-256 | `e0d92f2ace261cb9963a134486f096f2e7ca423688c3a2fb36977b1b2a174252` |
| Market Intelligence logical fingerprint | `dfa538a9a00ea1749053fc022622b7bd1913df2fa195d3e6dcce0472c78426c2` |
| Candidate publication | 496 Primary / 532 Secondary records; fingerprint `286d4eebcb2e0489f33b03894bec8c7c58c1641f113719a014f296db42c2f07a` |
| Dashboard Snapshot | `2026-08-26T053233Z-6c60502e4473` |
| Contracts | Snapshot 1.7 / Dashboard 2.4 |
| Snapshot pointer fingerprint | `5c6a5cce3e40c8ab07f3634fec05a1ffe02e8045d2d14c471ab5dc71d43bf122` |
| Active review metadata | none; ordinary fresh release |
| Current post-close pipeline freshness | expected 2026-08-27, canonical EOD 2026-08-26, lag one; no new analytics/Snapshot publication |
| `/data` inventory | 347 files / 158,668,614 bytes after the 2026-08-27 Identity Apply |
| `/data` inventory fingerprint | not recomputed by the post-Identity report; prior 340-file fingerprint `ee241ca8e89fe5a010d67a5bd654852293fbbf1c6a3c80090222e8d1eb3879b8` is historical only |
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
only an exact unchanged plan for one of four offline analytics actions. The
executor holds a global lock, journals start/terminal events in an immutable
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

## Analytics and presentation

- Market Regime: Primary 57.8456 Balanced; Secondary 57.9041 Balanced.
- Fixed registry: 30 ETFs and 16 relationships with 5/10/20-session windows.
- Relationship history: 336 rows over 26 sessions; confidence is low.
- English and Simplified Chinese use one language-neutral payload. English is
  the first-visit default.
- Credential and equal-capability guest entry both create the same role-free
  protected Session and load the same product payload.
- Production bundles exclude synthetic Dashboard data and fail closed on API
  or Snapshot failure.
- Production contains Candidate publication 1.1, MI 1.2, Snapshot 1.7 /
  Dashboard 2.4, the independent Candidate and Entry Geometry Oracles, strict
  frontend parsing, and the bilingual entry-location view. Leadership rank and
  entry location remain separate axes.
- The active formal Candidate audit is
  `/tmp/whalpha-candidate-phase5c-20260826`, fingerprint
  `34e97758863658bfd710e74b312481e5d9f0d170396882dcf2b9c5c63f7eb6d7`.
  The bound Entry Geometry audit is
  `/tmp/whalpha-candidate-entry-20260826`, fingerprint
  `b3e54546f297bcca9e9a23bb011e0137342777dedc979eca1b4cda71f173ff46`.
  Both formal rereads have zero Oracle mismatch and no external or Production
  writes; Entry Geometry input-permutation equivalence is true.
- Primary Entry Geometry assesses 1,715 securities: 53 technical-review-ready,
  1,250 monitor-for-trigger, 109 wait-for-reset, and 303 deprioritized. Its 98
  strong-but-extended results demonstrate that strong leadership does not
  automatically become an entry instruction. This is distribution evidence,
  not outcome validation.
- The active Candidate payload has 496 Primary and 532 Secondary records and
  is about 20.4 MB. Repository source now adds ADR 0048's Snapshot 1.8 /
  Dashboard 2.5 lossless delivery projection: a 1,490,756-byte first-load
  summary plus 32 stable-ID detail shards of 474,940–1,028,834 bytes. A real
  `/tmp` 2026-08-26 build formally reconstructed the unchanged full Candidate
  1.1 publication with the same 496/532 counts. A separate lag-zero build
  produced and validated approval plan 2.3 without applying it. This is not
  published or deployed; active Production remains Snapshot 1.7 / Dashboard
  2.4. Guest and credential Sessions remain capability-identical by contract.
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
  A 2026-08-26 offline calculation produced reconciled full-population counts
  and deterministic batch/consumer fingerprints. Its independent Oracle
  recomputed score, status, and rank without importing the Production
  calculator. The immutable `/tmp` audit fingerprint is
  `1c2036a6266647482de12d1ed7a1f9adf0f41311bc886979324ba3a0859c2877`;
  both Universes have zero mismatches and input-permutation equivalence. It has
  no publication, deployment, or Production effect. ADR 0057 adds a separate
  lazy `candidate-strategy-channels.json` product and bilingual Strategy
  Channels workspace. A real temporary-root Snapshot 1.9 / Dashboard 2.6 build
  formally reread the product: 195,211 bytes, logical fingerprint
  `45bad6eb7fd014c0cc36b1244be7274dc98b92d23fa57d9ddcabe10b271ca3cd`,
  with unchanged 496/532 Candidate counts and 8/8/8/0/0/0 displayed records
  per Universe. ADR 0058 now adds Approval Plan 2.4, strict OCI bundle
  validation, and temporary-guest postflight validation. A local 50-file
  bundle build passed without OCI access and carried the same product/audit
  fingerprints. No plan was approved/applied and no activation or deployment
  occurred. The subsequent UI continuity pass preserves Candidate view and
  strategy channel in the URL, removes the unrelated risk-mode control from
  strategy mode, and makes evidence-incomplete channels explicit; 91 frontend
  tests and the Snapshot-mode build pass. Human visual acceptance remains
  pending. ADR 0059 now records the user's exact 2026-08-26 stale-review
  acknowledgement and adds a separate versioned authorization without
  changing historical 1.0 reads. No new publication or deployment should be
  claimed until the exact apply and postflight finish. Technical reversal,
  fundamental value reversal, and defensive rotation remain explicitly
  unavailable rather than being synthesized from proxies.
- ADR 0050 adds the repository-only chronological evaluation boundary: source-
  dated signals are sealed without outcomes, and 1/3/5-session underlying-
  stock labels may be attached only later under a fixed no-random-split,
  five-session purge/embargo policy. Current-constituent replay is not
  performance-eligible. No evaluation dataset or result exists; 29 sessions,
  missing daily point-in-time membership, and incomplete corporate-action
  governance remain hard blockers.
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

## OCI production state

The active remote release and matching local immutable bundle are
`2026-08-26T053233Z-6c60502e4473`, built from deployed source commit
`6c60502e4473a7ee7512b720f71a135a665f2f34` and bound to the active Snapshot
and Market Intelligence publication. A later repository HEAD does not
invalidate this immutable lineage; the report exposes whether the two commits
match rather than hiding the bundle.

The 2026-08-27 deployment passed remote preflight, Nginx configuration checks,
atomic apply, unauthenticated protection, and the deployment tool's temporary
guest Session postflight against the exact Snapshot 1.7 payload. No credential
or cookie content was printed or retained. Password-based and visual browser
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

This handoff does not authorize provider or SEC access, credential inspection,
EOD or Identity acquisition, scheduler changes, Activation, publication,
Snapshot creation, bundle generation, OCI deployment or rollback, guest
access, further UI implementation, another quantitative feature, or guest/
source licensing remediation. The
completed 2026-08-26 publication and deployment described above are evidence,
not continuing authorization.

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
