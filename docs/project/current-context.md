# Authoritative Current Context

Verified at: 2026-08-27 UTC

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
| Same-day Identity | 9,974 instruments / 13,141 provider identities / 9,974 resolvers |
| Identity logical fingerprint | `3f9fe19f4f57cb16552443d5bdd45d5ca6367409dddf5e675d2a32d08fad7acf` |
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
| Current local freshness gate | `fresh`: actual and expected 2026-08-26, lag zero |
| `/data` inventory | 340 files / 156,415,379 bytes |
| `/data` inventory fingerprint | `ee241ca8e89fe5a010d67a5bd654852293fbbf1c6a3c80090222e8d1eb3879b8` |
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
and never re-executes. This boundary is repository-tested only: no durable real
run root is provisioned, no real action has run through it, and no scheduler is
enabled. Session-readiness/retry policy and provider acquisition/apply standing
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
request. This is repository-tested only: journal 1.2 has not been provisioned
for a real run and no fetch was executed. Provider fetch/canonical-apply
standing authorization is now defined by ADR 0033 as an expiring, exact-
revision, externally SHA-pinned contract for only Identity/EOD fetch and
canonical apply. Its reader and transition verifier are repository-tested, but
no real authorization directory, artifact, host pin, fetch, or apply was
created. Publication and public-serving operations stay outside this scope.
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
is `/data/trading-intelligence-platform`. The adapters remain uninstalled; that
slice created no real authorization artifact, host pin, credential read,
provider request, reservation, Apply, CLI, or scheduler entry.
ADR 0037 now adds the repository-tested one-transition CLI and external
host-runtime config contract. Authorized ports stay absent unless an externally
SHA-pinned owner-only config enables them and the invocation opts in. Runtime
derives the actual Dell hostname, executing source root, clean Git HEAD, and
current readiness-policy fingerprint rather than trusting asserted strings.
No real host config root/artifact, CLI transition, service, timer, alert, or
scheduler exists. ADR 0038 now routes one explicitly requested unresolved
acquisition, canonical-Apply, or offline-action event to its existing recovery
boundary after an exact locked journal reread. Recovery keeps networking
disabled, never performs Apply or replays calculation, and never loops. This is
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
root, command, network request, delivery, service, timer, or scheduler exists.

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
  is about 20.4 MB. Summary/detail separation, compression, and on-demand
  loading are the next payload-efficiency concern; guest and credential
  Sessions must remain capability-identical.
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
access, further UI implementation, or another quantitative feature. The
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
