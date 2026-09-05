# Current Status

Status date: 2026-09-05

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
- Canonical normalized historical Identity source custody now contains 301
  partitions / 3,687,175 rows. The two absent dates, 2026-08-13 and
  2026-08-19, have reacquired but non-equivalent provider packages and remain
  explicitly unbound.
- `/data` contains 3,958 files / 1,877,724,006 bytes, with zero symlinks and
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

Current-context contract 1.4 now makes this family-specific: the 303-session
price floor and all 303 same-date Identity completion manifests are present,
but neither has a published Historical Coverage claim. The provider-action,
canonical-action, daily-membership, lifecycle, adjustment-ledger, and
Historical Coverage evidence/final roots are absent. Real cost/liquidity,
complete revision lineage, chronological evaluation, and sealed-holdout inputs
also remain absent or fixture-only.

The 2026-09-05 aggregate inactive-security census reached 20 full pages and
20,000 rows with another page still available. It found `delisted_utc` on
19,565 rows, but retained no row data and grants no lifecycle-completeness
claim. This sizes the next source-custody task; it does not clear lifecycle or
terminal-outcome readiness.

ADR 0147 now implements and has executed the next temporary source boundary:
owner-only `/tmp` custody, per-page immutable hashes, atomic checkpoints,
interruption recovery, strict request-chain validation, and complete formal
reread. The exact 2026-07-16 package completed naturally in 24 pages / 23,260
rows / 6,644,157 physical bytes. It remains outcome-reconciliation-only, has
no canonical Apply path, and cannot produce lifecycle conclusions.

The report projects normalized Identity source observations as a separate
record layer: 301 canonical partitions, 3,687,175 records, 3,844 source-page
artifacts, and the exact two missing EOD sessions. It explicitly remains
`canonical_partitions_observed_not_coverage_validated`, so source custody is
visible without being promoted to Historical Coverage or research readiness.

ADRs 0132–0143 record the package census, versioned ETV compatibility,
fingerprint-bound profile map, normalized source custody, atomic Apply, and
22-session append-only recovery. Their current result is the 301 canonical
source partitions above; historical intermediate package counts and plans are
kept in the linked audits rather than repeated here.

ADR 0144 now makes those canonical normalized rows the normal Membership
shadow input. The retained-package V2 path remains only for compatibility
review. A real 2026-09-03 V3 replay produced 19,958 rows over 9,979 stable IDs
and matched V2 on every business decision after excluding the intentionally
changed methodology, lineage, and execution timestamp fields. Declaring the
PyArrow timezone dependency reduced measured single-session time to 59.53
seconds and the five-session boundary to 135.53 seconds without changing the
output fingerprint.

The initial preflight classified 300/303 sessions as source/evidence eligible.
ADR 0145 then proved that eight of the ten unique 2026-08-31 collision
observations were exact-duplicate Identity rows incorrectly retained as two
downstream join candidates. Collapsing only structurally identical references
raises that session's linkage ratio from 0.998996689074 to 0.999799337815 under
the unchanged 0.999 gate. The two distinct unresolved AREN/PAAI references
remain collisions. The only source gaps are still 2026-08-13 and 2026-08-19.

