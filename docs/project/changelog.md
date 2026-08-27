# Changelog

## 2026-08-27 — Default-deny standing daily data authorization

- Accepted ADR 0033 and added an expiring, exact-revision authorization
  contract limited to Massive Identity/EOD fetch and approved canonical apply.
- Required a separately activated whole-file SHA pin plus exact host, provider,
  `/data`, run-root, readiness-policy, custody, package, plan, and current-state
  bindings. Publication, deployment, scheduler, SEC, options, and orders remain
  explicitly unauthorized.
- Added canonical owner-only artifact validation and one-transition decisions
  with one-request/one-write maximums and fail-closed scope, expiry, revision,
  mode, hash, and stale-request tests.
- No real authorization directory, artifact, host pin, provider request,
  credential read, `/data` write, publication, deployment, or scheduler state
  was created or changed.

## 2026-08-27 — Durable provider-attempt custody

- Accepted ADR 0032 and extended the unused real-world run-journal contract to
  1.1 with disjoint provider-acquisition and offline-action event families
  under one global lock and cross-session SHA-256 chain.
- Added exact-readiness reservation, bounded outcome recording, persistent
  retry projection, and no-request recovery. Package-ready evidence must
  formally match operation, session, path, type, request count, hashes, and a
  reservation-to-result time interval.
- Exposed a non-sensitive formal fetch-package evidence reader and added a
  worktree-safe custody administrator entry with duplicate, concurrency-family,
  stale-plan, time, residue, wrong-package, recovery, and network-guard tests.
- No credential, provider request, fetch package, real run root, `/data` write,
  apply, notification, publication, deployment, OCI, Production, or scheduler
  state changed.

## 2026-08-27 — Market-close-aware daily readiness policy

- Accepted ADR 0031 and added a deterministic, network-free readiness plan
  separating XNYS close from unguaranteed provider EOD stability. The first
  fetch review is provisionally 30 minutes after actual close, including early
  closes and daylight-saving transitions; it never claims completeness.
- Added bounded 15/30/60/120-minute retry, provider `Retry-After` handling,
  five-attempt and six-hour limits, terminal failure diagnosis, explicit alert
  state, separate fetch/apply review, and oldest-missing-session recovery.
- Added a worktree-safe read-only administrator entry and calendar, policy,
  CLI, malformed history, backoff, exhaustion, and network-guard tests.
- No credential, provider request, `/data` write, fetch package, apply,
  notification, publication, deployment, OCI, Production, or scheduler state
  changed.

## 2026-08-27 — Single-action offline daily execution custody

- Accepted ADR 0030 and added an executor limited to one exact, unchanged
  planner action across Phase 1a, verified-prior Phase 1b, daily Candidate, or
  Candidate entry geometry. It holds a global lock, records start before
  calculation, validates returned evidence, formally re-plans, and records
  success only after the named immutable stage completes and the plan advances.
- Added an owner-only append-only Dell run journal with immutable canonical
  events, cross-session SHA-256 chaining, strict permissions/symlink/sequence
  validation, unresolved-prior-session blocking, and non-blocking concurrency
  rejection. Interrupted recovery inspects formal state and never re-executes.
- Added a worktree-safe administrator entry and failure, interruption,
  tampering, stale-plan, concurrency, recovery, evidence, and network-guard
  tests. No durable real run root was provisioned and no real action ran.
- No provider request, credential access, `/data` write, publication, Snapshot,
  bundle, deployment, OCI, Production, or scheduler state changed.

## 2026-08-27 — Read-only daily EOD automation control plane

- Accepted ADR 0029 and added a deterministic exact-session planner across
  same-day Identity/EOD, Phase 1a, verified-prior Phase 1b, daily Candidate,
  and Candidate entry geometry. Missing evidence yields one next action;
  corruption, lineage mismatch, or downstream residue blocks the run.
- Added worktree-safe planner and entry-geometry administrator scripts and
  corrected both Massive Identity/EOD administrator wrappers to use the shared
  project runner rather than a checkout-local virtual-environment path.
- A real 2026-08-26 read-only rehearsal selected `calculate_entry_geometry`
  after formally rereading the corrected daily incremental development chain.
  Plan fingerprint was
  `5f5f5be7a0e219ca21acaa01afc889f1397ca216ef7e8daab692686ee55cf21d`.
- No provider request, `/data` write, publication, Snapshot, bundle,
  deployment, OCI, credential, or scheduler state changed.

## 2026-08-27 — Deterministic cold-replay Oracle process parallelism

- Accepted ADR 0028 and added bounded 1–8 worker `forkserver` execution across
  independent cold-replay session Oracles. Workers disable network/DNS and the
  parent retains chronological state, ordered merge, aggregate fingerprints,
  and audit custody. Worker failures propagate without fallback.
- Four workers reduced the real 2026-08-26 cold Oracle stage from 117.09 to
  76.23 seconds and end-to-end cold replay from 597.70 to 560.02 seconds. Nine
  business/Oracle files, the audit logical fingerprint, and Oracle fingerprint
  were exact; Oracle mismatch was zero.
- Rejected a one-session Universe-level process prototype after real serial,
  2-worker, and 4-worker runs took 277.81, 286.99, and 291.22 seconds. Daily
  therefore retains one effective Oracle worker.
- No `/data`, publication, Snapshot, bundle, deployment, OCI, credential,
  provider, or scheduler state changed.

## 2026-08-27 — Explicit Candidate validation tiers

- Accepted ADR 0027 and added executable `daily`, `periodic`, and
  `code_change` gates. Daily requires verified-prior append; periodic and
  code/model change require cold replay. Invalid mode/input combinations fail
  before calculation.
- Periodic verification formally rereads both same-session audits and compares
  eight schema-neutral business projections. It deliberately does not compare
  incremental and cold Oracle containers, whose declared session scopes differ;
  both Oracles and all mode-specific equivalence gates must pass independently.
- A real 2026-08-26 cold reference completed in 597.70 seconds. Formal
  comparison with the final incremental audit took 197.20 seconds and all eight
  projections matched; Oracle mismatch, external requests, and Production
  writes were zero.
- No `/data`, publication, Snapshot, bundle, deployment, OCI, credential,
  provider, or scheduler state changed.

## 2026-08-27 — Streaming and resumable Candidate audit delivery

- Accepted ADR 0026 and retained Candidate audit schemas 1.0/1.1 plus exact
  completed business bytes while streaming canonical JSON, physical SHA-256,
  and logical hashes through bounded buffers. Formal reread no longer retains
  duplicate raw and canonical artifact copies.
- Added an explicit owner-controlled `/tmp` recovery directory with a canonical
  journal bound to the final path, artifact and typed-record fingerprints,
  source base, Oracle, equivalence gates, and prior audit. Verified contiguous
  prefixes resume; gaps, unexpected files, source drift, and corruption fail
  closed. A prepared interruption finalizes before reopening calculation data.
- The final real 2026-08-26 development run recorded 111.636 seconds before
  writing, 17.921 seconds for ten streamed artifacts, 3,343,112 KiB peak RSS,
  and an approximately 164-second recovery-directory-to-delivery boundary.
  Nine source/business/Oracle files were byte-identical to the prior panel-
  cache result; all equivalence gates passed and Oracle mismatch was zero.
- No `/data`, publication, Snapshot, bundle, deployment, OCI, credential,
  provider, or scheduler state changed.

## 2026-08-27 — Formally validated Phase 1a/Candidate panel reuse

- Accepted ADR 0025 and added the optional
  `market-regime-formal-panel-cache/1.0` Dell-local stage. Phase 1a may persist
  its already validated exact 26-session panel under a content-derived key;
  Candidate may reuse it only when the current Phase 1b source ledger binds
  the same EOD, Identity, Activation, session, and ordered-Universe custody.
- Cache absence uses the unchanged formal reader and populates the exact entry.
  A present unsafe, malformed, corrupt, or source-mismatched entry fails closed.
  Entries have canonical fixed-schema bars, physical/logical fingerprints,
  stable-ID memberships, owner-only custody, no `latest` pointer, and no OCI or
  Production role.
- On final V1.0.1 2026-08-26 development inputs, panel load fell from 217.409
  to 8.837 seconds and total time before audit writing from 310.008 to 101.792
  seconds. All nine source/business/Oracle files were byte-identical and both
  independent Oracles had zero mismatch. Cache evidence and physical timings
  intentionally changed only the audit container fingerprint.
- No `/data`, publication, Snapshot, bundle, deployment, OCI, credential,
  provider, or scheduler state changed.

## 2026-08-27 — Verified-prior Phase 1b and Candidate append

- Accepted ADR 0024 and added Phase 1b audit schema 1.1
  `verified_prior_incremental`. It formally rereads current Phase 1a and the
  immediately prior corrected Phase 1b audit, validates date/version/
  Activation/membership/prefix custody, appends one row per Universe, and runs
  a separate one-session state Oracle without reopening `/data`.
- Final V1.0.1 real-data audits covered a cold 2026-08-25 prefix and separate
  incremental/cold 2026-08-26 results. State history, explanation, transition,
  current-summary records, and both Universe history fingerprints were exact;
  both Oracles had zero mismatch. Incremental time before writing was 0.237
  seconds versus 302.736 seconds cold.
- Strengthened formal Phase 1a and Phase 1b readers to reject failed Oracle
  gates and inconsistent typed/container bindings while retaining successful
  legacy V1.0.0 state-audit compatibility. No `/data`, publication, Snapshot,
  bundle, deployment, provider, credential, or scheduler state changed.

- Added Candidate audit schema 1.1 execution mode
  `verified_prior_incremental`. It formally rereads an immediately prior audit,
  validates calculation/parameter/Activation/Universe/Phase 1b compatibility,
  calculates only the new session, independently Oracles score/risk/state
  append, and writes a cumulative immutable audit with an explicit validation
  ledger. Legacy cold audits remain readable.
- Real 2026-08-25 to 2026-08-26 validation first failed closed because legacy
  Phase 1b daily audits changed historical confirmed states when their rolling
  26-session input window advanced. The differences were business semantics,
  not container-only fingerprints, and were not bypassed.
- Accepted ADR 0023 and added state calculation V1.0.1 / parameter set
  `mrom-regime-state-v1-stable-prefix-2`. Phase 1b cold replay now retains the
  first contiguous canonical session as its state-history boundary while each
  Phase 1a Composite continues to use at most its exact trailing 26 sessions.
  Legacy V1.0.0 audits remain formally readable.
- Corrected 2026-08-25 and 2026-08-26 Phase 1b development audits retained all
  16 prior rows exactly and added only the two 2026-08-26 Universe rows, both
  with zero Oracle mismatch. This real-data rehearsal preceded freezing the
  corrected identifiers as V1.0.1; final versioned source passed the complete
  backend regression and did not create a new Production-bound audit.
- On corrected sources, incremental and cold 2026-08-26 Candidate development
  audits matched every source, raw-fact, normalization, score, state,
  transition, risk record, and business fingerprint; both had zero Oracle
  mismatch. Incremental took 309.02 seconds before writing versus 461.67
  seconds cold. Formal panel reread remains the dominant 216.57-second cost.
- Restored formal EOD session-directory validation to the cold path after
  proving that a Phase 1b 26-session source ledger is not the complete
  canonical EOD history. No `/data`, publication, Snapshot, bundle, OCI,
  credential, provider, or scheduler state changed.
- Routed the Market Regime and Phase 1b administrator wrappers through the
  repository-aware Python runner so linked Dell worktrees cannot silently
  import main-checkout source.

## 2026-08-27 — Candidate pipeline measurement and repeated-work removal

- Added physical per-stage wall/CPU timings plus process I/O, invocation, and
  context-switch counters to the Candidate audit manifest. Runtime evidence is
  excluded from the logical fingerprint and older audits remain readable.
- Added a repository-aware Dell Python runner and formal Candidate wrapper.
  Linked Codex worktrees may reuse the main checkout's virtual environment
  without silently importing main-checkout source.
