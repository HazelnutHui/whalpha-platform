# Current Status

Status date: 2026-09-09

This is the concise project-state summary. Exact volatile identities,
fingerprints, evidence scope, authorization boundaries, and cross-device
recovery belong in the [authoritative current context](current-context.md).
Historical execution detail belongs in the [changelog](changelog.md), ADRs,
and dated audits.

## Production

WH Alpha is live as a Session-protected bilingual U.S. equity market-
intelligence and research platform. The active OCI release is
`2026-09-09T020802Z-d53e98832ef5`, built from clean source commit
`d53e98832ef57f22e018f9f9b863f009eb355544`.

The deployed product uses:

- Market Intelligence 1.3 for analysis session 2026-09-04;
- Snapshot 1.11 / Dashboard 2.8 with zero completed-session lag;
- English as the first-visit default and Simplified Chinese as an equal view;
- identical data and capability for guest and credential Sessions;
- a public data-free WH landing page and favicon; and
- fail-closed private Snapshot/API behavior with no synthetic Production data.

The 2026-09-09 remote inspection matched the exact active release, source,
bundle, manifest, and checksums. Nginx and the localhost-only Auth Service are
healthy. Public entry, protected routes, guest entry, Dashboard, Candidate
summary/detail, Strategy Channels, Sector ETF Rotation, logout, and renewed
protection passed. No staging release, failed release, unexpected private
listener, or failed system unit remains. Password login and final visual
appearance remain manual checks.

## Data

- Canonical EOD contains 304 contiguous XNYS sessions from 2025-06-23 through
  2026-09-04. Latest EOD has 9,962 rows.
- Latest Identity is 2026-09-08 and contains 9,982 Instruments, 13,155 provider
  identities, and 9,982 Resolvers. It is one session ahead of canonical EOD.
- Canonical normalized Identity source custody contains 303 partitions /
  3,713,485 rows. Provider-revised dates 2026-08-13 and 2026-08-19 remain
  explicitly unbound; 2026-09-08 is source-only until same-session EOD exists.
- Canonical signal-eligible Membership contains one session, 2026-09-04, with
  19,964 decisions eligible for the 2026-09-08 open.
- Immutable EOD and point-in-time Identity family evidence is canonical. Final
  Historical Coverage remains absent.
- Canonical corporate-action source custody contains 70,099 split/dividend
  observations in two immutable event-year partitions: 42,056 exact-date
  stable-ID resolutions and 28,043 quarantined rows. Its coverage is a bounded
  query snapshot and remains outcome-only, not canonical Corporate Actions.
- Canonical split-only fact custody contains 709 resolved action rows: 707
  active single-action rows and two quarantined rows in one multiple-action
  group. It also exposes 43 possible-impact stable IDs without assigning any
  of the 1,240 unresolved source observations. Full Corporate Action coverage,
  neutral factors, and Adjustment Ledger authority remain false for that fact
  publication; the separate sparse ledger below has its own ADR 0178 custody.
- Canonical sparse split-adjustment custody contains 101,321 affected-path rows
  from 175,033 selected EOD rows: 98,291 clear and 3,030 quarantined. It is
  outcome-reconciliation only; omitted-row neutrality and total return remain
  false.
- `/data` contains 4,204 files / 2,151,679,313 bytes with zero symlinks and
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

Production includes a bilingual selected-channel decision map that places
published within-channel score against current extension risk and colours the
linked Candidate trade-review state. It does not recompute or compare strategy
scores across strategies.

Sector Rotation also includes a bilingual, same-session decision chain that
places the selected Universe's confirmed Market Regime beside five leading ETF
price proxies and eight Balanced-risk Candidate priorities. It preserves each
source rank and explicitly separates the columns: this is not formal sector
membership, fund flow, causality, a combined score, or a trade instruction.

Momentum Breakout, Strong-Stock Pullback, and Trend Continuation have
provisional technical mechanics. Technical Reversal, Fundamental Value
Reversal, and Defensive Rotation remain unavailable. Channel distinctness is
unvalidated, and no formal security-level Sector/Industry taxonomy currently
exists. The overlap display must not be presented as sector concentration.
Classification V1.1 contract, offline persistence, explicit coverage ledger,
and formal reader are fixture-validated, but no real source, adapter, canonical
partition, or product consumer exists. The GICS sample and data dictionary are
credential-gated; a public taxonomy map alone is insufficient.

Quant Research Lab is explicitly research-only and data-blocked. It exposes
family-specific readiness rather than a misleading aggregate progress score.
No current page makes a performance or option-return claim.

## Research readiness

Formal status is `data_blocked`; strategy development review and performance
claims are not authorized.

What is complete:

- 304-session canonical EOD and resolved Identity depth;
- immutable EOD and Identity family-evidence manifests;
- 303 canonical Identity source-observation partitions;
- one prospective signal-eligible Membership partition;
- canonical bounded split/dividend source-observation custody and exact-event-
  date resolution;
- a source-marker-bound 708-group split candidate with 707 clear candidates,
  one multiple-event quarantine, and 43 possible-impact stable IDs;
- canonical split-only fact publication with exact Plan/Apply and zero-write
  recovery evidence;
- a real, independently reconciled sparse split-adjustment candidate with
  98,291 clear and 3,030 quarantined affected-path rows;
- exact canonical split-adjustment Plan/Apply publication and zero-write
  recovery evidence;
- deterministic one-side equity cost/capacity scenario mechanics with separate
  commission, spread, delay, and square-root impact components;
- a 547-item lifecycle corroboration queue; and
- fixture-tested chronological, statistics, and holdout mechanics.

What remains incomplete:

- governed historical point-in-time Membership eligibility;
- complete canonical corporate-action type/availability/revision coverage and
  canonical lifecycle; the split-only bounded publication is not sufficient;
- complete adjustment coverage, absent-row neutrality evidence, and a later
  total-return ledger;
- source revision and availability evidence;
- governed quote evidence, impact calibration, and actual-execution validation
  for the current scenario-only equity cost mechanics;
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

The timer correctly identified 2026-09-08 as the oldest missing session. The
guarded Identity fetch/plan/Apply completed with 14 requests and no overwrite;
the initial EOD request, a bounded 22:52 UTC post-close retry, and one final
bounded 2026-09-09 01:48 UTC retry all returned provider HTTP 403 before any
package, staging, or canonical EOD write. The repeated result rules out a
short immediate-post-close delay as the working explanation and leaves
same-day account/endpoint entitlement unresolved. No blind retry loop is
running; the chain remains paused rather than publishing an inferred or stale
new session.

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

1. Resume the guarded 2026-09-08 chain when same-session EOD becomes available,
   then exercise ADR 0154 Membership preparation and record consolidated
   timings.
2. Obtain and review a GICS History specification/sample against ADR 0173.
3. After the new-session Membership/recovery gates pass, review coordinator
   integration and a controlled unattended-scheduler rehearsal.
4. Only after the sample passes, implement its adapter and a Dell-only current
   snapshot, then Candidate sector/industry concentration. Keep unknown visible.
5. Complete historical Membership, lifecycle, cost evidence/calibration,
   availability/revision, final Coverage, chronological evaluation, and sealed
   holdout evidence.
6. Begin real research with Strong-Leader Pullback, then Momentum Breakout,
   Trend Continuation, Technical Reversal, and Fundamental Value Reversal.
7. Add options expression, fundamentals/valuation/events, and later
   portfolio/IBKR integration after their required datasets exist.

Do not tune formulas, thresholds, or rankings before governed chronological
evaluation. Do not introduce guest restrictions, automated orders, complex ML,
new microservices, or a database without a separately demonstrated need.
