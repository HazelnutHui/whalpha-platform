# Current Status

Status date: 2026-09-09

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

- EOD and Identity are aligned through 2026-09-09 with 306 contiguous sessions.
  Latest EOD has 9,916 rows; latest Identity has 9,982 instruments.
- Historical Identity source custody has 304 partitions; 2026-08-13 and
  2026-08-19 remain explicitly unbound.
- Signal-eligible Membership has three prospective sessions and 59,892
  decisions.
- Corporate-action source custody has 70,099 bounded observations. Canonical
  split-only facts and a sparse affected-path adjustment ledger exist, but
  neither proves complete coverage, neutral omitted rows, or total return.
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

## Research readiness

Formal state is data-blocked; real evaluation and performance claims remain
unauthorized.

Complete:

- 306-session EOD/Identity depth and their family evidence;
- 304 Identity source partitions and three prospective Membership sessions;
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

Historical backfills observed later remain outcome-only unless source
availability at signal time is defensible. Current membership or taxonomy must
not be projected backward. The Strong-Leader Pullback input adapter has
fixture evidence only and has never produced a real backtest.

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

1. Close only Strong-Leader Pullback's exact point-in-time data blockers.
2. Freeze one admitted cohort and formal readiness decision before outcomes.
3. Execute its registered chronological research and retain success or failure.
4. Activate and connect a model to Stock Candidates only after separate
   operational review.

Daily reliability and one bounded next-session automation rehearsal may proceed
in parallel. Do not tune Baseline V1, restart indefinite Candidate
optimization, add guest restrictions, call stock outcomes option returns, or
add infrastructure without a demonstrated requirement.