- Replaced per-candidate full-panel scans with one stable-ID bar index per
  panel and reused the already Oracle-checked final risk results.
- Added a formal multi-panel reader that validates the union of overlapping
  immutable 26-session inputs once, then reconstructs the exact source-bound
  panel for each Candidate session.
- On the same complete 2026-08-26 inputs, the instrumented baseline took
  1840.44 seconds before audit writing; the optimized path took 461.88 seconds.
  Panel validation fell from 837.98 to 226.57 seconds and state update from
  773.19 to 4.50 seconds. Process character reads fell from about 734 MB to
  221 MB and the pre-writer RSS sample from about 3.0 GiB to 2.0 GiB.
- Both real-data audits produced Candidate fingerprint
  `34e97758863658bfd710e74b312481e5d9f0d170396882dcf2b9c5c63f7eb6d7`
  with zero Oracle mismatch and passed all replay-equivalence gates. No
  `/data`, publication, Snapshot, bundle, deployment, or OCI state changed.

## 2026-08-27 — Fresh 2026-08-26 publication and Candidate entry deployment

- Published and formally reread same-day 2026-08-26 Identity and EOD through
  their approval-bound workflows: 9,974 canonical instruments, 13,141 provider
  identities, 9,974 resolvers, and 9,953 EOD rows. Local history now contains
  29 sessions from 2026-07-17 through 2026-08-26.
- Completed and formally reread the 2026-08-26 Regime Phase 1a/1b, all 16 ETF
  relationships, preview, Candidate, and Entry Geometry audits. Candidate
  fingerprint is `34e97758863658bfd710e74b312481e5d9f0d170396882dcf2b9c5c63f7eb6d7`;
  Entry Geometry fingerprint is
  `b3e54546f297bcca9e9a23bb011e0137342777dedc979eca1b4cda71f173ff46`.
  Oracle mismatches are zero and Entry Geometry input-permutation equivalence
  is true.
- Published ordinary-fresh MI 1.2 publication
  `2026-08-26T050254Z-6c60502e4473` and Snapshot 1.7 / Dashboard 2.4 release
  `2026-08-26T053233Z-6c60502e4473`. Expected and actual session are both
  2026-08-26, lag is zero, and review mode is false.
- Built and deployed OCI release `2026-08-26T053233Z-6c60502e4473` from source
  commit `6c60502e4473a7ee7512b720f71a135a665f2f34`. Dry-run, remote preflight,
  Nginx checks, atomic apply, unauthenticated protection, and temporary guest
  Session postflight passed. Password-based visual behavior remains a manual
  user check.
- Post-deployment full-source reconciliation reports 340 `/data` files /
  156,415,379 bytes, no symlink or publication residue, and exact MI, Snapshot,
  Candidate, Entry Geometry, bundle, and source-commit bindings.
- Observed the heavy Candidate audit using roughly one logical CPU for about
  30 minutes and reaching about 2.7 GiB RSS on the 8-core / 16-thread Dell.
  Deterministic incremental processing, shared immutable panels, resumable
  stages, and then bounded process parallelism are the next performance work;
  provider requests retain their serial request gates.
- The active Candidate payload is about 20.4 MB. Summary/detail separation,
  compression, and on-demand loading are now explicit payload-efficiency work.

## 2026-08-27 — 2026-08-25 data and additive Candidate entry consumer

- Published and formally reread same-day 2026-08-25 Identity and EOD through
  their approval-bound workflows: 9,974 canonical instruments, 13,141 provider
  identities, 9,974 resolvers, and 9,954 EOD rows. Local history now contains
  28 sessions from 2026-07-17 through 2026-08-25.
- Completed and formally reread the 2026-08-25 Regime Phase 1a/1b, all 16 ETF
  relationships, preview, Candidate, and entry-geometry audits. Candidate
  fingerprint is `32c0647ae18e165052a4fdb5ea00a0ae7f3cec5306daecdc4360ef7de829e626`;
  entry fingerprint is
  `3875872f719537170f17aab04b0715c86ffb67259f75adf0ee796b4a8f0c182b`.
  Oracle mismatches, external requests, and Production writes are zero.
- Added fixed `candidate-entry-lane-consumer/1.0` selection from the complete
  hard-risk-qualified population. It preserves leadership ranks, reuses
  concentration caps, and provides bounded review-now, watch-trigger,
  wait-reset, and other-research lanes.
- Added Candidate publication 1.1, MI 1.2/plan 1.2, Snapshot 1.7 / Dashboard
  2.4/plan 2.2, strict bundle/deployment validation, bilingual frontend parsing,
  and the default quality-by-entry-location workspace while preserving older
  read and rollback contracts.
- Full validation passed: 1,104 backend tests, 84 frontend tests, and the
  production frontend build. Production remains on the 2026-08-24 MI 1.1 /
  Snapshot 1.6 / Dashboard 2.3 release until the separate freshness and
  deployment gates are satisfied.

## 2026-08-26 — Candidate entry geometry and chase-risk shadow

- Accepted ADR 0021 and added the fixed `candidate-entry-geometry/1.0` shadow
  contract. The original Candidate score, state, and risk ranks remain the
  leadership/research-priority axis and are not penalized or reordered.
  Parameter set `candidate-entry-geometry-v1-fixed-baseline-1` has fingerprint
  `e531ffdc18d334329ac906cbe89f0cc88fc2e8932412ff0b6d8ce0b732cc25a1`.
- Added deterministic SMA10/SMA20, ATR14, three-/five-session move,
  volatility-scaled extension, consecutive-up, gap/range/close-location,
  volume-ratio, prior-high/low, and reference-support facts. Added explicit
  breakout, breakout-watch, pullback, strong-but-extended, no-setup, extension,
  first-rejection, review-posture, counterevidence, and manual-check semantics.
- Added a second raw-panel Oracle, input-permutation gate, socket-guarded CLI,
  and four-file owner-read-only canonical `/tmp` audit. Focused tests cover
  additive source binding, high-extension chase rejection, Oracle equivalence,
  and audit reread/custody.
- Formally completed `/tmp/whalpha-candidate-entry-baseline1-20260824`,
  fingerprint
  `6b013f948d5c6d1011cab0685f661907739b77f1cd1fbfa4307d4789a8638bee`,
  with zero Oracle mismatch, no external request, and no Production write.
- Primary Balanced top 50 contains 41 wait-for-reset high/extreme extensions,
  two technical-review-ready structures, four breakout watches, and three
  no-viable-setup rows. This is current-distribution evidence, not predictive
  validation or a reason to tune thresholds.
- No `/data`, Market Intelligence, Snapshot, frontend, bundle, OCI release,
  provider, credential, or scheduler state changed.

## 2026-08-26 — Phase 6 production publication and OCI deployment

- Published and activated MI 1.1 publication
  `2026-08-24T142500Z-1f3eb5512eb0` from the baseline-3 Candidate audit under
  the exact one-session stale-review authorization.
- Published and activated Snapshot 1.6 / Dashboard 2.3 release
  `2026-08-24T144500Z-1f3eb5512eb0`, including the 5.14 MB bounded Candidate
  file with 146 Primary and 155 Secondary display/review cards.
- Built and deployed OCI release `2026-08-26T151600Z-1f3eb5512eb0` from source
  commit `1f3eb5512eb0d1ba67112395450c2783221596da`. Remote preflight, Nginx,
  current symlink, public entry, guest Session, protected Dashboard, exact
  Snapshot 1.6, Candidate contract, logout, and unauthenticated boundaries
  passed. Password-based visual behavior remains a manual user check.
- Post-publication reconciliation reports 312 `/data` files / 107,298,545
  bytes, no symlink/staging/partial residue, and a clean `main` repository.

## 2026-08-26 — Phase 6 Candidate consumer and Snapshot contract

- Added a bounded, language-neutral `opportunity-candidate-publication/1.0`
  projection. It formally rereads the Candidate audit, requires zero Oracle
  mismatch and all replay/permutation gates, joins score/state/risk facts by
  stable `instrument_id`, and publishes only the three fixed risk-mode display
  unions plus Prepare/Enter/invalidated review rows.
- Added Market Intelligence 1.1 and plan 1.1 while preserving 1.0 reader,
  pointer, namespace, revision, and rollback compatibility. The new contract
  binds Candidate audit, EOD, Identity, Activation, parameter, state, Oracle,
  batch, and risk-result lineage without copying raw audit or provider data.
- Added Snapshot 1.6 / Dashboard 2.3 and plan 2.1 with exact Candidate file-set,
  hash, publication, audit, parameter, Universe, and displayed-count checks.
  Existing Snapshot 1.5 / Dashboard 2.2 remains readable unchanged.
- Added the third first-level `Stock Candidates` / `个股候选` workspace with
  Balanced default, Conservative/Balanced/Aggressive formal ranks, stage and
  ticker filters, short-history explanation, seven-component visualization,
  structured support/counterevidence, visible invalidation, raw facts, human
  review checklist, bilingual copy, mobile layout, and fail-closed parsing.
- Extended the OCI bundle and guest postflight gates for the exact 1.6/2.3
  contract. A pre-publication `/tmp` build reread 146 Primary and 155 Secondary
  cards; the Candidate file is about 5.14 MB.

## 2026-08-26 — Phase 5 candidate state, Oracle, and canonical audit

- Upgraded the candidate contract to `opportunity-candidate/1.1` and the
  calculation to `market-regime-opportunity-candidate-v1.1.1`, with fixed
  parameter set `mrom-candidate-v1-fixed-baseline-3` and fingerprint
  `4e44d58430c82f95c6e612c5227db0b050acfff29615e6fec4e49b139087d347`.
  The full formula, normalization, confidence, risk, anomaly, and source-
  quality policy now enters the parameter fingerprint.
- Added a typed prior-state source so current confidence can use only the
  immediately preceding compatible candidate-state row. Added deterministic
  Watch/Prepare/Enter/invalidated replay, missing-session hold/null behavior,
  breakout facts, stable-ID ticker-change handling, and separate state/history
  fingerprints. Candidate invalidation remains explicitly distinct from a
  position Exit or sell instruction.
- Added stable registered-ETF driver IDs, preserved EOD adjustment/quality
  facts through the formal reader, and separated known source-level degraded
  flags from security-specific quarantine. Unknown quality flags, non-valid
  status, non-unit factors, and extreme returns/gaps still fail closed.
- Added an independent raw-panel Oracle for scores, risk rankings, and state
  replay, plus a socket-guarded CLI and exact ten-file canonical `/tmp` audit.
  The reader verifies custody, file and logical hashes, typed record hashes,
  Primary-first ordering, source panels, transitions, and replay equivalence.
- The first formal baseline-2 audit correctly exposed an over-broad quality
  rule that quarantined every scored member because all canonical bars carry
  the known source-level `adjustment_factors_unverified` flag. Baseline-3
  separates that visible degraded limitation from unknown/security-specific
  quality failures; it does not suppress or relabel the source flag.
- Completed and formally reread the 2026-08-24 baseline-3 audit at
  `/tmp/whalpha-candidate-phase5c-baseline3-20260824.0JaMYi`, fingerprint
  `1f25a1c9060d459e372903ad116579973c709363f365f19fa66bb515774c93df`.
  Two candidate sessions produced 7,090 score rows and 7,098 state rows with
  zero Oracle mismatch and all append/restart/permutation/future-prefix gates
  true. Current Primary/Secondary each retain 20 quarantined extreme-move rows;
  no Prepare/Enter state is possible from the two-session evidence. Each
  Universe reaches the fixed 25/50/100 risk-mode display caps.
- The full audit took about 928 seconds and 1.9 GiB peak memory. This is
  acceptable for a development audit but not the intended daily hot path;
  incremental state/source reuse is required before scheduler integration.
- This slice remains offline and read-only with no `/data`, publication,
  Snapshot, API/frontend, OCI, scheduler, position, or option boundary.

## 2026-08-26 — Phase 5A candidate scoring and risk-mode domain core

