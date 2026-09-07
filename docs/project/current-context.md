# Authoritative Current Context

Operational state verified at: 2026-09-06T13:10:51Z

Repository context updated at: 2026-09-07 UTC

This is the compact source of truth for a new Codex task or device. Historical
execution detail belongs in the [changelog](changelog.md), dated audits, and
ADRs. Proposed work belongs in the [roadmap](roadmap.md).

## Repository and infrastructure

| Field | Verified value |
| --- | --- |
| Workstation / user | `dell5820` / `hui` |
| Source-of-truth repository | `/home/hui/projects/trading-intelligence-platform` |
| Branch | `main`; verify current HEAD and cleanliness with the report rather than freezing them here |
| Public site | `https://whalpha.com/` |
| OCI alias | `whalpha-oci` |
| Deployed OCI release | `2026-09-06T121300Z-ab1abf1afaaf` |
| Deployed source commit | `ab1abf1afaaf87648dfde24f2a584fcc32e360d8` |

Dell is the authority for code, data, development, and heavy computation. OCI
is only the static web-serving, localhost Auth Service, and public Session
boundary. Windows and future Mac systems are remote entry points, not data or
compute authorities. A later clean repository commit does not invalidate an
older immutable deployed bundle; compare both identities explicitly.

## Formal Dell data state

The network-free current-context reader uses report contract 1.6. Normal
recovery completed at validation level `active_custody_and_contracts` with
`completion_index_plus_latest_partition`; the explicit all-partition mode
also completed successfully during the ADR 0125 validation.

ADR 0149 separates current-clock operational freshness from immutable
publication evidence. The report evaluates canonical EOD and the active
Snapshot against XNYS at report time, while retaining the Snapshot's sealed
publication-time assertion as a third, explicitly named view.

| Boundary | Verified value |
| --- | --- |
| Canonical EOD | 304 contiguous XNYS sessions, 2025-06-23 through 2026-09-04 |
| Latest EOD | 2026-09-04; 9,962 rows |
| Latest EOD fingerprint | `3266c411a556ee1813a73beae19a71dc14e855b476770b3b82f81a5151e4abc4` |
| Latest EOD Parquet SHA-256 | `853d6fa9837891419f633aed8401a6ab52a503976d6607888c9def6de64b8577` |
| Latest Identity | 2026-09-04; 9,982 Instruments / 13,155 provider identities / 9,982 Resolvers |
| Latest Identity fingerprint | `5eed9166d609cea7693aed324908427f113ab72c221921690bcbdc29f71727f7` |
| Identity/EOD alignment | aligned on 2026-09-04 |
| Canonical historical Identity source | 302 immutable source-observation partitions / 3,700,330 rows; 2 source sessions absent |
| Canonical signal-eligible Membership | 2026-09-04; 19,964 decisions; eligible for 2026-09-08 open |
| `/data` inventory | 4,058 files / 2,009,024,076 bytes |
| `/data` inventory fingerprint | `d7ddbace6669c1870e86d79fd48aa86ff99d276699d23b84939983f950b236b4` |
| `/data` symlinks | zero |
| Publication staging/partial residue | zero |

The exact 300-session historical target through 2026-08-31 is complete. The
four following daily sessions, 2026-09-01 through 2026-09-04, are also
canonical. No historical-backfill transient service or computation process is
running.

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
| Dashboard Snapshot | `2026-09-06T121300Z-ab1abf1afaaf` |
| Snapshot pointer fingerprint | `de5beb3aa326660b806284848ec22ee1172aa0f92e64421a48a94556db7c8125` |
| Contracts | Snapshot 1.11 / Dashboard 2.8 |
| Freshness | operational and publication-sealed views expected 2026-09-04; actual 2026-09-04; lag zero; review mode false |
| Immediate local Snapshot rollback | `2026-09-04T113333Z-717cb82c5369` |

Market Regime is Balanced in both Universes: Primary 56.7472 and Secondary
57.3733. Market Intelligence contains 16 preregistered ETF relationships, 336
bounded relationship-history rows, 30 ETF observations, and 5/10/20-session
views. Candidate publication 1.1 exposes 880 Primary and 951 Secondary display
records. These are eligible bounded Candidate records, not Universe sizes.

