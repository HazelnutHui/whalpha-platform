# Current Status

Status date: 2026-09-11

This is the concise actual-state summary. Exact volatile identities and
cross-device recovery belong in
[authoritative current context](current-context.md). Proposed work belongs in
the [roadmap](roadmap.md); history belongs in the changelog, ADRs, and audits.

## Production

WH Alpha is live as a Session-protected trilingual U.S. equity
market-intelligence and research platform. Active OCI release
2026-09-10T211413Z-030f75578668 was built from clean source
030f75578668b34cf67c82264284e31362ced235.

Production uses Market Intelligence 1.3 for 2026-09-09 and Snapshot 1.11 /
Dashboard 2.8. English is default; Simplified Chinese and neutral professional
Spanish are equal presentation layers. Guest and credential Sessions
intentionally receive identical data and capability.
Snapshot/API failures close without synthetic Production data.

Independent postflight matched release, source, bundle, manifest, checksums,
services, protected routes, guest access, logout, and residue state. Password
login and final visual appearance remain manual checks.

The public entry is now research-first: Quant Research Lab and future
model-driven equity selection lead the narrative; governed AI research
automation is explicitly planned; the three stable market-context workspaces
are presented as free supporting tools. The Strong-Leader Pullback dossier
shows data construction, unpublished out-of-sample evidence, inactive
Candidate authority, and no performance claim. Conventional account sign-in
is the first-viewport entry, equal-capability guest access follows immediately,
and a visible continuation rail leads into the supporting narrative. The
visual language uses layered rounded surfaces, asymmetric research modules,
and a restrained animated signal path while preserving explicit research
status and limitations. The second-screen research hierarchy presents Quant
Research Lab as the single core and places the current record, downstream
selection, and planned automation on one explicit vertical evidence rail.
Inside the authenticated/guest application, Quant Research Lab is also the
default and sole core workspace. Model-Driven Equity Selection is immediately
beneath it as the reserved downstream consumer of activated models. The three
stable market workspaces are grouped separately as free tools rather than
numbered as equivalent modules. Deep links, multilingual state, Universe choice,
and identical guest/credential capability remain unchanged.

The authenticated and guest application now uses a separate institutional
research-terminal visual system: a compact workspace context bar, quieter
navigation, flat analytical surfaces, table-like information groups,
restrained status color, and reduced rounding, gradients, glow, and motion.
The public entry is unchanged. No data, model, or access behavior changed.

All five application workspaces are route-level chunks with intent
preloading, while the Spanish catalog is fetched only when selected or linked.
The default Quant Research Lab path fell from about 297.6 KiB to 106.3 KiB
gzip JavaScript. Build-failing entry, asynchronous-chunk, and stylesheet size
budgets now guard this boundary.

## Data

- After the bounded case-sensitive-symbol recovery, the unique continuation
  and one exact-session recovery first advanced to 1,017 aligned EOD and
  Identity sessions. The sole `20260911g` continuation completed eleven full
  batches and most of its final batch before failing closed on the known
  Grouped Daily REST entitlement boundary at 05:35:28 UTC. Quiescent canonical
  EOD now has 1,253 sessions from 2021-09-13 through 2026-09-09; only
  2021-09-09 and 2021-09-10 are missing. Canonical Identity has 1,254 physical
  sessions from 2021-09-10 through 2026-09-09; 1,253 align to EOD and only
  2021-09-09 is missing.
- Historical Identity source custody aligns to 1,251 evaluation sessions; the
  difference from aligned EOD remains exactly the two explicitly unbound
  sessions 2026-08-13 and 2026-08-19.
- Signal-eligible Membership has three prospective sessions and 59,892
  decisions.
- Research-only latest-vintage Membership has 300 sessions and 5,571,154
  decisions. It is physically separate and has no signal, performance,
  Candidate, Production, or web authority.
- Canonical corporate-action source custody still has 70,099 bounded recent
  observations. Separately, exact five-year owner-only source packages now
  contain 6,491 split and 235,751 dividend rows with complete natural
  pagination and a full repeat. Five split provider IDs changed without an
  economic-payload change and remain explicit revision evidence. These source
  packages are not yet stable-ID-resolved or canonical; the split-only facts
  and sparse affected-path adjustment ledger still do not prove neutral
  omitted rows or total return.
- A fixed 30-item Massive Starter lifecycle diagnostic matched Ticker Events
  for only six instruments; 24 returned HTTP 404 and all nine returned events
  were ticker changes. Massive is useful partial evidence but is rejected as
  the sole-primary lifecycle source.
