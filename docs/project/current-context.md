# Authoritative Current Context

Operational state verified at: 2026-09-10T21:03:41Z

Deployment state additionally verified at: 2026-09-10T21:15:01Z

Backfill activity additionally verified at: 2026-09-10T23:11:02Z

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
| Active OCI release | 2026-09-10T211413Z-030f75578668 |
| Deployed source | 030f75578668b34cf67c82264284e31362ced235 |

Dell is the authority for code, data, development, governance, and heavy
computation. OCI is limited to static web serving, localhost Auth Service, and
the public Session boundary. Windows and future Mac systems are remote entry
points. A newer clean repository commit does not invalidate an older immutable
deployed release; compare both identities.

The source main was clean during the deployment postflight. An old
historical-backfill worktree had no unique commit and was far behind main; do
not use it as a development base.

## Canonical Dell data

The network-free report contract is 1.10. Active-custody validation and the
explicit all-partition validation both passed in their recorded audits.

| Boundary | Verified value |
| --- | --- |
| Canonical EOD | At least 984 contiguous XNYS sessions, 2022-10-06 through 2026-09-09; bounded continuation active |
| Latest EOD | 2026-09-09; 9,916 rows |
| Latest EOD fingerprint | 1ecd85558ca0fdf36e2460021b2da80a41ef5f17424aae33a9e94de5e70f1d1f |
| Latest Identity | 2026-09-09; 9,982 instruments / 13,158 provider identities / 9,982 resolvers |
| Latest Identity fingerprint | f29de23284b163955fc542b2c48ed3ebd60b618493366511935164e574694707 |
| Point-in-time Identity | At least 984 partitions, 2022-10-06 through 2026-09-09; aligned with EOD at the recorded checkpoint |
| Identity source custody | At least 982 immutable partitions; 2026-08-13 and 2026-08-19 remain unbound |
| Signal-eligible Membership | 3 sessions / 59,892 decisions: 2026-09-04, 2026-09-08, 2026-09-09 |
| Latest Membership fingerprint | a44ca1bb4d707406cab82b3a7ba5d146bc6d0850857b6714c1968cec17994835 |
| Research-only Membership | 300 sessions / 5,571,154 decisions, 2025-06-23 through 2026-09-03; latest-vintage, not signal eligible |
| Corporate-action observations | Canonical recent custody: 70,099 rows, 42,056 resolved / 28,043 quarantined; separate complete five-year owner-only packages: 6,491 splits / 235,751 dividends, not canonical |
| Canonical split-only facts | 709 rows: 707 active / 2 quarantined; incomplete coverage |
| Sparse split adjustment | 101,321 affected-path rows: 98,291 clear / 3,030 quarantined; outcome-only |
| Last quiescent data inventory | 12,216 files / 4,732,957,086 bytes before the later continuation; not the current post-run total |
| Last quiescent inventory fingerprint | f89a02ad0625b8391dc46e383e8056567c64c94b682e29ab0395f63008501559 |
| Symlinks / publication residue | zero / zero |

The 300-session historical target and six later sessions are canonical. The
2026-09-09 Stocks Starter run fetched Identity in 14 successful requests and
Grouped Daily in one successful request after the tested 20:30 UTC boundary.
It proved same-evening access for that session and removal of the old Basic
rate limit; it did not prove a guaranteed finality minute or the advertised
five-year endpoint depth. The finite exact-interval unit started at
2026-09-10 08:54:25 UTC, completed its first 20-session checkpoint, and then
continued to 346 EOD / 347 Identity partitions. It stopped safely when the
whole-data compare-and-swap guard observed a concurrent research-Membership
write. No overwrite or residue occurred; 2025-04-23 remains the exact reusable
Identity-only continuation point. A unique continuation unit recovered that
EOD partition without another provider request and resumed from clean source
revision `d9d77c124f1b9300613d97923493a1e696e1262c`. The succeeding `20260910d`
continuation advanced to 942 EOD
and 943 Identity partitions, then failed closed at 20:51:39 UTC while
constructing 2022-12-05 EOD. One provider VWAP exceeds the canonical decimal
scale of 10. The 2022-12-05 Identity partition remains the exact safe
transaction edge; no partial EOD partition or silent rounding was accepted.
ADR 0202 now confines round-half-even scale normalization to Massive VWAP at
the provider mapping boundary, with exact raw custody and row/session audit
evidence. A one-session recovery reused the retained package, made zero
external requests, and formally published and reread 2022-12-05 EOD. The
unique bounded `20260910e` continuation then started from clean source
`1f56f3ff7d0bb5319e40ae817ac75241391bfe7b` and advanced to 982 EOD / 983
Identity partitions. It stopped before 2022-10-07 EOD because the V1
upper-case ticker mapping collapsed case-distinct Massive securities into six
false duplicate pairs. ADR 0203 now binds exact provider-symbol case to
same-session Identity source evidence. A real zero-write replay passes with
8,136 canonical rows and zero false conflicts. A retained-package census also
confirmed at least 1,862 missing resolved bars across 676 already-published
sessions; all existing EOD V1 history remains research-quarantined pending an
immutable corrected rebuild or correction family. Clean source commit
`2da13b200cbe506332c05baa47f08de328170d70` then reused the 2022-10-07
package with zero external requests, formally published and reread 8,136 rows,
and started the unique bounded `20260910f` continuation. EOD and Identity were
aligned at 984 sessions through 2022-10-06 while that unit remained active at
the timestamp above. See the
[dated execution audit](../audits/five-year-eod-identity-continuous-run-2026-09-10.md).

