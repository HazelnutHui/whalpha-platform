# Current Status

Status date: 2026-09-12

This is the concise actual-state summary. Exact volatile identities and
cross-device recovery belong in
[authoritative current context](current-context.md). Proposed work belongs in
the [roadmap](roadmap.md); history belongs in the changelog, ADRs, and audits.

## Production

WH Alpha is live as a Session-protected trilingual U.S. equity
market-intelligence and research platform. Active OCI release
2026-09-11T211340Z-26cab64fabda was built from clean source
26cab64fabdafca710d6471cb09ac8c62ef17c2d.

Production uses Market Intelligence 1.3 for 2026-09-11 and Snapshot 1.11 /
Dashboard 2.8. English is default; Simplified Chinese and neutral professional
Spanish are equal presentation layers. Guest and credential Sessions
intentionally receive identical data and capability.
Snapshot/API failures close without synthetic Production data.

Independent postflight matched release, source, bundle, manifest, checksums,
services, protected routes, guest access, logout, and residue state. Password
login and final visual appearance remain manual checks.

The public entry is now research-first: Quant Research Lab and future
model-driven equity selection lead the narrative; governed AI research
automation is explicitly planned; the three stable market-context workspaces
are presented as free supporting tools. The Strong-Leader Pullback dossier
shows data construction, unpublished out-of-sample evidence, inactive
Candidate authority, and no performance claim. Conventional account sign-in
is the first-viewport entry, equal-capability guest access follows immediately,
and a visible continuation rail leads into the supporting narrative. The
visual language uses layered rounded surfaces, asymmetric research modules,
and a restrained animated signal path while preserving explicit research
status and limitations. The second-screen research hierarchy presents Quant
Research Lab as the single core and places the current record, downstream
selection, and planned automation on one explicit vertical evidence rail.
Inside the authenticated/guest application, Quant Research Lab is also the
default and sole core workspace. Model-Driven Equity Selection is immediately
beneath it as the reserved downstream consumer of activated models. The three
stable market workspaces are grouped separately as free tools rather than
numbered as equivalent modules. Deep links, multilingual state, Universe choice,
and identical guest/credential capability remain unchanged.

The authenticated and guest application now uses a separate institutional
research-terminal visual system: a compact workspace context bar, quieter
navigation, flat analytical surfaces, table-like information groups,
restrained status color, and reduced rounding, gradients, glow, and motion.
The public entry is unchanged. No data, model, or access behavior changed.

All five application workspaces are route-level chunks with intent
preloading, while the Spanish catalog is fetched only when selected or linked.
The default Quant Research Lab path fell from about 297.6 KiB to 106.3 KiB
gzip JavaScript. Build-failing entry, asynchronous-chunk, and stylesheet size
budgets now guard this boundary.

## Data

- The rolling five-calendar-year EOD target is complete: 1,255 contiguous XNYS
  sessions from 2021-09-13 through 2026-09-11. Point-in-time Identity covers
  all 1,255 EOD sessions and retains one additional Identity-only partition at
  2021-09-10. Latest EOD has 9,971 rows; latest Identity has 10,000
  instruments/resolvers and 13,176 provider identities.
- Historical Identity source custody aligns to 1,253 evaluation sessions; the
  difference from aligned EOD remains exactly the two explicitly unbound
  sessions 2026-08-13 and 2026-08-19.
- Signal-eligible Membership has three prospective sessions and 59,892
  decisions.
- Research-only latest-vintage Membership has 300 sessions and 5,571,154
  decisions. It is physically separate and has no signal, performance,
  Candidate, Production, or web authority.
- Canonical corporate-action source custody still has 70,099 bounded recent
  observations. Separately, exact five-year owner-only source packages now
  contain 6,491 split and 235,751 dividend rows with complete natural
  pagination and a full repeat. Five split provider IDs changed without an
  economic-payload change and remain explicit revision evidence. These source
  packages are not yet stable-ID-resolved or canonical; the split-only facts
  and sparse affected-path adjustment ledger still do not prove neutral
  omitted rows or total return.
- A fixed 30-item Massive Starter lifecycle diagnostic matched Ticker Events
  for only six instruments; 24 returned HTTP 404 and all nine returned events
  were ticker changes. Massive is useful partial evidence but is rejected as
  the sole-primary lifecycle source.
- The complete 2026-07-16 and 2026-09-03 inactive-listing source anchors are
  retained in owner-only persistent Dell custody and formally reread. Their
  23,260 / 23,469 rows remain discovery and reconciliation evidence, not
  canonical lifecycle or terminal outcomes.
