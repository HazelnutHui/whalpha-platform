# Current Status

Status date: 2026-09-08

This is the concise project-state summary. Exact volatile identities,
fingerprints, evidence scope, authorization boundaries, and cross-device
recovery belong in the [authoritative current context](current-context.md).
Historical execution detail belongs in the [changelog](changelog.md), ADRs,
and dated audits.

## Production

WH Alpha is live as a Session-protected bilingual U.S. equity market-
intelligence and research platform. The active OCI release is
`2026-09-08T171914Z-ca2d34d50692`, built from clean source commit
`ca2d34d506922f75699c376391dd6a9191ef0ae9`.

The deployed product uses:

- Market Intelligence 1.3 for analysis session 2026-09-04;
- Snapshot 1.11 / Dashboard 2.8 with zero completed-session lag;
- English as the first-visit default and Simplified Chinese as an equal view;
- identical data and capability for guest and credential Sessions;
- a public data-free WH landing page and favicon; and
- fail-closed private Snapshot/API behavior with no synthetic Production data.

The 2026-09-08 remote inspection matched the exact active release, source,
bundle, manifest, and checksums. Nginx and the localhost-only Auth Service are
healthy. Public entry, protected routes, guest entry, Dashboard, Candidate
summary/detail, Strategy Channels, Sector ETF Rotation, logout, and renewed
protection passed. No staging release, failed release, unexpected private
listener, or failed system unit remains. Password login and final visual
appearance remain manual checks.

## Data

- Canonical EOD contains 304 contiguous XNYS sessions from 2025-06-23 through
  2026-09-04. Latest EOD has 9,962 rows.
- Latest Identity is aligned to 2026-09-04 and contains 9,982 Instruments,
  13,155 provider identities, and 9,982 Resolvers.
- Canonical normalized Identity source custody contains 302 partitions /
  3,700,330 rows. Provider-revised dates 2026-08-13 and 2026-08-19 remain
  explicitly unbound.
- Canonical signal-eligible Membership contains one session, 2026-09-04, with
  19,964 decisions eligible for the 2026-09-08 open.
- Immutable EOD and point-in-time Identity family evidence is canonical. Final
  Historical Coverage remains absent.
- `/data` contains 4,186 files / 2,143,226,489 bytes with zero symlinks and
  zero publication residue.
- Active Primary is 1,718 CS. Secondary is 1,831 = 1,718 CS + 113 ADRC.
- The active provider-form Activation remains provisional and does not prove
  issuer structure or domicile.
- No historical backfill process or transient service is active.

Canonical price depth now exceeds the research minimum. Missing price history
is no longer the main blocker.

## Product

The decision chain remains:

```text
market state -> strength direction -> sector/theme -> stock candidate
-> trade preparation -> entry/invalidation -> position management
```

Live first-level workspaces cover Market Regime & Opportunities
(`市场风向与机会`), Market Structure & Activity, Sector ETF Rotation, Stock
Candidates (`个股候选`), and Quant Research Lab (`量化研究实验室`).

Market Regime is Balanced in both active Universes. The product includes 16
preregistered ETF relationships and 5/10/20-session relationship/rotation
views. ETF relationships remain price-derived proxies, not fund flow, formal
security classification, or causality.

Stock Candidate explanations expose component contributions, evidence,
counterevidence, entry position, risk, invalidation, parameters, raw facts, and
lineage. Strategy-channel ranks are meaningful only inside their own channel.
The decision-integrity presentation separately shows channel research priority
and linked Candidate trade-review readiness, plus stable-ID overlap,
all-risk-mode rejection, missing bounded setup, gap/volatility review, and
extension risk.

Momentum Breakout, Strong-Stock Pullback, and Trend Continuation have
provisional technical mechanics. Technical Reversal, Fundamental Value
Reversal, and Defensive Rotation remain unavailable. Channel distinctness is
unvalidated, and no formal security-level Sector/Industry taxonomy currently
exists. The overlap display must not be presented as sector concentration.

Quant Research Lab is explicitly research-only and data-blocked. It exposes
family-specific readiness rather than a misleading aggregate progress score.
No current page makes a performance or option-return claim.

## Research readiness

Formal status is `data_blocked`; strategy development review and performance
claims are not authorized.

What is complete:

- 304-session canonical EOD and resolved Identity depth;
- immutable EOD and Identity family-evidence manifests;
- 302 canonical Identity source-observation partitions;
- one prospective signal-eligible Membership partition;
- temporary split/dividend source custody and exact-event-date resolution;
- a temporary 708-group split-adjustment candidate;
- a 547-item lifecycle corroboration queue; and
- fixture-tested chronological, statistics, and holdout mechanics.

What remains incomplete:

- governed historical point-in-time Membership eligibility;
- canonical corporate actions and lifecycle;
- canonical split-adjustment and later total-return ledgers;
- source revision and availability evidence;
- a real cost/liquidity model;
- final transitive Historical Coverage;
- a real chronological evaluation dataset; and
- a sealed real holdout.

Historical facts observed after their represented sessions remain outcome-only
unless their source availability is independently defensible. Current
membership and classification must never be projected backward.

## Automation and performance

The installed `whalpha-daily-eod-wake-review.timer` is active and read-only. It
performs no fetch, Apply, calculation, publication, deployment, retry, alert
delivery, or credential access. No unattended write-capable scheduler is
installed. SMTP remains unconfigured.

The guarded manual chain works end to end. Reuse optimizations materially
reduced control-path and downstream stages, but Candidate remains the largest
measured analytics stage at about five minutes. Separate stage benchmarks must
not be summed as one end-to-end claim; the next live session must record a
single consolidated timeline.

The segmented Candidate experiment remains a Production cutover NO-GO. It
should not receive more work unless a new live measurement breaches an agreed
runtime budget and a bounded design resolves both large-base rehashing and
Visual Context's cumulative-state requirement.

## Next priority

1. Exercise the complete guarded daily chain and ADR 0154 Membership
   preparation on the next eligible session; record consolidated timings.
2. Implement the ADR 0173 provider-neutral Classification V1 observation,
   mapping, persistence, and fail-closed reader boundary against fixtures.
3. After the new-session Membership/recovery gates pass, review coordinator
   integration and a controlled unattended-scheduler rehearsal.
4. Review a GICS History specification/sample; only then implement its adapter
   and Candidate sector/industry concentration. Keep unknown mappings visible.
5. Build canonical split actions and a bounded split-adjustment ledger.
6. Complete historical Membership, lifecycle, costs, availability/revision,
   final Coverage, chronological evaluation, and sealed holdout evidence.
7. Begin real research with Strong-Leader Pullback, then Momentum Breakout,
   Trend Continuation, Technical Reversal, and Fundamental Value Reversal.
8. Add options expression, fundamentals/valuation/events, and later
   portfolio/IBKR integration after their required datasets exist.

Do not tune formulas, thresholds, or rankings before governed chronological
evaluation. Do not introduce guest restrictions, automated orders, complex ML,
new microservices, or a database without a separately demonstrated need.
