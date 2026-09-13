# Authoritative Current Context

Operational state verified at: 2026-09-12T23:00:36Z

Deployment state additionally verified at: 2026-09-11T21:23:56Z

Repository context updated at: 2026-09-13 UTC

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
| Active OCI release | 2026-09-11T211340Z-26cab64fabda |
| Deployed source | 26cab64fabdafca710d6471cb09ac8c62ef17c2d |

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
| Canonical EOD | 1,255 contiguous XNYS sessions, 2021-09-13 through 2026-09-11 |
| Latest EOD | 2026-09-11; 9,971 rows |
| Latest EOD fingerprint | eec1f813851b378f47fbcd810728ed8b33b4748929ba85ff5d77e837bd12c904 |
| Latest Identity | 2026-09-11; 10,000 instruments / 13,176 provider identities / 10,000 resolvers |
| Latest Identity fingerprint | 911f35275b341138c8c820e717910e240d06fd2be45db3ebd824d55d83006b05 |
| Point-in-time Identity | 1,256 physical partitions from 2021-09-10 through 2026-09-11; all 1,255 EOD sessions align, plus one Identity-only partition |
| Identity source custody | 1,254 physical partitions / 1,253 target sessions; 2026-08-13 and 2026-08-19 remain unbound |
| Signal-eligible Membership | 3 sessions / 59,892 decisions: 2026-09-04, 2026-09-08, 2026-09-09 |
| Latest Membership fingerprint | a44ca1bb4d707406cab82b3a7ba5d146bc6d0850857b6714c1968cec17994835 |
| Research-only Membership | 300 sessions / 5,571,154 decisions, 2025-06-23 through 2026-09-03; latest-vintage, not signal eligible |
| Corporate-action observations | Canonical recent custody: 70,099 rows, 42,056 resolved / 28,043 quarantined; separate complete five-year owner-only packages: 6,491 splits / 235,751 dividends, not canonical |
| Corporate-action resolution | Current owner-only shadow `build=20260913-v2`: 242,242 source rows; 129,292 exact-date resolved / 112,943 unresolved / 7 separately unrepresentable; 1,253 Identity sessions; prior v1 retained |
| Unresolved action census | Current owner-only `build=20260913-v2`: 112,943 typed rows / 13,780 tickers fully classified: zero candidate 89,074 / 11,433; one candidate 23,676 / 2,307; multiple 193 / 40; 2,387 candidate relations and zero assignments |
| Residual action evidence | Owner-only `build=20260913-v1`: all 112,943 unresolved rows joined to retained lifecycle/inactive/FINRA evidence; 29,127 have at least one lead, 83,816 have none; only 19 row/candidate occurrences fall inside a canonical observed span; zero assignments; fingerprint `3fbcf2719047bf753ed4014017a82f6d3a659e2d90be724e2b35a90cbabce525` |
| Official FINRA OTC source | 62 monthly packages / 68,714 observations, 2021-08-11 through 2026-09-09; official OTC corroboration only; four repeated IDs retained |
| FINRA/Massive action census | 2,298 split / 8,205 dividend unique numeric candidates; zero stable-ID resolution; candidate-only fingerprint `0559b1488ced840d786734b3dfa8b054d3c65dd18365d9d77c7a4616b9cd5317` |
| Official SEC fundamentals sources | Company Facts: 20,343 members / 41,619,407 five-year occurrences; Submissions: 989,553 members / 27,217,476 filing rows; both private source snapshots |
| SEC filing clocks and sparse facts | 172,265 clocks: 172,262 admitted / 3 quarantined; 41,619,407 normalized fact occurrences: 41,619,004 clock-admitted / 403 quarantined; no security-level feature authority |
| SEC semantic census | 41,619,407 occurrences / 24,498,347 exact semantic keys; 24,497,828 revision-eligible / 519 quarantined; 886,400 later-state value changes; fingerprint `8899aeb278f50861952d7308a815c62640a2ec274bb1d614ff07f8ba651e3e21`; source-level discovery only |
| SEC filer/security link | One-session pilot: 8,201 stable-ID decisions and 150 multi-security CIK groups; issuer projection unauthorized |
| Canonical split-only facts | 709 rows: 707 active / 2 quarantined; incomplete coverage |
| Sparse split adjustment | 101,321 affected-path rows: 98,291 clear / 3,030 quarantined; outcome-only |
| Current data inventory | 18,175 files / 7,022,164,015 bytes |
| Current inventory fingerprint | eda858b1db23dc58f22cdd0faa290f2141691fecf15862dc5bd6d095354834ff |
| Symlinks / publication residue | zero / zero |
| Corrected EOD edition | Canonical contract 1.2 edition: 1,234 sessions / 10,376,263 records / 2,469 files / 1,083,699,732 bytes; interval fingerprint `098ff756a463c0bf142d9ce597375e3a0574db02ca641fcdcef9b6e72cb6b5e3` |
| Corrected EOD Apply | Applied from approved plan SHA-256 `7e9c13b957ad9e2fceb850e9da645356c2e1930800d943f2af3927da31115505`; logical fingerprint `6a09ef14c77c475d46f0ae1d20f89058ea1457e32a1e633179b642edccbcf1d5`; canonical formal reread passed |
| Corrected EOD family evidence | Exact 1,234-session EOD and same-session Identity evidence is canonically published; EOD fingerprint `b65ee35bb65796dab501d4e59df132bffc566452c713bb18e8659401b632b0a5`, Identity fingerprint `faaa73bceace816d91a5a2483714055d20c48091fe4fc8bfbcde8c27d8b647db`; approved plan SHA `d328f1725dc4a74a6237d30e1ccdad6fa8c64765d45210a8cc7a76d6492f9168`; Apply and zero-write recovery passed |
| Identity extension evidence | Exact 2026-09-08/09 Identity-only evidence is published and formally reread; plan SHA `f099929d17c07695d3b468910e1c7233bed74bab1714a81ad1189dc9cfb7317a`; evidence fingerprint `35a45e158ffdedc2cd3f3667495bbb4fdd5841a70c02370e3c0baa80d5fa51d5`; one 3,623-byte manifest; zero-write recovery passed |