- The complete 2026-07-16 and 2026-09-03 inactive-listing source anchors are
  retained in owner-only persistent Dell custody and formally reread. Their
  23,260 / 23,469 rows remain discovery and reconciliation evidence, not
  canonical lifecycle or terminal outcomes.
- The last full quiescent inventory before the later continuation was 12,216
  files / 4,732,957,086 bytes with zero symlinks and zero publication residue;
  it is not the current post-run total.
- Primary has 1,718 CS. Secondary has 1,831 = 1,718 CS + 113 ADRC. This
  provider-form Activation remains provisional.
- Stocks Starter removed the old Basic rate limit and provided the tested 9/9
  same-evening EOD. The separate S3 credential is now valid: a 2026-09-09 Day
  Aggregates Flat File succeeded, while 2021-09-09 returned access denied.
  Current REST and Flat File controls matched exactly on shared OHLCV and trade
  count; Flat Files omit VWAP and 13 REST zero-volume records. Starter cannot
  close the two oldest evaluation days or the earlier 20-session warm-up.
- A lightweight read-only custody intersection at 2026-09-11 01:45:42 UTC
  found 777 unique retained Grouped Daily package dates among 1,082 then-
  canonical EOD sessions. All 777 matched a canonical date; 305 canonical dates
  within 2025-06-23 through 2026-09-09 lacked a retained Grouped Daily package.
  This is a source-reacquisition sizing diagnostic, not the formal coverage
  result; the new post-acquisition census must still reread every package,
  original Apply binding, EOD partition, and same-session Identity source.
- The shared `.venv` editable-install metadata currently points at the older
  Codex worktree rather than the canonical checkout. The active backfill is not
  affected: its admin entry point delegates to `scripts/dev/run-project-python.sh`,
  which prepends the canonical repository source path before Python starts.
  Reconciled EOD runbook commands now use that same wrapper. Do not invoke new
  operator modules through bare `.venv/bin/python -m`; reconcile the editable
  install only after the active writer stops.
- A coverage-hash-bound later-source reacquisition runner is implemented for
  source-only gaps confirmed by the final quiescent census. It accepts only
  explicit ordered batches of at most 40 dates, serially rate-limits requests,
  uses bounded transport retries, resumes from formally verified owner-only
  packages, writes zero canonical files, and emits no credential or response
  body. It is fixture-tested only; no real reacquisition request has run.
- A complete-interval Reconciled EOD candidate controller is implemented. It
  consumes only build-ready sealed coverage, automatically divides the exact
  interval into 1–40-session batches, uses at most four workers, reuses only
  partitions with the same source/revision/fixed-time binding, retains safe
  progress on failure, and publishes the sole interval marker last. It is
  fixture-tested only; no real candidate edition has been built.
- Source Coverage and full-edition construction now model the separate
  2021-08-11 through 2021-09-08 warm-up interval explicitly. Those 20 sessions
  will be included in source and edition custody without changing the
  2021-09-09 through 2026-09-09 evaluation boundary. The stopped evaluation
  run left two EOD and one Identity session missing; warm-up acquisition
  remains pending after those gaps close.
- Warm-up source custody has a separate fixed historical workspace named
  `warmup-2021-08-11--2021-09-08`. The existing evaluation workspace remains
  immutable and date-truthful. Source Coverage recognizes evaluation and
  warm-up backfills as distinct origins; no warm-up package exists yet.
