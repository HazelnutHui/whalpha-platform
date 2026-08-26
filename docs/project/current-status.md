# Current Status

Status date: 2026-08-26

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

The current production-capable slice covers market overview, breadth, movers,
Trading Activity Map, benchmark and sector-ETF context, a transparent five-
dimension Market Regime, and 16 preregistered ETF relationships. English is
the first-visit default; English and Simplified Chinese render the same
language-neutral analytics.

Repository `main` now presents Market Structure & Activity and Market Regime &
Opportunities (`市场风向与机会`) as first-level workspaces with persistent desktop
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

- Canonical EOD and same-day Identity are completed through 2026-08-24.
- Latest EOD contains 9,942 rows; same-day Identity contains 9,968 canonical
  instruments, 13,131 provider observations, and 9,968 resolver rows.
- Activation V2 is active with Common Shares as the sole default:
  - Primary: 1,718 CS.
  - Secondary: 1,831 = 1,718 CS + 113 ADRC.
- Active Market Intelligence publication is
  `2026-08-24T043223Z-aee1a6ab0f67`.
- Active Dashboard Snapshot is
  `2026-08-24T045652Z-aee1a6ab0f67`, contract 1.5 / Dashboard 2.2.
- The locally retained OCI bundle and live-verified deployed release are
  `2026-08-26T103119Z-f344a589a8c9` from source commit `f344a589a8c9`.

The active analytics and Snapshot are an exact, one-release review of
2026-08-24 data with expected session 2026-08-25 and lag one. Their required
status is `stale_review`. This authorization did not weaken the ordinary
lag-zero freshness gate and must not be generalized to another session.

## Market Regime

- Primary: 50.6585, Balanced.
- Secondary: 50.9036, Balanced.
- Fixed basket: 30 ETFs.
- Preregistered relationships: 16.
- Windows: 5, 10, and 20 XNYS sessions.
- Relationship-history rows: 336.
- History depth: 26 sessions, so relationship confidence remains low and is
  implementation evidence rather than predictive validation.

The underlying active publication was formally reread during the 2026-08-26
context audit. Exact displayed scores are publication facts, not trade signals.

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

The 2026-08-26 deployment verified over SSH that the remote current symlink
selects the recorded release, Nginx and the Auth Service are active/enabled,
and the Auth Service listens only on localhost. Postflight proved a temporary
guest Session could read the Dashboard and the exact bound Snapshot, logged it
out, and then reconfirmed the unauthenticated boundary. Three reviewed releases
remain with no staging/partial residue. Password-based browser health remains
a manual user check because no password was read or used.

## Current limitations and risks

- Active data is a stale review, not current-session production data.
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
- Stock forward returns must not be described as option returns.
- Unknown, ambiguous, malformed, heuristic-only, or insufficient-evidence
  classifications remain quarantined.

## Next candidate work

The next operational priority is to restore ordinary freshness through the
existing approval-bound same-day Identity/EOD workflow, then generate and
review a fresh Market Intelligence plan. Publication, Snapshot generation,
bundle construction, and OCI deployment remain separate explicit approvals.

The information-hierarchy and current-payload change layer are implemented in
repository source: first-level workspaces, shared controls, an opaque sticky
header, factual first-screen summaries, one-/five-session Regime deltas, both
threshold distances, relationship prior-state persistence, decision-lane
highlights, and the Universe/comparable explanation. Exact first-seen dates,
multi-session relationship persistence counts, and evidence acceleration need
an additive reviewed analytics-response contract; they are not inferred in the
browser.

The Phase 5 offline stock-candidate pipeline is implemented in repository
source: strict fact/component/confidence/batch contracts, a fingerprinted fixed
seven-component parameter set, pure 26-session scoring, missingness and anomaly
quarantine, separate Conservative/Balanced/Aggressive eligibility/ranking,
chronological Watch/Prepare/Enter/invalidated replay, an independent raw-panel
Oracle, and a canonical `/tmp` audit/reread boundary. It does not alter `/data`
or the active product. Publication, Snapshot, API/frontend integration, and
deployment remain pending and retain separate operational gates.

The formal read-only 2026-08-24 candidate audit is
`/tmp/whalpha-candidate-phase5c-baseline3-20260824.0JaMYi`, logical fingerprint
`1f25a1c9060d459e372903ad116579973c709363f365f19fa66bb515774c93df`.
It covers the independently calculable 2026-08-21 and 2026-08-24 sessions,
reports zero Oracle mismatches, and passes append, restart, input-permutation,
and future-prefix equivalence. On 2026-08-24, Primary has 1,716 scored / two
missing members, 20 quarantined rows, 1,414 Watch, 46 invalidated, and no
Prepare/Enter state; Secondary has 1,829 scored / two missing, 20 quarantined,
1,512 Watch, 55 invalidated, and no Prepare/Enter state. The absence of later
stages is expected from only two candidate sessions, not predictive evidence.
Current risk-mode outputs reach the fixed 25/50/100 display caps in each
Universe. The full two-session audit took about 928 seconds and peaked near
1.9 GiB, so incremental daily execution remains required before automation.

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
