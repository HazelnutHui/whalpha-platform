# Authoritative Current Context

Operational state verified at: 2026-09-09T02:09:00Z

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
| Deployed OCI release | `2026-09-09T020802Z-d53e98832ef5` |
| Deployed source commit | `d53e98832ef57f22e018f9f9b863f009eb355544` |

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
| Canonical EOD | 304 contiguous XNYS sessions, 2025-06-23 through 2026-09-04 |
| Latest EOD | 2026-09-04; 9,962 rows |
| Latest EOD fingerprint | `3266c411a556ee1813a73beae19a71dc14e855b476770b3b82f81a5151e4abc4` |
| Latest EOD Parquet SHA-256 | `853d6fa9837891419f633aed8401a6ab52a503976d6607888c9def6de64b8577` |
| Latest Identity | 2026-09-08; 9,982 Instruments / 13,155 provider identities / 9,982 Resolvers |
| Latest Identity fingerprint | `ccada891e47725796142b08381e4a24026ee074d8d5dc4cf1d33b9fbc7e422a5` |
| Identity/EOD alignment | Identity ahead of EOD: Identity 2026-09-08; EOD remains 2026-09-04 |
| Canonical historical Identity source | 303 immutable source-observation partitions / 3,713,485 rows; 2 EOD sessions remain without source evidence and 2026-09-08 is source-only pending EOD |
| Canonical signal-eligible Membership | 2026-09-04; 19,964 decisions; eligible for the 2026-09-08 open |
| Canonical EOD/Identity family evidence | 2 immutable manifests; final Historical Coverage absent |
| Canonical corporate-action source observations | 70,099 rows in 2 event-year partitions; 42,056 resolved / 28,043 quarantined; bounded query-snapshot coverage only |
| Corporate-action source publication | `7b13691e22b7e815a773ed1d575ed580bbee897eb0dbf10c41e4e0862a95b1d1` |
| Canonical split-only action facts | 709 rows: 707 active / 2 quarantined; 708 groups; 43 possible-impact stable IDs; full coverage and ledger authority false |
| Canonical split-action publication | `76f017a1547e20b997e40cd1e61497b71c749a94e88a8632a3898fe84c106218` |
| Canonical sparse split adjustment | 101,321 affected-path rows: 98,291 clear / 3,030 quarantined; basis 2026-09-04; outcome-reconciliation only |
| Split-adjustment publication | `7e08b8a8ee364cf215c1459645f76240368b50cc3d2cb4bc77db86d3ca7c3c2a` |
| `/data` inventory | 4,204 files / 2,151,679,313 bytes |
| `/data` inventory fingerprint | `af06b692cf1f9708e75cf44defd198cb25317b65403a2adbc503d9e03e1fa71f` |
| `/data` symlinks | zero |
| Publication staging/partial residue | zero |

The exact 300-session historical target through 2026-08-31 is complete. The
four following EOD sessions, 2026-09-01 through 2026-09-04, are also canonical.
The guarded 2026-09-08 Identity catch-up completed, including Plan 1.1 source
observation. The same-session EOD fetch returned provider HTTP 403 on its first
attempt, a bounded 22:52 UTC post-close retry, and one final bounded 2026-09-09
01:48 UTC retry; none created a package or staging path. At 02:27 UTC, a
credential-safe same-process comparison returned 12,510 Grouped Daily results
for 2026-09-04 and HTTP 403 for 2026-09-08. The credential and endpoint are
therefore globally usable; the unresolved boundary is current-session recency
under the current account. Basic is officially described as end-of-day while
Starter is 15-minute delayed, but Basic's exact release minute remains
unproven. No retry loop, historical-backfill transient service, or computation
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
| Market Intelligence | `2026-09-04T112916Z-717cb82c5369`; contract 1.3 |
| MI payload SHA-256 | `34f9ae867d44aae4fda77ed47d2921570a52aade1147869f1c7835439f2439c8` |
| MI logical fingerprint | `2d8957011113e944304c8609ed4ff771f7ad8e3b9e0d59a6823a6ec2b827ac5e` |
| Dashboard Snapshot | `2026-09-08T171914Z-ca2d34d50692` |
| Snapshot pointer fingerprint | `c1469a1dbde97fc5212b57d039e60b585be5ba0488ae4626c2e0d393fe387ea5` |
| Contracts | Snapshot 1.11 / Dashboard 2.8 |
| Freshness | current-clock operational view expects 2026-09-08 and is one session stale at 2026-09-04; the immutable Snapshot publication assertion remains sealed lag-zero for its 2026-09-04 expectation; review mode false |
| Immediate local Snapshot rollback | `2026-09-08T171250Z-8c3dc878d6ab` |

Market Regime is Balanced in both Universes: Primary 56.7472 and Secondary
57.3733. Market Intelligence contains 16 preregistered ETF relationships, 336
bounded relationship-history rows, 30 ETF observations, and 5/10/20-session
views. Candidate publication 1.1 exposes 880 Primary and 951 Secondary display
records. These are eligible bounded Candidate records, not Universe sizes.

The active analytics status is `degraded_short_history`: Market Intelligence
currently consumes 26 sessions even though canonical EOD contains 304. This is
a consumer-integration limitation, not missing price acquisition.

## Historical research readiness

The formal status is `data_blocked`, with
`ready_for_strategy_development_review=false` and
`performance_claims_authorized=false`.

