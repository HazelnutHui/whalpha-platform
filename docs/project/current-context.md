# Authoritative Current Context

Operational state verified at: 2026-09-04T09:20:37Z

Repository context updated at: 2026-09-04 UTC

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
| Deployed OCI release | `2026-09-03T090150Z-a4f10a02b6ae` |
| Deployed source commit | `a4f10a02b6ae8bc5dea64fda7ea90267cfca305b` |

Dell is the authority for code, data, development, and heavy computation. OCI
is only the static web-serving, localhost Auth Service, and public Session
boundary. Windows and future Mac systems are remote entry points, not data or
compute authorities. A later clean repository commit does not invalidate an
older immutable deployed bundle; compare both identities explicitly.

## Formal Dell data state

The network-free current-context reader uses report contract 1.2. Normal
recovery completed at validation level `active_custody_and_contracts` with
`completion_index_plus_latest_partition`; the explicit all-303-partition mode
also completed successfully during the ADR 0125 validation.

| Boundary | Verified value |
| --- | --- |
| Canonical EOD | 303 contiguous XNYS sessions, 2025-06-23 through 2026-09-03 |
| Latest EOD | 2026-09-03; 9,956 rows |
| Latest EOD fingerprint | `9eb9c445d8032c151af009d7dc342d70ad567b473d9a51f8f72b2c80e7436e69` |
| Latest EOD Parquet SHA-256 | `ead984bbb60478c5d2bbe388f9886ebf764458b6d0e03bf2c2e8108544fc0bbd` |
| Latest Identity | 2026-09-03; 9,979 Instruments / 13,153 provider identities / 9,979 Resolvers |
| Latest Identity fingerprint | `5c8e377e22ef15b6a5dfd91a9548327d148e26a47c002690117dcd009d966855` |
| Identity/EOD alignment | aligned on 2026-09-03 |
| `/data` inventory | 3,356 files / 1,597,544,378 bytes |
| `/data` inventory fingerprint | `2928d804ea48cf076b0a589d09b0e150cf07810dc4dd0cef503121d53d95d794` |
| `/data` symlinks | zero |
| Publication staging/partial residue | zero |

The exact 300-session historical target through 2026-08-31 is complete. The
three following daily sessions, 2026-09-01 through 2026-09-03, are also
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
| Market Intelligence | `2026-09-03T070700Z-f506e025475e`; contract 1.3 |
| MI payload SHA-256 | `fbb0309e02d2798b558f05720d3eeb4c3f92060b0455b590feaee45d494a00e7` |
| MI logical fingerprint | `8db1d95b97bad6d34ebd3dad9a102a26907f2294bede33025fcf9b114945de74` |
| Dashboard Snapshot | `2026-09-03T090150Z-a4f10a02b6ae` |
| Snapshot pointer fingerprint | `e8548194c8b16e73f793507fb23927e2789fcbf2f7cccb1a6e09913c738a33f9` |
| Contracts | Snapshot 1.11 / Dashboard 2.8 |
| Freshness | expected 2026-09-03; actual 2026-09-03; lag zero; review mode false |
| Immediate local Snapshot rollback | `2026-09-03T083901Z-f506e025475e` |

Market Regime is Balanced in both Universes: Primary 59.7744 and Secondary
60.5223. Market Intelligence contains 16 preregistered ETF relationships, 336
bounded relationship-history rows, 30 ETF observations, and 5/10/20-session
views. Candidate publication 1.1 exposes 857 Primary and 928 Secondary display
records. These are eligible bounded Candidate records, not Universe sizes.

The active analytics status remains `degraded_short_history`: the published MI
path currently consumes 26 sessions even though canonical EOD now contains 303.
The Quant Research Lab must therefore remain research-only/data-blocked until
historical analytics inputs and the missing point-in-time lifecycle,
membership, corporate-action, adjustment, and evaluation families are wired
and validated. Canonical price history alone is not backtest readiness.

## OCI production proof

The final independent remote inspector matched the exact Dell bundle:

| Evidence | Verified value |
| --- | --- |
| Bundle logical fingerprint | `b4d7ab72481d07d5b8add31669c558ea6459794346fea3954906b4ef056f5c61` |
| Manifest SHA-256 | `953f56f1a98da84fc661ea2303da8714a6d145c0e54cfc6b918bfb6e36831d51` |
| Checksums file SHA-256 | `82a086ac395cb552e327f38490b2069b684c53a408b65ecebdc2f770f5244629` |
| Remote-state fingerprint | `70753f36342d441767c0c262625c6f65c329498bb8f7e9ffef38067f5399d3db` |
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

OCI has one pre-existing unrelated failed unit, `fwupd-refresh.service`. It was
not changed. Deployment now records the failed-unit baseline and rejects only a
new failed unit while separately requiring Nginx and WH Alpha Auth health. The
first 9/3 deployment attempt exposed the prior inconsistent global-zero gate,
rolled back to the 9/1 release, and left one marked failed release; that exact
non-current residue was verified and deleted before the successful deployment.

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

1. **Daily-chain performance:** ADR 0125 removed full-history reconstruction
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
   identity. Measure the next complete daily chain and add reuse,
   vectorization, or safe process parallelism only where evidence justifies it
   and outputs remain exact.
2. **Historical analytics consumption:** connect the 303-session canonical
   foundation to research/analytics through point-in-time governed inputs;
   reconcile the current 26-session MI history and research-readiness display.
3. **Research foundation:** complete lifecycle/terminal, membership, actions,
   adjustments, costs, and sealed chronological evaluation before interpreting
   strategy performance.
4. **Strategy research:** validate one preregistered strategy family at a time,
   beginning with Strong-Leader Pullback; compare against same-opportunity-set
   controls and preserve holdout discipline.
5. **Product visualization:** add only decision-answering charts for price path,
   entry position, threshold distance, signal age, contribution, regime-to-
   sector-to-stock linkage, persistence, and invalidation.
6. **Later data/product layers:** options expression, fundamentals/valuation,
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
