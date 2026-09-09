# Authoritative Current Context

Operational state verified at: 2026-09-09T08:29:13Z

Repository context updated at: 2026-09-09 UTC

This is the compact source of truth for a new Codex task or device. Historical
execution detail belongs in the [changelog](changelog.md), dated audits, and
ADRs. Proposed sequencing belongs in the [roadmap](roadmap.md).

## Repository and infrastructure

| Field | Verified value |
| --- | --- |
| Workstation / user | `dell5820` / `hui` |
| Source-of-truth repository | `/home/hui/projects/trading-intelligence-platform` |
| Branch | `main`; verify HEAD and cleanliness with the report rather than freezing them here |
| Public site | `https://whalpha.com/` |
| OCI alias | `whalpha-oci` |
| Deployed OCI release | `2026-09-09T075821Z-32321f0dadd5` |
| Deployed source commit | `32321f0dadd5c8f605ee11c8188d3ed90df0814d` |

Dell is the authority for code, data, development, and heavy computation. OCI
is only the static web-serving, localhost Auth Service, and public Session
boundary. Windows and future Mac systems are remote entry points. A later clean
repository commit does not invalidate an older immutable deployed bundle;
compare both identities explicitly.

The source-of-truth `main` was clean during this verification. The stale
`codex/historical-research-backfill` worktree had no unique commit and was 79
commits behind `main`; do not use it as a development base. Exact recovery
detail belongs in the changelog rather than a frozen HEAD field here.

## Formal Dell data state

The network-free reader uses report contract 1.10. The 2026-09-09 verification
completed at validation level `active_custody_and_contracts` with
`completion_index_plus_latest_partition`. The explicit all-partition mode also
passed during ADR 0125 validation.

ADR 0149 separates current-clock operational freshness from immutable
publication evidence. Canonical EOD, the active Snapshot, and the Snapshot's
sealed publication assertion are reported separately.

| Boundary | Verified value |
| --- | --- |
| Canonical EOD | 305 contiguous XNYS sessions, 2025-06-23 through 2026-09-08 |
| Latest EOD | 2026-09-08; 9,964 rows |
| Latest EOD fingerprint | `3942c205efc681d789ee4e7c1dc8051c801a21304fa112e936be51e52b4c42ac` |
| Latest EOD Parquet SHA-256 | `aa2b3e43e5c07fd43cbe111267142dc493483a4eac024e08d74da4c4c7164e9f` |
| Latest Identity | 2026-09-08; 9,982 Instruments / 13,155 provider identities / 9,982 Resolvers |
| Latest Identity fingerprint | `ccada891e47725796142b08381e4a24026ee074d8d5dc4cf1d33b9fbc7e422a5` |
| Identity/EOD alignment | Aligned at 2026-09-08 |
| Canonical historical Identity source | 303 immutable source-observation partitions / 3,713,485 rows; 2026-08-13 and 2026-08-19 remain without source evidence; no source-only date remains |
| Canonical signal-eligible Membership | 2 sessions / 39,928 decisions: 2026-09-04 and 2026-09-08; publication fingerprints `3f71cd40edd2ed6d7e215a95e0cb89c08c7e96dcb9a8fb543a4de34286c15518` and `f02a67923d60ea4293a87b0884f3fadb109e9cfc3956b3617a4c678648789bb8` |
| Canonical EOD/Identity family evidence | 2 immutable manifests; final Historical Coverage absent |
| Canonical corporate-action source observations | 70,099 rows in 2 event-year partitions; 42,056 resolved / 28,043 quarantined; bounded query-snapshot coverage only |
| Corporate-action source publication | `7b13691e22b7e815a773ed1d575ed580bbee897eb0dbf10c41e4e0862a95b1d1` |
| Canonical split-only action facts | 709 rows: 707 active / 2 quarantined; 708 groups; 43 possible-impact stable IDs; full coverage and ledger authority false |
| Canonical split-action publication | `76f017a1547e20b997e40cd1e61497b71c749a94e88a8632a3898fe84c106218` |
| Canonical sparse split adjustment | 101,321 affected-path rows: 98,291 clear / 3,030 quarantined; basis 2026-09-04; outcome-reconciliation only |
| Split-adjustment publication | `7e08b8a8ee364cf215c1459645f76240368b50cc3d2cb4bc77db86d3ca7c3c2a` |
| `/data` inventory | 4,253 files / 2,236,844,204 bytes |
| `/data` inventory fingerprint | `aad4f05da35422280160956192c3c431880751792002a08b602d321d7c5701b9` |
| `/data` symlinks | zero |
| Publication staging/partial residue | zero |