The active analytics status remains `degraded_short_history`: the published MI
path currently consumes 26 sessions even though canonical EOD now contains 304.
The Quant Research Lab must therefore remain research-only/data-blocked until
historical analytics inputs and the missing point-in-time lifecycle,
membership, corporate-action, adjustment, and evaluation families are wired
and validated. Canonical price history alone is not backtest readiness.

### Historical research readiness

The 2026-09-07 contract-1.6 current-context run exposes family-specific
progress rather than treating all historical inputs as one missing block:

- the 252-session price-depth floor is satisfied by 304 contiguous EOD
  partitions;
- all 304 EOD dates have exact same-date completed Identity manifests;
- both families are canonical and acquired but have not been promoted through
  a formal Historical Coverage publication;
- provider corporate-action observations, canonical corporate actions, daily
  point-in-time membership, lifecycle, adjustment ledger, and Historical
  Coverage evidence/final roots are absent from `/data`;
- a real cost/liquidity model, complete availability/revision lineage, real
  chronological evaluation dataset, and sealed real holdout are also absent or
  fixture-only.

The report status is therefore `data_blocked`, with
`ready_for_strategy_development_review=false` and
`performance_claims_authorized=false`. Directory presence alone can never
change those results; future partitions remain unvalidated until the existing
transitive formal Coverage reader proves them.

ADR 0140 exposes the normalized source-observation layer separately from
resolved Identity snapshots. ADR 0150 adds direct daily binding and append-only
exact repair without altering the historical profile-map partitions. The
current typed read reports 302 partitions, 302 manifests, 302 Parquet files,
3,700,330 rows, 3,858 source-page artifacts, no source-only sessions, and only
the two provider-revised dates 2026-08-13 and 2026-08-19 as missing. Its state is
`canonical_partitions_observed_not_coverage_validated`; the explicit
incompleteness blocker remains and no readiness gate changes.

ADRs 0132–0143 record the complete-base Membership mechanics, exact package
census, versioned ETV compatibility, fingerprint-bound profile routing,
normalized source custody, atomic Apply/recovery, and source-gap attempt. Their
historical result is represented by the original 301 profile-bound partitions;
the directly bound 2026-09-04 daily partition is recorded separately by ADR
0150 and its dated audit. Intermediate counts and fingerprints remain there.

ADR 0144 makes the canonical normalized source the normal input to V3
Membership shadows while preserving the retained-package V2 path for
compatibility review. The 2026-09-03 V3 result contains 19,958 decisions over
9,979 stable IDs and is business-decision-identical to V2. A corrected timezone
runtime dependency reduced the measured single-day path to 59.53 seconds and a
five-session boundary to 135.53 seconds without changing output hashes.

The historical preflight found 300/303 source/evidence-eligible sessions. ADR 0145
then localized the 2026-08-31 gate failure: eight of ten unique collisions were
structurally identical Identity references already marked as exact provider
duplicates. Deduplicating only those identical references raises linkage to
0.999799337815 under the unchanged 0.999 gate; the two genuinely distinct
unresolved AREN/PAAI references remain collisions. The two historical revised-
source gaps remain 2026-08-13 and 2026-08-19. Routine 2026-09-04 normalized
source custody is now exact and directly bound; neither revised gap may be
approximated.

Combined disconnected V3 evidence now covers all 302 source-available dates
and 5,611,048 formally reread decisions. The new 2026-09-04 partition adds
19,964 decisions under the same V3 methodology and binds the direct daily
source fingerprint; it remains a separate owner-only temporary root. The
original 300-session root and its
600-file / 129,736,636-byte inventory fingerprint
`8afa4e188d006e5ac732447d0ca1042b6797b2af51bd3a3547a87a5167e886cf`
remain preserved as pre-correction evidence. A separate five-session corrected
boundary passed 5/5: three dates are business-decision-identical, 2026-09-03
changes only FAN from false-collision quarantine to explicit ETF exclusion in
both Universes, and 2026-08-31 adds 19,930 decisions. Every source cutoff is
after its represented session.

