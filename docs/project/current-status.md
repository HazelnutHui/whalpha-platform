# Current Status

Status date: 2026-09-10

This is the concise actual-state summary. Exact volatile identities and
cross-device recovery belong in
[authoritative current context](current-context.md). Proposed work belongs in
the [roadmap](roadmap.md); history belongs in the changelog, ADRs, and audits.

## Production

WH Alpha is live as a Session-protected bilingual U.S. equity
market-intelligence and research platform. Active OCI release
2026-09-09T211131Z-e06bd62ecab3 was built from clean source
e06bd62ecab3cbf65867c9ddd9853a909379af9a.

Production uses Market Intelligence 1.3 for 2026-09-09 and Snapshot 1.11 /
Dashboard 2.8. English is default and Simplified Chinese is equal. Guest and
credential Sessions intentionally receive identical data and capability.
Snapshot/API failures close without synthetic Production data.

Independent postflight matched release, source, bundle, manifest, checksums,
services, protected routes, guest access, logout, and residue state. Password
login and final visual appearance remain manual checks.

## Data

- EOD and Identity are aligned through 2026-09-09 with 310 contiguous sessions.
  Latest EOD has 9,916 rows; latest Identity has 9,982 instruments.
- Historical Identity source custody has 308 partitions; 2026-08-13 and
  2026-08-19 remain explicitly unbound.
- Signal-eligible Membership has three prospective sessions and 59,892
  decisions.
- Corporate-action source custody has 70,099 bounded observations. Canonical
  split-only facts and a sparse affected-path adjustment ledger exist, but
  neither proves complete coverage, neutral omitted rows, or total return.
- A fixed 30-item Massive Starter lifecycle diagnostic matched Ticker Events
  for only six instruments; 24 returned HTTP 404 and all nine returned events
  were ticker changes. Massive is useful partial evidence but is rejected as
  the sole-primary lifecycle source.
- Data inventory is 4,311 files / 2,321,416,033 bytes with zero symlinks and
  zero publication residue.
- Primary has 1,718 CS. Secondary has 1,831 = 1,718 CS + 113 ADRC. This
  provider-form Activation remains provisional.
- Stocks Starter removed the old Basic rate limit and provided the tested 9/9
  same-evening EOD. Guaranteed finality time and five-year endpoint depth are
  not yet proven.
- No historical backfill or transient compute service was active at
  verification.

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
all real result areas remain locked. This interface is not in the active OCI
release.

ADR 0194 records a future bounded AI Quant Research Factory inside the Lab.
No agent orchestrator or autonomous research service exists yet. The first
implementation gate is still one complete Strong-Leader Pullback path; only
after it proves reproducible rejection and stage isolation may a small multi-
role agent pilot begin.

## Research readiness

Formal state is data-blocked; real evaluation and performance claims remain
unauthorized.

Complete:

- 310-session EOD/Identity depth and their family evidence;
- 308 Identity source partitions and three prospective Membership sessions;
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
2021-09-09 through 2026-09-09. Current exact coverage is EOD 310/1,255,
Identity 310/1,255, normalized Identity source 308/1,255, and Membership
3/1,255. Required lifecycle, PIT classification, PIT fundamentals, and
Historical Coverage are absent; status remains `quarantined`.

1. Implement and pilot the Massive Starter Day Aggregates Flat File source,
   then continue the exact EOD/Identity acquisition plan. Four pilot sessions
   are complete and 945 remain. The
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
2. Continue independent construction using Massive plus bounded official/free
   source pilots for identity, listing status, lifecycle, corporate actions,
   terminal outcomes, and point-in-time fundamentals. LSEG is a later
   measured-gap option rather than the mandatory next dependency.
3. Repeat the outcome-blind census and decision, then admit at least 252
   complete session cross-sections or retain rejection without opening outcomes.
4. Execute the registered chronological research only after admission, and
   retain success or failure.
5. Generalize only the proven path into a bounded multi-agent research pilot.
6. Activate and connect a model to Stock Candidates only after separate
   operational review.

Daily reliability and one bounded next-session automation rehearsal may proceed
in parallel. Do not tune Baseline V1, restart indefinite Candidate
optimization, add guest restrictions, call stock outcomes option returns, or
add infrastructure without a demonstrated requirement.