The bounded historical run stopped safely at the Starter rolling entitlement
edge; ADR 0206 rejected retries or a deeper purchase solely for the expired
2021-09-09/10 boundary. Normal 2026-09-10/11 daily updates then rolled the
active five-calendar-year target to 2021-09-13 through 2026-09-11. The fresh
network-disabled census confirms zero EOD and Identity target-session gaps.
It remains `quarantined`: Membership covers only 303 sessions, source-time
Identity is unbound for two sessions, lifecycle/classification are absent,
and corporate-action/adjustment evidence is incomplete. Price depth is
complete; the anti-survivorship research foundation is not. Historical
execution detail remains in the
[continuous-run audit](../audits/five-year-eod-identity-continuous-run-2026-09-10.md),
[terminal audit](../audits/five-year-eod-identity-backfill-terminal-2026-09-11.md),
and [final daily audit](../audits/daily-eod-publication-deployment-2026-09-11.md).

The final rolling Source Coverage census has zero Grouped Daily gaps but remains
Identity-source-incomplete for 2026-08-13 and 2026-08-19. ADR 0207 therefore
bounded the first corrected edition at the preceding 1,234 fully source-proven
sessions. Its build-ready coverage artifact has SHA-256
`4dc34a7851a0a2d851d4d75da86cd66a2c6a34508a9f016b08fa5a42d2d34ba9`,
logical fingerprint
`9bd386efe1fed7e6c39c5f11bc85dfe82f5f71d039079761ba838fe952e2ac6a`,
947 retained-original sources, 287 visibly later-reacquired sources, and zero
missing, invalid, or conflict sessions.

The shared virtual environment's editable metadata points at an older Codex
worktree. The completed backfill remained source-correct because its admin
script used the project Python wrapper, which prepends the canonical checkout
source. Use `scripts/dev/run-project-python.sh` for operator modules until the
now-quiescent environment is rebound. A network-disabled rebind attempt stopped
before mutation because `setuptools` is absent; no dependency was downloaded.

The coverage-hash-bound, resumable later-source reacquisition runner has now
completed its first real full missing-set execution. Its private custody holds
305 session directories, 610 files, and 381,337,205 bytes with owner-only
modes, zero symlinks, and zero staging residue. It grants no canonical or
research authority.

The clean contract 1.2 candidate built all 1,234 sessions in 31 bounded batches
and passed final formal reread. It contains 10,376,263 records, including 2,461
accepted additions, 50 source-proven expected absences, and 2,648,128
source-proven ticker-case repairs. No unexpected absence, economic-value
change, source gap, or quarantine reached the sealed interval. The owner-only
candidate has zero symlinks or residue and remains outside `/data`.

The exact Apply plan independently reread the full candidate, bound all 2,469
artifacts and 1,083,699,732 bytes, and bound canonical pre-state fingerprint
`a83136b65d76371a9932aa58fc142aa815d1303dc89f600d852cc177eea36d5e`.
Explicitly approved atomic Apply published that exact edition without overwrite
or deletion and formally reread all 1,234 sessions / 10,376,263 records. The
postflight found zero symlinks or publication residue and current inventory
fingerprint
`8baec95b3a4e81cc2b4ca05f9f1fb24a8a112237c6c217bf88c09066462aa307`.
Historical Coverage, research, Production, publication, and website authority
remain unchanged.

