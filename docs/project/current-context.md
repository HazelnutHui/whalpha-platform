# Authoritative Current Context

Operational state verified at: 2026-09-08T17:24:54Z

Repository context updated at: 2026-09-08 UTC

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
| Deployed OCI release | `2026-09-08T171914Z-ca2d34d50692` |
| Deployed source commit | `ca2d34d506922f75699c376391dd6a9191ef0ae9` |

Dell is the authority for code, data, development, and heavy computation. OCI
is only the static web-serving, localhost Auth Service, and public Session
boundary. Windows and future Mac systems are remote entry points, not data or
compute authorities. A later clean repository commit does not invalidate an
older immutable deployed bundle; compare both identities explicitly.

## Formal Dell data state

The network-free current-context reader uses report contract 1.6. The final
post-deployment report completed at validation level `active_sources_reread`
with `completion_index_plus_latest_partition`; the explicit all-partition mode
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
| Canonical EOD/Identity family evidence | 2 immutable manifests; final Historical Coverage absent |
| `/data` inventory | 4,186 files / 2,143,226,489 bytes |
| `/data` inventory fingerprint | `3f4a5780a69a8d60688ce34b64f8df06fc0dd12070801f265b46f3f7a1f6ac49` |
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
| Dashboard Snapshot | `2026-09-08T171914Z-ca2d34d50692` |
| Snapshot pointer fingerprint | `c1469a1dbde97fc5212b57d039e60b585be5ba0488ae4626c2e0d393fe387ea5` |
| Contracts | Snapshot 1.11 / Dashboard 2.8 |
| Freshness | operational and publication-sealed views expected 2026-09-04; actual 2026-09-04; lag zero; review mode false |
| Immediate local Snapshot rollback | `2026-09-08T171250Z-8c3dc878d6ab` |

Market Regime is Balanced in both Universes: Primary 56.7472 and Secondary
57.3733. Market Intelligence contains 16 preregistered ETF relationships, 336
bounded relationship-history rows, 30 ETF observations, and 5/10/20-session
views. Candidate publication 1.1 exposes 880 Primary and 951 Secondary display
records. These are eligible bounded Candidate records, not Universe sizes.

The Strategy Channels browser now separates the unchanged channel-local
research priority from trade-review readiness derived from the linked
same-Snapshot Candidate facts. It visibly flags all-risk-mode rejection,
non-reviewable/no-bounded entry structure, gap/realized-volatility review,
moderate-or-higher extension, and stable-ID cross-channel repetition. The
display diagnostic is not formal sector concentration: the technical channels
share price/volume, relative-strength, and trend inputs, and point-in-time
sector taxonomy remains absent. Event timing remains an explicit manual check.
No score, status, rank, threshold, analytics contract, or guest/credential
capability changed.

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
- both families are canonical and acquired, and now have immutable transitive
  family-evidence manifests, but no final Historical Coverage publication;
- provider corporate-action observations, canonical corporate actions, daily
  point-in-time membership, lifecycle, adjustment ledger, and final Historical
  Coverage remain absent or incomplete in `/data`;
- a real cost/liquidity model, complete availability/revision lineage, real
  chronological evaluation dataset, and sealed real holdout are also absent or
  fixture-only.

The report status is therefore `data_blocked`, with
`ready_for_strategy_development_review=false` and
`performance_claims_authorized=false`. Directory presence alone can never
change those results; future partitions remain unvalidated until the existing
transitive formal Coverage reader proves them.

The separate ADR 0100 full-content mechanics adapter was rerun against all 304
canonical sessions on 2026-09-08. It returned `mechanics_only`, zero missing
sessions, zero requests, and zero writes. EOD evidence is
`validated_not_published` over 304 artifacts / 2,816,903 rows with logical
fingerprint
`923f27a8fa4e85c6d20b5c8ac0804f17dbab7437b350f02d54fea2ed5293aeb1`
and proposed evidence SHA-256
`ba652cb4ed21a0bfce1ce0cbd690c933cb8ae98de3f39231e282ea8f22789593`;
point-in-time Identity evidence is `validated_not_published` over 304 artifacts
/ 2,825,403 canonical Instrument rows with logical fingerprint
`d2225da8d4ffd2b7e83ff98b72f75647503690a2aff2c87731c00b115b65fefb`
and proposed evidence SHA-256
`5046dd6b3b1f8dd028528636a9caf989bcbb53040082ca0060016b07a49d67a2`.
The report fingerprint is
`85ea7384c8ff546fcbd2506d1f86c6ae16add458044248cbb1e8971af1f3497f`.
This is a GO only for later separate family-evidence publication review. No
evidence was published, and the five blockers remain daily historical
Membership, canonical corporate actions, lifecycle, adjustment reconciliation,
and final Historical Coverage publication.

