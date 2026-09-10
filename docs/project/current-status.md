# Current Status

Status date: 2026-09-10

This is the concise actual-state summary. Exact volatile identities and
cross-device recovery belong in
[authoritative current context](current-context.md). Proposed work belongs in
the [roadmap](roadmap.md); history belongs in the changelog, ADRs, and audits.

## Production

WH Alpha is live as a Session-protected bilingual U.S. equity
market-intelligence and research platform. Active OCI release
2026-09-10T185300Z-4c0719b9b4a4 was built from clean source
4c0719b9b4a469d1f85d1371dff5a6797d0010aa.

Production uses Market Intelligence 1.3 for 2026-09-09 and Snapshot 1.11 /
Dashboard 2.8. English is default and Simplified Chinese is equal. Guest and
credential Sessions intentionally receive identical data and capability.
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
and a visible continuation rail leads into the supporting narrative.

## Data

- At the 2026-09-10 18:12:02 UTC checkpoint, EOD and Identity had at least 809
  aligned contiguous sessions from 2023-06-20 through 2026-09-09. A newer
  in-flight one-partition Identity lead may appear as the expected transaction
  ordering while the bounded backfill remains active. Latest EOD
  has 9,916 rows; latest Identity has 9,982 instruments.
- Historical Identity source custody has 345 partitions; 2026-08-13 and
  2026-08-19 remain explicitly unbound.
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
- The last quiescent data inventory before the continuation was 5,660 files /
  2,603,087,394 bytes with zero symlinks and zero publication residue. Exact
  inventory counts are intentionally deferred until the writer is quiescent.
- Primary has 1,718 CS. Secondary has 1,831 = 1,718 CS + 113 ADRC. This
  provider-form Activation remains provisional.
- Stocks Starter removed the old Basic rate limit and provided the tested 9/9
  same-evening EOD. Guaranteed finality time and five-year endpoint depth are
  not yet proven.
- The first finite unit began at 2026-09-10 08:54:25 UTC and stopped safely on
  a concurrent research-Membership inventory change. The unique continuation
  `whalpha-five-year-backfill-20260910c.service` recovered the Identity-only
  edge but later stopped at a bounded historical alias gate. The successor
  `whalpha-five-year-backfill-20260910d.service` kept those collisions
  quarantined and was still active at the deployment postflight. It is bounded
  to 24 hours, 2 GiB and serial provider access; completed sessions remain
  canonical if a later session fails. Exact later progress belongs in the
  dated audit and current context.

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

- an active finite EOD/Identity continuation with at least 386 / 387 durable
  partitions at its recorded checkpoint;
- 345 Identity source partitions, 300 research-only Membership sessions, and
  three prospective signal-eligible Membership sessions;
- bounded corporate-action observations, split-only facts, and sparse
  split-adjustment evidence;
- fixture-tested input, chronology, statistics, cost-scenario, and holdout
  mechanics; and
- a preregistered Strong-Leader Pullback V1.

Incomplete:

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
2021-09-09 through 2026-09-09. Its initial coverage counts are now superseded
by the active finite EOD/Identity continuation; final aligned and normalized
counts wait for a quiescent reread. Membership remains 303/1,255. Required
lifecycle, PIT classification, PIT fundamentals, and Historical Coverage are
absent; status remains `quarantined`.

1. Let the already-running exact EOD/Identity continuation finish or stop at
   its next explicit resumable boundary; do not start a competing writer. The
   completed REST probe found 2021-09-09/10 Grouped Daily denied and
   2022-09-09 accessible; all three PIT Tickers/action probes were accessible.
   Implement the documented Starter Day Aggregates Flat File route for bulk
   five-year prices rather than treating REST retries as progress. Fetch-only
   code and raw-source readback are fixture-tested; live schema/entitlement
   remains unverified until the separate dashboard S3 credential exists. The
   first live attempt stopped before any request or write because that
   credential was absent. The backfill executor now supports a frozen exact
   1,255-session interval plus an explicit 0.25-to-15-second serial paid-plan
   interval, while retaining the older count-based mode unchanged.
   The nominal interval is not enough for the first Membership calculation:
   retain a separate 20-session warm-up extension from 2021-08-11 through
   2021-09-08 after the exact interval run.
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