ADR 0210's edition-scoped offline adapter subsequently reread the canonical
edition and all same-session Identity snapshots with eight bounded Dell
workers. The 374.70-second run validated exact unpublished EOD and Identity
family-evidence candidates over all 1,234 sessions. Their logical fingerprints
are respectively
`b65ee35bb65796dab501d4e59df132bffc566452c713bb18e8659401b632b0a5` and
`faaa73bceace816d91a5a2483714055d20c48091fe4fc8bfbcde8c27d8b647db`.
The older published current-EOD/Identity evidence covers only 304 sessions and
remains separate. At that validation stage, no family evidence or Historical
Coverage was published.

ADR 0211 then sealed and independently reread the distinct edition-specific
no-write publication plan. Its logical fingerprint is
`443d80c7347b794b7f105c2d8b5dc8e57fbc4d4dd67442773983647d69d0fcfc`
and family-set fingerprint is
`30722680a6d2f8448db0e895fed7e060ca8a81f2d5faebca3b4d23fbba2b0d8e`.
It bound exactly two absent targets / 2,673,980 bytes and granted no implied
Historical Coverage, research, or Production authority. ADR 0212 added an
explicit reconciled-edition entry to the existing recoverable Apply mechanism;
the old rolling-current entry still rejects this plan. The separately approved
real Apply published both exact manifests, and immediate completed-state
recovery reused both with zero writes. At that earlier checkpoint, independent
postflight found 18,174
canonical files / 7,022,160,392 bytes, fingerprint
`87a2a573b3350918a90db3cea51faaa1839a4e5fb420e2f20278dfc3cb9aa244`,
zero symlinks, and zero residue. The current inventory is the later value in
the table above.

Source Coverage and the full-build controller can preserve a separate
2021-08-11 through 2021-09-08 warm-up declaration. ADR 0206 leaves that
optional deeper-history path unpopulated under Starter. The active target has
now rolled to 2021-09-13; its first 20 sessions are outcome-free feature
warm-up and performance eligibility begins on 2021-10-11.

Any future external warm-up will use the distinct fixed historical workspace
`warmup-2021-08-11--2021-09-08`; the existing evaluation source workspace will
not be renamed or populated outside its stated dates. Source Coverage treats
the two workspaces as different origins with the same possible retained-
original provenance.

The fixed 30-item Massive Starter lifecycle diagnostic had stable Composite
FIGI locators and provider delisting dates for every item, but Ticker Events
matched only six; 24 returned HTTP 404 and all nine returned events were ticker
changes. Massive remains a partial lifecycle input and is rejected as the
sole-primary lifecycle source. The complete 2026-07-16 and 2026-09-03
inactive-listing source anchors are now retained in owner-only persistent Dell
custody and formally reread; their 23,260 / 23,469 rows remain discovery and
reconciliation evidence rather than canonical lifecycle or terminal outcomes.
Their five-year re-resolution is also durably retained as six exact files /
9,005,301 bytes: 2,206 / 2,278 review candidates and 21,054 / 21,191
quarantines, or 2,283 unique review-candidate instruments across anchors. It is
the bounded corroboration queue only; final lifecycle authority remains absent.

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
| Market Intelligence | 2026-09-11T205429Z-26cab64fabda; contract 1.3 |
| MI logical fingerprint | c03d69c0d46f40b55ca94863701befd970c3038701785d574dd0ada4febf0c11 |
| Dashboard Snapshot | 2026-09-11T211340Z-26cab64fabda |
| Snapshot pointer | a57ecbaef4f4ebc8bcda012193d7c07875f2bd7830a9a1eb6775c2819687e460 |
| Contracts | Snapshot 1.11 / Dashboard 2.8 |
| Immediate local rollback | 2026-09-09T211131Z-e06bd62ecab3 |

Both Universes have confirmed Balanced Market Regime and Balanced candidate
state: Primary 50.1578, Secondary 50.1501. Market Intelligence contains 16
preregistered ETF relationships, 336 bounded history rows, 30 ETF observations,
and 5/10/20-session views. Candidate publication 1.1 contains 870 Primary and
924 Secondary eligible display records; these are not Universe sizes.

Analytics remains degraded-short-history because Market Intelligence consumes
26 sessions although canonical EOD has substantially more. This is a consumer-integration
limit, not missing acquisition.