- Added strict opportunity-candidate fact, component, submetric, confidence,
  batch, risk-assessment, and risk-mode result contracts. Candidate score facts
  remain separate from risk eligibility and rank.
- Added the immutable seven-component/three-risk-mode parameter set
  `mrom-candidate-v1-fixed-baseline-1`, fingerprint
  `2256e94a45d979bf818cdc048939c4650c10f9312099f83756e321ceee910b6f`.
  The parameter fingerprint fixes Decimal Type-7 5th/95th percentile
  interpolation and inclusive average-tie 0–100 percentile fallback.
- Implemented a pure, source-bound 26-session scorer over active stable-ID
  memberships. It preserves as-of bar coverage, same-session ticker metadata,
  CS/ADRC separation, the V1A registered-ETF price-proxy cap, missing-component
  reweighting, exact displayed-contribution reconciliation, and explicit
  underlying-not-option/proxy-not-sector caveats.
- Implemented separate Conservative/Balanced/Aggressive gates and deterministic
  concentration-aware ranks without changing base facts or score. Extreme
  return/gap observations quarantine a row and remain visible even when its
  score is otherwise unavailable.
- Added focused coverage for missingness, proxy absence/cap, CS/ADRC isolation,
  anomaly quarantine, risk-mode separation, concentration caps, source failure,
  deterministic fingerprints, and outer Decimal precision/trap invariance.
- A no-write 2026-08-24 formal-source memory rehearsal covered 1,716/1,718
  Primary and 1,829/1,831 Secondary members, produced scores for every covered
  member, selected registered-ETF proxies for 1,475/1,552, and quarantined 20
  extreme-move rows in each view. Balanced/Aggressive retained their fixed
  50/100 caps; Conservative retained zero because Phase 5A correctly lacked
  state-confirmation history rather than bypassing its 0.75 confidence floor.
  Reusing per-instrument log returns preserved both batch fingerprints; the
  two-Universe formal read/calculation remained about 219 seconds, so source
  validation and shared Primary/Secondary fact reuse remain optimization work.
- This slice makes no network request and adds no `/data`, API, frontend,
  Snapshot, publication, bundle, deployment, scheduler, position, or option
  boundary. Candidate state history, independent oracle, and canonical `/tmp`
  audit remain the next Phase 5 work.

## 2026-08-26 — Daily decision layer and equal-capability guest entry

- Built and deployed OCI release `2026-08-26T103119Z-f344a589a8c9` from source
  commit `f344a589a8c93e527e63470335d88d293141aee1`, reusing the exact active
  Snapshot 1.5 / Dashboard 2.2 and Market Intelligence publication. Dry-run,
  checksums, service/listener checks, atomic switch, unauthenticated boundary,
  temporary guest Dashboard/Snapshot access, and logout postflight passed.
- Added a conclusion-first Daily Decision Brief using the existing immutable
  Regime payload: broad Risk-on confirmation, one-/five-session Composite
  changes, exact supporting/conflicting dimensions, and remaining distance to
  both Risk-on and Defensive boundaries. No analytics score, threshold,
  publication, or fingerprint is recalculated in React.
- Replaced generic support/drag sentences with evidence-consistent copy,
  selected relationship highlights across six fixed economic decision lanes,
  added current-versus-prior state markers, consolidated the global
  short-history reliability warning, and collapsed the complete 16-pair audit
  table by default. Returns remain excluded from highlight selection/ranking.
- Renamed the second user-facing workspace to `Market Structure & Activity` /
  `市场结构与活跃度`; formal Dashboard contract identifiers remain unchanged.
- Accepted ADR 0019 and added same-origin, rate-limited `POST /auth/guest`.
  Guest entry creates the same opaque role-free Session, cookie, Nginx
  authorization result, Dashboard, and private-data access as credential
  login. It accepts no credential or role and does not create a second data
  path.
- Extended login, Auth Service, Nginx, deployment postflight, bilingual copy,
  and regression coverage. Deployment postflight now proves a temporary guest
  Session can read both the Dashboard and bound Snapshot, logs it out, and
  removes local cookie material without printing it.
- Exact first-seen dates, multi-session relationship run lengths/evidence
  acceleration, stock candidate scoring, trade-state publication, portfolio
  state, options analytics, data acquisition, and automated execution are not
  fabricated by this interface slice and remain separate contract work.

## 2026-08-26 — First-level workspace and current-market hierarchy

- Built and deployed OCI release `2026-08-26T094339Z-f9711d5403f6` from source
  commit `f9711d5403f60cd70a93b50ee314ab38a6af24a2`, reusing the active immutable
  Snapshot and Market Intelligence publication. Dry-run, apply, checksum,
  service, listener, and unauthenticated access-boundary checks passed;
  authenticated visual verification remains manual.
- Promoted Market Regime & Opportunities to the first navigation item and
  default workspace; Market Dashboard is the second explicit route.
- Replaced the small sticky view tabs with a persistent desktop left rail that
  treats Market Dashboard and Market Regime & Opportunities as first-level
  workspaces. Universe, language, and private Session controls now share one
  opaque sticky utility header; narrow layouts retain explicit workspace
  navigation without overlaying content.
- Renamed the user-facing Chinese workspace from the literal
  `市场状态与机会图谱` to `市场风向与机会`; English is shortened to `Market Regime &
  Opportunities`. Machine contract IDs and URLs remain compatible.
- Added a first-screen factual market read using existing one-session breadth,
  share-volume participation, sector-ETF leadership, and comparison coverage.
  It explicitly does not claim to be Market Regime or a trade signal and
  explains 1,718 Universe members versus 1,716 comparable observations.
- Increased fixed-priority relationship highlights from four to six while
  retaining all 16 preregistered pairs and the existing non-return-based order.
- Added shared-shell, history, locale, coverage-explanation, and presentation
  tests. Production build/demo-isolation checks pass. No analytics formula,
  API/data contract, authentication, formal data, Snapshot, bundle, OCI
  release, or deployment changed.

## 2026-08-26 — Authoritative context and status reconciliation

- Replaced the mixed historical/current 572-line status ledger with a concise
  current-state summary and moved recovery-critical IDs, fingerprints,
  verification scope, product guardrails, and Windows/Mac continuity into one
  authoritative current-context handoff. Historical execution detail remains
  in this changelog and dated audits.
- Reconciled AGENTS, README, roadmap, Market Regime product/contract status,
  private API governance, and the OCI runbook with active EOD/Identity,
  Activation V2, Market Intelligence, Snapshot 1.5 / Dashboard 2.2, bilingual
  presentation, and the last recorded OCI release.
- Added a fixed-root, network-prohibited, credential-free current-context
  report. It formally reads active contracts, verifies `/data` inventory and
  residue, validates the matching local bundle checksums, and offers a slower
  explicit full-source reread without exposing a write or network mode.
- Defined a minimal local build retention set and removed superseded/failed
  ignored private-Snapshot and OCI bundle directories plus transient Vite
  output. Canonical `/data`, the legacy fallback, the deliberate rollback
  bundle, and current bundle were retained.
- Live-verified the OCI current symlink, manifest boundary, Nginx, Session Auth
  Service, localhost-only listener, and unauthenticated routes without reading
  credentials or using a public endpoint. Removed 21 exact superseded/failed
  remote release directories after pointer/type checks; current and one
  rollback release remain with no staging/partial residue.
- Replaced historical troubleshooting in current operations documents with a
  concise current deployment, access, retention, and verification baseline.

## 2026-08-26 — Production Dashboard demo isolation

- Removed the synthetic Dashboard fixture from the production static dependency
  graph. Explicit demo mode remains available only in development through a
  guarded lazy import.
- Formal API/snapshot failures remain visible errors with retry and never fall
  back to synthetic data. The formal Dashboard parser now rejects synthetic
  response status.
- Added source-graph and emitted-bundle gates that fail a production build if
  any JS chunk or asset contains a known Dashboard fixture marker. Snapshot 1.5,
  Dashboard 2.2, stale-review display, authentication, and analytics semantics
  are unchanged.

## 2026-08-25 — Market Intelligence Production publication preparation

- Added immutable publication/manifest/pointer/plan contracts, source-validating
  reader, offline administrator, CAS/fsync, recovery, rollback, and fault guards.
- Added Snapshot 1.5 / Dashboard 2.2, explicit OCI binding, formal API cache,
  and bilingual snapshot-mode integration without changing analytics.
- Generated a deterministic historical 2026-08-21 candidate and stale-gated
  `/tmp` plan; Production remained unchanged and no deployment occurred.

## 2026-08-25 — English and Simplified Chinese interface

- Added a typed React `en`/`zh` catalog, shared locale provider, fixed domain
  terminology/reason mappings, and accessible global language selector. The
  static login surface uses the same URL/storage/default policy without
  changing its session or redirect security boundary.
- Localized the current Market Dashboard and Market Regime & Opportunity Map,
  including loading/error/empty states, full 16-pair map, five dimensions,
  pair details, tooltips, audit labels, limitations, and warnings. Raw IDs,
  reason codes, exact values, and fingerprints remain unmodified.
- Added deterministic URL > explicit localStorage > English resolution,
  invalid-value canonicalization, history/deep-link preservation, dictionary
  parity, data-invariance, login, and bilingual page tests.
- This remains local preview work. No analytics formula, API numeric semantics,
  Production data, snapshot, Activation, guest access, network, credential,
  OCI, or deployment boundary changed.

## 2026-08-25 — Market Regime local-preview UX refinement

- Reordered the local preview around the confirmed market state, fixed-rule
  support/drag context, and transition distance; Composite is now supporting
  information rather than the dominant visual.
- Added display-only precision, score bars, Support/Neutral/Drag labels, and
  compact short-viewport behavior while retaining exact calculation ledgers in
  expandable audit sections.
- Expanded relationship highlights and pair detail with both-leg returns,
  relative spread, deterministic investor-readable evidence, and clearer
  state-versus-relative-performance separation. All 16 preregistered pairs
  remain visible.
- No API payload, formula, parameter, threshold, state, fingerprint,
  Production data, snapshot, authentication, network, or deployment boundary
  changed.

## 2026-08-25 — Market Regime read-only API and desktop preview

- Added the canonical, source-bound `/tmp` preview bundle and formal reader,
  plus a socket-guarded no-apply CLI. Payload identity excludes `generated_at`
  and binds all three completed offline audits.
- Added default-disabled private overview and relationship-detail endpoints.
  The configured bundle is validated once at startup; default Production
  behavior never depends on `/tmp` and no request scans the EOD panel.
- Added the desktop Market Regime & Opportunity Map with both Universes, five
  auditable dimensions, full 16-pair 5/10/20 map, fixed highlights, filters,
  URL navigation, pair detail, evidence/counterevidence, and methodology.
- Real local 2026-08-21 data reconciled exactly. Production data, snapshot,
  Activation, authentication, guest access, network, credentials, OCI, and
  deployment were unchanged.

## 2026-08-25 — Market Regime Phase 2 offline ETF relationship map

- Added the immutable 30-ETF/16-pair registry, typed relationship contracts,
  deterministic 5/10/20-session calculations, explicit state precedence,
  confidence/missingness, and fixed evidence/counterevidence explanations.
- Added a genuinely independent raw-panel Oracle, chronological replay/append,
  permutation and future-prefix checks, nine-case Decimal context matrix, and a
  socket-guarded no-apply CLI with canonical `/tmp` artifacts.
- The formal 2026-08-21 run produced 336 history rows and all 16 current pairs.
  Oracle mismatch was zero; two runs had logical fingerprint
  `e5acfa29771d965e9bdf21d1bfab24148220217ac474327cdc60e2212532e3a5`
  and byte-identical non-time artifacts.
- Confidence is `low` for every pair because only 26 sessions exist. Regime
  comparison is contemporaneous and non-causal. No EOD/Identity/Activation,
  Production, API, frontend, snapshot, network, credential, bundle, or OCI
  state changed.

