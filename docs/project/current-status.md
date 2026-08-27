# Current Status

Status date: 2026-08-27

This document is the concise current-state summary. Exact publication IDs,
fingerprints, verification scope, and cross-device handoff are maintained in
the [authoritative current context](current-context.md). Historical execution
detail belongs in the [changelog](changelog.md) and dated audits, not here.

## Current product

WH Alpha is a Session-protected, bilingual U.S. equity market-intelligence
dashboard for discretionary research. Its intended decision chain is:

```text
market state -> strength direction -> sector/theme -> stock candidate
-> trade preparation -> entry/invalidation -> position management
```

The current production-capable source slice covers market overview, breadth, movers,
Trading Activity Map, benchmark and sector-ETF context, a transparent five-
dimension Market Regime, 16 preregistered ETF relationships, and a bounded
Stock Candidate research workspace. English is
the first-visit default; English and Simplified Chinese render the same
language-neutral analytics.

Repository source now presents Market Regime & Opportunities
(`市场风向与机会`), Market Structure & Activity, and Stock Candidates
(`个股候选`) as first-level workspaces with persistent desktop
left navigation and one shared Universe/language/Session utility header. Market
Regime & Opportunities is the first item and default workspace; Market
Structure & Activity is second and begins with a factual “what is happening
now” summary.
It explains Universe membership versus same-session comparable coverage. A
Daily Decision Brief adds one- and five-session Composite changes, distances
to both state boundaries, and an explicit broad Risk-on stance. Six fixed
economic decision lanes precede the collapsed complete 16-pair audit table;
each highlight shows current-versus-prior relationship state, and the short-
history warning is consolidated. These changes and equal-capability guest entry
are deployed in the current OCI release.

The interface supports human decisions. It does not issue orders, model option
returns, or claim causality. Price and volume analytics are participation or
relative-performance proxies, never actual fund flow.

## Active data and publications

- Canonical EOD and same-day Identity are completed through 2026-08-26.
- Latest EOD contains 9,953 rows; same-day Identity contains 9,974 canonical
  instruments, 13,141 provider observations, and 9,974 resolver rows.
- Activation V2 is active with Common Shares as the sole default:
  - Primary: 1,718 CS.
  - Secondary: 1,831 = 1,718 CS + 113 ADRC.
- Active Market Intelligence publication is
  `2026-08-26T050254Z-6c60502e4473`, contract 1.2, with 496 Primary and 532
  Secondary bounded Candidate research records across the fixed entry lanes.
- Active Dashboard Snapshot is
  `2026-08-26T053233Z-6c60502e4473`, contract 1.7 / Dashboard 2.4.
- The locally retained OCI bundle and live-verified deployed release are
  `2026-08-26T053233Z-6c60502e4473` from source commit `6c60502e4473`.

The active analytics and Snapshot are the ordinary fresh 2026-08-26 release:
expected and actual completed XNYS session are both 2026-08-26, lag is zero,
data status is `complete`, and review mode is false. The prior narrowly bound
2026-08-24 `stale_review` release remains historical evidence only; it did not
weaken the normal freshness gate.

## Market Regime

- Primary: 57.8456, Balanced.
- Secondary: 57.9041, Balanced.
- Fixed basket: 30 ETFs.
- Preregistered relationships: 16.
- Windows: 5, 10, and 20 XNYS sessions.
- Relationship-history rows: 336.
- History depth: 26 sessions, so relationship confidence remains low and is
  implementation evidence rather than predictive validation.

The underlying active publication was formally reread after the 2026-08-27
deployment. Exact displayed scores are publication facts, not trade signals.

## Access and deployment boundary

- `/` is the branded credential-or-guest Session entry.
- `/dashboard/` and `/private-data/` share the server-side Session boundary.
- The Auth Service design is localhost-only on OCI.
- Production bundles contain no canonical Parquet, raw provider payload, or
  credentials.
- Synthetic Dashboard data is excluded from the production dependency graph.
  API and Snapshot failures fail closed and never fall back to demo data.
- Guest entry creates the same role-free opaque Session as credential login.
  Guest and credential Sessions expose the same data, functionality, language,
  Universe, precision, freshness, and analytics. No role-based difference is
  authorized.

The 2026-08-27 deployment passed remote preflight, Nginx configuration checks,
atomic apply, unauthenticated protection, and the temporary equal-capability
guest Session postflight defined by the deployment tool. Password-based and
visual browser behavior remains a manual user check because no password was
read or used.

## Current limitations and risks

- The analytics history is only 29 EOD sessions and the active calculations
  use 26 sessions. This is contract and implementation evidence, not enough
  history for predictive validation or stable threshold calibration.
- Provider security form does not prove issuer operating structure or
  domicile. Both public Universes remain explicitly provisional.