ADR 0165 now turns those same two validated objects into one deterministic,
owner-read-only `/tmp` publication plan. It binds exactly two absent immutable
targets and 675,569 proposed bytes; plan logical fingerprint is
`6ae6738181012b6f9364d5b624d7edaa81d992b7be623e6bd6b58c2854d5e663`
and plan SHA-256 is
`dced91a98cf4a71fe28748c241f83aa31dcdb588a9f322245a9b14de6d4511ae`.
An independent exact-SHA reread revalidated every source byte and both absent
targets. At that planning checkpoint, the context report kept `/data` at 4,058
files / 2,009,024,076 bytes with inventory fingerprint
`d7ddbace6669c1870e86d79fd48aa86ff99d276699d23b84939983f950b236b4`
and zero publication residue. The plan itself granted no Apply, research,
performance, deployment, or final Coverage authority.

ADR 0166 supplies the separately bounded executor and recovery mechanics.
It uses the shared canonical-data lock, requires the exact plan SHA, logical
fingerprint, family-set fingerprint, and Dell root, publishes EOD before
Identity as two atomic one-file directories, and accepts recovery only from an
exact ordered prefix. Disconnected fault injection proves interruption and
zero-write recovery, corruption/order/staging refusal, outside-target drift
detection, and network prohibition. The separately reviewed real Apply then
published both exact manifests / 675,569 bytes; its completed-state postflight
reused both targets and wrote zero files/bytes. `/data` now has the inventory
shown above with zero residue. Final `historical-coverage` remains absent, and
the formal status remains `data_blocked`.

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

ADR 0167 now converts the complete latest-anchor review subset into one exact
corroboration work plan without promoting it. The owner-read-only plan contains
547 unique source-occurrence / canonical-instrument work items: 271 XNAS rows
route only to a required Nasdaq Daily List pilot, while 276 ARCX/BATS/XASE/XNYS
rows remain blocked on all-exchange source selection. Every row still requires
effective-date, last-tradable-session, terminal-classification,
successor/consideration-applicability, and source-availability evidence. All
remain `first_observed_only`; the provider last-updated field is not treated as
historical availability and point-in-time eligible count is zero. The plan is
temporary, made no request or `/data` write, and grants no canonical lifecycle
or research authority.

ADR 0168 now closes the public-document source review without pretending that
documentation is a payload. A cross-venue corporate-action/trading-status
sample is the preferred first external input, with LSEG first in the inquiry
order and Nasdaq/NYSE/Cboe retained as official exchange benchmarks. The fixed
diagnostic selects 30 earliest/latest candidates across all 15 non-empty
exchange/year/observation-gap strata: six per exchange, ten from 2025, and
twenty from 2026. No source is selected or accessed, and no adapter exists.
The next lifecycle transition requires the user to review an exact
price/sample/permission offer; only a provisioned sample can define the real
request ceiling and test stable-ID, revision, knowledge-time, last-tradable,
terminal, successor, consideration, and usage-permission gates.

ADR 0169 separately implements a resumable Massive V1 source-custody boundary
for split and dividend observations over one exact historical range. The two
package kinds share one implementation but remain independently recoverable
and formally readable below `/tmp`. The boundary preserves source fields,
measures schema additions and malformed dates, and performs no identity
resolution, `/data` write, canonical Corporate Action, Adjustment Ledger,
analytics, publication, deployment, or scheduler change. The first real range,
2025-06-23 through 2026-09-04, has now completed: 1,949 split rows in one page
and 68,150 dividend rows in 14 pages. Both had zero invalid/out-of-range dates,
duplicate provider IDs, or unexpected fields, and passed a separate formal
reread. These `/tmp` packages prove current technical access and source
custody—not stable identity, canonical events, revision history, provider
availability time, adjustment reconciliation, or Historical Coverage.