## 2026-08-25 — Market Regime Phase 1b deterministic state classification

- Added an immutable state parameter contract, typed candidate/confirmed state
  records, deterministic bootstrap and hysteresis state machine, chronological
  replay/append boundary, and complete transition and explanation ledgers.
- Added a genuinely independent state Oracle plus exact threshold, reversal,
  missingness, XNYS gap, restart, future-prefix, cross-Universe, and global
  Decimal-context coverage. The offline CLI is socket guarded and writes only
  canonical `/tmp` review artifacts.
- The formal 2026-08-21 trajectory had six calculable sessions per Universe.
  Both Universes initialized Balanced provisionally on 2026-08-17, cleared it
  on 2026-08-18, held Balanced in the 2026-08-20 hysteresis band, and ended
  candidate/confirmed Balanced on 2026-08-21 with zero Oracle mismatch.
- Two full runs produced byte-identical non-time artifacts. No Phase 1a
  formula, EOD, Identity, Activation, API, frontend, snapshot, Production,
  network, credential, bundle, or OCI state changed.

## 2026-08-25 — Market Regime Phase 1a offline core

- Added typed Phase 1a analytics contracts, immutable fixed V1 parameters, a
  formal 26-session EOD/same-day-Identity/Activation source reader, pure five-
  dimension calculation service, and a complete raw/normalized/weight/
  contribution/missingness/explanation ledger.
- Added an independently implemented raw-panel oracle, stable-ID permutation
  checks, no-future/no-cross-Universe gates, explicit local Decimal precision
  50 arithmetic, outer precision/trap invariance, and contribution
  reconciliation.
- Added a socket-guarded offline CLI and canonical `/tmp` artifact reader. The
  path boundary rejects `/data`, repository paths, symlinks, traversal, and
  existing non-empty targets; no apply or Production writer exists.
- The formal 2026-08-21 calculation produced Primary/Secondary Composites
  `63.9102`/`64.8167`, with all 18 metrics available per Universe and zero
  oracle mismatch. State/hysteresis is explicitly deferred to Phase 1b; ETF
  relationships, sectors, candidates, API, frontend, snapshot, bundle, and OCI
  remain unimplemented.

## 2026-08-25 — Market Regime & Opportunity Map V1 design

- Added the product specification, proposed data contract, implementation
  architecture, and ADR for a transparent four-layer Market Regime &
  Opportunity Map.
- Defined five exact regime dimensions and fixed composite weights, hysteretic
  regime and candidate states, a 16-pair registered ETF ledger, seven-component
  candidate score, three visible risk modes, evidence templates, and a
  walk-forward anti-overfitting framework.
- Recorded the formal data feasibility boundary: 26 completed EOD sessions
  support 5/10/20-session analytics; point-in-time sector taxonomy, 40/60-session
  history, market cap, fundamentals, options, corporate-action reconciliation,
  and true fund flows remain deferred.
- Split V1A existing-data analytics from V1B taxonomy-dependent sector
  transmission and recommended an offline `/tmp` Phase 1a ledger as the next
  minimum implementation slice. This change is documentation only; no
  Production, network, snapshot, frontend, bundle, or OCI action occurred.

## 2026-08-23 — Approval-bound same-day Identity and EOD catch-up

- Split both Massive administrator entrypoints into fetch-only `/tmp` package,
  offline deterministic approval plan, approval-bound offline apply, and
  formal reread stages. Disabled the old direct network-to-production Python
  functions.
- Bound EOD to the exact same-day logical Identity fingerprint and made the
  Identity logical marker last. Added immutable-component
  verify-then-complete recovery with baseline CAS and fail-closed partial or
  changed state.
- Added HTTPS host/path/date pagination controls, duplicate/loop ceilings,
  credential-bearing URL sanitization, package/plan custody, apply socket
  prohibition, durable atomic publication, and replay/symlink/traversal gates.
- Completed the two-session 2026-08-20/21 workflow only in `/tmp` with fake
  transport. Provider, credential, external network, Production apply, `/data`,
  Dashboard snapshot, Activation, frontend bundle, and OCI changes were zero.

## 2026-08-23 — Formal Dashboard Funnel and durable Snapshot V2 readiness

- Added Dashboard contract 2.1 with ten source-backed, sequentially closed Funnel stages for each active public Universe; API/snapshot carry them directly and React switches the matching ledger with the existing stable URL selection.
- Added snapshot contract 1.4 plus immutable publication, active pointer with V1 no-pointer compatibility, canonical approval plan, lock/CAS, fsync, completed-target verify-then-link, and independent rollback.
- Added an XNYS freshness gate at plan creation and inside the apply lock. The formal candidate is 1,718/1,831 with all 20 stages, but actual EOD 2026-08-19 trails expected 2026-08-21 by two sessions, so publication is blocked.
- Production snapshot, Activation pointer, Dashboard deployment, and OCI release were unchanged; `/data` and external-network writes were zero.

## 2026-08-22 — Versioned Activation V2 readiness

- Bound the main Activation V2 apply to a canonical dry-run approval package. Bare apply is rejected; the immutable plan freezes time/IDs and binds current state, sources, paths, catalog, rollback, fingerprints, and exact Parquet/manifest/pointer hashes. Apply requires the separately approved plan digest and current-state token, revalidates them under lock before production directory creation, and verifies the published bytes against the plan.
- Closed the four authorization-review findings: completed inactive targets now have a verify-then-link path, first-created directories receive durable parent-entry fsyncs, rollback apply requires the dry-run-approved pointer digest, and the public catalog is contractually Primary-first.

- Added a revisioned immutable Activation V2 contract/repository and a fingerprinted atomic active/default pointer. Formal consumers now use one active reader, with compatibility fallback only when no pointer exists and fail-closed behavior for malformed or inconsistent pointers.
- Added a separately authorized rollback boundary, exclusive lock and compare-and-swap concurrency protection, explicit crash-boundary behavior, existing/partial-target rejection, final formal reread, and default-dry-run CLIs.
- The production-root dry-run binds only superseding publication `51403e939930265ba1a273e9f8bc2113cb455f22e8437c1d2775005fd293ee97` and plans 1,718 CS plus 1,831 CS+ADRC. Apply count was zero; production remains 1,641/1,747 and no pointer, snapshot, Dashboard, frontend, or OCI change occurred.

## 2026-08-21 — HSAI historical security-form interval correction

- Corrected the unpublished HSAI reviewed-form plan so ADR/ADS is effective from the 2023-02-09 Nasdaq listing, not the 2026-07-10 ADS ratio adjustment. The frozen four-source ledger separates security-form effective time, source document/covered-fact time, and UTC review/record time. Two production-root dry-runs of immutable revision `authoritative-security-form-v2` were identical and yielded 1,718 CS / 1,831 CS+ADRC with zero oracle, V1, type, duplicate, orphan, conflict, or funnel errors. No apply, `/data` write, production/Shadow mutation, Activation, Dashboard, snapshot, network, credential, or OCI action occurred.

## 2026-08-21 — HSAI authoritative security-form readiness

- Added an offline-only reviewed security-form evidence contract and immutable superseding full-base revision strategy. HSAI is corrected by stable instrument ID from provider CS to reviewed ADR/ADS without bypassing quantitative gates. The dry-run plans 1 reviewed-form row, 4,565 metrics, 9,130 decisions, 3,549 memberships/diffs, and 20 funnels; Primary is 1,718 CS and Secondary is 1,831 (1,718 CS + 113 ADRC). AKR, UNIT, and DFNS warnings remain accepted and non-blocking. No apply, production data, Activation, Dashboard, snapshot, network, credential, or OCI change occurred.

## 2026-08-20 — Full-base trailing-liquidity scope correction

- Proved by formal reader and code-path review that Trailing Liquidity V1 was scoped to candidates already passing the old previous-session USD 20M dollar-volume gate.
- Reproduced all frozen V1 decisions and fingerprints before calculating the correction.
- Added a provider-evidence-first builder, complete decision ledger, sequential/overlapping funnel contract, versioned Parquet repository, formal reader, offline CLI, and scope-regression fixtures.
- Corrected shadow results are 1,719 CS and 1,831 CS+ADRC; current activated members are fully retained, with 78/84 additions and zero prohibited-type leakage.
- Recorded completed authenticated desktop selector validation without claiming mobile, tablet, or keyboard acceptance.
- No provider request, credential access, canonical-data mutation, Dashboard/API/frontend/snapshot change, OCI access, or deployment occurred.
- The sole shadow apply exited 1 before staging on an audit-only Decimal scale violation. No target or residue was created and no second apply ran. The offline contract now persists an exact threshold-state boolean instead of narrowing the daily Decimal product; publication remains pending separate authorization.
- Strengthened the future publication gate to compare every immutable V1 metric as well as every V1 decision before a corrected shadow can be published.
- Added exact Decimal-threshold boundary coverage and corrected the V1 metric reproduction gate to compare Decimal values independently of harmless trailing-zero scale; the full backend now passes 838 tests with two existing warnings.
- The newly authorized dry-run exited 0 and exactly reproduced all expected counts, fingerprints, and 20 closed funnel stages. Its one apply exited 1 before staging because a remaining metric Decimal exceeded `decimal128(38,10)`; no target, staging residue, Activation, Dashboard, snapshot, or OCI change resulted, and no second apply ran.
- Diagnosed the failure completely offline: only two of 3,218 non-null metric medians exceeded scale 10; previous close had zero violations. Canonical Decimal128(38,10) inputs imply a theoretical 76/20 product and 77/21 exact even median, exceeding Decimal256's precision-76 ceiling.
- Finalized the unpublished full-base V1 physical contract with Decimal128(38,10) previous close and a bounded exact Decimal tuple for medians. The final no-apply dry-run round-tripped all 4,565/8,758/3,550/3,550/20 planned rows through temporary Parquet, preserved V1 and corrected fingerprints, and left `/data`, production 1,641/1,747, Dashboard, snapshot, and OCI unchanged.
- Audited Python Decimal context semantics and found a latent silent-rounding risk in daily multiplication and even-median arithmetic despite zero mismatches in the 2026-08-19 dataset. Replaced eligibility arithmetic with signed integer coefficients and explicit scales, made ratio gates exact by cross multiplication, isolated audit analytics in a derived precision-78 local context, and added an independent `Fraction` oracle to the dry-run gate.
- Verified context invariance at precisions 9/28/50, alternate rounding modes, and trapping `Inexact`/`Rounded`. The final dry-run reconciled 90,506 available daily observations, 4,435 complete medians, all decisions/memberships, and 1,864 immutable V1 metrics with zero mismatch; corrected memberships remain numerically unchanged. No apply, `/data` write, provider request, credential access, Dashboard/snapshot change, OCI access, or deployment occurred.
- Removed the final authorization blockers: EOD fingerprint Decimal rendering now uses context-free tuple encoding, the Fraction oracle rebuilds every decision and membership from raw canonical inputs, and nonmembership analytics uses a fresh explicit precision-78 context without inherited traps or leaked flags.
- Repeated the complete production-root dry-run at precisions 9, 28, and 50 and with outer `Inexact`/`Rounded` traps. All four runs exited 0 with zero stored-EOD fingerprint, daily-product, median, decision, membership, or V1 mismatch; corrected counts/fingerprints remain 1,719/1,831. No apply or production change occurred.

## 2026-08-19