- The first finite unit began at 2026-09-10 08:54:25 UTC and stopped safely on
  a concurrent research-Membership inventory change. The unique continuation
  `whalpha-five-year-backfill-20260910c.service` recovered the Identity-only
  edge but later stopped at a bounded historical alias gate. The successor
  `whalpha-five-year-backfill-20260910d.service` preserved those conflicts and
  advanced to the exact counts above before failing closed at 20:51:39 UTC.
  The 2022-12-05 grouped payload contains a VWAP value beyond the canonical
  decimal scale of 10; no silent rounding or partial EOD publication occurred.
  ADR 0202 now normalizes only audited Massive VWAP float tails at the provider
  boundary. A zero-request one-session recovery published and reread
  2022-12-05. The unique bounded `20260910e` continuation later stopped before
  2022-10-07 EOD because V1 upper-case ticker mapping collapsed six pairs of
  case-distinct Massive securities. ADR 0203 preserves exact provider-symbol
  case and binds it to same-session source evidence; its real zero-write replay
  passes. A retained-package census found at least 1,862 resolved bars missing
  across 676 published sessions. Existing EOD V1 partitions remain immutable
  and research-quarantined pending a corrected version or correction family.
  Clean source `2da13b200cbe506332c05baa47f08de328170d70` recovered
  2022-10-07 with zero requests, and the unique bounded `20260910f`
  continuation advanced through 2022-08-22 before stopping at 23:54:38 UTC
  ahead of 2022-08-19 Identity. Its retained package has 168 missing-type rows
  out of 12,172. ADR 0205 keeps those rows rejected and permits only the
  explicit historical-reconstruction profile a 2.0% malformed ceiling; the
  prospective ceiling remains 1.0%. A zero-request candidate replay passes,
  then clean source `49ef83a4bc5ee70914eabb9930a8c9f7c6d78f3b`
  reused the Identity package with zero requests, acquired EOD in one request,
  and formally aligned both families at 1,017 sessions. The next exact session
  was 2022-08-18. Clean source `6851d005bd9808d970e49988000223ff4898dd16`
  started the sole `whalpha-five-year-backfill-20260911g.service` at
  00:20:35 UTC. It completed eleven full batches with zero transient retries,
  safely retained partial final-batch progress, and stopped at 05:35:28 UTC
  when 2021-09-10 Grouped Daily returned HTTP 403. The independent exact-date
  probe had already shown the same denial for 2021-09-09 and 2021-09-10. A
  post-stop census fingerprinted the resulting state as
  `c6a49fa8bbe67acb2134f8223fb65f249aeab1022c805320bb63d522c26303fc`;
  zero symlinks, zero staging/partial directories, and no remaining writer were
  observed. See the
  [terminal audit](../audits/five-year-eod-identity-backfill-terminal-2026-09-11.md).

Price depth is no longer the main research blocker.

## Product

The stable market workspaces are:

1. Market Regime & Opportunities (市场风向与机会);
2. Sector ETF Rotation (行业轮动); and
3. Market Structure & Activity (市场结构与活跃度).

Market Regime is confirmed Balanced in both Universes; candidate state is
Defensive. The product contains 16 preregistered ETF relationships and
5/10/20-session views. These are price-derived proxies, not fund flow,
classification, or causality.

Quant Research Lab is the model registry, research evidence, and lifecycle
authority. Stock Candidates will later consume one to three separately
validated and activated Lab models under ADR 0191.

The deployed Candidate score, Entry Geometry, and three technical Strategy
Channels are frozen, unvalidated **Baseline V1**. Current display counts are
862 Primary and 922 Secondary eligible records, not Universe sizes. Their
logic remains transparent, but they are not expected-return models and will
not be tuned in place. Technical Reversal, Fundamental Value Reversal, and
Defensive Rotation remain unavailable.

The repository now has a typed Lab model registry, result-publication
semantics, catalog activation guard, and one browser-rendered
Strong-Leader-Pullback method record under ADR 0192. The record is
contract-validated against its canonical Python builder. It has no real
performance result, no out-of-sample observation, and no Candidate authority;
all real result areas remain locked. This interface is now present in the
active OCI release.

ADR 0194 records a future bounded AI Quant Research Factory inside the Lab.
No agent orchestrator or autonomous research service exists yet. The first
implementation gate is still one complete Strong-Leader Pullback path; only
after it proves reproducible rejection and stage isolation may a small multi-
role agent pilot begin.

## Research readiness

Formal state is data-blocked; real evaluation and performance claims remain
unauthorized.

Complete:

- 1,062 aligned EOD and Identity durable partitions through the live
  continuation boundary;
- 1,060 Identity source partitions, 300 research-only Membership sessions, and
  three prospective signal-eligible Membership sessions;
- bounded corporate-action observations, split-only facts, and sparse
  split-adjustment evidence;
- fixture-tested input, chronology, statistics, cost-scenario, and holdout
  mechanics; and
- a preregistered Strong-Leader Pullback V1.

Incomplete:

- immutable corrected EOD history for the ADR 0203 case-sensitive-symbol
  defect and full-interval reconciliation; ADR 0204's contracts, diff
  classifier, isolated one-session candidate builder, owner-only candidate
  persistence, memory-bounded formal reader, final interval completion marker,
  exact whole-edition Apply planning, and atomic Apply executor are implemented,
  but real batch construction, an executed canonical edition, and its later
  research admission are not;
- historical point-in-time Membership eligibility;
- canonical cross-venue lifecycle and terminal outcomes;
- complete action availability/revision and adjustment/total-return evidence;
- final transitive Historical Coverage;
- observed spread/impact and calibrated execution costs;
- a real chronological evaluation dataset and sealed real holdout.

