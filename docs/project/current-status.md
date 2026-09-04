# Current Status

Status date: 2026-09-04

This is the concise project-state summary. Exact IDs, fingerprints, evidence
scope, authorization boundaries, and cross-device recovery are maintained in
the [authoritative current context](current-context.md). Historical execution
detail belongs in the [changelog](changelog.md), ADRs, and dated audits.

## Production

WH Alpha is live as a Session-protected bilingual U.S. equity market-
intelligence and research platform. The current OCI release is
`2026-09-03T090150Z-a4f10a02b6ae`, built from clean main commit
`a4f10a02b6ae8bc5dea64fda7ea90267cfca305b`.

The deployed product uses:

- Market Intelligence 1.3 for analysis session 2026-09-03;
- Snapshot 1.11 / Dashboard 2.8, fresh with zero session lag;
- English as the first-visit default and Simplified Chinese as an equal view;
- identical data and capability for guest and credential Sessions;
- a public data-free WH landing page and favicon;
- fail-closed private Snapshot/API behavior with no synthetic Production data.

Nginx and the localhost-only Auth Service are healthy. Independent postflight
matched the local and remote manifest/checksum identities and verified public
entry, favicon, protected routes, guest entry, Dashboard, Candidate
summary/detail, Strategy Channels, Sector ETF Rotation, logout, and renewed
protection. No staging or failed-release residue remains. Password login and
final visual appearance remain manual checks.

OCI has one unrelated pre-existing failed `fwupd-refresh.service`. The
deployer now rejects newly failed units while separately requiring Nginx/Auth
health; it does not alter unrelated services.

## Data

- Canonical EOD contains 303 contiguous XNYS sessions from 2025-06-23 through
  2026-09-03. The original 300-session historical target is complete.
- Latest EOD has 9,956 rows and is aligned to the 2026-09-03 Identity snapshot.
- Latest Identity contains 9,979 Instruments, 13,153 provider identities, and
  9,979 Resolvers.
- `/data` contains 3,356 files / 1,597,544,378 bytes, with zero symlinks and
  zero publication residue.
- Active Primary is 1,718 CS. Secondary is 1,831 = 1,718 CS + 113 ADRC.
- The active provider-form Activation remains provisional and does not prove
  issuer structure or domicile.
- No historical backfill process or transient service remains active.

## Product

The decision chain remains:

```text
market state -> strength direction -> sector/theme -> stock candidate
-> trade preparation -> entry/invalidation -> position management
```

Live first-level workspaces cover Market Regime & Opportunities
(`市场风向与机会`), Market Structure & Activity, Sector ETF Rotation, Stock
Candidates (`个股候选`), and the explicitly research-only Quant Research Lab
(`量化研究实验室`).

The Market Regime is Balanced in both active Universes. The product includes 16
preregistered ETF relationships and 5/10/20-session relationship/rotation
views. Stock Candidate explanations expose component contributions, evidence,
counterevidence, entry position, risk, invalidation, parameters, raw facts, and
lineage. Strategy-channel ranks are meaningful within a channel and must not be
treated as one comparable cross-strategy score.

The interface supports discretionary decisions. It does not place orders,
claim price/volume proxies are fund flow, or represent underlying-stock forward
returns as option returns.

## Research readiness

Historical price acquisition is complete, but professional research readiness
is not. Active Market Intelligence still reports
`degraded_short_history` and consumes 26 sessions. Lifecycle/terminal,
point-in-time membership, corporate actions, adjustments, costs, and sealed
evaluation datasets are not yet fully wired.

The Quant Research Lab therefore remains data-blocked/research-only. It must not
show synthetic performance or promote a method based only on the new canonical
price history. The first intended registered study remains Strong-Leader
Pullback, followed by Momentum Breakout, Trend Continuation, Oversold Technical
Reversal, and Fundamental Value Reversal.

## Automation

The installed `whalpha-daily-eod-wake-review.timer` is active/waiting and
read-only. It performs no fetch, Apply, calculation, publication, deployment,
alert delivery, or credential access. No unattended write-capable daily chain
is installed. SMTP delivery is unconfigured.

The manual/agent-run guarded chain now works end to end:

```text
Identity -> EOD -> Phase 1a -> Phase 1b -> Candidate -> Entry Geometry
-> ETF Relationships -> Market Preview -> Strategy Channels
-> Candidate Visual Context -> MI Plan/Apply -> Snapshot Plan/Apply
-> serving bundle -> OCI deploy/postflight
```

The 9/1-9/3 catch-up proved correctness but also showed material performance
debt. Several stages and repeated review readers are CPU-heavy and mainly
single-core. MI Apply alone took more than ten minutes; context reporting still
rescans all history and takes several minutes.

## Next priority

1. Profile the complete daily chain on Dell.
2. Remove repeated evidence reconstruction through hash-bound cache/reuse.
3. Vectorize or safely parallelize Phase 1a, Candidate, Entry Geometry, ETF
   Relationships, and publication validation without changing outputs.
4. Connect the 303-session canonical foundation to a governed point-in-time
   research dataset and reconcile the 26-session analytics limitation.
5. Only then begin real preregistered chronological strategy research.
6. Continue decision-useful visualization in parallel where it does not change
   models or delay the data/performance foundation.
7. Add options expression, fundamentals/valuation, events, and later
   portfolio/IBKR integration after their required datasets exist.

Do not tune new formulas or claim backtest results before the governed research
dataset, leakage controls, costs, comparisons, and holdout rules are complete.
