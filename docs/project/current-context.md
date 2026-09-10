# Authoritative Current Context

Operational state verified at: 2026-09-10T04:45:32Z

Repository context updated at: 2026-09-10 UTC

This is the compact recovery source for a new task or device. It records
verified current identities and boundaries, not full execution history.
Historical detail belongs in the [changelog](changelog.md), dated audits, and
ADRs. Proposed work belongs in the [roadmap](roadmap.md).

## Repository and infrastructure

| Field | Verified value |
| --- | --- |
| Workstation / user | dell5820 / hui |
| Source repository | /home/hui/projects/trading-intelligence-platform |
| Source branch | main; verify current HEAD and cleanliness with the report |
| Public site | https://whalpha.com/ |
| OCI alias | whalpha-oci |
| Active OCI release | 2026-09-09T211131Z-e06bd62ecab3 |
| Deployed source | e06bd62ecab3cbf65867c9ddd9853a909379af9a |

Dell is the authority for code, data, development, governance, and heavy
computation. OCI is limited to static web serving, localhost Auth Service, and
the public Session boundary. Windows and future Mac systems are remote entry
points. A newer clean repository commit does not invalidate an older immutable
deployed release; compare both identities.

The source main was clean during the verified operational report. An old
historical-backfill worktree had no unique commit and was far behind main; do
not use it as a development base.

## Canonical Dell data

The network-free report contract is 1.10. Active-custody validation and the
explicit all-partition validation both passed in their recorded audits.

| Boundary | Verified value |
| --- | --- |
| Canonical EOD | 306 contiguous XNYS sessions, 2025-06-23 through 2026-09-09 |
| Latest EOD | 2026-09-09; 9,916 rows |
| Latest EOD fingerprint | 1ecd85558ca0fdf36e2460021b2da80a41ef5f17424aae33a9e94de5e70f1d1f |
| Latest Identity | 2026-09-09; 9,982 instruments / 13,158 provider identities / 9,982 resolvers |
| Latest Identity fingerprint | f29de23284b163955fc542b2c48ed3ebd60b618493366511935164e574694707 |
| Identity source custody | 304 immutable partitions / 3,726,643 rows; 2026-08-13 and 2026-08-19 unbound |
| Signal-eligible Membership | 3 sessions / 59,892 decisions: 2026-09-04, 2026-09-08, 2026-09-09 |
| Latest Membership fingerprint | a44ca1bb4d707406cab82b3a7ba5d146bc6d0850857b6714c1968cec17994835 |
| Corporate-action observations | 70,099 bounded split/dividend source rows; 42,056 resolved / 28,043 quarantined |
| Canonical split-only facts | 709 rows: 707 active / 2 quarantined; incomplete coverage |
| Sparse split adjustment | 101,321 affected-path rows: 98,291 clear / 3,030 quarantined; outcome-only |
| Data inventory | 4,311 files / 2,321,416,033 bytes |
| Inventory fingerprint | 0cbc099b84b084641f97d87bc0eb94a57fad279c41aa5a4d47554e4138b395f0 |
| Symlinks / publication residue | zero / zero |

The 300-session historical target and six later sessions are canonical. The
2026-09-09 Stocks Starter run fetched Identity in 14 successful requests and
Grouped Daily in one successful request after the tested 20:30 UTC boundary.
It proved same-evening access for that session and removal of the old Basic
rate limit; it did not prove a guaranteed finality minute or the advertised
five-year endpoint depth. No backfill, transient service, or heavy computation
process was active at verification.

The fixed 30-item Massive Starter lifecycle diagnostic had stable Composite
FIGI locators and provider delisting dates for every item, but Ticker Events
matched only six; 24 returned HTTP 404 and all nine returned events were ticker
changes. Massive remains a partial lifecycle input and is rejected as the
sole-primary lifecycle source.

## Active Universe

The provider-form Activation remains provisional and was derived from analysis
session 2026-08-19.

