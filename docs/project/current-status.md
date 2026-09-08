# Current Status

Status date: 2026-09-08

This is the concise project-state summary. Exact IDs, fingerprints, evidence
scope, authorization boundaries, and cross-device recovery are maintained in
the [authoritative current context](current-context.md). Historical execution
detail belongs in the [changelog](changelog.md), ADRs, and dated audits.

## Production

WH Alpha is live as a Session-protected bilingual U.S. equity market-
intelligence and research platform. The current OCI release is
`2026-09-06T121300Z-ab1abf1afaaf`, built from clean main commit
`ab1abf1afaaf87648dfde24f2a584fcc32e360d8`.

The deployed product uses:

- Market Intelligence 1.3 for analysis session 2026-09-04;
- Snapshot 1.11 / Dashboard 2.8, fresh with zero session lag;
- English as the first-visit default and Simplified Chinese as an equal view;
- identical data and capability for guest and credential Sessions;
- a public data-free WH landing page and favicon;
- fail-closed private Snapshot/API behavior with no synthetic Production data.

The static browser view now explicitly labels freshness as a publication-time
check. Current-context report 1.6 separately evaluates current canonical and
active-Snapshot operational freshness, preserves the immutable Snapshot
assertion, and counts Membership only through its governed publication marker
and transitive formal read.

Nginx and the localhost-only Auth Service are healthy. Independent postflight
matched the local and remote manifest/checksum identities and verified public
entry, favicon, protected routes, guest entry, Dashboard, Candidate
summary/detail, Strategy Channels, Sector ETF Rotation, logout, and renewed
protection. No staging or failed-release residue remains. Password login and
final visual appearance remain manual checks.

The final postflight reported zero failed system units. The deployer rejects a
new failed unit while separately requiring Nginx/Auth health; it does not alter
unrelated services.

## Data

- Canonical EOD contains 304 contiguous XNYS sessions from 2025-06-23 through
  2026-09-04. The original 300-session historical target is complete.
- Latest EOD has 9,962 rows and is aligned to the 2026-09-04 Identity snapshot.
- Latest Identity contains 9,982 Instruments, 13,155 provider identities, and
  9,982 Resolvers.
- Canonical normalized Identity source custody now contains 302 partitions /
  3,700,330 rows. The two revised dates, 2026-08-13 and 2026-08-19, remain
  explicitly unbound. The 2026-09-04 daily source is exact, directly bound,
  and retained at its actual observation time.
- Canonical signal-eligible Membership now contains the 2026-09-04 partition:
  19,964 decisions, eligible for the 2026-09-08 open.
- Canonical EOD and point-in-time Identity family evidence now contains two
  immutable, transitively source-bound manifests. Final Historical Coverage
  remains absent.
- `/data` contains 4,060 files / 2,009,699,645 bytes, with fingerprint
  `16033737d18cd8d34de3e8401ee0f3e5d195a49470a2cda384a604ed6f29db1e`,
  zero symlinks, and
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

Current-context contract 1.6 makes this family-specific: the 304-session price
floor and all 304 same-date Identity completion manifests are present,
and both now have published immutable family evidence, but neither has a final
Historical Coverage claim. The provider-action,
canonical-action, daily-membership, lifecycle, adjustment-ledger, and
final Historical Coverage roots are absent. Real cost/liquidity,
complete revision lineage, chronological evaluation, and sealed-holdout inputs
also remain absent or fixture-only.

The 2026-09-08 full-content ADR 0100 assessment now confirms both acquired
families across the entire 304-session interval with zero missing sessions:
EOD contains 2,816,903 rows and point-in-time Identity contains 2,825,403
canonical Instrument rows. Both are `validated_not_published`; the combined
state remains `mechanics_only`. This admits a later separate family-evidence
publication review, not Historical Coverage, research readiness, or a
performance claim.

ADR 0165 now supplies that reviewable no-write intent as one deterministic
`/tmp` plan. It embeds both exact evidence contracts, binds two absent targets,
and proposes only two manifests / 675,569 bytes. Plan logical fingerprint is
`6ae6738181012b6f9364d5b624d7edaa81d992b7be623e6bd6b58c2854d5e663`;
plan SHA-256 is
`dced91a98cf4a71fe28748c241f83aa31dcdb588a9f322245a9b14de6d4511ae`.
An independent exact-SHA formal reread passed. The follow-up context report
confirmed the same 4,058-file `/data` inventory, zero residue, and no published
family evidence. Apply, final Coverage, research development, and performance
claims remain unauthorized.

ADR 0166 implements that exact two-file Apply boundary. It requires the
reviewed plan SHA-256, plan logical fingerprint, family-set fingerprint, and
approved Dell root; shares the global canonical-data lock; publishes EOD before
Identity by atomic directory rename; permits only exact-prefix or completed
zero-write recovery; and detects outside-target inventory drift. Disconnected
fault injection and adjacent Apply regression passed. The separately reviewed
real Apply published both exact manifests / 675,569 bytes with zero requests,
overwrites, or deletions. A completed-state postflight reused both and wrote
zero files/bytes. Final Historical Coverage remains absent and research remains
`data_blocked`.

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

