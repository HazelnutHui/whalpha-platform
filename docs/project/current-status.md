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
`2026-09-09T211131Z-e06bd62ecab3`, built from clean source commit
`e06bd62ecab3cbf65867c9ddd9853a909379af9a`.

The deployed product uses:

- Market Intelligence 1.3 for analysis session 2026-09-09;
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

- Canonical EOD contains 306 contiguous XNYS sessions from 2025-06-23 through
  2026-09-09. Latest EOD has 9,916 rows.
- Latest Identity is 2026-09-09 and contains 9,982 Instruments, 13,158 provider
  identities, and 9,982 Resolvers. Identity and EOD are aligned.
- Canonical normalized Identity source custody contains 304 partitions /
  3,726,643 rows. Provider-revised dates 2026-08-13 and 2026-08-19 remain
  explicitly unbound; there is no longer an Identity-only session.
- Canonical signal-eligible Membership contains three sessions: 2026-09-04,
  2026-09-08, and 2026-09-09, with 59,892 decisions.
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
- The ADR 0182 read-only coverage diagnostic scanned 2,802,728 adjacent
  stable-ID EOD transitions. All 645 comparable active split groups had bounded
  adjusted residuals and none was extreme, but 387 severe discontinuities
  across 321 stable IDs lacked same-date canonical split evidence. These are
  review flags, not inferred actions; they keep omitted-row neutrality and
  complete split coverage unproven. A prioritization-only cross-check found 13
  current Primary / 14 current Secondary IDs, 31 lifecycle-queue IDs with no
  current-Universe overlap, and 44 IDs with at least one fourfold or
  quarter-scale gap; current membership was not projected backward. The 15
  current-Secondary flags then produced 13 date-aligned first-party event
  contexts, one explicit VISN special cash distribution, and one unresolved
  DFNS case. No split was inferred or canonicalized.
- ADR 0183 formally reread all 68,150 cash-dividend observations and 304 EOD
  evidence partitions. Of 41,200 resolved stable-ID/reported-date groups,
  40,454 passed bounded arithmetic checks only and 746 retained review reasons,
  including 31 large-distribution groups, 17 date-order risks, 145 multi-event
  groups, 13 same-date split/dividend groups, 160 non-USD groups, and 399
  groups without both adjacent EOD bars. The VISN USD 5 case proves a provider
  record date can be represented as the ex-date for a large distribution;
  canonical dividend facts and total-return adjustment therefore remain
  blocked on independent date semantics and the other explicit quarantines.
- `/data` contains 4,311 files / 2,321,416,033 bytes with zero symlinks and
  zero publication residue.
- Active Primary is 1,718 CS. Secondary is 1,831 = 1,718 CS + 113 ADRC.
- The active provider-form Activation remains provisional and does not prove
  issuer structure or domicile.
- No historical backfill process or transient service is active.

Canonical price depth now exceeds the research minimum. Missing price history
is no longer the main blocker; dividend date authority and total-return
semantics remain material research-input blockers.

The owner supplied a 2026-09-09 Massive Stocks Starter purchase confirmation.
The controlled 9/9 run then completed 14 Identity requests and one same-evening
Grouped Daily request under the delayed profile without the old Basic rate
limit. Five-year endpoint depth and a guaranteed aggregate-finality minute
remain unproven.

## Product

The decision chain remains:

```text
market state -> strength direction -> sector/theme -> stock candidate
-> trade preparation -> entry/invalidation -> position management
```

Live first-level workspaces cover Market Regime & Opportunities
(`市场风向与机会`), Market Structure & Activity, Sector ETF Rotation, Stock
Candidates (`个股候选`), and Quant Research Lab (`量化研究实验室`).

Market Regime is confirmed Balanced in both active Universes, while the
candidate state is Defensive: Primary 46.7798 and Secondary 46.8524. The
product includes 16 preregistered ETF relationships and 5/10/20-session
relationship/rotation views. ETF relationships remain price-derived proxies,
not fund flow, formal security classification, or causality.

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

Current Candidate display counts are 862 Primary and 922 Secondary. These are
eligible bounded Candidate records, not Universe sizes.

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

- 306-session canonical EOD and resolved Identity depth;
- immutable EOD and Identity family-evidence manifests;
- 304 canonical Identity source-observation partitions;
- three prospective signal-eligible Membership partitions;
- a read-only Membership sidecar planner and optional non-blocking Pipeline
  Wake 2.1 projection, plus a default-review two-action workspace runner that
  always stops before canonical Apply; no unattended sidecar action is enabled;
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
- fixture-tested exact-input, chronological, statistics, and holdout mechanics.

What remains incomplete:

- governed historical point-in-time Membership eligibility;
- complete canonical corporate-action type/availability/revision coverage and
  canonical lifecycle; the split-only bounded publication is not sufficient;
- complete adjustment coverage, absent-row neutrality evidence, and a later
  total-return ledger; the 387 unexplained severe price-discontinuity flags
  require independent corporate-action/lifecycle evidence;