The fixed 30-item Massive Starter lifecycle diagnostic had stable Composite
FIGI locators and provider delisting dates for every item, but Ticker Events
matched only six; 24 returned HTTP 404 and all nine returned events were ticker
changes. Massive remains a partial lifecycle input and is rejected as the
sole-primary lifecycle source. The complete 2026-07-16 and 2026-09-03
inactive-listing source anchors are now retained in owner-only persistent Dell
custody and formally reread; their 23,260 / 23,469 rows remain discovery and
reconciliation evidence rather than canonical lifecycle or terminal outcomes.

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
26 sessions although canonical EOD has substantially more. This is a consumer-integration
limit, not missing acquisition.

The 2026-09-10 21:15:01 UTC independent OCI postflight matched release,
source, manifest, checksums,
services, protected routes, guest Session, Candidate summary/detail, Strategy
Channels, Sector ETF Rotation, logout, and residue state. Nginx and the
localhost-only Auth Service are active. English is default; Simplified Chinese
and neutral professional Spanish are equal presentation layers. Spanish is an
on-demand catalog; all five workspaces are route-level chunks with build-time
size budgets. Guest and credential Sessions have identical capability. No
credentials, raw provider responses, or Parquet are served. Password login
and final visual appearance remain manual checks.

The public entry remains unchanged. Inside the product, guest and credential
Sessions share the same compact institutional research-terminal layout across
the Lab, downstream Candidate surface, and three market tools. This is a
presentation-only change; model authority, data, and access remain unchanged.

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
evidence, and lifecycle authority. It is the default guest/credential
workspace and the sole core item in first-level navigation. Model-Driven
Equity Selection is its downstream product surface and will later consume only
one to three separately validated and explicitly activated Lab models. The
three stable market workspaces are grouped separately as free tools rather
than numbered peers. Every active Candidate must identify the model/version, current-market
applicability, within-model rank, evidence, counterevidence, entry readiness,
and invalidation, with a link to the complete Lab record.

Repository main includes the ADR 0192 Lab model-record, result-publication, and
catalog boundaries plus one contract-validated Strong-Leader Pullback method
projection for the browser. It is `method_only`,
`preregistered_data_blocked`, has zero out-of-sample observations, and grants
no Candidate authority. The active OCI release now carries this truthful Lab
interface and the research-first public entry recorded above.

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
| At least 984 aligned EOD / Identity partitions under one bounded continuation | Corrected and reconciled EOD history plus final transitive Historical Coverage |
| EOD/Identity family evidence | Complete and admitted historical Membership |
| At least 982 Identity source partitions | Two source-unbound dates |
| 3 prospective Membership sessions | Canonical cross-venue lifecycle/terminal outcomes |
| 300 research-only Membership sessions | Research tier is not signal eligible and remains outcome-blind |
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

The ADR 0196 baseline census fixes 2021-09-09 through 2026-09-09 as 1,255
XNYS sessions. Its original counts are superseded by the at-least-984 aligned
checkpoint above. The former precision gate is resolved under
ADR 0202; ADR 0203 resolves the forward exact-symbol mapping but not the
already-published missing-bar history.
Membership covers 303 sessions and misses 952: 300 reconstructed research-only
sessions plus three signal-eligible sessions. Lifecycle, point-in-time classification, point-in-time
fundamentals, and complete Historical Coverage are absent. The census is
`quarantined`, fingerprint
`c193895b7cb795fb5054c5e8493bb7c5e438e646c37e03d336a82d52f3a903e7`.

1. Let the unique bounded `20260910f` EOD/Identity continuation complete or
   stop at its next explicit resumable boundary; do not start a competing
   writer. Completing acquisition does not authorize
   research use of the affected V1 EOD history. Design and execute a new
   complete immutable Reconciled EOD Edition under ADR 0204, then formally
   reconcile the full interval before research admission. ADR 0202
   resolved the exact 2022-12-05 VWAP precision case without rewriting source
   custody or weakening the provider-neutral repository. The 2026-09-10
   REST pilot found Grouped Daily denied for
   2021-09-09/10 but accessible with 11,063 rows for 2022-09-09; PIT Tickers,
   splits, and dividends were accessible on all three dates. Use the documented
   five-year Day Aggregates Flat Files as the preferred bulk-price route and
   retain REST as a bounded fallback/cross-check. The fetch-only adapter and
   transitive raw-gzip custody are fixture-tested; a live pilot awaits the
   separate dashboard S3 credential, not another REST API-key retry.
   The first Flat File attempt verified fail-closed behavior and made zero requests
   because that separate credential is not configured. Exact-interval REST
   execution freezes both 2021-09-09 and 2026-09-09 and permits an explicit
   bounded paid-plan serial interval; it does not alter the older 300-session
   planning contract.
   After the nominal interval, acquire the separately declared 20-session
   Membership warm-up from 2021-08-11 through 2021-09-08; do not count it in
   the 1,255-session evaluation interval.
2. Use Massive as the primary price/reference source and evaluate official
   free evidence through bounded source-specific pilots. Preserve every
   conflict, missing semantic, and permission limit; no first-non-null merge.
3. Persist latest-vintage historical Membership under the ADR 0197
   research-only family; never place it behind the signal-eligible publication
   marker or expose it through that reader. Then repair identity/lifecycle,
   actions, terminal
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