The exact 300-session historical target through 2026-08-31 is complete, and all
five later sessions through 2026-09-08 are also canonical. After the earlier
bounded 403 observations, one guarded Grouped Daily request succeeded at
06:59 UTC on 2026-09-09 and froze 12,534 raw records. Exact-plan Apply produced
9,964 canonical rows with zero duplicate business keys or orphan Identity
references. This one observation proves availability by 06:59 UTC for this
session only; Basic's earliest or guaranteed release minute remains unproven.
No blind retry loop, historical-backfill transient service, or computation
process is running.

### Active Universe

The active Activation V2 remains provisional provider-form evidence from
analysis session 2026-08-19.

| Universe | Verified value |
| --- | --- |
| Primary | 1,718 CS; membership fingerprint `c3665203965b96528c9be07db3c49d18023104e346da16050f1170d4fe148978` |
| Secondary | 1,831 = 1,718 CS + 113 ADRC; membership fingerprint `2dce08e728774510878c47dc80898e10236952dacd146990ad344c4dcb75a295` |
| Activation pointer fingerprint | `dbe6056e1ed4b87ebce88b356c346831ce67431a263066cd283b9ad7e8067168` |
| Activation logical fingerprint | `6ea818cb3079bb77fd5fe1b8000530d2c8e2d1127fcccd40be68ac590678c7a5` |

Provider security form does not prove issuer operating structure or domicile.
Core remains the intended future default and Broad the future secondary only
after authoritative issuer-structure evidence passes the documented gates.

## Active analytics and Snapshot

| Boundary | Verified value |
| --- | --- |
| Market Intelligence | `2026-09-08T071528Z-d6cc4ee57917`; contract 1.3 |
| MI payload SHA-256 | `78cc31f056f224092aeebb250a30929cae777f1731f7c4365c0758665d7d3c8e` |
| MI logical fingerprint | `a7d063cc560df7851c7ace4ca0d766dff9e3ccfb6e1be6f573d5f04792d55976` |
| Dashboard Snapshot | `2026-09-08T072146Z-d6cc4ee57917` |
| Snapshot pointer fingerprint | `3bbb7286d9747b9072b2d778d7c08310438f7c0e8baf8464a799a33f78eee857` |
| Contracts | Snapshot 1.11 / Dashboard 2.8 |
| Freshness | current-clock operational and immutable publication views are fresh at 2026-09-08 with zero session lag; review mode false |
| Immediate local Snapshot rollback | `2026-09-08T171914Z-ca2d34d50692` |

Market Regime is confirmed Balanced in both Universes while both candidate
states are Defensive: Primary 44.9243 and Secondary 45.4356. Market
Intelligence contains 16 preregistered ETF relationships, 336 bounded
relationship-history rows, 30 ETF observations, and 5/10/20-session views.
Candidate publication 1.1 exposes 904 Primary and 966 Secondary display
records. These are eligible bounded Candidate records, not Universe sizes.

The active analytics status is `degraded_short_history`: Market Intelligence
currently consumes 26 sessions even though canonical EOD contains 305. This is
a consumer-integration limitation, not missing price acquisition.

## Historical research readiness

The formal status is `data_blocked`, with
`ready_for_strategy_development_review=false` and
`performance_claims_authorized=false`.