Historical backfills observed later remain ineligible for formal validation,
holdout, and Production claims unless source availability at signal time is
defensible. Current membership or taxonomy must not be projected backward.
ADR 0193 permits the fixed 287-session interval through 2026-08-12 only for an
outcome-blind coverage census and possible later development cohort. ADR 0195
has now frozen a 100%-complete Primary session-cross-section rule and the
existing 252-session minimum. The typed decision rejected current evidence:
zero of 267 candidate sessions passed, 20 were zero-included warmup sessions,
and all 437,402 raw-complete paths still lack proven sparse-row neutrality and
canonical lifecycle evidence. No cohort is admitted and development remains
unauthorized. The Strong-Leader Pullback V1 input adapter has fixture evidence
only and has never produced a real backtest.

## Automation and performance

The installed wake timer is active but read-only. No unattended write-capable
scheduler is installed and SMTP is unconfigured. The guarded manual chain
works end to end.

The 2026-09-09 persistent run completed nine offline stages in about 15.7
minutes. Candidate remained the main hotspot at about 6.3 minutes, 8.2 GiB
peak, and one CPU core. The segmented Candidate path remains a cutover NO-GO;
do not continue that optimization without a new budget breach and a design
that fixes both known gaps.

## Next priority

The completed network-disabled ADR 0196 baseline fixes 1,255 sessions from
2021-09-09 through 2026-09-09. The quiescent post-run state is 1,253 EOD,
1,254 physical Identity sessions, and 1,253 EOD-aligned Identity sessions.
Membership remains 303/1,255.
Required lifecycle, PIT classification, PIT fundamentals, and Historical Coverage are
absent; status remains `quarantined`.

1. Do not restart the stopped `20260911g` Grouped Daily continuation. Preserve
   its 1,253 EOD and 1,254 Identity sessions and close only the exact
   2021-09-09/10 EOD and 2021-09-09 Identity gaps. Existing
   affected EOD V1 history
   must be rebuilt as ADR 0204's
   complete immutable Reconciled EOD Edition and formally reconciled before
   research admission. ADR 0202 resolved the 2022-12-05 VWAP
   case with explicit normalization and audit
   evidence while preserving strict repository rejection. The
   completed REST probe found 2021-09-09/10 Grouped Daily denied and
   2022-09-09 accessible; all three PIT Tickers/action probes were accessible.
   Do not retry the entitlement-denied EOD dates under Starter. The live Flat
   File control proves current access and shared OHLCV compatibility, but the
   old object is also denied and Flat Files omit VWAP/REST zero-volume rows.
   Prefer a temporary 10-year Massive entitlement and the existing Grouped
   Daily REST schema for the remaining evaluation and warm-up dates; otherwise
   qualify a second source through explicit field and identity reconciliation.
   The backfill executor supports a frozen exact
   1,255-session interval plus an explicit 0.25-to-15-second serial paid-plan
   interval, while retaining the older count-based mode unchanged.
   The nominal interval is not enough for the first Membership calculation:
   retain a separate 20-session warm-up extension from 2021-08-11 through
   2021-09-08 after the exact interval run.
   Corrected-edition construction now has a network-disabled, resumable
   1–40-session batch primitive with at most four spawned workers. It has run
   only in temporary tests. The matching immutable source-coverage contract,
   formal retained-original Apply binding, gap/conflict classification,
   owner-read-only persistence, and hash-bound batch CLI are implemented and
   fixture-tested. After the writer stops, execute that census and select one
   exact source package per declared session before any real candidate build.
   The complete-interval controller is ready, but do not infer source
   precedence from directory order.
2. Continue independent construction using Massive plus bounded official/free
   source pilots for identity, listing status, lifecycle, corporate actions,
   terminal outcomes, and point-in-time fundamentals. LSEG is a later
   measured-gap option rather than the mandatory next dependency.
3. Persist reconstructed historical Membership only in the ADR 0197
   research-only family. Keep the three signal-eligible sessions and their
   Production reader physically separate.
4. Repeat the outcome-blind census and decision, then admit at least 252
   complete session cross-sections or retain rejection without opening outcomes.
5. Execute the registered chronological research only after admission, and
   retain success or failure.
6. Generalize only the proven path into a bounded multi-agent research pilot.
7. Activate and connect a model to Stock Candidates only after separate
   operational review.

Daily reliability and one bounded next-session automation rehearsal may proceed
in parallel. Do not tune Baseline V1, restart indefinite Candidate
optimization, add guest restrictions, call stock outcomes option returns, or
add infrastructure without a demonstrated requirement.