ADR 0170 has completed the next disconnected step without weakening those
limits. The real owner-only `/tmp` Parquet shadow binds both source packages
and all 304 used exact-date Resolvers to the published point-in-time Identity
family evidence. It preserves all 70,099 source rows: 42,056 resolve to a
stable ID and 28,043 remain quarantined, including 39 rows on dates without an
exact Identity session. Latest/nearest/name/Universe fallback counts remain
zero. The local observation revision `1` and
`outcome_reconciliation_only` status grant no canonical action, adjustment,
Coverage, or research authority. The shadow manifest SHA-256 is
`547218cf639bf4e06daa216868bd669cd73e4b69a55f7da4fad072077ffcacb8`.

ADR 0171's first real repeat observation and both disconnected diffs have now
completed. All 1,949 split and 68,150 dividend provider IDs and payloads were
unchanged over the approximately 69–73 minute observation intervals; changed,
added, removed, effective-date, ticker, and pagination-shape deltas were all
zero. Both source packages and diff outputs passed formal reread. This proves
only short-interval stability, not historical immutability, provider revision
numbers, or point-in-time availability. Future changes must remain append-only
observed deltas until separately interpreted.

ADR 0172 records the completed adjustment-semantics review. A 2026-09-04-basis
split factor must be derived from resolved event ratios and dates; the
provider's cumulative current-basis factor is audit evidence only. The 709
resolved split rows form 708 stable-ID/date groups. Forty-one unresolved rows
have some historical ticker presence and expose 43 stable IDs to conservative
non-clear treatment; only two are in the active Universes. Dividend total
return remains deferred because 160 CAD rows, 34 USD split-cash mismatches, 145
multi-event groups, and 13 same-date split/dividend groups require separate
semantics.

The first ADR 0172 owner-only candidate has now completed on Dell main
`2e4e1f21f09c357180f3ac6f67ef82f709ed6b32`. It contains 708 resolved
stable-ID/date event groups, preserves the one multiple-action date through
pre-quantization ratio composition, and lists 43 possible-impact stable IDs
without assigning any unresolved event. Its 564,826-byte file SHA-256 is
`83e8a3722132bd2172e0546e3d8fb84a5a5cece6e289a2b1c3744e1e8d175618`;
logical fingerprint is
`b3efa16da5570cddf41f7fc741d71a29e73e6a1f696f68828b2f5e67b596d226`.
Total return remains unavailable and ledger projection remains not built.

## OCI production proof

The final independent remote inspector matched the exact Dell bundle:

| Evidence | Verified value |
| --- | --- |
| Bundle logical fingerprint | `09d3afc53612e296bde062220a51fdb2437d5136f8da6bf3eab01560ab8117ce` |
| Manifest SHA-256 | `94ca6bbd585a982a518572e4b4c856074da2a3f7973bd0c388d08288d19a1684` |
| Checksums file SHA-256 | `a27698cd7407e793da9699ec9695b7b22e8528619c41717e74ef02567dcc8173` |
| Remote-state fingerprint | `3ea4e2e58d2bf3b6f93c8b1a39907440b761a4254ed8506b82ffa965424edeb6` |
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

The final 9/8 postflight reported zero failed system units. Deployment records
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