- Accepted Dashboard Universe Activation V1: `Common Shares` is the sole default and `Common Shares + ADRs` the optional view. Legacy remains formally readable for rollback and is not an ordinary selector option.
- Added the versioned activation contract/repository/formal reader and default-dry-run administrator CLI, with explicit Arrow schema, atomic publication, final logical marker, source validation, and a regression that requires successful apply postflight to return exit 0.
- Integrated stable-ID activation selection across private market APIs, multi-Universe private snapshots, and the React Dashboard. URL selection is allowlisted and all Universe-dependent modules use one fingerprint; failures do not silently fall back to Legacy or demo.
- Published the two-row 2026-08-19 activation in one `--apply` invocation that completed formal reread and exited 0. Dataset/logical fingerprints are `a4e76ddc328f3d971d8c66ed305640b6c9810b82bbb6b9849fc9f353ffd0e504` and `f9018502a57dc859c83ce843872c8119b3fb855980cd143a2da8d0a8bbc1e0ca`; the prior 240-file inventory remained byte-identical.
- Exported private snapshot contract 1.3, built the 13-file versioned bundle, and deployed OCI release `2026-08-19T083341Z-7ed7fdc21686`. Public login and unauthenticated protection checks passed; authenticated selector/visual verification remains manual.

- Implemented Reviewed Eligibility Override V1, stable-ID Legacy/A/B comparison, explicit Parquet schemas, atomic shadow repository, formal reader, and a default-dry-run administrator CLI. VCX receives an authoritative closed-end-fund exclusion and AKAN an authoritative operating ordinary-share allow; allow cannot bypass upstream gates.
- Published 2 overrides and 3,388 pre-activation decisions plus a final logical marker. The sole apply atomically wrote all targets but exited 1 during final reread because of a missing reader import; no second apply occurred, and the repaired reader subsequently validated all sources, schemas, counts, fingerprints, and hashes read-only.
- Legacy is 1,864; Candidate A/B passed and final shadows are 1,641/1,747. A removes 223 from Legacy (including 113 ADRCs); B removes 117; B minus A is 106 passed ADRCs. Ten incomplete/missing-previous records retain their data-derived exclusions.
- Recommended Provider-Classified Common Shares (Provisional) as primary, the ADR-inclusive view as optional secondary, and Legacy for compatibility/rollback only. Production Universe and Dashboard remain unchanged; network, credential, provider, OCI, snapshot/bundle, and deployment operations were zero.

- Accepted ADR 0016 and implemented versioned `decimal128(38, 10)` Parquet contracts, a provider-neutral metric/decision service, atomic repository, formal reader, and default-dry-run administrator CLI for Trailing Liquidity V1 shadow publication.
- Published one 1,864-row union metric dataset and one 3,615-row Candidate A/B decision dataset after one successful dry-run and one authorized apply. The final logical marker binds the exact 20 EOD/identity sources, 2026-08-14 membership evidence, thresholds, counts, hashes, and fingerprints.
- Reconciled Candidate A to 1,641 passed, 97 below-liquidity, 4 below-price, 1 missing-previous, and 8 insufficient-history records; Candidate B reconciles to 1,747/103/4/1/9. Ten unique incomplete/missing-previous instruments were audited only from local bar and identity evidence.
- Preserved all 223 canonical protected files byte- and metadata-identically; five derived artifacts were added with zero staging/raw residue. External requests and credential accesses were zero, and production Universe, Dashboard/API/frontend, snapshot/bundle, OCI, and deployment state did not change.

- Used the existing XNYS 4.13.2 freshness service at the execution instant to authorize exactly 2026-08-17, 08-18, and 08-19 after finding actual latest 08-14, expected latest 08-19, and lag three. The weekend generated no request.
- Published and formally reread three same-day identity snapshots and three adjusted=false EOD partitions in strict order: 9,939/9,947/9,947 canonical instruments and 9,916/9,909/9,926 bars. All six entrypoints exited 0; total Massive requests were 45 and retries were zero.
- Preserved the original 196-file inventory content and metadata; exactly 27 authorized files yielded 223 files and digest `e453c759200cdf1dfb603a38b4eb519a74092c0f594865c226c233a92d2306d2`. Canonical freshness is now lag zero at 2026-08-19.
- The rolling 07-22 through 08-18 window is 20/0/0 and `ready`. With membership evidence fixed as-of 08-14, A/B have 1,738/1,850 non-null medians, 1,641/1,747 passes, and 8/9 insufficient histories. No derived dataset, Dashboard/API/frontend, Universe activation, SEC/OCI access, snapshot/bundle, or deployment occurred.

## 2026-08-16

- Completed the separately authorized final Massive backfill batch for 2026-08-10 and 08-11 in strict order. Each Instrument Master entrypoint ran once with 14 reference pages and each same-day Grouped Daily entrypoint ran once with adjusted=false; all four exited 0 with zero retries and at least 15 seconds between adjacent entrypoints.
- Published and formally reread two same-day identity snapshots with 9,913/9,924 canonical instruments and two EOD partitions with 9,892/9,885 bars. Schema, count, ordering, fingerprint, physical hash, same-day identity reference, conflict isolation, atomic publication, and staging cleanup passed.
- The original 178-file inventory remained content- and metadata-identical; 18 authorized files yielded 196 files and digest `eb86f69336e567019b7e1553501e38e8545be6a60e5c43e2da0544b7b04c98c0`. The 20-session descriptor is `ready`: A/B have 1,742/1,854 complete medians and 9/10 insufficient-history members.
- No production derived publisher exists, so no trailing dataset, Dashboard result, Universe activation, snapshot, bundle, or deployment was created. Only 30 authorized Massive requests occurred; SEC, OCI, other services, other dates, and retries were zero.

- Completed the separately authorized fifth three-session Massive backfill batch for 2026-08-05, 08-06, and 08-07 in strict order. Each Instrument Master entrypoint ran once with 14 reference pages and each same-day Grouped Daily entrypoint ran once with adjusted=false; all six exited 0 with zero retries and at least 15 seconds between adjacent live entrypoints.
- Published and formally reread three same-day identity snapshots with 9,898/9,907/9,907 canonical instruments and three canonical EOD partitions with 9,869/9,875/9,877 bars. Existing quality, schema, count, ordering, fingerprint, physical-hash, identity-reference, atomic-publication, and staging-cleanup gates all passed.
- The original 151-file protected inventory remained content- and metadata-identical; exactly 27 authorized files were added, yielding 178 files and digest `6033cd1b1dad4f74d62dec4d8addcdd64af4b73b8b3b99ab976f1c4eed65e2df`. The history window now has 18 completed and two missing sessions, remains `insufficient_history`, and emits no 20-session median.
- Reached only the authorized Massive reference and three Grouped Daily endpoints: 45 requests total, zero retries. No SEC/OCI/other service, later session, scheduler, API/frontend, Dashboard, snapshot/bundle, deployment, or Universe activation occurred. Final state: `completed_three_session_batch`.

- Completed the separately authorized fourth three-session Massive backfill batch for 2026-07-31, 08-03, and 08-04 in strict order. Each Instrument Master entrypoint ran once with 14 reference pages and each same-day Grouped Daily entrypoint ran once with adjusted=false; all six exited 0 with zero retries and at least 15 seconds between adjacent live entrypoints.
- Published and formally reread three same-day identity snapshots with 9,886/9,882/9,896 canonical instruments and three canonical EOD partitions with 9,853/9,858/9,877 bars. Existing quality, schema, count, ordering, fingerprint, physical-hash, identity-reference, atomic-publication, and staging-cleanup gates all passed.
- The original 124-file protected inventory remained content- and metadata-identical; exactly 27 authorized files were added, yielding 151 files and digest `e775d09906593cd15bc5d324dac73d9042cbc46645d012d9e5bcaf66dd77a040`. The history window now has 15 completed and five missing sessions, remains `insufficient_history`, and emits no 20-session median.
- Reached only the authorized Massive reference and three Grouped Daily endpoints: 45 requests total, zero retries. No SEC/OCI/other service, later session, scheduler, API/frontend, Dashboard, snapshot/bundle, deployment, or Universe activation occurred. Final state: `completed_three_session_batch`.

- Completed the separately authorized third three-session Massive backfill batch for 2026-07-28, 07-29, and 07-30 in strict order. Each Instrument Master entrypoint ran once with 14 reference pages and each same-day Grouped Daily entrypoint ran once with adjusted=false; all six exited 0 with zero retries and at least 15 seconds between adjacent live entrypoints.
- Published and formally reread three same-day identity snapshots with 9,881/9,882/9,888 canonical instruments and three canonical EOD partitions with 9,848/9,851/9,855 bars. Existing quality, schema, count, ordering, fingerprint, physical-hash, identity-reference, atomic-publication, and staging-cleanup gates all passed.
- The original 97-file protected inventory remained content- and metadata-identical; exactly 27 authorized files were added, yielding 124 files and digest `1187d3de85c668dbb459e3808640b86325daf9e5f247a553b99785bfe465e9b1`. The history window now has 12 completed and eight missing sessions, remains `insufficient_history`, and emits no 20-session median.
- Reached only the authorized Massive reference and three Grouped Daily endpoints: 45 requests total, zero retries. No SEC/OCI/other service, later session, scheduler, API/frontend, Dashboard, snapshot/bundle, deployment, or Universe activation occurred. Final state: `completed_three_session_batch`.

- Completed the separately authorized second three-session Massive backfill batch for 2026-07-23, 07-24, and 07-27 in strict order. Each Instrument Master entrypoint ran once with 14 reference pages and each same-day Grouped Daily entrypoint ran once with adjusted=false; all six exited 0 with zero retries and at least 15 seconds between adjacent live entrypoints.
- Published and formally reread three same-day identity snapshots with 9,881/9,879/9,881 canonical instruments and three canonical EOD partitions with 9,844/9,833/9,859 bars. Existing quality, schema, count, ordering, fingerprint, physical-hash, identity-reference, atomic-publication, and staging-cleanup gates all passed.
- The original 70-file protected inventory remained content- and metadata-identical; exactly 27 authorized files were added, yielding 97 files and digest `27fe6529ca6b7789f5901065f0d9dad405c8532a835be04846022437e7c330dc`. The history window now has nine completed and 11 missing sessions, remains `insufficient_history`, and emits no 20-session median.
- Reached only the authorized Massive reference and three Grouped Daily endpoints: 45 requests total, zero retries. No SEC/OCI/other service, later session, scheduler, API/frontend, Dashboard, snapshot/bundle, deployment, or Universe activation occurred. Final state: `completed_three_session_batch`.

- Completed the separately authorized first three-session Massive backfill batch for 2026-07-20, 07-21, and 07-22 in strict order. Each Instrument Master entrypoint ran once with 14 reference pages, and each same-day Grouped Daily entrypoint ran once with adjusted=false; all six exited 0 with zero retries and at least 15 seconds between adjacent live entrypoints.
- Published and formally reread three same-day identity snapshots with 9,880/9,879/9,879 canonical instruments and three canonical EOD partitions with 9,858/9,846/9,847 bars. Existing quality, schema, count, ordering, fingerprint, physical-hash, identity-reference, atomic-publication, and staging-cleanup gates all passed.
- The original 43-file protected inventory remained content- and metadata-identical; exactly 27 authorized files were added, yielding 70 files and digest `b2537a2d3627f1915c38540ea7af32a93b960a8c826ef1913151c426ae169fe3`. The history window now has six completed and 14 missing sessions, remains `insufficient_history`, and emits no 20-session median.
- Reached only the authorized Massive reference and three Grouped Daily endpoints: 45 requests total, zero retries. No SEC/OCI/other service, later session, scheduler, API/frontend, Dashboard, snapshot/bundle, deployment, or Universe activation occurred. Final state: `completed_three_session_batch`.

- Completed the separately authorized 2026-07-17 single-session Massive backfill pilot. The Instrument Master entrypoint ran once with 14 reference pages and zero retries, then the Grouped Daily entrypoint ran once after a 52-second interval with one adjusted=false request and zero retries.
- Published and formally reread the same-day identity snapshot (13,024 observations, 9,879 canonical instruments/resolver entries) and canonical EOD partition (9,844 bars). Existing schemas, quality gates, fingerprints, Parquet hashes, identity references, atomic publication, and staging cleanup all passed; raw provider payload was not retained.
- The original 34-file protected inventory remained content- and metadata-identical; nine authorized identity/EOD files were added. The 20-session window now has three completed and 17 missing sessions, remains `insufficient_history`, and emits no 20-session median.
- Reached only the authorized Massive reference and 2026-07-17 Grouped Daily endpoints: 15 requests total, zero retries. No SEC/OCI/other service, later session, scheduler, API/frontend, Dashboard, snapshot/bundle, deployment, or Universe activation occurred. Final state: `completed_single_session_pilot`.