ADR 0151 now separates market-information and execution clocks. Formal
read-only assessment classifies the exact 9/4 partition as next-open
`signal_eligible` because its direct daily source and completed evaluation
precede the 9/8 XNYS open; assessment fingerprint is
`586cde811b9c26496584f56a89f489d6314dbc00e9ed7c112829238dfebdfedf`.
The corrected 9/3 historical partition is `outcome_reconciliation_only`, with
assessment fingerprint
`be8b100a0bf595d31032220d62325a909fe9488ef060b313a83d8813279463ce`.
The other historical-source sessions remain outcome-only by source policy.
Only the direct 9/4 result is now canonical Membership; it is not Historical
Coverage, a performance claim, or permission to fill 8/13 and 8/19.

ADR 0152 adds the next no-write boundary. The owner-only 9/4 plan binds the
exact two Membership files, the prospective logical completion marker, both
absent targets, and `/data` fingerprint
`a49348fc48219771d96ddc8bafed4fc3d5b32774ac61e45f102eef4fc0bb4f56`.
It proposes 3 files / 463,460 bytes; plan SHA-256 is
`67cf92606ddc5a314a30df304d568f93c7c051d09925d89b81f3b20a964833c8`
and logical fingerprint is
`57a59eaf9bfe0b44ba3cf2257e710a59c8f90b6a93b7c34d34dd064bf77c30c4`.
`apply_authorized=false` records that the plan was evidence rather than its own
authorization. Under the separate exact execution boundary in ADR 0153, the
physical partition and last marker were published and formally reread: 19,964
decisions, publication fingerprint
`3f71cd40edd2ed6d7e215a95e0cb89c08c7e96dcb9a8fb543a4de34286c15518`,
marker SHA-256
`1aabc12560a0e7d0ed058c7a82aaa842e983bfd06e04595f8b1d560d94a4af09`,
and post-state fingerprint
`d7ddbace6669c1870e86d79fd48aa86ff99d276699d23b84939983f950b236b4`.
The zero-write postflight reused both targets and wrote zero files/bytes. A real
9/3 attempt remains rejected before plan creation. Current-context report 1.6
now exposes exactly 1/304 canonical Membership sessions and will not count an
unmarked physical partition as canonical.

ADR 0154 now provides a repeatable, network-prohibited prospective candidate
entry point in the exact persistent daily workspace. It reuses canonical or
candidate completion, assesses next-open eligibility, rejects partial
canonical publication, and performs zero canonical writes. Its real 9/4
read-only replay returned the existing 19,964-row canonical publication and
unchanged assessment/publication fingerprints. It remains outside the serving
coordinator and scheduler until a new live-session observation passes.

The aggregate-only inactive lifecycle census for 2026-07-16 reached its hard
20-page / 20,000-result boundary with another page still present. All rows had
`active=false`; 19,565 exposed `delisted_utc`, but last tradable session,
terminal reason, successor identity, and point-in-time availability remain
unverified. No response rows were retained and no data was written. Active-page
disappearance therefore remains a review flag rather than a lifecycle fact.

ADR 0147 then completed the exact inactive source in resumable owner-only
temporary custody: 24 pages / 23,260 rows / 6,644,157 physical bytes, with
formal reread, zero symlinks, logical fingerprint
`5b298512378f80fc5e72eb90bf05b588feb91c1ea1caedd802c8d54ac8cee7fb`.
It contains 22,754 `delisted_utc` observations and 132 duplicate ticker values.
The package is not under `/data`, remains `outcome_reconciliation_only`, and
has no canonical lifecycle or Historical Coverage authority.

The latest-EOD `2026-09-03` anchor also completed naturally: 24 pages / 23,469
rows / 6,714,161 physical bytes, logical fingerprint
`8ae15be74aa8c554ab83075346f93c3d966cec72811d47375f53a91a8734ff98`.
Compared with 7/16 it has 262 added and 53 absent-or-revised exact source rows;
262 observations carry delisting dates inside 7/17–9/3. Only 1,631 of all
latest-anchor records, including 135 in that new window, have a selected stable
FIGI matching the 303-session canonical Instrument history. The remaining
records are unresolved, not ticker-joined.