| Universe | Verified value |
| --- | --- |
| Primary | 1,718 CS; fingerprint c3665203965b96528c9be07db3c49d18023104e346da16050f1170d4fe148978 |
| Secondary | 1,831 = 1,718 CS + 113 ADRC; fingerprint 2dce08e728774510878c47dc80898e10236952dacd146990ad344c4dcb75a295 |
| Activation pointer | dbe6056e1ed4b87ebce88b356c346831ce67431a263066cd283b9ad7e8067168 |

Provider security form does not prove issuer operating structure or domicile.
Core remains the intended future default and Broad the future secondary only
after authoritative issuer evidence passes the documented gates.

## Active analytics and serving

| Boundary | Verified value |
| --- | --- |
| Market Intelligence | 2026-09-09T205635Z-e06bd62ecab3; contract 1.3 |
| MI logical fingerprint | 3ec78b40dde6563f81aa3b1aadd8152ee35e6c8344c761a0314117408b6330dd |
| Dashboard Snapshot | 2026-09-09T211131Z-e06bd62ecab3 |
| Snapshot pointer | a43487bacc77dc1e28e83018ca4f469296ac0e2dff7b84650870de83fe368897 |
| Contracts | Snapshot 1.11 / Dashboard 2.8 |
| Immediate local rollback | 2026-09-08T171914Z-ca2d34d50692 |

Both Universes have confirmed Balanced Market Regime and Defensive candidate
state: Primary 46.7798, Secondary 46.8524. Market Intelligence contains 16
preregistered ETF relationships, 336 bounded history rows, 30 ETF observations,
and 5/10/20-session views. Candidate publication 1.1 contains 862 Primary and
922 Secondary eligible display records; these are not Universe sizes.

Analytics remains degraded-short-history because Market Intelligence consumes
26 sessions although canonical EOD has 306. This is a consumer-integration
limit, not missing acquisition.

The independent OCI postflight matched release, source, manifest, checksums,
services, protected routes, guest Session, Candidate summary/detail, Strategy
Channels, Sector ETF Rotation, logout, and residue state. Nginx and the
localhost-only Auth Service are active. English is default; English and
Simplified Chinese are equal. Guest and credential Sessions have identical
capability. No credentials, raw provider responses, or Parquet are served.
Password login and final visual appearance remain manual checks.

## Product authority

The durable decision chain is:

~~~text
market state -> strength direction -> sector/theme -> validated stock candidate
-> trade preparation -> entry/invalidation -> position management
~~~

The three stable market workspaces are Market Regime & Opportunities
(市场风向与机会), Sector ETF Rotation (行业轮动), and Market Structure &
Activity (市场结构与活跃度).

Quant Research Lab (量化研究实验室) is now the model registry, research
evidence, and lifecycle authority. Stock Candidates (个股候选) will later
consume only one to three separately validated and explicitly activated Lab
models. Every active Candidate must identify the model/version, current-market
applicability, within-model rank, evidence, counterevidence, entry readiness,
and invalidation, with a link to the complete Lab record.

Repository main includes the ADR 0192 Lab model-record, result-publication, and
catalog boundaries plus one contract-validated Strong-Leader Pullback method
projection for the browser. It is `method_only`,
`preregistered_data_blocked`, has zero out-of-sample observations, and grants
no Candidate authority. This repository interface has not been deployed; the
active OCI release remains the one recorded above.

ADR 0194 now records the future AI Quant Research Factory as a governed Lab
backend: high-throughput ideas are permitted, but real experiments remain
deduplicated, finitely budgeted, stage-isolated, deterministic, and fully
retained whether they pass or fail. The factory is a direction, not an
implemented long-running agent system, and it cannot activate Candidate models
or trade.

The currently deployed Candidate score, Entry Geometry, and three technical
Strategy Channels are transparent but unvalidated **Baseline V1**. They remain
Production facts and receive compatibility/correctness maintenance, but are
not the target model architecture and must not be tuned in place. Technical
Reversal, Fundamental Value Reversal, and Defensive Rotation remain
unavailable. Current channel overlap is not formal sector concentration.