- The current verified inventory is 18,174 files / 7,022,160,392 bytes with
  zero symlinks and zero publication residue.
- Primary has 1,718 CS. Secondary has 1,831 = 1,718 CS + 113 ADRC. This
  provider-form Activation remains provisional.
- Stocks Starter removed the old Basic rate limit and provided the tested 9/9
  same-evening EOD. The separate S3 credential is now valid: a 2026-09-09 Day
  Aggregates Flat File succeeded, while 2021-09-09 returned access denied.
  Current REST and Flat File controls matched exactly on shared OHLCV and trade
  count; Flat Files omit VWAP and 13 REST zero-volume records. Starter cannot
  close the two oldest fixed-run days or the earlier external warm-up. ADR
  0206 therefore ends those retries and declines a deeper purchase solely for
  this edge: normal daily updates will roll the active source target to
  2021-09-13, and its first 20 sessions will be excluded as feature warm-up.
- The final network-disabled rolling census confirms price/Identity depth but
  remains `quarantined`: Membership covers 303 sessions, lifecycle and PIT
  classification are absent, and actions/adjustments remain incomplete.
- The shared `.venv` editable-install metadata currently points at the older
  Codex worktree rather than the canonical checkout. The completed backfill was
  not affected: its admin entry point delegated to `scripts/dev/run-project-python.sh`,
  which prepends the canonical repository source path before Python starts.
  Reconciled EOD runbook commands use that same wrapper. Do not invoke operator
  modules through bare `.venv/bin/python -m` until the now-quiescent environment
  is rebound. A network-disabled local rebind attempt stopped before mutation
  because the environment lacks `setuptools`; the wrapper remains the safe
  path and no dependency was downloaded.
- The sealed 2026-09-12 Reconciled EOD source census initially exposed 305
  missing Grouped Daily packages and two invalid Identity-source bindings. A
  reporting correction then showed that those two invalid dates also lacked
  price packages. All 307 price packages are now reacquired with zero retries
  or failures. Final private custody is 614 files / 384,055,489 bytes with
  owner-only modes, zero symlinks, and zero staging residue. The final
  four-worker census selects 948 retained originals plus 305 visibly later
  reacquisitions, with zero price gaps and zero conflicts. It remains
  incomplete only for 2026-08-13 and 2026-08-19, whose original Identity
  responses were not retained. Isolated later-Identity rebuild diagnostics
  omitted one and five canonical business keys, so the no-removal gate was not
  weakened. ADR 0207 instead fixes the first real candidate interval at the
  preceding 1,234 fully source-bound sessions through 2026-08-12. See the
  [dated audit](../audits/reconciled-eod-source-reacquisition-2026-09-12.md).
- The clean contract 1.2 Reconciled EOD candidate is complete and formally
  reread: 1,234 sessions from 2021-09-13 through 2026-08-12, 10,376,263
  records, 2,461 accepted additions, 50 source-proven expected absences, and
  2,648,128 source-proven ticker-case repairs. Its interval fingerprint is
  `098ff756a463c0bf142d9ce597375e3a0574db02ca641fcdcef9b6e72cb6b5e3`.
  Owner-only custody contains 2,469 files / 1,083,699,732 bytes with zero
  symlinks or staging residue. It is bound to implementation revision
  `c798e582b0ad3b49ada5fc7fde94125382ef9c06`. All stopped predecessors remain
  incomplete, have no interval marker, and are not reused. See the
  [build audit](../audits/reconciled-eod-edition-first-build-2026-09-12.md).
- The separately sealed no-write Apply plan was executed exactly once after
  explicit approval. Its
  file SHA-256 is
  `7e9c13b957ad9e2fceb850e9da645356c2e1930800d943f2af3927da31115505`,
  logical fingerprint is
  `6a09ef14c77c475d46f0ae1d20f89058ea1457e32a1e633179b642edccbcf1d5`,
  and expected canonical pre-state fingerprint is
  `a83136b65d76371a9932aa58fc142aa815d1303dc89f600d852cc177eea36d5e`.
  Planning formally reread all candidate sessions and bound all 2,469 files.
  Atomic Apply published exactly 2,469 files / 1,083,699,732 bytes and formally
  reread all 1,234 sessions / 10,376,263 records. The canonical postflight has
  zero symlinks and zero residue. Apply made no provider request, overwrote or
  deleted no existing partition, and grants no research, Candidate,
  Production, or website authority.