| Family | Current evidence | Remaining boundary |
| --- | --- | --- |
| EOD Price Bar | 305 canonical sessions; immutable family evidence remains coverage-scoped | final transitive Historical Coverage |
| Point-in-time Identity | 305 canonical completed snapshots aligned through 2026-09-08; immutable family evidence remains coverage-scoped | final transitive Historical Coverage |
| Identity source observations | 303 canonical partitions / 3,713,485 rows | 2026-08-13 and 2026-08-19 remain unbound |
| Daily Universe Membership | 2 canonical signal-eligible sessions / 39,928 decisions; disconnected mechanics cover 302 source-available sessions | 303 missing EOD sessions; governed historical point-in-time eligibility and complete publication |
| Corporate-action source observations | canonical bounded 2025-06-23 through 2026-09-04 query snapshot; 42,056 resolved / 28,043 quarantined | not signal eligible; future incremental/revision layout and stronger availability evidence |
| Canonical corporate actions | 709 canonical split-only fact rows: 707 active / 2 quarantined; bounded query snapshot and outcome-only | complete action-type, availability, and revision scope; keep 1,240 unresolved rows unassigned |
| Instrument lifecycle | temporary 547-item corroboration queue complete | licensed cross-venue sample, terminal/successor/availability evidence, canonical family |
| Adjustment ledger | Canonical ADR 0177 publication contains 98,291 clear / 3,030 quarantined affected-path rows; Plan/Apply and exact-existing recovery passed; ADR 0182 found 387 unexplained severe price discontinuities across 321 stable IDs; ADR 0183 retained 746 of 41,200 resolved dividend groups for review and kept the other 40,454 arithmetic-only | independently resolve flagged discontinuities; complete coverage and absent-row neutrality evidence; independently authoritative dividend dates, currency/order handling, and total-return publication |
| Costs and liquidity | deterministic one-side equity scenario mechanics; no observed quote or calibrated-impact evidence | governed point-in-time spread evidence, impact calibration/stress validation, and actual-execution comparison |
| Evaluation and holdout | fixture mechanics and custody seam only | real chronological dataset and sealed real holdout |
| Historical Coverage | reader and fixture mechanics exist; two family-evidence manifests are canonical | final publication across every required admitted family |

Historical source observations made after their represented sessions remain
outcome-reconciliation evidence unless a selected source supplies defensible
point-in-time availability semantics. Current Membership must never be
projected backward. Canonical price history alone is not backtest readiness.

### Corporate-action and lifecycle evidence already completed

- Massive V1 temporary source custody covers 1,949 split rows and 68,150
  dividend rows from 2025-06-23 through 2026-09-04.
- Exact-event-date Identity resolution preserves all 70,099 observations:
  42,056 resolve by stable ID and 28,043 remain quarantined. Latest/nearest,
  name, and current-Universe fallbacks remain zero.
- A later identical-scope observation was unchanged over an approximately
  69–73 minute interval. This proves short-interval stability only, not
  historical immutability or provider revision semantics.
- ADR 0174 published the exact 70,099 normalized source observations in two
  immutable event-year partitions plus a marker-last bounded coverage record.
  A zero-write postflight reused both partitions and the marker. This is
  canonical source custody, not canonical Corporate Actions or point-in-time
  signal evidence.
- The source-marker-bound split candidate contains 708 resolved stable-ID/date
  groups: 707 single-action clear candidates and one multiple-action
  quarantine. Forty-three possible-impact stable IDs remain conservatively
  non-clear; only two enter the active Universes. Its event math and unresolved
  impact set exactly match the prior shadow candidate. Total return remains
  unavailable.
- ADR 0176 published the 709 resolved source actions as a sparse canonical
  split-only fact family. The one two-action group remains quarantined, 1,240
  unresolved rows remain unassigned, and the 43 possible-impact stable IDs
  remain explicit. The exact second Apply was zero-write. This does not prove
  absent-event neutrality or complete Corporate Action coverage.
- ADR 0178 published the exact 101,321-row sparse split-adjustment candidate as
  canonical outcome-reconciliation evidence. The exact second Apply was zero-
  write. Omitted rows still do not authorize factor one, total return remains
  unavailable, and research readiness remains blocked.
- ADR 0182 scanned 2,802,728 adjacent stable-ID transitions without network or
  writes. All 645 comparable active split groups were bounded after exact ratio
  adjustment with zero extreme residuals. The scan also retained one canonical
  multiple-action quarantine, 19 unresolved-impact quarantines, 80 known keys
  without a comparable two-sided transition, and 387 unexplained severe gaps
  across 321 stable IDs. Price gaps remain review flags only and cannot assign
  actions or authorize omitted-row neutrality. Current-state prioritization
  finds 13 Primary / 14 Secondary affected IDs and 31 lifecycle-queue overlaps
  with no overlap between those two sets; this locator does not create
  historical Membership evidence. Public first-party review of the 15 current-
  Secondary flags found 13 date-aligned event contexts, one explicit VISN
  special cash distribution, and one unresolved DFNS case. None establishes a
  split or omitted-row neutrality; the VISN evidence reinforces the separate
  total-return requirement.