ADR 0148 now materializes both anchors into a disconnected, one-to-one
source-observation and resolution-decision shadow. The 7/16 result uses only
268 canonical Instrument sessions through its anchor and classifies 471 of
23,260 rows as review candidates; the 9/3 result uses 303 sessions and
classifies 547 of 23,469. The remaining 22,789 and 22,922 rows are explicitly
quarantined. Of the 262 later-anchor additions, 76 are review candidates and
186 are quarantined; no shared exact source row changes disposition. These are
still review candidates rather than lifecycle facts, remain owner-only in
`/tmp`, and grant no Historical Coverage or performance authority.

## OCI production proof

The final independent remote inspector matched the exact Dell bundle:

| Evidence | Verified value |
| --- | --- |
| Bundle logical fingerprint | `385152eb5e145916e5641f2e65828f87948bb452cd633a093c9b84b65ae918cf` |
| Manifest SHA-256 | `2bac8520a9f66f8b6c13a904d87f9951da5e230ef68b2ee7ecb0e2bd23ec91e6` |
| Checksums file SHA-256 | `a649e751cf2ba357655b7c45086d900773cd95bd4521677a410d3adea7aa77da` |
| Remote-state fingerprint | `d25b6e24dd37580be5538af7567b805b25b65ee73f40473f0c714a7ce5ae8012` |
| Bundle files | 51; checksum validation passed |
| Locales | English default; English and Simplified Chinese supported |
| Access capability | guest and credential Sessions are identical |
| Sensitive/provider payload | no credentials, raw provider data, or Parquet |

Nginx and `whalpha-dashboard-auth.service` are active and enabled. The Auth
Service listens only on `127.0.0.1:8010`. Public entry, favicon, compatibility
redirect, protected routes, invalid-login handling, temporary guest Session,
Dashboard, Snapshot, Candidate summary/detail, Strategy Channels, Sector ETF
Rotation, logout, and renewed protection all passed postflight. There is no
staging or failed-release residue. Password-based login and final visual
inspection remain manual user checks.

The final 9/4 postflight reported zero failed system units. Deployment records
the preflight baseline and rejects a newly failed unit while separately
requiring Nginx and WH Alpha Auth health. No staging or failed-release residue
remains.

## Current product boundary

WH Alpha is a Session-protected, bilingual U.S. equity market-intelligence and
research platform for discretionary decisions. The product chain is:

```text
market state -> strength direction -> sector/theme -> stock candidate
-> trade preparation -> entry/invalidation -> position management
```

Live first-level workspaces include Market Regime & Opportunities
(`市场风向与机会`), Market Structure & Activity, Sector ETF Rotation, Stock
Candidates (`个股候选`), and the explicitly research-only Quant Research Lab
(`量化研究实验室`). The landing page and in-app shell share the dark navy/cyan
WH identity and favicon. Planned capabilities are labeled as planned, not live.

Stock Candidates provide explainable evidence rather than a black-box verdict:
seven component contributions reconcile to the unchanged base score; strategy
channels are not compared by one cross-strategy score; leadership, entry
position, risk, evidence, counterevidence, invalidation, parameters, raw facts,
and lineage remain inspectable. Candidate stock outcomes are never represented
as option returns.

Guest and credential Sessions must remain identical in data, features,
language, Universe, and analysis until the user explicitly changes that policy.
The project is personal/friends use, but engineering, data governance,
validation, security, and research standards should be commercial-grade.

## Product and research guardrails

- Decision support, not automated trading or order execution.
- Human investment meaning first; algorithm labels second.
- Show conclusion, source values, parameters, contributions, supporting and
  contrary evidence, market adjustment, and invalidation conditions.
- Never call price/volume proxies actual fund flow.
- Never call underlying-stock forward return an option return.
- Keep security form, issuer structure, listing scope, evidence, and Universe
  disposition separate and effective-dated by stable `instrument_id`.
- Quarantine unknown, ambiguous, malformed, heuristic-only, and insufficient-
  evidence records.