Disconnected V3 evidence now covers all 301 source-available sessions and
5,591,084 formally reread decisions. The original 300-session root remains a
record of the pre-correction run: 600 files / 129,736,636 bytes with fingerprint
`8afa4e188d006e5ac732447d0ca1042b6797b2af51bd3a3547a87a5167e886cf`.
An independent corrected five-session boundary completed 5/5 with zero
external request or canonical write. The three unaffected dates have zero
business-decision difference; 2026-09-03 changes only FAN in both Universes
from false-collision quarantine to explicit ETF exclusion, and 2026-08-31 now
adds 19,930 valid decisions. No Membership partition was published to `/data`,
and every source cutoff remains after its represented session, so the combined
evidence is retrospective mechanics—not historical knowledge-time or research
authority.

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
debt. ADR 0125 separates date-only discovery from deep partition validation;
the normal current-context report fell from roughly 7–8 minutes to 27.65
seconds. ADR 0126 now reuses the exact formal panel and finalized current
Candidate evidence downstream. On unchanged 9/3 inputs, Entry Geometry
completed in 49.67 seconds instead of an approximately 19-minute
uninstrumented stage interval, and ETF Relationships completed in 15.36
seconds instead of 155.34 seconds after ADR 0125. Every business artifact was
byte-identical, logical fingerprints matched, and Oracles remained at zero.
ADR 0127 then reduced Strategy Channels to 33.82 seconds by replacing a
225.978-second complete Candidate reconstruction with a 12.588-second exact
current-batch projection. Its four business artifacts were also byte-identical
and its Oracle remained at zero. Visual Context was measured at 51.11 seconds
and left unchanged. ADR 0128 reduced daily Candidate completion from 521.21 to
294.99 seconds by using the already validated write plus complete physical
custody for the daily commit gate. All ten business files were byte-identical;
the unchanged logical fingerprint and Oracle passed a separate 228.285-second
full semantic reread. These were `/tmp` development replays; Production and
`/data` did not change.

Current-code attribution also found that MI candidate plus plan now takes
53.84 seconds, so the older nine-minute journal interval is stale. Snapshot
candidate plus plan initially took 135.00 seconds. ADR 0129 removed one
duplicate formal active-Snapshot read while binding rollback and CAS to the
same observation; the exact replay took 121.57 seconds. All 42 Snapshot files
were byte-identical and all business, rollback, CAS, pointer, and content
bindings matched. Apply still performs a fresh CAS read. This replay was also
`/tmp` only with no Production or `/data` write.

## Next priority

1. Measure the next complete daily chain on Dell with ADRs 0125–0129 active.
2. Treat Candidate's cumulative writer as the measured remaining hotspot:
   follow-up instrumentation assigned it 193.525 seconds, including 88.528
   seconds across overlapping fingerprint calls, versus 1.739 seconds for
   finalization and 0.061 seconds for explicit garbage collection.
3. Treat MI, Visual Context, Entry, Strategy, and ETF Relationships as bounded;
   Snapshot is now 121.57 seconds and its largest remaining input is the
   necessary formal Activation read rather than duplicate active-state reads.
4. Continue ADR 0130's default-disconnected segmented Candidate proof. The real
   ten-session shadow reconstructed all eight V1 business projections exactly;
   its bounded current read took 16.53 seconds versus 228.285 seconds for V1
   full semantics. Current panel, batches, states, risks, and all 1,718/1,831
   prior-state support rows are exact; only the cumulative V1 history
   fingerprint requires a new versioned chain identity. Next design that
   identity, recovery, and periodic cold equivalence before considering
   cutover.
5. Vectorize or safely parallelize only independently measurable CPU-heavy
   work after exact serial output equivalence is proven.
6. **Canonical source custody complete for exact packages:** 301 sessions are
   canonical after the original and append-only Apply/recovery passes. Keep
   2026-08-13 and 2026-08-19 unbound unless an alternative exact source is
   proven; do not approximate them.
7. **Disconnected Membership mechanics complete for available sources:** keep
   the 301-session V3 evidence temporary. Separately resolve the two exact
   source gaps and historical knowledge-time before any canonical Membership
   decision.
8. Complete lifecycle, corporate-action, adjustment, cost, availability, and
   revision families; then publish transitive Historical Coverage and reconcile
   the 26-session analytics limitation.
9. Only after those gates begin real preregistered chronological strategy
   research.
10. Continue decision-useful visualization in parallel where it does not change
   models or delay the data/performance foundation.
11. Add options expression, fundamentals/valuation, events, and later
   portfolio/IBKR integration after their required datasets exist.

Do not tune new formulas or claim backtest results before the governed research
dataset, leakage controls, costs, comparisons, and holdout rules are complete.