- ADR 0183 scanned all 68,150 cash-dividend source observations against the
  exact 304-session EOD evidence through 2026-09-04. It retained 26,803 unresolved source rows,
  classified 40,454 resolved groups as bounded arithmetic candidates only, and
  retained 746 resolved groups for one or more review reasons. The VISN USD 5
  row automatically failed the large-distribution date-order gate: issuer
  evidence calls August 17 the record date and August 28 the ex-date, while the
  provider row reports August 17 as effective/ex-date. No dividend was
  canonicalized and no total-return authority changed.
- The lifecycle queue contains 547 stable-ID review candidates. A real licensed
  cross-venue sample and the fixed 30-item diagnostic are required before an
  adapter can become authoritative.

Detailed execution evidence belongs in ADRs 0147–0184 and their dated audits,
not in this recovery document.

## OCI production proof

The 2026-09-09T08:17:05Z independent remote inspector matched the active
release and exact Dell deployment audit:

| Evidence | Verified value |
| --- | --- |
| Release | `2026-09-09T075821Z-32321f0dadd5` |
| Source revision | `32321f0dadd5c8f605ee11c8188d3ed90df0814d` |
| Bundle logical fingerprint | `57afdf0052521e7daf631bed5995c7abc9f714a8bf962983180d49b6a4cc2979` |
| Manifest SHA-256 | `85a37e213a14f0e48a34f7c167b4ee81ebcb4872a2eda78f8b5567d6b33ced8c` |
| Checksums file SHA-256 | `107b887382b88c71ce6d67c5369407021290751fa020db217a3f2bc77b836edb` |
| Remote-state fingerprint | `97edc9097ff81bb73c93b2ac5744b0cb95fe67b94f7792b486c75a6fd8b323a1` |
| Bundle files | 52; checksum validation passed |
| Locales | English default; English and Simplified Chinese supported |
| Access capability | guest and credential Sessions are identical |
| Sensitive/provider payload | no credentials, raw provider data, or Parquet |

Nginx and `whalpha-dashboard-auth.service` are active and enabled. Auth listens
only on `127.0.0.1:8010`. Public entry, favicon, protected routes, temporary
guest Session, Dashboard, Snapshot, Candidate summary/detail, Strategy
Channels, Sector ETF Rotation, logout, and renewed protection passed. There is
no staging/failed-release residue, unexpected private listener, or failed
system unit. Password login and final visual inspection remain manual checks.

## Current product boundary

WH Alpha is a Session-protected, bilingual U.S. equity market-intelligence and
research platform for discretionary decisions. The product chain is:

```text
market state -> strength direction -> sector/theme -> stock candidate
-> trade preparation -> entry/invalidation -> position management
```

Live first-level workspaces are Market Regime & Opportunities
(`市场风向与机会`), Market Structure & Activity, Sector ETF Rotation, Stock
Candidates (`个股候选`), and Quant Research Lab (`量化研究实验室`). The landing
page and in-app shell share the dark navy/cyan WH identity and favicon. Planned
capabilities remain labelled as planned.

Sector Rotation now includes a same-session market-to-candidate decision chain:
the selected Universe's confirmed Regime, five leading fixed-registry ETF price
proxies for the selected window, and eight Balanced-risk Candidate priorities.
The columns preserve separate source ranks and are explicitly not formal sector
membership, fund flow, causality, a combined score, or a trade instruction.

Stock Candidates expose component contributions, evidence, counterevidence,
entry position, risk, invalidation, parameters, raw facts, and lineage. Strategy
Channels keep research priority separate from trade-review readiness and show
stable-ID cross-channel repetition, all-risk-mode rejection, unavailable entry
structure, gap/volatility review, and extension risk without changing source
scores or ranks.

Only Momentum Breakout, Strong-Stock Pullback, and Trend Continuation currently
have provisional technical mechanics. Technical Reversal, Fundamental Value
Reversal, and Defensive Rotation remain unavailable. The technical channels
share price/volume, relative-strength, and trend inputs; their distinctness is
not validated. Security-level point-in-time sector taxonomy is absent, so the
current overlap display is not formal sector concentration.