The matching latest-EOD anchor `2026-09-03` also completed in 24 pages / 23,469
rows / 6,714,161 physical bytes. Its exact comparison with 7/16 identifies 262
new-window delisting-date observations, but only 135 have a stable FIGI that
matches canonical Instrument history. Provider revision and missing stable-ID
counts remain explicit blockers; ticker is not used as a fallback key.

ADR 0148 has now normalized and resolved both packages into a disconnected
one-to-one shadow. The 2026-07-16 result has 471 review candidates and 22,789
quarantined rows using only the 268 canonical Instrument sessions through that
anchor. The 2026-09-03 result has 547 review candidates and 22,922 quarantined
rows across all 303 sessions. The later source adds 76 review candidates and
186 quarantined rows; no shared exact row changes disposition. These temporary
results remain outcome-reconciliation evidence, not canonical lifecycle facts
or research-ready labels.

ADR 0167 adds a formally reread, owner-only `/tmp` corroboration plan for all
547 latest-anchor review candidates. It binds 547 unique canonical instruments
without copying ticker/name locators. The 271 XNAS work items require a bounded
Nasdaq Daily List pilot; 276 ARCX/BATS/XASE/XNYS work items remain blocked on
all-exchange source selection. All rows remain `first_observed_only`, with
source availability unknown and point-in-time eligibility zero. The plan made
no external request or `/data` write and authorizes no canonical lifecycle,
Historical Coverage, or performance transition.

ADR 0168 and the dated official-source review now set the next external gate.
The preferred first inquiry is a real cross-venue corporate-action/trading-
status sample, with LSEG first in the evaluation order and Nasdaq/NYSE/Cboe
retained as official exchange benchmarks. A deterministic 30-item diagnostic
covers all 15 non-empty exchange/year/observation-gap strata. No vendor is
selected, purchased, contacted, accessed, or permission-cleared, and no
adapter has been implemented. Lifecycle research remains blocked until the
user reviews exact price/sample/license terms and a provisioned sample passes
stable-ID, revision, knowledge-time, last-tradable, terminal, successor,
consideration, and equal-capability-use gates.

The report projects normalized Identity source observations as a separate
record layer: 302 canonical partitions, 3,700,330 records, 3,858 source-page
artifacts, and the exact two missing EOD sessions: 8/13 and 8/19. It
explicitly remains
`canonical_partitions_observed_not_coverage_validated`, so source custody is
visible without being promoted to Historical Coverage or research readiness.

ADRs 0132–0143 record the package census, versioned ETV compatibility,
fingerprint-bound profile map, normalized source custody, atomic Apply, and
22-session append-only recovery. Their historical result is the 301 profile-
bound partitions; ADR 0150 adds the directly bound 9/4 daily partition without
modifying that evidence. Detailed package counts and plans remain in the linked
audits.

ADR 0144 now makes those canonical normalized rows the normal Membership
shadow input. The retained-package V2 path remains only for compatibility
review. A real 2026-09-03 V3 replay produced 19,958 rows over 9,979 stable IDs
and matched V2 on every business decision after excluding the intentionally
changed methodology, lineage, and execution timestamp fields. Declaring the
PyArrow timezone dependency reduced measured single-session time to 59.53
seconds and the five-session boundary to 135.53 seconds without changing the
output fingerprint.

The historical preflight classified 300/303 sessions as source/evidence eligible.
ADR 0145 then proved that eight of the ten unique 2026-08-31 collision
observations were exact-duplicate Identity rows incorrectly retained as two
downstream join candidates. Collapsing only structurally identical references
raises that session's linkage ratio from 0.998996689074 to 0.999799337815 under
the unchanged 0.999 gate. The two distinct unresolved AREN/PAAI references
remain collisions. Those two revised-source gaps remain. Routine 2026-09-04
normalized source custody is now exact and directly bound.

Combined disconnected V3 evidence covers all 302 source-available sessions and
5,611,048 formally reread decisions. The 9/4 direct-source shadow adds 19,964
decisions in a separate owner-only temporary root. ADR 0151 now proves that
this exact 9/4 partition is next-open `signal_eligible`: source and evaluation
both completed before the 9/8 XNYS open. The corrected 9/3 historical
partition remains `outcome_reconciliation_only`. The original 300-session
root remains a
record of the pre-correction run: 600 files / 129,736,636 bytes with fingerprint
`8afa4e188d006e5ac732447d0ca1042b6797b2af51bd3a3547a87a5167e886cf`.
An independent corrected five-session boundary completed 5/5 with zero
external request or canonical write. The three unaffected dates have zero
business-decision difference; 2026-09-03 changes only FAN in both Universes
from false-collision quarantine to explicit ETF exclusion, and 2026-08-31 now
adds 19,930 valid decisions. That corrected-boundary run did not publish its
partitions to `/data`, and the 301 historical-source sessions remain
retrospective mechanics—not historical knowledge-time or research authority.
The separately assessed and now-published 9/4 forward-usable partition does not
turn that historical set into Coverage.