The 2026-09-11 21:23:56 UTC independent OCI postflight matched release,
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
| 1,255 aligned EOD / Identity partitions through 2026-09-11; ADR 0207's 1,234-session corrected edition is canonical and formally reread | Seal final transitive Historical Coverage for the admitted price family |
| Legacy 304-session and exact corrected-edition 1,234-session EOD/Identity evidence are separately published | Complete and admitted historical Membership |
| 1,253 target-session Identity source partitions and zero Grouped Daily source-package gaps | Two later dates remain Identity-source-unbound and quarantined outside the first edition |
| 3 prospective Membership sessions | Canonical cross-venue lifecycle/terminal outcomes |
| 300 research-only Membership sessions | Research tier is not signal eligible and remains outcome-blind |
| Five-year corporate-action source, 1,253-session exact-date resolution shadow, and assignment-free unresolved census | Resolve measured lifecycle/security-scope gaps and seven unrepresentable rows; complete availability/revision, absent-event, and adjustment semantics |
| Canonical split-only facts and sparse affected-path ledger | Complete adjustment/neutrality and total-return semantics |
| Fixture-only input, chronology, statistics, and holdout mechanics | Real chronological dataset and sealed real holdout |
| Scenario-only equity costs | Observed spread/impact calibration and execution comparison |

ADR 0207 separately governs the corrected price family. Later Identity
responses for 2026-08-13 and 2026-08-19 omitted one and five canonical business
keys in isolated diagnostics, so the ADR 0204 no-removal gate remains intact.
The first real Reconciled EOD candidate is therefore the maximal preceding
continuous interval: 1,234 sessions from 2021-09-13 through 2026-08-12. This
price-edition route does not change the rejected Membership-development census
or authorize outcomes.

The first real 1.0 build retained 275 sessions before five October 2022
absences stopped completion. Exact retained source proves each was the same
legacy `ALpA` preferred-stock bar falsely attributed to common stock `ALPA`.
ADR 0208 and manifest contract 1.1 admit only that seven-condition proven
misbinding removal and keep every other absence blocked. The incomplete 1.0
candidate has no interval marker. The clean 1.1 successor retained 300 sessions
before 20 dates exposed 30 otherwise-identical source IDs whose exact provider
ticker case had been restored. ADR 0209 and contract 1.2 admit only that eight-
condition provenance repair; the real 20-date replay found zero blocking or
economic changes. The first clean 1.2 run then retained 1,079 sessions before a
price-only `SRVR`/`SRVr` collision exposed one incorrect expected-addition
input: the builder used Identity collision groups instead of Grouped Daily
collision groups. The existing ADR 0203 classifier is now wired to exact price
symbols and the real date replays with zero blockers or economic changes. No
incomplete candidate was reused. The clean successor bound to
`c798e582b0ad3b49ada5fc7fde94125382ef9c06` is complete with interval
fingerprint
`098ff756a463c0bf142d9ce597375e3a0574db02ca641fcdcef9b6e72cb6b5e3`;
its exact plan and atomic canonical Apply completed with a full target reread.

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

The owner-only persistent runtime workspace contains the verified 2026-09-10
and 2026-09-11 packages, plans, analytics, Snapshot, bundle, Membership
evidence, and journals.
ADR 0190 fixed artifact-role, persistent-plan, and Membership-clock integration
without changing timer authority.

The 2026-09-11 offline run completed nine actions in about 17.1 minutes.
Candidate was the largest stage at about 7.0 minutes, peaked near 11.2 GiB, and
used one CPU core. Snapshot planning took about 3.8 minutes, bundle construction
2.1 minutes, and deployment 2.4 minutes. The segmented Candidate experiment
remains a cutover NO-GO because it rehashes the large base and lacks cumulative
Visual Context history. Do not resume it unless a new clean-path measurement
breaches an agreed budget and one bounded design solves both gaps.

## Immediate direction

The current rolling census fixes 2021-09-13 through 2026-09-11 as 1,255 XNYS
sessions. EOD and target-session Identity are complete. The former precision
gate is resolved under ADR 0202; ADR 0203 resolves the forward exact-symbol
mapping but not the already-published missing-bar history.
Membership covers 303 sessions and misses 952: 300 reconstructed research-only
sessions plus three signal-eligible sessions. Lifecycle, point-in-time
classification, point-in-time fundamentals, and complete Historical Coverage
are absent. The census remains `quarantined`; exact results are recorded in
the 2026-09-11 daily audit.

1. Do not restart the stopped `20260911g` continuation or retry its expired
   boundary. The rolling census is complete for price/Identity but does not
   authorize research use of affected V1 EOD history. The complete corrected
   edition has passed inventory-bound planning, atomic Apply, canonical
   postflight, read-only family-evidence validation, and exact no-write
   evidence publication planning, exact Apply, and zero-write recovery. Keep
   final Historical Coverage and research admission as separately reviewed
   decisions; this publication does not repair Membership, lifecycle, action,
   adjustment, or availability gaps. Use the first 20 edition sessions as
   disclosed feature warm-up and exclude them from signals and performance.
   Keep the
   external warm-up workspace reserved but empty under Starter.
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