- source revision and availability evidence;
- governed quote evidence, impact calibration, and actual-execution validation
  for the current scenario-only equity cost mechanics;
- final transitive Historical Coverage;
- a real chronological evaluation dataset; and
- a sealed real holdout.

Historical facts observed after their represented sessions remain outcome-only
unless their source availability is independently defensible. Current
membership and classification must never be projected backward.

ADR 0186 now freezes the first experiment's outcome-free input translation:
exact 21-session split-adjusted formulas, complete same-session point-in-time
Primary membership, stable-ID SPY, same-session confirmed Regime, and whole-
batch rejection for any missing member/session/adjustment. This is a pure
fixture-tested seam only. No real batch, signal, return, parameter result,
performance claim, `/data` write, or Production change exists.

## Automation and performance

The installed `whalpha-daily-eod-wake-review.timer` is active and read-only. It
performs no fetch, Apply, calculation, publication, deployment, retry, alert
delivery, or credential access. No unattended write-capable scheduler is
installed. SMTP remains unconfigured.

ADR 0180 provides a finite runner for consecutive, formally successful
Dell-local offline actions. It keeps every existing single-action journal and
postcondition, defaults to review-only, and has zero provider, canonical Apply,
publication Apply, deployment, retry, recovery, or scheduler-install authority.
The real 2026-09-09 run completed nine offline actions in about 15.7 minutes,
then stopped at publication review as designed. Snapshot planning took about
3.8 minutes, Serving Bundle construction about 2.1 minutes, and OCI deployment
about 2.4 minutes. Candidate remained the largest stage at about 6.3 minutes,
peaked near 8.2 GiB, and used one CPU core.

ADR 0187 separately composes only the Membership candidate and near-Apply-plan
workspace actions. It replans around each action, holds an owner-only session
lock, stops at waiting/blocked/Apply-review boundaries, and invokes neither the
primary pipeline nor canonical Membership Apply. This is fixture-tested
repository execution capability. The 9/9 live candidate exposed a post-action
clock defect; ADR 0190 corrects it. Exact Plan/Apply and zero-write recovery
published the third 19,964-row Membership partition. The website pipeline was
never blocked by this sidecar.

ADR 0188 now carries an explicit provider-recency profile through readiness,
acquisition and Apply custody, coordinator entry points, host verification,
external preflight, and read-only scheduler candidates. Basic remains the safe
default and rollback profile; the owner-confirmed Starter tier uses
`massive_stocks_delayed_15_minutes`. A new owner-only, exact-revision external
data-control pair is provisioned under the existing four-operation standing
scope and has passed the data-only, zero-network preflight. It grants no
publication, deployment, scheduler, or trading authority. The installed
detached read-only timer remains unchanged. The controlled live chain verified
14 Identity requests and one same-evening EOD request under this profile.

The forward runtime workspace retains the complete 2026-09-09 package, plans,
analytics, Snapshot, Serving Bundle, Membership evidence, and journals. ADR
0190 gives Identity and EOD separate persistent artifact pairs, admits exact
persistent MI/Snapshot plans to coordinator custody, and uses action completion
time for Membership replanning. Compatibility paths remain readable, while
mixed role/session/custody inputs remain rejected.

The guarded chain now works end to end for 9/9. Exact-plan Apply published
9,916 EOD rows with zero duplicate business keys or orphan Identity references.
The active OCI release, clean source revision, bundle and manifest hashes,
services, protected routes, and guest parity all passed independent postflight.
No blind retry, staging residue, failed release, or write-capable timer exists.

The segmented Candidate experiment remains a Production cutover NO-GO. It
should not receive more work unless a new live measurement breaches an agreed
runtime budget and a bounded design resolves both large-base rehashing and
Visual Context's cumulative-state requirement.

## Next priority

1. Merge and revalidate ADR 0190, then provision an exact-revision host runtime
   whose journal root matches the persistent workspace.
2. Run one controlled next-session unattended-scheduler rehearsal. Do not
   enable recurring writes until acquisition timing, recovery, publication,
   deployment, and final status reporting all pass together.
3. Set a finite runtime budget from the 9/9 clean-path measurements and profile
   Candidate before changing it; preserve all validation/equivalence gates.
4. Obtain and review a GICS History specification/sample against ADR 0173 and
   the exact field/role gates in the 2026-09-08 source review.
5. Only after the sample passes, implement its adapter and a Dell-only current
   snapshot, then Candidate sector/industry concentration. Keep unknown visible.
6. Complete historical Membership, lifecycle, cost evidence/calibration,
   availability/revision, final Coverage, chronological evaluation, and sealed
   holdout evidence.
7. Begin real research with Strong-Leader Pullback, then Momentum Breakout,
   Trend Continuation, Technical Reversal, and Fundamental Value Reversal.
8. Add options expression, fundamentals/valuation/events, and later
   portfolio/IBKR integration after their required datasets exist.

Do not tune formulas, thresholds, or rankings before governed chronological
evaluation. Do not introduce guest restrictions, automated orders, complex ML,
new microservices, or a database without a separately demonstrated need.