Strategy Channels now opens with a cross-channel decision desk containing only
the first published record from each available channel in fixed channel order.
Each card retains its own channel rank, score, stage, extension risk, supporting
reason, and rejection risk. Opening it joins by stable `instrument_id` to the
same-Snapshot Candidate detail and fails closed on any missing or mismatched
identity; no cross-channel score, preferred strategy, or return inference is
created. The Quant Research Lab now shows family-specific readiness gates: the
304-session price-length floor is met, while Membership, corporate actions,
lifecycle, costs, and sealed evaluation remain visibly incomplete or locked.

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
   full semantics. Append-input, recovery, periodic cold comparison, and
   bounded downstream compatibility were then evaluated through ADR 0164; V1
   remains authoritative because the resulting cutover decision is NO-GO. The
   current checkpoint reproduces all 1,718/1,831 prior-state support rows
   exactly; only the cumulative V1 history fingerprint needs an explicitly
   versioned chain identity. ADR 0155 now supplies a distinct forward hash chain
   and explicitly does not relabel it as V1 evidence. ADR 0156 extends the real
   ten-session parent through 9/4 with one immutable 86,610,428-byte segment, unchanged
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
   output. ADR 0161 now adds a no-write immutable-release/current-pointer plan
   with bounded-family CAS, exact one-successor enforcement, prior-active
   rollback reference, fail-closed recovery states, and retain-all immutable
   heads. Its real 9/4 bootstrap proof used only `/tmp` and proposed 4,962 +
   1,712 bytes. ADR 0162 now proves the exact plan's release-first/pointer-last
   Apply, release-only interruption recovery, staging-residue refusal, and
   zero-write completed postflight in disconnected simulation. The retained
   real plan wrote 6,674 bytes only to its `/tmp` root; post-family fingerprint
   is `ab5ccd10017c7f14087c50f455a3212d3278e55d2efef1e8b7a4c2da92f30dac`
   and pointer-state fingerprint is
   `02dfb715872bec8cb11c1b51f7791b95fe24ede244f1d7d28da9f12dcab9a476`.
   The executor refuses the Production root by code. No `/data` canonical
   pointer exists. ADR 0163 now cold-audits the retained base plus every
   ordered append against that exact simulated active head, binds the current
   state before and after the replay, and returns zero mismatches and writes.
   The real run took 39.79 seconds / 2,079,080 KiB peak RSS; its audit logical
   fingerprint is
   `8adc21deec2bda549f1bb142e482376d6c07183c997050fb008689affb761ca3`.
   It defines daily, periodic, and code-change validation levels but adds no
   CLI, executor, journal, scheduler, or Production authority. ADR 0164 now
   closes the downstream-compatibility gate without authorizing cutover. The
   real 9/4 current consumer returned two ordered Universe batches and 3,549
   state rows; exact V1 comparison had zero mismatches, and Entry plus Strategy
   recalculation matched all four retained batch fingerprints with zero Oracle
   mismatches. The current segmented read still took 43.43 seconds because it
   rehashes the roughly 840 MB base, and Visual Context still requires
   cumulative state history absent from the current append. Entry/Strategy
   correctness is therefore GO, but whole-V1 replacement and CLI/executor
   exposure are NO-GO. Further segmented work should resume only under one
   bounded design for expected-head payload resolution and Visual state input.
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
4. **Research foundation:** ADRs 0165–0166 have completed the exact plan,
   canonical two-file Apply, and zero-write postflight for the 304-session EOD
   and point-in-time Identity evidence. Final Historical Coverage remains
   absent and research remains data-blocked. The disconnected inactive
   lifecycle normalization and stable-identity resolution shadow is complete
   for both anchors. ADR 0167 provides the exact 547-item work queue. ADR 0168
   completes public source review and requires a real licensed cross-venue
   sample plus the deterministic 30-item diagnostic before lifecycle adapter
   work. ADR 0169 independently provides the no-canonical-write Massive V1
   split/dividend source boundary, and both exact real packages have completed
   and passed formal reread. ADR 0170's real event-date stable-ID mapping shadow
   has also passed formal reread. ADR 0171's later identical-scope observation
   and two zero-delta diffs have completed. ADR 0172 has completed the semantic
   and cross-event readiness review and narrows the next implementation to an
   owner-only split-adjustment candidate. That candidate has now completed and
   passed formal reread. Next design the canonical split-action candidate and
   bounded ledger projection without promoting unresolved rows; keep dividend
   total return unavailable.
   Request exact price/sample/permission terms from the user before any vendor
   contact, trial, purchase, or access; do not promote candidates by ticker or
   provider status alone.
   Then complete canonical lifecycle, actions, adjustments, costs, and
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