- Added provider-neutral frozen contracts and services for bounded multi-session canonical EOD reads, XNYS 20-session planning, exact Decimal median dollar-volume proxy calculation, readiness reconciliation, and a planning-only historical backfill plan. Analysis-day bars are structurally excluded from their own eligibility window.
- Added a stable-ID history reader that validates only requested partitions, manifest/schema/count/content fingerprints, physical Parquet SHA-256, identity references, revisions, path containment, and symlinks without calling a ticker resolver. `current_as_of_constituent_liquidity` is implemented; the distinct `point_in_time_historical_panel` remains unimplemented.
- Read-only production audit computed the 2026-07-17 through 2026-08-13 XNYS window: 08-12 and 08-13 completed, 18 missing, zero corrupt. Candidate A/B have zero 20/20 results and all 1,751/1,864 records are `insufficient_history`; no median or Dashboard result was generated.
- Produced a no-execution plan for 18 same-day identity plus Grouped Daily sessions: estimated 270 requests, conservative ceiling 378, retry zero, fixed 15-second spacing, a separately authorized pilot, then at most six three-session batches. No network, credential, `/data` write, production dataset/API/frontend/snapshot/bundle, OCI, deployment, backfill, scheduler, or Universe activation occurred.

- Added a provider-neutral, frozen offline audit service for two non-production shadows: 1,751 Massive-`CS` Provider-Classified Common Shares and a separate 1,864-member CS+ADRC comparison containing 113 ADRCs. Classification uses only stable `instrument_id` evidence; the sequential USD 5/USD 20M Decimal filter is labeled `one_session_liquidity_provisional`.
- Reread the completed 25-code catalog, 13,110 observations, 9,939 canonical evidence records, 9,939-member identity snapshot, and 2026-08-13/14 EOD partitions through existing manifest/schema/count/fingerprint/hash gates. All shadow hard gates passed; memberships and fingerprints are order-independent, and Legacy reconciles as 1,751 CS plus 113 ADRC.
- Recorded provider-form limitations and edge evidence for VCX, AKAN, BCPC, TPC, VXT, and AZ. Known reviewed conclusions are report-only because no completed reviewed-override dataset exists; no ticker exception changes membership. SEC B2 remains paused and Core/Broad activation remains deferred.
- The audit was fully offline: zero SEC/Massive/other network requests, zero credential access, read-only `/data`, tmp-only test/audit output, and no production dataset, API, frontend, Dashboard Universe, snapshot, bundle, OCI, deployment, EOD/backfill/scheduler, or production activation change.

- Executed the final authorized SEC B2 entrypoint exactly once from `2026-08-16T10:39:44Z` through `2026-08-16T10:39:51Z`. It made six SEC requests and zero retries, progressed through Series/Class landing/selected-CSV validation and CEF landing selection, then failed during the selected CEF CSV attempt with `sec_transport_or_source_validation_failure`; BDC and submissions were not reached.
- Retained one 329-byte sanitized diagnostic with request/retry counts and the generic failure code. Its empty quality summary and cleaned staging do not preserve the successful schema `3.0` landing selections or a narrower sixth-request subcondition, so no candidate counts, selected dates/paths, artifact hashes, or new exception are inferred. No second live run occurred.
- Published no SEC source cache, observations, canonical evidence, logical manifest, or Core/Broad shadow audit. Four targets remain absent, staging is zero, and the protected 34-file/12,942,699-byte inventory digest is unchanged. No Massive/OCI/EOD/Dashboard/snapshot/bundle/deployment or Universe activation occurred. SEC B2 is paused for the current product stage.

- Formalized the SEC source cache as exactly nine private provenance artifacts: two official ticker JSON files, three official landing HTML pages, three selected CSV files, and `submissions.zip`. Each artifact now records its role, official URL, byte size, and SHA-256; all are reread before the completion manifest is written last and staging is atomically published. Landing HTML remains private and is never Dashboard/public content.
- Hardened synthetic-only submissions ZIP validation for encryption, duplicate and normalized-duplicate names, absolute/traversing/backslash/percent-encoded paths, symlink/non-regular/nested/unapproved members, count and expansion bounds, compression ratio, zero compressed-size metadata, bounded reads, JSON parsing, CIK consistency, and basic filings schema. No extracted content is persisted.
- Added offline fake-transport and `tmp_path` regressions for exact manifest reconciliation, manifest secrecy, landing Content-Type/signature, atomic publication, cleanup, existing/symlink targets, malicious ZIPs, and socket prohibition. No live SEC/Massive request, credential metadata/content access, `/data`, OCI, snapshot/bundle, deployment, EOD/backfill/scheduler, Dashboard, or Universe activation occurred.

- Replaced SEC landing discovery's all-history exact-template gate with a two-stage policy: every CSV candidate must pass Baseline URL Safety, selection uses all structurally/date-valid cutoff candidates, and only the unique latest selected source must pass its dataset-specific Exact Dataset Template before download. There is no fallback to an older allowlisted source.
- Added strict nonblocking handling only for baseline-safe, explicitly dated, file-year-consistent candidates strictly older than the selection whose sole exact-rule failure is `path_template_mismatch`, plus a separate strictly older undated warning. The observed 2022 path was not added to the allowlist and is never a transport target; the existing exact 2023/2024 rules and CEF/BDC rules are unchanged.
- Upgraded new landing diagnostics to schema `3.0` with explicit baseline/template/temporal/action fields, warning and blocking aggregates, selected template, status/failure/warnings, and deterministic fingerprint. Historical schema `2.0` diagnostics remain unchanged and audit-readable. Source acquisition now revalidates the structured selected object, counts, fingerprint, baseline safety, and exact template before transport is called.
- Added a local 2026–2022 fixture and offline regressions for row/XML order independence, multiple unknown old filenames, selected/same/newer/future hard failures, undated history, date integrity, complete baseline URL safety, dataset isolation, warning/blocking counts, schema compatibility, redaction, socket prohibition, and selected-only fake transport behavior. No live run, credential metadata/content access, `/data`, OCI, snapshot/bundle, deployment, EOD/backfill/scheduler, Dashboard, or Universe work occurred.

- Executed the separately authorized post-2023-remediation SEC entrypoint exactly once. The run used cutoff 2026-08-14, request ceiling 12, made three SEC requests and zero retries, accepted the 2026/2025 modern, exact 2024 legacy, and exact 2023 underscore Series/Class candidates, then failed closed on a fifth 2022 underscore basename with `path_template_mismatch`.
- Schema `2.0` reported five candidates, four allowlisted/cutoff-eligible, one rejected, and zero selected. No CSV, CEF, BDC, or submissions request followed. The 2022 path was not approved, no rule was changed, and no second run occurred.
- Published no SEC source cache, observation, canonical evidence, or logical manifest. Staging residue was zero, the 34-file protected inventory remained unchanged, and only the 5,674-byte sanitized diagnostic was retained. No Massive/OCI access, snapshot, bundle, deployment, EOD, backfill, scheduler, Dashboard, or Universe activation occurred.

- Added one exact offline Series/Class filename contract based only on the fifth run's schema `2.0` evidence: the modern directory plus `investment_company_series_class_2023.csv` is accepted only for parsed file year 2023. No rule is inferred for 2022 or earlier, and underscore basenames for 2024 and later remain rejected.
- Added a four-candidate official-shape fixture and regressions proving four allowlisted/cutoff-eligible candidates, zero rejected, exactly one deterministic 2026 selection, row-order independence, exact relative/absolute acceptance, URL-security rejection coverage, CEF/BDC isolation, duplicate stability, aggregate consistency, sentinel redaction, and zero external socket attempts.
- Preserved the modern Series/Class template, exact 2024 legacy-directory rule, CEF/BDC paths, cutoff, live retry setting, generic SEC transport, diagnostic schema `2.0`, and candidate-derived aggregates. No live run, credential metadata/content access, `/data` or OCI access, snapshot/bundle, deployment, EOD, backfill, scheduler, Dashboard, or Universe work occurred.

- Executed the separately authorized post-remediation SEC entrypoint exactly once. The run used cutoff 2026-08-14, made three SEC requests and zero retries, accepted the 2026 and 2025 modern Series/Class candidates plus the exact 2024 legacy candidate, then failed closed on a fourth 2023 underscore-style basename with `path_template_mismatch`.
- Real schema `2.0` aggregates remained consistent with candidate states: four CSV candidates, three allowlisted/cutoff-eligible, one rejected, and zero selected. No CSV, CEF, BDC, or submissions request followed; no rule was changed and no second run occurred.
- Published no SEC source cache, observation, canonical evidence, or logical manifest. Staging residue was zero, the 34-file protected inventory remained unchanged, and only the 4,798-byte sanitized diagnostic was retained. No Massive/OCI access, snapshot, bundle, deployment, EOD, backfill, scheduler, or Universe activation occurred.

- Added one exact offline Series/Class legacy-path rule based only on the fourth run's schema `2.0` evidence: the observed 2024 directory and 2024 basename are accepted only for file year 2024. The modern template remains valid; 2023-or-earlier, 2025, 2026, future legacy paths, neighboring spellings, CEF, and BDC remain rejected or unchanged.
- Made candidate diagnostics the single source for CSV candidate, allowlisted, parsed-date, future, historical-undated, rejected, cutoff-eligible, and selected aggregates. Added `selected_count` within compatible schema `2.0` and explicit duplicate exclusion so normal and mid-stream fail-closed diagnostics cannot drift from candidate states.
- Added an official-shape three-candidate fixture and regression coverage for deterministic 2026 selection, row reversal, relative/absolute exact-legacy acceptance, year/basename/directory and all URL safety rejections, aggregate consistency, other-dataset isolation, sentinel redaction, and socket prohibition. No live run, credential or `/data` access, provider request, OCI access, snapshot, bundle, deployment, EOD, backfill, or scheduler work occurred.

- Executed the separately authorized post-schema SEC evidence entrypoint exactly once with cutoff 2026-08-14. It ran from `2026-08-16T07:46:45Z` to `2026-08-16T07:46:51Z`, returned exit code 1, made three SEC requests and zero retries, and stopped at Investment Company Series/Class landing discovery; CEF, BDC, submissions, Massive, OCI, and all other endpoints were not reached.
- Captured sanitized schema `2.0` evidence for three Series/Class CSV candidates. The 2026 and 2025 candidates matched the current path template; the 2024 candidate used the public `investment-company-series-and-class-information` directory variant and failed with `path_template_mismatch`. Query, fragment, and userinfo were absent. The allowlist was not changed and no second run was performed.
- Published no SEC source cache, observation, canonical evidence, or logical completion manifest. Staging residue was zero; the pre/post 34-file protected inventory remained 12,942,699 bytes with unchanged deterministic digest `398d3c8eb8a986ffc34a7f2fe19c50961eca0d9ed52bd980da95217561333f17`. Existing identity, canonical EOD, and Massive evidence data were unchanged.
- Retained only the sanitized 3,903-byte failed diagnostic (`9abd62a6ef9dc4f61e41b6e32c9dde54b594d33dbf8b640c5673b764ede05c50`). No credential value, raw response, production snapshot/bundle, deployment, Universe activation, or OCI access occurred.