ADR 0173 completed the source boundary audit. GICS History is the first
specification/sample candidate, TRBC is second, RBICS is complementary, and
Massive SIC is current-diagnostic only. No taxonomy source has been selected,
sampled, licensed, acquired, implemented, published, or deployed. Classification
V1.1 contracts, immutable offline Parquet persistence, explicit coverage
decisions, and a fail-closed reader are now fixture-validated. No adapter or
physical classification dataset exists, so the product limitation is
unchanged. S&P's public Marketplace gates the GICS sample and data dictionary
behind sign-in, and public methodology requires licensing for display and
derived-product use. Public hierarchy files do not satisfy the sample gate.

Guest and credential Sessions must remain identical in data, features,
language, Universe, and analysis until the user explicitly changes that policy.
Engineering, governance, validation, security, and research standards remain
commercial-grade even though current use is personal/friends.

## Guardrails

- Decision support, not automated trading or order execution.
- Human investment meaning first; algorithm labels second.
- Show source values, parameters, contributions, supporting and contrary
  evidence, market adjustment, and invalidation.
- Never call price/volume proxies actual fund flow.
- Never call underlying-stock forward return an option return.
- Stable `instrument_id` is the join key; ticker is display metadata.
- Unknown, ambiguous, malformed, heuristic-only, and insufficient-evidence
  records remain quarantined.
- Prevent look-ahead, survivorship, revision, selection, and leakage bias.
- Keep research, validation, shadow, Production, monitoring, and retirement
  states explicit.

Priority research families are Strong-Leader Pullback, Momentum Breakout,
Trend Continuation, Technical Reversal, and Fundamental Value Reversal.
Defensive opportunity is Regime-conditioned context. Earnings, macro, and news
begin as risk/context inputs. Options are a separate later expression layer;
naked short-option strategies remain outside the intended scope.

## Automation and performance

The installed `whalpha-daily-eod-wake-review.timer` is active/waiting and
credential-free. Its service is inactive between wakes. It only plans and
reports: no fetch, Apply, calculation, publication, deployment, retry, or alert
delivery occurs. No unattended write-capable scheduler is installed. SMTP is
unconfigured.

ADR 0180 and `daily-eod-bounded-offline-run/1.0` now provide a finite Dell-local
runner for consecutive successful offline stages. It preserves the existing
single-action journal and postcondition boundary, defaults to review-only, and
stops before every data, publication, Snapshot, deployment, failure, recovery,
or budget boundary. It is repository capability only and is not installed in
the timer. The real 2026-09-08 invocation completed nine analytics/MI-plan
actions in about 14.6 minutes of recorded action time and stopped at
`review_publication` as designed.

The stable owner-only runtime workspace is now active at
`/home/hui/.local/state/trading-intelligence-platform/automation/daily-eod`.
Its bootstrap retains an exact 192-event journal copy plus formally reread
2026-09-04 Phase 1b and Candidate priors, followed by the real 2026-09-08
package, plans, analytics, Snapshot, and Serving Bundle. All directories are
`0700`, immutable files are `0400`, the journal lock is `0600`, and there are
zero symlinks or staging residues. The 27-event 2026-09-08 journal has no
unresolved action or cadence reservation. The legacy sources remain unchanged;
the runtime root is still not an installed scheduler binding.

ADR 0181 closes the code-level package/plan custody mismatch: future live data
transitions may use only the exact `acquisition-package` and
`canonical-apply-plan.json` pair in their owner-only session directory, while
legacy `/tmp` evidence remains readable. All provider, Identity-source,
acquisition, Apply, coordinator, capability, and standing-authorization
boundaries enforce the same session and custody mode. The 2026-09-08
acquisition package and canonical plan now provide real persistent-custody
lineage proof. ADR 0184 likewise permits
the exact same-session persistent Serving Bundle and shares its validator
across the deployment capability, custody, and reviewed shell entrypoint. No
timer authority changed.

The manual guarded chain works end to end:

```text
Identity -> EOD -> Phase 1a -> Phase 1b -> Candidate -> Entry Geometry
-> ETF Relationships -> Market Preview -> Strategy Channels
-> Candidate Visual Context -> MI Plan/Apply -> Snapshot Plan/Apply
-> serving bundle -> OCI deploy/postflight
```