- Prevent look-ahead, survivorship, revision, selection, and leakage bias.
- Keep research, validation, shadow, and Production stages explicit. Models and
  parameters may be personal/proprietary, but their risk and validation status
  must be visible.

Priority strategy families are Momentum Breakout, Strong-Leader Pullback,
Trend Continuation, Oversold Technical Reversal, and Fundamental Value
Reversal. Defensive/anti-market context is a regime-conditioned opportunity
layer. Earnings, macro, and news are mainly risk/context inputs rather than a
claim of first-information advantage. Option expression is a separate later
layer covering long Calls/Puts, debit spreads, covered calls, moneyness and DTE;
naked short-option strategies are outside the intended scope.

## Automation and runtime state

The installed `whalpha-daily-eod-wake-review.timer` is active/waiting; its
service is inactive between wakes. It is read-only and credential-free. It does
not fetch, apply, calculate, publish, deploy, retry, or send alerts. No
unattended data-transition scheduler is installed.

Routine daily Identity/EOD fetch, guarded canonical Apply, existing analytics,
standard MI publication, Snapshot, bundle, and OCI deployment may proceed
without a separate chat confirmation at every stage under the user's standing
workflow direction. Every date, fingerprint, quality, freshness, custody,
clean-source, CAS, residue, and postflight gate remains mandatory. A failed
gate stops the chain and requires diagnosis; it does not broaden authority.

SMTP code exists but no provider, sender, recipient, or credential is
configured; no email can currently be sent. SEC access, new providers/endpoints,
credential inspection/change, model or Universe rule changes, rollback,
scheduler mutation, orders, and materially new data/product scope remain
separately bounded.

## Immediate risks and next work

1. **Daily-chain performance:** the complete 9/4 chain has now passed with
   ADRs 0125–0129 active. Candidate remained the largest analytics stage at
   roughly 4.5 minutes; the other offline stages and publication plans were
   bounded below it. ADR 0125 removed full-history reconstruction
   from date-only control paths. ADR 0126 reuses the same exact formal panel
   and finalized current Candidate evidence in downstream Entry/ETF stages. On
   unchanged 9/3 inputs, Entry completed in 49.67 seconds and ETF in 15.36
   seconds with byte-identical business artifacts and unchanged zero-mismatch
   Oracles. ADR 0127 similarly reduced Strategy Channels to 33.82 seconds.
   ADR 0128 reduced daily Candidate completion from 521.21 to 294.99 seconds
   while keeping all ten business files byte-identical; a separate 228.285-
   second full semantic reread passed with the same fingerprint and zero
   Oracle mismatches. Visual Context was measured at 51.11 seconds and left
   unchanged. Follow-up profiling assigned 193.525 seconds to the cumulative
   audit writer, including 88.528 seconds across overlapping fingerprint calls;
   finalization was only 1.739 seconds and garbage collection 0.061 seconds.
   Current-code MI candidate plus plan is bounded at 53.84 seconds. ADR 0129
   reduced Snapshot candidate plus plan from 135.00 to 121.57 seconds by
   deriving rollback and CAS from one formal active observation; all 42 output
   files and all non-path plan bindings matched exactly, while Apply retains a
   fresh CAS read. ADR 0130 then proved a disconnected ten-session Candidate
   shadow: all eight V1 business projections reconstructed exactly, and its
   current-checkpoint reader took 16.53 seconds versus 228.285 seconds for V1
   full semantics. V1 remains authoritative until append-input, recovery,
   periodic cold comparison, and downstream compatibility pass. The current
   checkpoint reproduces all 1,718/1,831 prior-state support rows exactly; only
   the cumulative V1 history fingerprint needs an explicitly versioned chain
   identity. ADR 0155 now supplies a distinct forward hash chain and explicitly
   does not relabel it as V1 evidence. ADR 0156 extends the real ten-session
   parent through 9/4 with one immutable 86,610,428-byte segment, unchanged
   parent bytes, recoverable atomic delivery, and independent zero-mismatch
   cold equivalence. Its two 8.5-minute / 13.1-GiB passes deliberately reread
   complete V1 and are not a hot-path performance result. ADR 0157 now emits
   the same current session directly from the already validated calculation
   objects: the final write took 38.907 seconds, produced an 86,608,577-byte
   payload, matched all eight cold-append projections, and passed a separate
   32.831-second semantic read. It remains an optional `/tmp`-only candidate;
   V1, the executor, coordinator, scheduler, publication, and Production are
   unchanged. ADR 0158 now verifies the exact completed intended V1 artifact
   set and incremental ledger, then copies the same direct bytes into a
   versioned 1.1 successor append in 36.70 seconds without cumulative semantic
   replay. Its separate reader took 40.36 seconds, and a cold 1.0/1.1 comparison
   found all eight current fields exact. The chain tips intentionally differ
   because 1.1 names session-local rather than V1-global raw-fact ordinals.
   ADR 0159 now proves two ordered 1.1 generations with an explicit base-plus-
   append parent reader; append-2 binds append-1's exact manifest and chain tip,
   while missing or reordered lineage fails closed. That cold reader validates
   every append and remains linear; its real one-append read took 39.79 seconds
   and reproduced the exact 11-session ADR 0158 head. ADR 0160 now proves a
   4,962-byte expected-identity chain head: incremental advancement and full
   cold construction produced identical bytes, the head read took 1.08 seconds,
   and real composer time fell from 36.70 to 21.18 seconds with byte-identical
   output. No governed canonical head pointer exists yet. Next define its
   immutable publication, CAS/recovery/rollback, retention, and periodic full-
   lineage audit before CLI, executor, downstream, or cutover work.
