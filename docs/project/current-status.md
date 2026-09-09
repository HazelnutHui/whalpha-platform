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
`2026-09-09T075821Z-32321f0dadd5`, built from clean source commit
`32321f0dadd5c8f605ee11c8188d3ed90df0814d`.

The deployed product uses:

- Market Intelligence 1.3 for analysis session 2026-09-08;
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

- Canonical EOD contains 305 contiguous XNYS sessions from 2025-06-23 through
  2026-09-08. Latest EOD has 9,964 rows.
- Latest Identity is 2026-09-08 and contains 9,982 Instruments, 13,155 provider
  identities, and 9,982 Resolvers. Identity and EOD are aligned.
- Canonical normalized Identity source custody contains 303 partitions /
  3,713,485 rows. Provider-revised dates 2026-08-13 and 2026-08-19 remain
  explicitly unbound; there is no longer an Identity-only session.
- Canonical signal-eligible Membership contains two sessions, 2026-09-04 and
  2026-09-08, with 39,928 decisions. The later 19,964-row partition was
  evaluated before the 2026-09-09 open.
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
- `/data` contains 4,253 files / 2,236,844,204 bytes with zero symlinks and
  zero publication residue.
- Active Primary is 1,718 CS. Secondary is 1,831 = 1,718 CS + 113 ADRC.
- The active provider-form Activation remains provisional and does not prove
  issuer structure or domicile.
- No historical backfill process or transient service is active.

Canonical price depth now exceeds the research minimum. Missing price history
is no longer the main blocker; dividend date authority and total-return
semantics remain material research-input blockers.

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
candidate state is Defensive: Primary 44.9243 and Secondary 45.4356. The
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

Current Candidate display counts are 904 Primary and 966 Secondary. These are
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

- 305-session canonical EOD and resolved Identity depth;
- immutable EOD and Identity family-evidence manifests;
- 303 canonical Identity source-observation partitions;
- two prospective signal-eligible Membership partitions;
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
The real 2026-09-08 run completed nine analytics/MI-plan actions in about 14.6
minutes of recorded action time, then stopped at publication review as
designed. Snapshot planning and Serving Bundle construction completed only
after their separate review/Apply boundaries. Candidate remained the largest
stage at about 5.8 minutes.

ADR 0187 separately composes only the Membership candidate and near-Apply-plan
workspace actions. It replans around each action, holds an owner-only session
lock, stops at waiting/blocked/Apply-review boundaries, and invokes neither the
primary pipeline nor canonical Membership Apply. This is fixture-tested
repository execution capability; the real 9/8 default-review entrypoint also
returned canonical completion with zero actions or writes. No timer, live
candidate, plan, or `/data` state was changed by its implementation.

The forward runtime workspace is active under the owner-only Dell state root.
It retains the verified 2026-09-04 priors and the complete 2026-09-08 package,
plans, analytics, Snapshot, Serving Bundle, and 27-event journal. The journal's
last event formally closes the unsuccessful persistent-bundle deployment
reservation without replay: one remote read, zero remote writes, old release
unchanged, and target absent. No unresolved action or cadence reservation
remains; no timer has been rebound.

ADR 0181 now permits the exact per-session `acquisition-package` and
`canonical-apply-plan.json` paths to cross every data-transition boundary,
including same-day Identity source normalization, acquisition/operator review,
canonical Apply, coordinator, authorized capabilities, and standing
authorization. The pair is same-session, owner-only, non-symlinked, and cannot
mix persistent and legacy `/tmp` custody. This path is now proven with the real
2026-09-08 persistent acquisition package and canonical plan. ADR 0184 extends
the same principle to the persistent Serving Bundle and shares one validator
across deployment capability, custody, and the reviewed shell entrypoint.

The timer correctly identified 2026-09-08 as the oldest missing session. After
the earlier bounded 403 observations, one guarded Grouped Daily request became
available at 06:59 UTC on 2026-09-09 and produced a 12,534-record immutable
package. Exact-plan Apply published 9,964 canonical rows with zero duplicate
business keys or orphan Identity references. This single observation proves
availability by 06:59 UTC for that session only; the Basic plan's earliest or
guaranteed release minute remains unproven and no blind retry loop is running.

The guarded chain now works end to end from acquisition through OCI deployment
and has one consolidated real-session offline timeline. Post-publication review
executed zero actions and stopped at the expected deployment-review boundary;
the scheduler wake reports 9/8 current, zero missing sessions, and waits for
the 9/9 stabilization review. Reuse optimizations materially reduce the control
path, but Candidate remains the largest stage. The deployment-path correction
was exceptional engineering work and must not be included in the normal daily
runtime estimate.

The segmented Candidate experiment remains a Production cutover NO-GO. It
should not receive more work unless a new live measurement breaches an agreed
runtime budget and a bounded design resolves both large-base rehashing and
Visual Context's cumulative-state requirement.

## Next priority

1. Observe ADR 0187's bounded Membership sidecar on the next live session
   before considering unattended execution; prove candidate timing, primary-
   pipeline waiting, near-Apply inventory binding, and fail-open website behavior.
2. Run one controlled next-session unattended-scheduler rehearsal. Do not
   enable recurring writes until acquisition timing, recovery, publication,
   deployment, and final status reporting all pass together.
3. Record the next live session's clean-path acquisition-to-deployment elapsed
   time without including engineering/debugging time, and set a finite runtime
   budget before any further performance optimization.
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