- SEC B2 published no completed source cache or issuer-structure evidence and
  remains paused.
- No point-in-time sector/industry taxonomy, market-cap dataset, fundamentals,
  valuation model, options chain, implied volatility, Greeks, open interest,
  true fund-flow data, automated daily ingestion, scheduler, database/catalog
  service, or general production API exists.
- Historical analytics replay current-as-of membership and are not a
  survivorship-free backtest.
- The OCI bundle helper's `--snapshot-release` shortcut still resolves the
  legacy local snapshot directory; current V2 snapshots require the supported
  explicit `--snapshot-path` plus `--bundle-release` form until this is fixed.
- The frontend production build reports a chunk above 500 KB, and the active
  Candidate JSON is about 20.4 MB. Workspace code splitting and summary/detail
  payload separation are required before substantially expanding the UI.
- Stock forward returns must not be described as option returns.
- Unknown, ambiguous, malformed, heuristic-only, or insufficient-evidence
  classifications remain quarantined.

## Next candidate work

The first Candidate performance slice is implemented without changing results:
physical per-stage runtime evidence, a worktree-safe Dell Python runner,
overlapping-panel shared reads, one stable-ID state bar index per panel, and
reuse of the already verified current risk ranking. On the same complete
2026-08-26 audit, time before the audit writer fell from 1840.44 to 461.88
seconds while the logical fingerprint remained
`34e97758863658bfd710e74b312481e5d9f0d170396882dcf2b9c5c63f7eb6d7`
with zero Oracle mismatch. The next operational priority is verified-prior
incremental state, resumable content-addressed stages, and validation tiers;
deterministic process parallelism follows with the serial path retained.
Publication, Snapshot generation, bundle construction, and OCI deployment
remain separate explicit approvals.

The information-hierarchy and current-payload change layer are implemented in
repository source: first-level workspaces, shared controls, an opaque sticky
header, factual first-screen summaries, one-/five-session Regime deltas, both
threshold distances, relationship prior-state persistence, decision-lane
highlights, and the Universe/comparable explanation. Exact first-seen dates,
multi-session relationship persistence counts, and evidence acceleration need
an additive reviewed analytics-response contract; they are not inferred in the
browser.

The Phase 5 stock-candidate pipeline and Phase 6 consumer integration are
active: strict fact/component/confidence/batch contracts, a fingerprinted
seven-component parameter set, pure 26-session scoring, missingness and anomaly
quarantine, separate Conservative/Balanced/Aggressive eligibility/ranking,
chronological Watch/Prepare/Enter/invalidated replay, independent Oracles,
canonical `/tmp` audit/reread boundaries, Candidate publication 1.1, MI 1.2,
Snapshot 1.7 / Dashboard 2.4, and strict frontend parsing. Earlier contracts
remain readable rollback boundaries.

Candidate Entry Geometry V1 remains separate from leadership score/state/rank.
It uses fixed SMA/ATR/return/gap/range/volume facts to distinguish bounded
breakout, breakout watch, orderly pullback, strong-but-extended, and no viable
setup. The active UI selects fixed review-now, watch-trigger, wait-reset, and
other-research lanes from the complete hard-risk-qualified population; it does
not convert stock-price structure into an option-return claim.

The formal 2026-08-26 Candidate audit is
`/tmp/whalpha-candidate-phase5c-20260826`, fingerprint
`34e97758863658bfd710e74b312481e5d9f0d170396882dcf2b9c5c63f7eb6d7`;
the bound entry audit is `/tmp/whalpha-candidate-entry-20260826`, fingerprint
`b3e54546f297bcca9e9a23bb011e0137342777dedc979eca1b4cda71f173ff46`.
Both formal rereads passed with zero Oracle mismatch and zero network or
Production writes; entry input-permutation equivalence is true. Primary has
53 technical-review-ready, 1,250 monitor-for-trigger, 109 wait-for-reset, and
303 deprioritized records. It has 98 strong-but-extended setups, so strength
does not automatically become an entry instruction.

The active Candidate JSON is about 20.4 MB and should be split into summary
and on-demand detail before the payload grows materially further. Dell remains
the sole heavy-compute, historical-storage, and data-governance authority;
OCI is only the static serving/Session boundary. The optimized full Candidate
path remains serial and has no explicit process pool yet. Provider requests
retain their fixed serial request gates; immutable CPU-bound calculations are
the safe parallelization target after incremental execution is complete.

## Verification entry point

Run the local, credential-free report from the repository root:

```bash
scripts/admin/report-current-context.sh
```

The report is read-only, performs no network request, and validates the local
repository, `/data`, active EOD/Identity/Activation/Market Intelligence/
Snapshot state, inventory, and publication residue. Use
`--full-source-validation` when a slower complete Market Intelligence source
reread is required.