Research order is Strong-Leader Pullback, Momentum Breakout, distinct Trend
Continuation, Technical Reversal, and Fundamental Value Reversal. Defensive
opportunity is Regime-conditioned context. Earnings, macro, and news begin as
risk/context evidence. Options are a later expression layer and never inherit
stock-return claims. ADR 0191 and
[Quant Research Lab](../product/quant-research-lab-v1.md) are the direction
authorities.

## Research readiness

Formal state remains data-blocked. Strategy-development review and performance
claims are false.

| Complete or present | Still blocking real research |
| --- | --- |
| 306-session EOD and Identity depth | Final transitive Historical Coverage |
| EOD/Identity family evidence | Historical point-in-time Membership eligibility |
| 304 Identity source partitions | Two source-unbound historical dates |
| 3 prospective Membership sessions | Canonical cross-venue lifecycle/terminal outcomes |
| Bounded corporate-action source custody | Complete action availability/revision and absent-event coverage |
| Canonical split-only facts and sparse affected-path ledger | Complete adjustment/neutrality and total-return semantics |
| Fixture-only input, chronology, statistics, and holdout mechanics | Real chronological dataset and sealed real holdout |
| Scenario-only equity costs | Observed spread/impact calibration and execution comparison |

Historical backfills observed later remain ineligible for formal validation,
holdout, or Production claims unless source availability at the signal time is
defensible. Current membership or classification must never be projected
backward. ADR 0193 creates one narrower development path: the exact 287-session
historical source interval through 2026-08-12 may first support an outcome-
blind coverage census. ADR 0195 now requires 100%-complete Primary session
cross-sections and at least 252 admitted sessions before development. It
remains latest-vintage reconstruction, not `as_operated` evidence.

That census completed from source revision `1f6447110142` with fingerprint
`09ffe4edc38aeaccb3f101f5b1b784eb0769af0de9fde0c28fafbc18fe32388f`.
It reconciled 2,656,006 Primary decisions and 437,402 raw-complete included
feature paths, including 722 clear split exposures and 12 quarantined paths.
All 437,402 still lack proven sparse-row neutrality and canonical lifecycle
evidence, so all-required-evidence-complete remains zero. The bound ADR 0195
decision has fingerprint
`543fdd10e6c7df087d077754674f49660fd558a9f2dafcd4fe9dfa2131af36e8`:
267 candidate sessions were incomplete, 20 sessions contained no included path
during warmup, zero sessions passed, and no cohort, outcome, or development
authority exists.

ADR 0186 freezes the dormant V1 complete-cross-section Strong-Leader Pullback
input adapter with exact 21-session feature semantics, point-in-time
Membership, stable-ID SPY, clear adjustments, and no outcome fields. It has
fixture evidence only; no real input batch or performance result exists. ADR
0193 does not rewrite V1: a future V2 development input may use only the
separately frozen admitted cohort and split-adjusted underlying-price-return
basis. Validation and holdout keep the stronger next-open knowledge-time gate.

The sparse split evidence does not prove neutral omitted rows. A read-only
diagnostic retained 387 severe unexplained discontinuities across 321 stable
IDs. Dividend analysis also retained date, currency, multi-event, and
price-completeness risks; no canonical total-return ledger exists. Detailed
counts and cases belong in ADRs 0174–0183 and their audits.

## Automation and performance

The installed daily EOD wake timer is active and read-only. It performs no
fetch, Apply, analytics, publication, deployment, retry, alert delivery, or
credential access. No unattended write-capable scheduler is installed; SMTP is
unconfigured.

The guarded manual chain works end to end:

~~~text
Identity -> EOD -> Market/Regime -> Candidate -> Entry Geometry
-> ETF Relationships -> Strategy Channels -> Visual Context
-> MI -> Snapshot -> serving bundle -> OCI deploy/postflight
~~~

The owner-only persistent runtime workspace contains the verified 2026-09-09
package, plans, analytics, Snapshot, bundle, Membership evidence, and journals.
ADR 0190 fixed artifact-role, persistent-plan, and Membership-clock integration
without changing timer authority.