ADR 0154 Membership preparation remains a research sidecar after Identity/EOD.
The 9/8 candidate used aligned same-session EOD, Identity, and normalized
Identity source evidence, retained the canonical 8/14 provider type-code
catalog, and was evaluated before the next open. Exact Plan/Apply published
19,964 decisions; zero-write postflight reused both targets. ADR 0185 now adds
a pure read-only sidecar planner and optional Pipeline Wake 2.1 projection.
The real 9/8 read returned `complete` / `none`, the exact publication
fingerprint, and zero network/write/authority; no installed timer or
coordinator execution changed and the website did not change.

The 2026-09-08 real persistent run records Phase 1a about 96 seconds, Phase 1b
4 seconds, Candidate 346 seconds, Entry Geometry 62 seconds, ETF Relationships
21 seconds, Market Preview 7 seconds, Strategy Channels 47 seconds, Visual
Context 72 seconds, and MI planning 87 seconds. These nine actions total about
14.6 minutes. Snapshot planning took about 137 seconds and Serving Bundle
construction about 87 seconds after their separate gates. Engineering time for
the deployment-path defect is exceptional and not a normal daily-runtime
measurement.

The post-publication default-review run executed zero actions and stopped at
the expected `review_bundle_deployment` boundary: the final successful OCI
deployment came through the separately audited one-shot path, so the earlier
zero-write coordinator recovery event was not rewritten. The scheduler wake
independently reports 9/8 current, zero missing sessions, target 9/9, and
`wait` until the 20:30 UTC stabilization review. No fetch, write, or scheduler
enablement occurred.

Candidate's cumulative writer remains the main measured hotspot. The segmented
Candidate path proved several equivalence boundaries but remains a cutover
NO-GO because the current reader rehashes the large base and Visual Context
lacks cumulative state history. Do not resume that line of optimization unless
a new live-chain measurement breaches an agreed runtime budget and one bounded
design addresses both gaps.

## Immediate next work

1. Observe the ADR 0185 read-only Membership sidecar on the next live session,
   including candidate readiness and a research-only fault, before considering
   any unattended sidecar execution.
2. Perform one controlled next-session unattended-scheduler rehearsal. Do not
   enable recurring writes merely because the read-only timer is active.
3. Record one clean-path acquisition-to-deployment elapsed time on the next
   live session, excluding engineering/debugging time, and set a finite runtime
   budget before any further optimization.
4. Obtain and review a GICS History specification/sample against ADR 0173 and
   the field-to-contract and role gates already frozen in the source review.
5. Implement a live adapter and Dell-only current snapshot only after that
   review passes. Integrate Candidate sector/industry concentration only after
   current source coverage, mapping, permission, and quarantine behavior pass.
6. Complete lifecycle, historical Membership eligibility, costs, availability,
   revision, final Historical Coverage, and sealed evaluation evidence.
7. Begin real preregistered chronological research with Strong-Leader Pullback,
   then Momentum Breakout, Trend Continuation, Technical Reversal, and
   Fundamental Value Reversal.
8. Add options expression, fundamentals/valuation/events, and later
   portfolio/IBKR integration after their required datasets exist.

Do not tune formulas, thresholds, or paid-data scope merely because price
history is available. First identify the exact missing fact family and its
research or product use.

## Cross-device continuity

- Windows already has its own dedicated passwordless SSH key and saved Dell
  remote project.
- For Mac, join the same Tailscale network and generate a new Mac-only SSH key;
  never copy the Windows private key.
- Add only the Mac public key to Dell, configure SSH alias `dell5820`, save
  `/home/hui/projects/trading-intelligence-platform` in Codex Desktop, and run
  the read-only context report before continuing.
- Never place literal server addresses, private-key paths, credentials, or
  Session material in repository documentation or chat.

## Recovery procedure for a new task

1. Read `AGENTS.md`, `README.md`, `docs/README.md`, this document, and
   `current-status.md` in that order.
2. Run `scripts/admin/report-current-context.sh` from the source-of-truth main
   repository. Use `--full-history-validation` only for a periodic or
   investigative all-partition audit.
3. Compare repository, EOD, Identity, Activation, MI, Snapshot, inventory, and
   residue with this baseline.
4. If deployment state matters, run the non-secret OCI inspector separately;
   the local report is intentionally network-free.
5. Classify differences before mutation. Never silently rewrite an active
   pointer, rerun acquisition, deploy, or clean a remote release.
6. Read only the architecture, operations, ADR, and audit documents relevant to
   the selected single objective.