ADR 0152 now binds the eligible 9/4 partition into a no-write canonical Apply
plan. It proposes the two exact Membership files plus one logical publication
marker written last: 3 files / 463,460 bytes, plan SHA-256
`67cf92606ddc5a314a30df304d568f93c7c051d09925d89b81f3b20a964833c8`,
and plan logical fingerprint
`57a59eaf9bfe0b44ba3cf2257e710a59c8f90b6a93b7c34d34dd064bf77c30c4`.
ADR 0153's separate exact-plan executor published the two physical files first
and the one logical marker last: 3 files / 463,460 bytes, 19,964 formally read
decisions, no overwrite/delete/network request, publication fingerprint
`3f71cd40edd2ed6d7e215a95e0cb89c08c7e96dcb9a8fb543a4de34286c15518`,
and post-state fingerprint
`d7ddbace6669c1870e86d79fd48aa86ff99d276699d23b84939983f950b236b4`.
The separate postflight reused both exact targets and wrote zero files/bytes.
Historical Coverage and research performance remain unauthorized.

ADR 0154 converts the prospective portion of that one-off workflow into a
network-prohibited daily preparation entry point. It builds or reuses the V3
candidate in deterministic owner-only session custody, immediately applies the
same next-open timing assessment, reuses a completed canonical publication,
and refuses a physical-only or marker-only target. It writes neither `/data`
nor OCI and does not gate the website. The persistent Apply-plan path is now
supported with fsynced atomic publication, but the inventory-bound plan remains
a separate near-Apply action after other expected canonical writes. The new
boundary is fixture-tested and passed a real zero-write 9/4 canonical replay;
it has not yet been exercised on a new session or connected to the coordinator.

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

The ADR 0154 Membership candidate preparation is a separate research sidecar
after Identity/EOD. It is not yet an action in that serving chain or the
installed read-only timer.

The 9/1-9/4 catch-up proved correctness but also showed material performance
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

1. Observe ADR 0154's prospective daily Membership preparation on the next
   eligible session. It must consume the direct Daily Identity Plan 1.1 source,
   finish before the next XNYS open, and remain outside the website serving
   gate. Create its inventory-bound plan only near the separately reviewed
   Apply after other expected `/data` writes are complete.
2. After candidate reuse, outcome-only classification, canonical reuse, and
   partial-publication rejection pass on a new session, review one-action
   coordinator integration. Do not enable the write-capable scheduler.
3. ADR 0164 has completed the bounded downstream decision for ADR 0130's
   segmented Candidate proof. Exact 9/4 V1/current-input comparison and
   Entry/Strategy recalculation passed, but whole-V1 replacement is not ready:
   the current reader still rehashes the large base and Visual Context lacks
   cumulative state history in the append projection. Keep V1 authoritative;
   do not expose the segmented path to CLI/executor or create canonical custody
   until one bounded design resolves both gaps.
4. ADRs 0165–0166 have completed the deterministic plan, canonical two-file
   Apply, zero-write postflight, and read-only report for the validated
   EOD/Identity evidence manifests. This does not authorize final Historical
   Coverage or research readiness. Continue with the missing lifecycle,
   corporate-action, adjustment, cost, availability, and evaluation evidence.
5. Keep the earlier hotspot evidence explicit: the V1 Candidate cumulative
   writer used 193.525 seconds, including 88.528 seconds across overlapping
   fingerprint calls, versus 1.739 seconds for finalization and 0.061 seconds
   for explicit garbage collection.
6. Treat MI, Visual Context, Entry, Strategy, and ETF Relationships as bounded;
   Snapshot is now 121.57 seconds and its largest remaining input is the
   necessary formal Activation read rather than duplicate active-state reads.
7. Vectorize or safely parallelize only independently measurable CPU-heavy
   work after exact serial output equivalence is proven.
8. **Canonical source custody complete for exact available packages:** 302
   sessions are canonical after historical and direct-daily Apply/recovery.
   Keep 2026-08-13 and 2026-08-19 unbound unless an alternative exact source is
   proven; do not approximate either gap.
9. **Canonical Membership remains incomplete:** V3 evidence covers all 302
   available-source sessions, but only the directly observed 2026-09-04
   partition is canonical and signal-eligible. ADR 0154 implements the
   prospective candidate boundary but has not yet been exercised on a new
   session or connected to the coordinator. Keep the 301 retrospective
   partitions outcome-only.
10. Use the exact ADR 0167 queue and ADR 0168 sample gate to obtain one reviewed
   cross-venue sample, execute the deterministic 30-item diagnostic, and only
   then decide whether to implement a primary adapter or compose explicit
   exchange corroborators; then complete canonical lifecycle,
   corporate-action, adjustment, cost, availability, and revision families,
   publish transitive Historical Coverage, and reconcile the 26-session
   analytics limitation.
11. Only after those gates begin real preregistered chronological strategy
   research.
12. Continue decision-useful visualization in parallel where it does not change
   models or delay the data/performance foundation.
13. Add options expression, fundamentals/valuation, events, and later
   portfolio/IBKR integration after their required datasets exist.

Do not tune new formulas or claim backtest results before the governed research
dataset, leakage controls, costs, comparisons, and holdout rules are complete.