- Reconciled repository status documentation against current code, Git history, read-only `/data` metadata, completed logical manifests, and the SEC run audits. Corrected stale claims that real Massive ingestion, canonical EOD persistence, private analytics/Dashboard APIs, static Dashboard publication, and deployment tooling were absent.
- Recorded the last known OCI deployment strictly as Git/documentation history; OCI was not accessed and current live health was not asserted. Recorded ignored build/dist/snapshot/bundle artifacts, the open retention policy, undocumented `/data` child group-write policy, and the non-overwriteable `accepted_with_provenance_exception` 2026-08-14 identity snapshot.
- Clarified Event Engine design history in ADR 0004 and the Event Layer document: `Subject` is a Domain Object; `Observation` is a possible processing stage but not a core Domain Object; `Candidate` is temporary; `Event` is validated behavior; `Knowledge` is durable learning; full implementation remains deferred. This is distinct from SEC `SecEvidenceSubject`.
- Revalidated the documentation-only change with the offline backend, SEC, bulk-discovery, frontend, build, compile/import/health, shell syntax, Markdown-link, network-prohibition, and sensitive-information checks recorded in Current Status. No provider request, credential read, `/data` write, OCI access, snapshot/bundle generation, deployment, or artifact deletion occurred.

### SEC diagnostic remediation history

- Added landing-discovery diagnostic schema `2.0` with candidate/table/row ordinals, parsed year/date, bounded Size, public path structure, selection state, and finite URL rejection codes while retaining the compatible top-level `href_rejected` reason.
- Preserved all Series/Class, CEF, and BDC URL allowlists and selection semantics. Query, fragment, userinfo, external-host, raw HTML, headers, User-Agent, and contact values remain excluded from diagnostics. This offline work made zero network requests and did not access credentials, `/data`, OCI, snapshots, bundles, or deployment.
- Disabled retries specifically for the bounded SEC evidence live entrypoint and added a transport regression proving a recoverable first failure makes one request with zero retries; other provider retry behavior was unchanged.
- Executed the single newly authorized SEC run with cutoff 2026-08-14: three requests, zero retries, then a fail-closed `href_rejected` result in Investment Company Series/Class landing discovery. CEF, BDC, CSV files, and submissions were not requested.
- Published no SEC source cache, observation, canonical evidence, or logical completion manifest. Staging was clean and the 34-file protected canonical/identity/provider-evidence inventory was unchanged; no Massive access, snapshot, bundle, OCI access, or deployment occurred.

- Reworked SEC dated-CSV discovery around the official multi-table `File / Format / Size` DOM shape, including anchor-tail dates, deterministic two-digit year expansion, historical-undated exclusions, exact per-dataset paths, and row-order independence.
- Replaced the collapsed discovery failure with bounded structural reason codes and counts, and limited `application/octet-stream` acceptance to an already selected, non-empty CSV with matching dataset headers.
- Added three minimal synthetic official-shape fixtures and offline network-prohibition regression coverage. No SEC/Massive request, credential or `/data` access, snapshot, OCI access, or deployment occurred; the production Legacy Liquid Screen remains unchanged.

- Replaced the SEC landing-page single-CSV assumption with deterministic table-row selection by dataset year and effective/update date, including cutoff filtering, tied-URL rejection, URL containment, candidate statistics, and multi-year offline fixtures.
- Ran the separately authorized dated-selection B2B attempt once: three SEC requests, zero retries, then a safe stop at the first landing-page discovery gate. No CSV/submissions download, completed cache/evidence, shadow audit, snapshot, production Universe change, or OCI deployment occurred.

- Added the bounded Phase B2B SEC streaming transport, atomic source-cache safety checks, safe submissions ZIP reader, observation/canonical Parquet layers, logical completion marker, and offline tests.
- The first authorized run made three SEC requests and zero retries. It failed closed at the first official-CSV landing-page discovery gate; no completed cache/evidence partition, production snapshot, Universe switch, or OCI deployment was produced.

- Added the offline SEC issuer-structure evidence boundary with immutable point-in-time contracts, authoritative evidence grades, stable identity reconciliation, filing cutoff, BDC state-machine rules, deterministic Core/Broad decisions, and atomic tmp-only Parquet persistence.
- Added a private SEC User-Agent loader and interactive workstation helper plus an HTTPS allowlist, redaction, serial two-request-per-second ceiling, and bounded retry policy. No real contact value was configured and no SEC/Massive request, `/data` write, snapshot, OCI deployment, or production Universe change occurred.

## 2026-08-16

- Executed the separately authorized corrected Phase B1B run: one Ticker Types request plus 14 point-in-time All Tickers pages, zero retries, and no other provider endpoint.
- Published a 25-code provider catalog, 13,110 normalized observations, 9,939 canonical evidence records, and a logical completion marker after schema/count/fingerprint/hash rereads. Reconciliation was 9,939 mapped plus 3,171 expected-unjoined with zero ambiguity, collision, malformed record, duplicate, or canonical conflict.
- Re-audited the unchanged legacy 1,864-member universe: 1,862 remain quarantine, VCX is the one authoritative exclusion, and AKAN is the one authoritative Broad candidate. Core remains 0 and Broad remains 1 because provider type does not establish issuer structure or domicile.
- Added logical completed-snapshot reads, a 99.9% linkage gate, exact request-attempt accounting, and nullable sanitized diagnostics for failures before reconciliation. Existing Instrument Master, identity, resolver, EOD, and legacy calculations were not modified.
- Deployed provisional disclosure release `2026-08-14T020535Z-ebb16015b7da` from clean source commit `ebb16015b7da259e68033ca442544def5a300d63`. The bundle retained the exact prior summary, movers, and Trading Activity Map payloads while adding the legacy/provisional label and material evidence warning.
- Verified root/login/dashboard/private-data/auth boundaries, remote checksums, active Nginx/Auth Service, localhost-only 8010, zero failed units, and no 8000/8001/5173 listener. No real user password was used.

## 2026-08-15

- Completed Phase B1A entirely offline. Read-only reconciliation found two duplicate-ticker groups (`BCPC`, `TPC`), each with one stable-ID resolved observation and one identifier-free excluded observation; old ticker fallback caused all four false ambiguities and a business-key conflict count of four.
- Split normalized Provider Security Observation V1 from canonical Provider Instrument Security Evidence V1, corrected linkage to 9,939/9,939 with 3,171 expected-unjoined observations, and added deterministic observation IDs plus canonical conflict handling.
- Added sanitized failed-run diagnostics outside completed evidence datasets. No Massive/SEC request, credential access, `/data` write, production snapshot, frontend deployment, or OCI access occurred.

- Selected Core U.S. Domestic Operating Equities as the future default and Broad U.S.-Listed Operating Equities as the future secondary view; production activation remains deferred.
- Implemented provider ticker-type catalog and point-in-time instrument security evidence contracts, bounded Massive ingestion, atomic Parquet persistence, and provisional Dashboard governance metadata.
- Ran one authorized Phase B1 sequence: 1 Ticker Types request plus 14 All Tickers pages, zero retries. The 13,110 raw records reconciled, but four ambiguous mappings, nonzero mapped business-key conflicts, and an initially incorrect identity-link denominator failed hard gates.
- Published no evidence partition, generated no production snapshot, and made no OCI deployment. Corrected the identity-link denominator and retained the production stop pending a separately authorized rerun.

- Accepted ADR 0015 and implemented provider-neutral, effective-dated Security Classification V1 with separate security form, issuer structure, listing scope, evidence, status, and disposition.
- Completed the read-only Phase A audit: 9,939 Instrument Master records, 9,889 comparable records, 5,360 explicit ETFs, 4,527 unknown/quarantined non-ETF records, one excluded VCX closed-end fund, and one Broad candidate AKAN foreign ordinary share.
- Computed non-production Phase A Core and Broad candidates of 0 and 1. Production remains on the legacy 1,864-member universe pending evidence remediation; the later product-policy decision does not make these evidence-limited counts production-ready.
- Added deterministic contract, override, point-in-time, reconciliation, funnel, and pollution tests. No Massive call, credential access, `/data` modification, snapshot generation, frontend change, or OCI deployment occurred.

- Accepted the integrity-verified 2026-08-14 Instrument Master, provider identity, and ticker resolver logical snapshot as `accepted_with_provenance_exception`; original request and pagination provenance remains unknown, and the snapshot must not be requested again or overwritten.
- Accepted ADR 0014 and implemented an offline XNYS market-session calendar with injectable time, expected-versus-actual session lag, and separate file-consistency and calendar-freshness statuses.
- Executed exactly one authorized Massive Grouped Daily request for 2026-08-14 with `adjusted=false` and no retry; all hard gates passed and 9,912 canonical EOD bars were published without raw payload persistence.
- Generated a current 2026-08-14 / previous 2026-08-13 private snapshot with XNYS lag zero and freshness `fresh`, then deployed release `2026-08-14T224306Z-21d0e7fda749` from source commit `21d0e7fda749e3afec7edc9a884eb6408663004f`.
- Verified root login, compatibility redirect, unauthenticated Dashboard redirect, private-data/status protection, external internal-auth denial, remote checksums, active services, and localhost-only Auth listener. No authentication credential or policy changed.

- Upgraded Dashboard V1.1 Market Overview with SPY/QQQ/IWM/DIA benchmark strip, equal-weight universe benchmark, Sector ETF relative-to-SPY performance, conservative data freshness wording, top-50 Trading Activity Map default, improved map labels/search/detail panel, and categorized Data Details.
- Completed read-only SNDK review against canonical 2026-08-12 and 2026-08-13 data: identity and OHLC are internally consistent, but corporate-action/adjustment evidence is insufficient; canonical `/data` was not modified.
- Did not call Massive, read Massive credentials, modify `/data`, change authentication/password/session behavior, or alter market-data canonical partitions.
- Deployed private Dashboard Market Overview release `2026-08-13T214820Z-32fed3a8b17b` from source commit `32fed3a8b17b020e00c33f839d2a12e9de50d855`; unauthenticated root/login/dashboard/private-data protection checks passed.

- Recorded user-completed production acceptance for root session login, Dashboard data loading, Logout, and WH Alpha password rotation without recording any password or hash.
- Accepted ADR 0013 and implemented Dashboard V1.1 professional universe cleanup with `Tradable U.S. Equities` as the default view.
- Added Sector Benchmark ETFs as a separate fixed benchmark module and renamed the filtered treemap UI to Trading Activity Map.
- Moved broad engineering/session details into collapsible Data Details and categorized quality flags instead of showing a single large warning count.

- Repaired the OCI password rotation helper after the first real run failed during immediate listener verification; current password version is marked unknown until the user reruns the repaired interactive rotation.
- Hardened listener parsing, bounded readiness polling, and post-replacement rollback status output; password minimum is now a hard 10 characters with longer unique passwords recommended.

- Deployed root-login release `2026-08-13T135949Z-92819ed17316` from source commit `92819ed17316c567c40b440f5c2e8487f9db4b53`; made `https://whalpha.com/` the official branded WH Alpha session-login entry and changed `/login/` to a compatibility redirect to `/`.
- Added a minimal `/auth/status` check for root-entry session detection; it returns only 204 or 401 with no session details.
- Updated Dashboard unauthenticated redirects to `/?next=/dashboard/` while keeping `/private-data/` protected with 401 JSON.
- Added and deployed the OCI-only password rotation helper for interactive user-run rotation; it does not accept or print passwords or hashes.
- Did not call Massive, read Massive credentials, modify `/data`, or change Dashboard analytics, numeric formatting, or Liquidity Map behavior.

- Fixed the production login form submission contract so Sign In uses same-origin JSON `POST /auth/login` instead of native navigation; deployed release `2026-08-15T133119Z-137f244e8508`.
- Repaired the OCI `/login/` route verification by mapping the login path explicitly to the release artifact and requiring branded-login body markers during deployment; deployed release `2026-08-15T130949Z-78eedc071786`.
- Deployed private Dashboard session-login release `2026-08-15T125517Z-0fa5cac89847` and replaced browser-native Basic Auth with a branded `/login/` page and localhost-only server-side session Auth Service.
- Added secure session cookies, logout, wrong-password safe failure behavior, and Nginx `auth_request` protection for `/dashboard/` and `/private-data/`.
- Fixed Dashboard presentation formatting for long Decimal ratios, percentages, compact volume, compact currency, and metric/card overflow.
- Did not read or output the Dashboard password/hash, call Massive, read Massive credentials, modify `/data`, or change Liquidity Map algorithms.