The 2026-09-09 offline run completed nine actions in about 15.7 minutes.
Candidate was the largest stage at about 6.3 minutes, peaked near 8.2 GiB, and
used one CPU core. Snapshot planning took about 3.8 minutes, bundle construction
2.1 minutes, and deployment 2.4 minutes. The segmented Candidate experiment
remains a cutover NO-GO because it rehashes the large base and lacks cumulative
Visual Context history. Do not resume it unless a new clean-path measurement
breaches an agreed budget and one bounded design solves both gaps.

## Immediate direction

The ADR 0196 baseline census now fixes 2021-09-09 through 2026-09-09 as 1,255
XNYS sessions. EOD and Identity cover 306 sessions and miss 949; normalized
Identity source custody covers 304 and misses 951; Membership covers three and
misses 1,252. Lifecycle, point-in-time classification, point-in-time
fundamentals, and complete Historical Coverage are absent. The census is
`quarantined`, fingerprint
`c19c520f202aacef0dada46cf82e984ccba6b77078d667363eccfcc152a81bfb`.

1. Implement and pilot the Massive Starter Day Aggregates Flat File source,
   then freeze the exact 949-session EOD/Identity backfill plan. The 2026-09-10
   REST pilot found Grouped Daily denied for
   2021-09-09/10 but accessible with 11,063 rows for 2022-09-09; PIT Tickers,
   splits, and dividends were accessible on all three dates. Use the documented
   five-year Day Aggregates Flat Files as the preferred bulk-price route and
   retain REST as a bounded fallback/cross-check. The fetch-only adapter and
   transitive raw-gzip custody are fixture-tested; a live pilot awaits the
   separate dashboard S3 credential, not another REST API-key retry.
2. Use Massive as the primary price/reference source and evaluate official
   free evidence through bounded source-specific pilots. Preserve every
   conflict, missing semantic, and permission limit; no first-non-null merge.
3. Repair historical Membership, identity/lifecycle, actions, terminal
   outcomes, adjustments, and transitive Historical Coverage in independent
   stages. Re-run ADR 0195 after mandatory-family evidence changes and either
   admit at least 252 complete session cross-sections or retain rejection.
4. Only after admission, run Strong-Leader Pullback development; locked
   point-in-time validation,
   sealed holdout, and prospective shadow under their exact evidence tiers.
5. Retain either validated evidence or recorded failure without editing V1.
6. Generalize the proven path into a small, bounded multi-agent pilot under ADR
   0194; scale only after measured benefit and holdout integrity.
7. Activate a model only through separate review; then redesign Candidate.

One bounded next-session automation rehearsal and normal daily reliability work
may proceed in parallel when an eligible session exists. They must not block
Lab design or restart indefinite Candidate performance optimization. See the
[roadmap](roadmap.md) for full sequencing.

## Guardrails

- Decision support, not automated trading or order execution.
- Human meaning first; algorithm label second.
- Stable instrument ID is the join key; ticker is display metadata.
- Unknown or insufficient evidence is quarantined.
- Research, validation, shadow, active, rejected, and retired are distinct.
- Price/volume is not fund flow; correlation is not causality.
- Stock forward return is not option return.
- Guest and credential Sessions remain identical until explicitly changed.

## Cross-device continuity

- Windows already has a dedicated passwordless SSH key and saved Dell project.
- For Mac, join the same Tailscale network and create a Mac-only SSH key; never
  copy the Windows private key.
- Add only the Mac public key to Dell, configure alias dell5820, save the same
  source repository path in Codex Desktop, and run the read-only context report.
- Never place server addresses, private-key paths, credentials, or Session
  material in repository documentation or chat.

## Recovery procedure

1. Read AGENTS.md, root README, docs/README, this file, and current-status.
2. Run scripts/admin/report-current-context.sh from source main. Use full
   history validation only for periodic or investigative review.
3. Compare repository, EOD, Identity, Activation, MI, Snapshot, inventory, and
   residue with this baseline.
4. Inspect OCI separately only when deployment state matters.
5. Classify differences before mutation; never silently rewrite a pointer,
   reacquire data, deploy, or clean a release.
6. Read only documents tied to one selected objective.
