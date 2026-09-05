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

The report projects normalized Identity source observations as a separate
record layer: 301 canonical partitions, 3,687,175 records, 3,844 source-page
artifacts, and the exact two missing EOD sessions. It explicitly remains
`canonical_partitions_observed_not_coverage_validated`, so source custody is
visible without being promoted to Historical Coverage or research readiness.

The first complete-base daily membership adapter is now proven only in
`/tmp`. A read-only census found 279/303 custody-valid retained Identity
reference packages, with an exact 24-session gap from 2026-07-17 through
2026-08-19. The 2026-09-03 shadow evaluated all 9,979 same-day stable IDs for
both Universes and isolated one source collision while formally rereading all
19,958 decisions. Because its source was observed after the session and no
membership partition exists in `/data`, this does not change research
readiness.

The bounded batch adapter now shares one fully validated EOD panel across at
most five adjacent sessions. Independent 9/2 and 9/3 results match their batch
outputs exactly; the two-session batch took 139.71 seconds versus 222.47
seconds for the measured independent optimized paths. A five-session audit
completed 9/1–9/3 but correctly rejected the custody-valid 8/28 and 8/31
packages because they did not exactly reproduce accepted same-day Identity
fingerprints. The 279-package count must therefore not be represented as 279
reconstructable sessions under the current builder.

The full ADR 0134 census is now complete: 58/303 sessions are exactly
reconstructable under current code, 221 have exact Instrument/Resolver but a
Provider Identity mismatch, and 24 are physically missing. All 279 discovered
packages passed custody; duplicate, unroutable, outside-index, and canonical-
snapshot failures are zero. Four representative row-level comparisons found
only the governed ETV change from unknown/rejected to excluded, matching the
ETV row count exactly.

ADR 0135's explicit legacy profile now reconstructs all 221 and mismatches the
58 current-profile sessions. The two exact sets are disjoint and cover all 279
retained packages; both identify the same 24 physical gaps. Every retained
package therefore has one fingerprint-proven accepted profile. This is still
`/tmp` source readiness—not daily membership or Historical Coverage.

ADR 0136 now binds all 279 retained sessions in a formally reread owner-only
map; 58 use `current_v1`, 221 use `pre_etv_governance_v1`, and the same 24
physical gaps remain unbound. Single and bounded membership paths require this
map and revalidate package locator/custody/time plus accepted Identity-family
fingerprints. A repeated real 2025-09-09/10 boundary batch produced identical
manifests and Parquet bytes under the two correct profiles. Durable canonical
source custody is complete for those 279 packages; the 24 gaps, broad daily
membership, and Historical Coverage remain open.

ADRs 0137 and 0138 now preserve those 279 bound sources in one complete
normalized `/tmp` candidate and bind them into one no-write prospective Apply
plan. The candidate contains 3,399,877 complete result rows in 279 Parquet plus
279 manifest files, totaling 258,394,518 bytes versus 1,006,791,465 represented
source-response bytes. All hashes, modes, schemas, page/row counts, record
fingerprints, profile bindings, and accepted Identity reconstructions passed;
zero symlinks or staging residue remain. The plan binds all 558 files, all 279
absent target partitions, candidate inventory, and current `/data` inventory.
Its SHA-256 is
`97e22c62bc8554f1229a41925970a365d189a5ad05bbf802e984fc9f3885c1a0`.
Its immutable self-status remains `ready_for_separate_review` with
`apply_authorized=false`; the separate user-directed execution is now complete.
Parallel plan construction was byte-identical to serial and reduced measured
wall time from 5:17.38 to 1:30.46.

ADR 0139 now implements the exact-plan atomic Apply boundary and its explicit
`verify_then_complete` recovery mode. Disposable `/tmp` canonical-root tests
prove ordinary publication, canonical modes and typed reread, refusal to
replay an existing target, pre-state drift rejection, interruption after an
atomic rename, reuse of exact completed partitions, continuation of absent
partitions, and fail-closed handling of partial targets and staging residue.
The CLI requires the plan SHA-256, logical fingerprint, expected pre-state,
and exact root. The real ordinary Apply subsequently published all 279
partitions and formally reread every session with zero overwrites/deletions. A
separate recovery postflight reused all 279, wrote zero bytes, and repeated
post-state fingerprint
`27dccc3039aed87dce903f41b55f488bd0b07a67c47885449b957c98b4ad49f5`.
This changes source custody only; research readiness remains blocked.

ADR 0143 then separated actual reacquisition observation time from the one
row-level replay timestamp shared by each accepted canonical Identity family.
The corrected full census finds 301/303 sessions exact under exactly one
profile: 58 current and 243 legacy. The 2026-08-13 and 2026-08-19 packages
mismatch both profiles because provider records and stable-identity fields
were revised, so profile-map 1.1 keeps them discovered but unbound. The 22
other reacquired packages were normalized and appended by exact plan; ordinary
Apply and a separate zero-write recovery passed with no overwrite or deletion.
Post-state fingerprint is
`12b35440e876f8f61fa0bccef8cc06b4c1721c0dc751ebdaa6c572c2df166345`.

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
7. Run and reconcile the broad disconnected membership batches before
   canonical membership review.
8. Connect the complete point-in-time foundation to a governed historical
   research dataset and reconcile the 26-session analytics limitation.
9. Only then begin real preregistered chronological strategy research.
10. Continue decision-useful visualization in parallel where it does not change
   models or delay the data/performance foundation.
11. Add options expression, fundamentals/valuation, events, and later
   portfolio/IBKR integration after their required datasets exist.

Do not tune new formulas or claim backtest results before the governed research
dataset, leakage controls, costs, comparisons, and holdout rules are complete.