- Provisioned a dedicated `dell5820` to OCI deployment SSH key while retaining the existing WSL OCI key.
- Regenerated the private Dashboard snapshot and OCI bundle from clean source commit `987b5289a7835316ef6aae4aa326aff46de58896`.
- Deployed private Dashboard release `2026-08-13T120220Z-987b5289a783` to OCI as the initial Basic Auth-protected release; it was later superseded by the session-login release.
- Verified public `/` remains the data-free placeholder and unauthenticated `/dashboard/` plus `/private-data/v1/manifest.json` return 401.
- Did not read or output the Dashboard password/hash, call Massive, read Massive credentials, modify `/data`, deploy raw/Parquet data, or access another OCI instance.

- Accepted ADR 0011 for authenticated static private dashboard snapshots.
- Implemented the private Dashboard JSON snapshot exporter and manifest/hash validation.
- Added frontend `snapshot` mode for `/dashboard/` static deployment and `/private-data/` JSON snapshots.
- Added a versioned OCI dashboard bundle builder, Nginx template, dry-run deployment script, and private access runbook.
- Completed read-only OCI preflight without creating credentials, uploading files, reloading Nginx, modifying whalpha.com, accessing Massive, or changing `/data`.

- Implemented the first local React Market Dashboard V1 using the private Market Summary, Movers, and Liquidity Map APIs.
- Added explicit API and synthetic demo modes; API mode does not fall back to demo fixtures on failure.
- Rendered Market Pulse, Market Breadth, Up/Down Volume, liquidity-screened movers, Liquidity Map V1, and Data Quality / Session Metadata.
- Added frontend unit/component tests with Vitest, React Testing Library, jsdom, and mocked ECharts initialization/disposal.
- Verified frontend production build locally; no Massive request, credential access, `/data` write, OCI access, or deployment was introduced.

- Published the 2026-08-12 Massive Instrument Master, provider identity, provider ticker resolver, and canonical EOD Price Bar datasets through the existing bounded pipelines.
- Implemented provider-neutral close-to-close EOD return analytics across the completed 2026-08-12 and 2026-08-13 sessions.
- Added Market Summary V1, liquidity-screened movers, paginated returns, and Liquidity Map V1 private API response contracts.
- Documented that Liquidity Map V1 is not market-cap weighted, not sector grouped, and not a fund-flow or money-flow map.
- No frontend change, OCI access, deployment, database, raw payload persistence, or system service change was introduced.


- Implemented the first canonical EOD read repository for completed Parquet sessions with manifest, schema, fingerprint, and identity snapshot validation.
- Added a paginated provider-neutral EOD query service and private FastAPI response contracts with Decimal values serialized as strings.
- Added default-disabled private EOD market-data routes gated by `TIP_ENABLE_PRIVATE_MARKET_DATA_ROUTES`; default OpenAPI does not show the private routes.
- Verified the completed 2026-08-13 production session read path locally without modifying `/data`, reading credentials, calling Massive, changing frontend code, or deploying OCI.

## 2026-08-14

- Accepted ADR 0010 to represent aggregate EOD volume as exact non-negative Decimal while keeping trade count and timestamps integer-semantic.
- Updated EOD Price Bar V1, Massive mapping, Grouped Daily inspection/ingestion, Arrow schema, Parquet persistence, fingerprints, and tests for Decimal volume.
- Re-ran the authorized 2026-08-13 Massive Grouped Daily request once with `adjusted=false`; all V1 gates passed and 9,901 canonical EOD bars were published.
- Recorded 11,208 fractional-volume records, 4 isolated conflicting duplicate records, 4 missing optional VWAP values, 4 missing optional trade-count values, and 4 zero-volume records as quality warnings.
- No raw provider payload, Dashboard data flow, OCI access, database, scheduler, or system change was introduced.

- Hardened Massive Grouped Daily numeric parsing for JSON int, finite float, Decimal, and numeric string inputs while rejecting bool, non-finite values, malformed strings, and fractional integer-semantic fields.
- Fixed Grouped Daily processing so identity classification is counted before numeric validation and remains independent from OHLCV parse failures.
- Changed low-ratio conflicting duplicate bars from a hard session failure to isolated quality warnings, while preserving a hard gate above the accepted ratio.
- Re-ran the authorized 2026-08-13 Grouped Daily request once; identity coverage passed, but numeric conversion failures and canonical bar count gates blocked publication.
- No raw payload, EOD Parquet partition, Dashboard data flow, OCI access, or system change was introduced.

- Added a controlled Massive Grouped Daily publication entrypoint for the completed 2026-08-13 session using the completed point-in-time ticker resolver.
- Executed one authorized Grouped Daily request with `adjusted=false`; access succeeded but quality gates blocked publication.
- Recorded conflicting duplicate bars, numeric conversion failures, low identity coverage, and insufficient canonical bar count as the exact blockers.
- No raw payload, EOD Parquet partition, Dashboard data flow, OCI access, or system change was introduced.

- Refined Massive Instrument Master snapshot quality classification to separate eligible records, expected exclusions, malformed records, ticker ambiguity, and stable-ID collisions.
- Added Provider Ticker Resolver V1 and included it in the logical Instrument Master snapshot completion marker.
- Re-ran the authorized 2026-08-13 Massive All Tickers pagination once; corrected quality gates passed and published 9,932 canonical instruments, 13,106 provider identity records, and 9,932 resolver entries.
- No raw Massive payload, Grouped Daily call, Dashboard data flow, OCI access, or system change was introduced.

- Added Provider Instrument Identity V1 as a Python contract and data-contract document.
- Accepted ADR 0009 for stable provider identifiers and deterministic UUIDv5 canonical instrument identity.
- Implemented bounded Massive All Tickers point-in-time Instrument Master snapshot ingestion with fixed-interval pagination.
- Implemented Instrument Master and provider identity Parquet snapshot repositories with logical completion marker semantics.
- Executed one live Massive All Tickers snapshot attempt for 2026-08-13; pagination completed, but quality gates blocked publication.
- No raw provider payload, completed Instrument Master snapshot, Grouped Daily publication, Dashboard data flow, OCI access, or system change was introduced.

- Added a safe one-request Massive Grouped Daily inspection tool.
- Executed one read-only Grouped Daily inspection for 2026-08-13 with `adjusted=false`.
- Verified Grouped Daily access and payload structure without saving raw or canonical data.
- Confirmed production publication is blocked pending Instrument Master identity coverage.
- No Parquet write, `/data` write, repository publish, second Massive request, Dashboard data flow, OCI access, or provider-backed deployment was introduced.
- Accepted partitioned Parquet as the initial canonical EOD Price Bar persistence format.
- Implemented a one-session provider-neutral EOD ingestion service for mocked fixtures.
- Implemented an explicit PyArrow EOD Price Bar V1 Parquet repository, manifest, deterministic content fingerprint, atomic publish, idempotency, and conflict/corruption checks.
- Added mocked-fixture ingestion and Parquet persistence tests.
- No Massive API call, credential access, production `/data` write, scheduler, historical backfill, analytics, database, Dashboard API, or OCI deployment was introduced.
- Implemented the protected Massive credential-file loader.
- Implemented a minimal standard-library HTTPS transport using Authorization bearer headers.
- Added local security tests for credential parsing, transport behavior, error mapping, redirect handling, and network prohibition.
- Verified one read-only Massive Stocks reference smoke test without outputting raw data or credentials.
- No ingestion, Grouped Daily download, persistence, Dashboard data flow, OCI deployment, or public provider-backed access was introduced.
- Implemented the Massive Stocks configuration and credential boundary.
- Added a mocked-only Massive adapter skeleton for Instrument Master and EOD Price Bars.
- Added deterministic mocked HTTP response tests for Massive mapping, error handling, pagination, and credential redaction.
- No real API key, Massive API call, market-data download, persistence, provider-backed deployment, or access-control change was introduced.
- Evaluated Massive Stocks Basic using official public documentation.
- Accepted Massive Stocks Basic as the first private EOD development provider.
- Documented public-display and Derived Works restrictions for provider-backed data.
- Accepted the public placeholder, public data-free demo, and private real-data dashboard boundary.
- No account, credential, adapter, API request, data ingestion, deployment, or access-control change was introduced.
- Implemented the synchronous provider-neutral MarketDataProvider Protocol.
- Added provider capabilities and query models for Instrument Master and EOD Price Bars.
- Added explicit provider error taxonomy.
- Added deterministic in-memory provider contract test fake.
- No real provider, network access, credentials, ingestion, persistence, database, or Dashboard implementation was introduced.

## 2026-08-13

- Expanded workstation root LV from 100 GiB to 150 GiB.
- Created 700 GiB ext4 data LV mounted at `/data`.
- Created `/data/trading-intelligence-platform`.
- Retained approximately 100.82 GiB VG free.
- Verified `/data` persisted across a controlled reboot.
- Confirmed zero failed systemd units after reboot.
- Documented the accepted application technology stack.
- Documented the target application architecture.
- Added the documentation checkpoint policy for future material changes.
- Created the minimal FastAPI backend scaffold.
- Created the minimal React/Vite frontend scaffold.
- Introduced the versioned Health API contract.
- Added local development scripts and documentation.
- Installed backend dependencies in the project virtualenv and verified backend tests.
- Verified the Health API locally on `127.0.0.1:8000`.
- Frontend dependency installation and build were not verified because Node.js and npm were unavailable.
- Prepared guarded Node.js 24 LTS provisioning script and operations document.
- Completed Node.js 24 LTS provisioning and verified npm.
- Corrected provisioning script GPG behavior to avoid interactive overwrite prompts.
- Locked frontend dependencies with npm-generated `package-lock.json`.
- Verified frontend production build.
- Verified local Vite server and Vite-to-FastAPI proxy.
- Revalidated backend tests and the direct Health API endpoint.
- No market data provider, database, production deployment, or Dashboard V1 implementation was introduced.
- Accepted the Initial EOD Universe boundary.
- Accepted the three-layer classification model for Sector/Industry, Theme, and Analytical Groups.
- Accepted five normalized EOD logical contracts.
- Documented point-in-time membership and revision principles.
- No provider, data ingestion, physical schema, database, or Dashboard implementation was introduced.
- Implemented the Instrument Master V1 Pydantic contract.
- Implemented the EOD Price Bar V1 Pydantic contract.
- Added validation and serialization tests for the two implemented contracts.
- No provider adapter, persistence, real market data, database, or Dashboard implementation was introduced.

## 2026-08-12

- Completed workstation and OCI infrastructure audits.
- Removed obsolete projects and services.
- Replaced old public trading console with static placeholder.
- Separated workstation and OCI SSH identities.
- Established initial product, architecture, and Dashboard V1 decisions.
- Created project documentation foundation.
# 2026-08-25 — Explicit Production review deployment contract

- Added `production-review-deployment/1.0`, narrowly bound to analysis and
  actual session 2026-08-24, expected session 2026-08-25, lag one, and an
  explicit acknowledgement. Normal publications still require lag zero.
- Bound review metadata through Market Intelligence candidate/manifest/plan,
  active reader/API, Snapshot 1.5 candidate/manifest/plan, and both English and
  Chinese first-screen banners. The payload remains language neutral.
- Added fail-closed checks for missing/wrong acknowledgement, changed session,
  expected date or lag, plus focused and full regressions. No generic
  `--allow-stale` was introduced.

# 2026-08-25 — Dashboard Snapshot 1.5 frontend contract compatibility

- Added typed, fail-closed Snapshot 1.5 manifest validation to the existing
  static Dashboard loader, including Dashboard 2.2, Market Intelligence,
  Funnel, and exact stale-review bindings.
- Kept the embedded Dashboard overview on its defined 2.1 response contract;
  unknown snapshot versions, Dashboard contracts, and data-status values remain
  rejected instead of being converted to empty or synthetic data.