- ADR 0210's offline adapter then formally validated the canonical corrected
  edition and its exact same-session Identity snapshots as two unpublished
  family-evidence candidates. EOD covers 1,234 sessions / 10,376,263 records
  with evidence fingerprint
  `b65ee35bb65796dab501d4e59df132bffc566452c713bb18e8659401b632b0a5`;
  Identity covers the same 1,234 sessions / 10,472,243 instrument-snapshot
  records with fingerprint
  `faaa73bceace816d91a5a2483714055d20c48091fe4fc8bfbcde8c27d8b647db`.
  The eight-process run took 374.70 seconds and made zero requests or writes.
  Both were initially `validated_not_published`; the separate legacy
  304-session family evidence was not reused or overwritten.
- ADR 0211's distinct no-write plan now binds those two candidates to the exact
  corrected edition and two absent targets. Plan SHA-256 is
  `d328f1725dc4a74a6237d30e1ccdad6fa8c64765d45210a8cc7a76d6492f9168`,
  logical fingerprint is
  `443d80c7347b794b7f105c2d8b5dc8e57fbc4d4dd67442773983647d69d0fcfc`,
  and family-set fingerprint is
  `30722680a6d2f8448db0e895fed7e060ca8a81f2d5faebca3b4d23fbba2b0d8e`.
  The independent exact-SHA reread passed before Apply.
- ADR 0212 now routes that distinct plan through the already proven
  ordered-prefix, recoverable family-evidence Apply mechanism. Temporary-root
  publication and zero-write completed-state recovery passed while the old
  rolling-current entry continued to reject the edition plan. This tested
  capability was then executed only after exact-plan approval.
- The authorized Apply published exactly two evidence manifests / 2,673,980
  bytes. Outside-target inventory remained
  `8baec95b3a4e81cc2b4ca05f9f1fb24a8a112237c6c217bf88c09066462aa307`
  before and after. Immediate completed-state recovery reused both targets with
  zero writes. Independent postflight produced full inventory fingerprint
  `87a2a573b3350918a90db3cea51faaa1839a4e5fb420e2f20278dfc3cb9aa244`,
  with zero symlinks and zero residue. Historical Coverage, research,
  Production, and website state remain unchanged.
- Source Coverage and full-edition construction now model the separate
  2021-08-11 through 2021-09-08 warm-up interval explicitly. That optional
  contract remains available for a future deeper-history source. The stopped
  fixed run left two EOD and one Identity session missing, but external warm-up
  acquisition is no longer active for the Starter-backed first program under
  ADR 0206.
- Warm-up source custody has a separate fixed historical workspace named
  `warmup-2021-08-11--2021-09-08`. The existing evaluation workspace remains
  immutable and date-truthful. Source Coverage recognizes evaluation and
  warm-up backfills as distinct origins; no warm-up package exists, and ADR
  0206 keeps that reserved workspace unpopulated unless deeper history is
  separately approved.
The detailed bounded-backfill execution history, typed stops, and recovery
evidence remain in the
[continuous-run audit](../audits/five-year-eod-identity-continuous-run-2026-09-10.md)
and [terminal audit](../audits/five-year-eod-identity-backfill-terminal-2026-09-11.md).
Price depth and Grouped Daily source-package coverage are no longer the main
research blockers.

## Product

The stable market workspaces are:

1. Market Regime & Opportunities (市场风向与机会);
2. Sector ETF Rotation (行业轮动); and
3. Market Structure & Activity (市场结构与活跃度).

Market Regime is confirmed Balanced in both Universes; candidate state is
Defensive. The product contains 16 preregistered ETF relationships and
5/10/20-session views. These are price-derived proxies, not fund flow,
classification, or causality.

Quant Research Lab is the model registry, research evidence, and lifecycle
authority. Stock Candidates will later consume one to three separately
validated and activated Lab models under ADR 0191.

The deployed Candidate score, Entry Geometry, and three technical Strategy
Channels are frozen, unvalidated **Baseline V1**. Current display counts are
862 Primary and 922 Secondary eligible records, not Universe sizes. Their
logic remains transparent, but they are not expected-return models and will
not be tuned in place. Technical Reversal, Fundamental Value Reversal, and
Defensive Rotation remain unavailable.

The repository now has a typed Lab model registry, result-publication
semantics, catalog activation guard, and one browser-rendered
Strong-Leader-Pullback method record under ADR 0192. The record is
contract-validated against its canonical Python builder. It has no real
performance result, no out-of-sample observation, and no Candidate authority;
all real result areas remain locked. This interface is now present in the
active OCI release.

ADR 0194 records a future bounded AI Quant Research Factory inside the Lab.
No agent orchestrator or autonomous research service exists yet. The first
implementation gate is still one complete Strong-Leader Pullback path; only
after it proves reproducible rejection and stage isolation may a small multi-
role agent pilot begin.