2. **Historical Universe foundation:** 302 exact source partitions are now
   canonical after historical append-only and direct-daily Apply/recovery.
   Disconnected Membership mechanics also cover all 302 available dates. The
   timing gate admits only the direct 9/4 result for next-open use and keeps the
   historical-source sessions outcome-only. The inventory-bound 9/4 canonical
   Membership and its final marker are now published, independently read, and
   zero-write postflight verified. ADR 0154 now provides a governed,
   network-prohibited daily candidate preparation boundary in persistent
   session custody. Next observe it on a new session, create the inventory-bound
   plan only near Apply, and then review coordinator integration. Keep 8/13 and
   8/19 unbound and never approximate an absent session.
3. **Historical analytics consumption:** connect the 304-session canonical
   foundation to research/analytics through point-in-time governed inputs;
   reconcile the current 26-session MI history and research-readiness display.
4. **Research foundation:** the disconnected inactive lifecycle normalization
   and stable-identity resolution shadow is complete for both anchors. Next
   design corroboration and source-availability evidence for the 547 latest
   review candidates without promoting them by ticker or provider status
   alone. Then complete canonical lifecycle, actions, adjustments, costs, and
   sealed chronological evaluation before interpreting strategy performance.
5. **Strategy research:** validate one preregistered strategy family at a time,
   beginning with Strong-Leader Pullback; compare against same-opportunity-set
   controls and preserve holdout discipline.
6. **Product visualization:** add only decision-answering charts for price path,
   entry position, threshold distance, signal age, contribution, regime-to-
   sector-to-stock linkage, persistence, and invalidation.
7. **Later data/product layers:** options expression, fundamentals/valuation,
   point-in-time event analysis, then portfolio/IBKR integration.

Do not start new formulas, thresholds, paid-data acquisition, or UI scope merely
because the data catch-up and deployment are complete. First establish the
performance profile and the governed research dataset contract.

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
   repository. It uses the completion index and fully validates the latest EOD
   partition plus current artifacts. Use `--full-history-validation` only for a
   periodic or investigative all-partition audit.
3. Compare repository, EOD, Identity, Activation, MI, Snapshot, inventory, and
   residue with this baseline.
4. If deployment state matters, run the non-secret OCI inspector separately;
   the local context report is intentionally network-free.
5. Classify differences before mutation. Never silently rewrite an active
   pointer, rerun acquisition, deploy, or clean a remote release.
6. Read only the architecture, operations, ADR, and audit documents relevant to
   the selected single objective.