| Family | Current evidence | Remaining boundary |
| --- | --- | --- |
| EOD Price Bar | 304 canonical sessions; immutable family evidence published | final transitive Historical Coverage |
| Point-in-time Identity | 305 canonical completed snapshots, including one Identity-only 2026-09-08 date; immutable family evidence remains scoped through 2026-09-04 | EOD alignment and final transitive Historical Coverage |
| Identity source observations | 303 canonical partitions / 3,713,485 rows | 2026-08-13 and 2026-08-19 remain unbound; 2026-09-08 awaits EOD |
| Daily Universe Membership | 1 canonical signal-eligible session; disconnected mechanics cover 302 source-available sessions | governed historical point-in-time eligibility and complete publication |
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
  exact 304-session EOD evidence. It retained 26,803 unresolved source rows,
  classified 40,454 resolved groups as bounded arithmetic candidates only, and
  retained 746 resolved groups for one or more review reasons. The VISN USD 5
  row automatically failed the large-distribution date-order gate: issuer
  evidence calls August 17 the record date and August 28 the ex-date, while the
  provider row reports August 17 as effective/ex-date. No dividend was
  canonicalized and no total-return authority changed.
- The lifecycle queue contains 547 stable-ID review candidates. A real licensed
  cross-venue sample and the fixed 30-item diagnostic are required before an
  adapter can become authoritative.

Detailed execution evidence belongs in ADRs 0147–0183 and their dated audits,
not in this recovery document.

## OCI production proof

The 2026-09-09T02:09:00Z independent remote inspector matched the active
release and exact Dell deployment audit:

| Evidence | Verified value |
| --- | --- |
| Release | `2026-09-09T020802Z-d53e98832ef5` |
| Source revision | `d53e98832ef57f22e018f9f9b863f009eb355544` |
| Bundle logical fingerprint | `28b936259a59b38deeeaeeca7c89d6a908c9885c18b8e501574b40bc2d9e8023` |
| Manifest SHA-256 | `df2e01816596efdf28e0a3a3e48b69ae8ee013b6e43f755fb72586ffa913cde9` |
| Checksums file SHA-256 | `02bf93dd85cfa51e60336172aab10c4bfb2401cf8657f69848c156cbbc2dfbe2` |
| Remote-state fingerprint | `1a43b9b798b83dbafe0d0102eea3e46a7e4c960972993e00e8906c9653589a81` |
| Bundle files | 53; checksum validation passed |
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
or budget boundary. It is repository capability only: it is not installed in
the timer, and no real multi-action execution has yet been recorded.

The stable owner-only runtime workspace is now active at
`/home/hui/.local/state/trading-intelligence-platform/automation/daily-eod`.
Its bootstrap retains an exact 192-event journal copy plus formally reread
2026-09-04 Phase 1b and Candidate priors. All directories are `0700`, immutable
files are `0400`, the journal lock is `0600`, and there are zero symlinks or
staging residues. An execute-enabled 2026-09-08 preflight passed custody and
stopped at `eod_required` with zero actions. The legacy sources remain
unchanged; the new root is the forward runtime candidate, not an installed
scheduler binding.

ADR 0181 closes the code-level package/plan custody mismatch: future live data
transitions may use only the exact `acquisition-package` and
`canonical-apply-plan.json` pair in their owner-only session directory, while
legacy `/tmp` evidence remains readable. All provider, Identity-source,
acquisition, Apply, coordinator, capability, and standing-authorization
boundaries enforce the same session and custody mode. No real persistent
package/plan has yet been created, and no timer authority changed.

The manual guarded chain works end to end:

```text
Identity -> EOD -> Phase 1a -> Phase 1b -> Candidate -> Entry Geometry
-> ETF Relationships -> Market Preview -> Strategy Channels
-> Candidate Visual Context -> MI Plan/Apply -> Snapshot Plan/Apply
-> serving bundle -> OCI deploy/postflight
```

ADR 0154 Membership preparation remains a research sidecar after Identity/EOD;
it has passed a zero-write 9/4 replay. The 9/8 Identity leg completed, but the
provider rejected the initial and both bounded post-close EOD retries before
package creation, so Membership correctly remains unavailable for that session
and coordinator integration is still pending.

Measured isolated/current-code stages include Candidate about 295 seconds,
Entry 49.67 seconds, ETF Relationships 15.36 seconds, Strategy Channels 33.82
seconds, Visual Context 51.11 seconds, MI candidate plus plan 53.84 seconds,
and Snapshot candidate plus plan 121.57 seconds. These measurements come from
separate controlled runs and must not be summed into a claimed end-to-end
runtime. The next live session must supply one consolidated timing record.

Candidate's cumulative writer remains the main measured hotspot. The segmented
Candidate path proved several equivalence boundaries but remains a cutover
NO-GO because the current reader rehashes the large base and Visual Context
lacks cumulative state history. Do not resume that line of optimization unless
a new live-chain measurement breaches an agreed runtime budget and one bounded
design addresses both gaps.

## Immediate next work

1. Resume the guarded 2026-09-08 chain only when the current account makes its
   EOD package available. If same-evening operation is required, the lowest
   currently documented 15-minute-delayed tier is Stocks Starter; after any
   user purchase, record one controlled timing/completeness observation before
   changing readiness policy. Then exercise ADR 0154 Membership preparation
   against direct Daily Identity Plan 1.1 evidence and record consolidated
   timings.
2. After a new canonical session exists, use the activated owner-only runtime
   workspace for one controlled ADR 0180 multi-action execution and record its
   consolidated timing and stop state.
3. After the new-session Membership and recovery gates pass, review the
   one-action coordinator integration and a controlled scheduler rehearsal.
   Do not enable unattended writes merely because the timer is active.
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