## Research readiness

Formal state is data-blocked; real evaluation and performance claims remain
unauthorized.

Complete:

- 1,255 aligned EOD and Identity durable partitions through 2026-09-11;
- 1,253 target-session Identity source partitions, 300 research-only
  Membership sessions, and three prospective signal-eligible Membership
  sessions;
- 1,253 formally selected Grouped Daily packages plus two Identity-source
  exceptions awaiting disposition;
- bounded corporate-action observations, split-only facts, and sparse
  split-adjustment evidence;
- fixture-tested input, chronology, statistics, cost-scenario, and holdout
  mechanics;
- a preregistered Strong-Leader Pullback V1;
- the canonical contract 1.2 corrected EOD edition for 1,234 sessions through
  2026-08-12, formally reread after atomic Apply;
- the exact edition-specific two-family evidence publication plan; and
- canonical publication and zero-write recovery of both exact evidence
  manifests.

Incomplete:

- later Historical Coverage and research admission of the canonical ADR 0207
  corrected EOD edition; edition construction, reconciliation, edition Apply,
  postflight, family-evidence validation, planning, and publication are
  complete;
- historical point-in-time Membership eligibility;
- canonical cross-venue lifecycle and terminal outcomes;
- complete action availability/revision and adjustment/total-return evidence;
- final transitive Historical Coverage;
- observed spread/impact and calibrated execution costs;
- a real chronological evaluation dataset and sealed real holdout.

Historical backfills observed later remain ineligible for formal validation,
holdout, and Production claims unless source availability at signal time is
defensible. Current membership or taxonomy must not be projected backward.
ADR 0193 permits the fixed 287-session interval through 2026-08-12 only for an
outcome-blind coverage census and possible later development cohort. ADR 0195
has now frozen a 100%-complete Primary session-cross-section rule and the
existing 252-session minimum. The typed decision rejected current evidence:
zero of 267 candidate sessions passed, 20 were zero-included warmup sessions,
and all 437,402 raw-complete paths still lack proven sparse-row neutrality and
canonical lifecycle evidence. No cohort is admitted and development remains
unauthorized. The Strong-Leader Pullback V1 input adapter has fixture evidence
only and has never produced a real backtest.

## Automation and performance

The installed wake timer is active but read-only. No unattended write-capable
scheduler is installed and SMTP is unconfigured. The guarded manual chain
works end to end.

The 2026-09-11 persistent run completed nine offline stages in about 17.1
minutes. Candidate remained the main hotspot at about 7.0 minutes, 11.2 GiB
peak, and one CPU core. The segmented Candidate path remains a cutover NO-GO;
do not continue that optimization without a new budget breach and a design
that fixes both known gaps.

## Next priority

The current rolling census fixes 1,255 sessions from 2021-09-13 through
2026-09-11. EOD and target-session Identity are complete. Membership remains
303/1,255.
Required lifecycle, PIT classification, PIT fundamentals, and Historical
Coverage are absent; status remains `quarantined`.

1. Do not restart the stopped `20260911g` continuation or retry its expired
   boundary. The rolling price/Identity target and final census are complete.
   The complete corrected edition has now passed exact planning, atomic Apply,
   canonical postflight, read-only EOD/Identity family-evidence validation, and
   edition-specific evidence publication planning, exact Apply, and zero-write
   recovery. This still does not admit research: the other mandatory
   families and final Historical Coverage remain later gates. Treat the first
   20 edition sessions as disclosed feature warm-up and exclude them from
   signals and performance. Do not retry the
   expired 2021-09-09/10 price boundary or populate the reserved external
   warm-up workspace under Starter.
2. Continue independent construction using Massive plus bounded official/free
   source pilots for identity, listing status, lifecycle, corporate actions,
   terminal outcomes, and point-in-time fundamentals. LSEG is a later
   measured-gap option rather than the mandatory next dependency.
3. Persist reconstructed historical Membership only in the ADR 0197
   research-only family. Keep the three signal-eligible sessions and their
   Production reader physically separate.
4. Repeat the outcome-blind census and decision, then admit at least 252
   complete session cross-sections or retain rejection without opening outcomes.
5. Execute the registered chronological research only after admission, and
   retain success or failure.
6. Generalize only the proven path into a bounded multi-agent research pilot.
7. Activate and connect a model to Stock Candidates only after separate
   operational review.

Daily reliability and one bounded next-session automation rehearsal may proceed
in parallel. Do not tune Baseline V1, restart indefinite Candidate
optimization, add guest restrictions, call stock outcomes option returns, or
add infrastructure without a demonstrated requirement.
