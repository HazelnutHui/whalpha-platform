# Changelog

## 2026-09-13 — Retain the frozen SEC documents in resumable custody

- Accepted ADR 0230 and added a source-custody runner for exactly the 219
  requests frozen by ADR 0229. Each document has its own bounded retry budget,
  shares the plan's two-request-per-second limiter, and is atomically retained
  with a typed artifact and physical hash.
- A restart formally rereads every completed document before skipping it. An
  exact fully completed partial can be adopted without another request, while
  changed content, unsafe metadata, unknown members, and final/partial
  coexistence fail closed.
- Fixture tests proved one-document interruption and 218-document resumption,
  zero-redownload completed-partial adoption, full formal readback, and
  tamper/unknown-member rejection. The full API suite passed 2,646 tests with
  two unchanged warnings.
- The real run retained the first document as a bounded pilot, then formally
  resumed the remaining 218. All 219 requests succeeded with zero retry and
  retained 5,430,894 bytes; the independent completed-package invocation made
  zero requests and formally reread every artifact and physical hash.
- The final manifest SHA-256 is
  `38d7cf826769e4f3541ba5e22b4066b3f9a8779e56c770f81e7c2b5fc0833bb5`
  and the logical fingerprint is
  `2bf0aa1510902415c0530d2f49630b7b03757d6780805157b03ffbad1c7d1c3e`.
  No credential material, `/data`, lifecycle fact, research, Candidate,
  publication, deployment, or scheduler action occurred.

## 2026-09-13 — Freeze the SEC transition-document acquisition plan

- Accepted ADR 0229 and converted all 219 on-or-after-last-observation SEC
  candidates into 219 unique official URLs. No form, case, or accession was
  hand-selected after coverage inspection.
- The immutable plan has 22 deterministic batches: 21 batches of ten and a
  final batch of nine. It caps rate at two requests per second, retries at two,
  and each document at 64 MiB; only safe HTTPS paths on `www.sec.gov` are
  permitted.
- The 174,159-byte plan has SHA-256
  `bb79ec052e7296b1a7234f83d5c91a11097bdb54f9215e8c806e5159ab0d41f7`
  and logical fingerprint
  `fbce15f14b151fc179a5b16d1bdea97a72bf1c57dd025ee91ea56e33fe62c500`.
  Formal reread passed with zero staging residue.
- The complete API suite passed 2,643 tests with two unchanged warnings. No
  request, credential read, document write, security assignment, terminal
  fact, `/data`, Historical Coverage, research, Candidate, publication,
  deployment, or scheduler action occurred.

## 2026-09-13 — Bound SEC lifecycle-document discovery to the first strategy

- Accepted ADR 0228 and implemented a network-prohibited SEC Submissions
  metadata pilot over ADR 0223's exact 64 lifecycle cases. It formally binds
  the source sample, immutable Submissions package, and full-payload census;
  reads every CIK root and referenced historical shard; and retains no
  security assignment or terminal fact.
- The real run read 64 roots, 42 shards, and 91,640 filing rows. It retained
  2,144 official document locators, including 219 on or after the last
  canonical observation. Sixty-two cases have Form 25 family candidates, 62
  have Form 15 family candidates, and 61 have structured 8-K candidates.
- All eight complete security-level lifecycle fields remain `unsupported` at
  the metadata layer. The pilot grants no document request, credential read,
  Historical Coverage, research admission, outcome access, Candidate,
  publication, deployment, or scheduler authority.
- Real-source diagnostics corrected two assumptions before durable custody:
  accession prefixes do not have to equal filer CIKs, and primary documents
  may use safe relative paths. One unreferenced output with a future evaluation
  time was exactly deleted and rebuilt correctly to avoid conflicting custody.
- The final 1,204,695-byte report has SHA-256
  `ba4803207492a00229a0bc1025e17882ece600a8a3f5c97cca5c8645da786059`
  and logical fingerprint
  `c68cd6c8b0677091cb467323938c4255525da2106c2c9d859b0bc76497502ad1`.
  Formal reread passed, focused tests passed, and the complete API suite passed
  2,639 tests with two unchanged warnings.

## 2026-09-13 — Complete source-available research Membership coverage

- Corrected the first V4 pilot's overly strict proof condition before any
  canonical write by separately counting collisions with and without canonical
  candidates. The corrected real 2022-08-01 pilot produced 16,682 complete
  decisions while keeping all uncertain instruments quarantined.
- Froze a new 37-session / 13-batch plan at revision `4052ccc`, logical
  fingerprint
  `c71c9e7cb08c019e4b05fb60531be5319a047b97297245248c79afa2624e38e1`.
  Four Dell workers completed 37 / 37 candidates / 622,424 decisions with zero
  failed batch, external request, or canonical write.
- The exact archive preview passed, then Apply archived and formally reread all
  37 V4 sessions. Failed, reused, overwritten, deleted, and external-request
  counts were zero; staging/partial residue, symlinks, and residual processes
  were also zero.
- Research Membership now contains 1,213 V3 plus 37 V4 sessions. Combined with
  three signal-eligible sessions, coverage is 1,253 / 1,255 and 21,323,450
  decisions. Only 2026-08-13 and 2026-08-19 remain missing because Identity
  source custody is unavailable.
- The five-year census remains `quarantined`, performance authority remains
  false, and its logical fingerprint is
  `1c75a304056c60f6a7c79f1f74797734aaa13ff87c31d130e05c57cc887557cd`.
  The canonical inventory is 21,025 files / 7,397,444,417 bytes with fingerprint
  `b4f1dc83b5b26a6ccde3b5dffd47ac58de465fced41d129ef74c0e2282228ff7`.

## 2026-09-13 — Localize collision-derived join failures in research Membership

- Accepted ADR 0227 and added the separately versioned
  `provider-form-complete-base-localized-collision-v4` method. A sub-0.999 join
  ratio becomes research-localizable only when the complete failure set is
  exactly stable-ID collision plus its derived join failure, the denominator
  reconciles to mapped plus collided rows, ambiguity and business conflicts
  are zero, raw categories reconcile, and collision candidate-scope counts
  reconcile. Canonical candidates must retain explicit stable-ID quarantine;
  collisions confined to noncanonical Identity references remain separately
  counted outside the evaluated base.
- V3 remains immutable and the 0.999 threshold is not lowered. Every original
  quality flag remains retained. All other failure combinations still reject
  the whole session, and V4 is unavailable to signal-eligible Membership,
  validation, holdout, performance, Candidate, Production, or web publication.
- The five-year census now formally reads and unions approved, nonoverlapping
  V3/V4 research methodology partitions while rejecting unsupported methods or
  duplicate dates. The resumable continuation CLI requires an explicit
  approved method for V4 execution and keeps V3 as its default.
- All 67 focused Membership/evidence tests and the complete 2,635-test API
  suite pass with two unchanged dependency deprecation warnings. No canonical
  or Production write occurred during implementation verification.

## 2026-09-13 — Extend five-year research-only Membership custody

- Executed the immutable 950-session continuation plan at four-process
  candidate-build concurrency under the unchanged evidence gates. Archived
  and formally reread 913 completed sessions / 15,069,980 decisions; failed,
  overwritten, deleted, and external-request counts were zero.
- Research-only Membership now contains 1,213 sessions / 20,641,134 decisions.
  Together with three signal-eligible sessions, the formal five-year census
  covers 1,216 / 1,255 sessions and 20,701,026 decisions. Thirty-seven
  source-available sessions remain rejected by `identity_join_ratio_below_gate`;
  2026-08-13 and 2026-08-19 remain unavailable at source.
- A bounded quality census found that all 37 join-gate failures also have
  stable-ID collision observations. The gate was not lowered. Later ADR 0227
  distinguishes collisions involving canonical candidates from collisions
  confined to noncanonical Identity references; signal and Production
  semantics remain unchanged.
- Postflight found zero staging/partial residue, symlinks, or residual archive
  processes. The fresh five-year census remains `quarantined` with logical
  fingerprint
  `71c78262c0e3be33c7f1ba3676ffb35f5301002f846728b0b9f0b45af564a89c`.
  The full canonical inventory is 20,914 files / 7,382,699,983 bytes with
  fingerprint
  `b7e0789db07fcb69165723fa6b537ba70379ec836085c8f934ce1812fbeb5f9c`.
- Current-context report 1.11 now surfaces the physically separate research
  Membership family explicitly instead of showing only signal-eligible
  Membership. It reports observed custody without upgrading research
  readiness or weakening the signal Membership blocker.
- Reconstructed Membership still grants no signal, validation, holdout,
  performance, Candidate, Production, or web authority. Lifecycle, complete
  action/adjustment semantics, costs, and final Historical Coverage remain
  blocking.

## 2026-09-13 — Bound the five-year research Membership continuation

- Added one resumable, network-disabled continuation entrypoint for the
  physically separate research-only Membership family. It freezes an
  owner-read-only plan, excludes existing research and signal sessions,
  isolates unavailable Identity sources, and groups only adjacent sessions in
  batches of at most five.
- Execution is capped at four Dell processes. Workers share one formally read
  security catalog per process, write disjoint `/tmp` candidate roots, and
  support bounded pilot runs and exact continuation without granting signal,
  validation, holdout, performance, Candidate, Production, or web authority.
- Corrected the custody runbook's superseded warm-up dates to ADR 0206's active
  target: 1,255 source sessions from 2021-09-13 through 2026-09-11, with the
  first 20 sessions ending 2021-10-08 and first eligible strategy session
  2021-10-11.
- All 28 focused continuation, batch, shadow, and archive tests pass. The full
  2,625-test API suite also passes with two unchanged dependency deprecation
  warnings. Real candidate build and canonical research archive remain
  separate measured execution stages.

## 2026-09-13 — Census cutoff-aware SEC security projection

- Added the cutoff-aware issuer selector and immutable aggregate projection
  census for the four registered SEC queries. Every fact is bounded by source
  availability, filing-clock eligibility, period end, following-XNYS-open
  cutoff, and ADR 0224's session-local single-common-stock CIK class.
- The real run scanned all 10,681,604 link row-sessions and evaluated all four
  queries for 6,122,451 structurally projectable rows, producing exactly
  24,489,804 evaluations. Strict as-operated projection contains only 17,879
  rows across four sessions; 6,104,572 rows across 1,249 sessions remain
  reconstructed development evidence.
- Reconstructed selection coverage is 84.97% Assets, 81.52% equity, 73.01%
  annual net income, and 61.98% annual operating income. Missingness and 1,834
  reconstructed plus 12 strict net-income ambiguities remain explicit.
- Corrected the prior 11-session interpretation: it measured timely source
  timestamps only and included seven `outcome_reconciliation_only` sessions.
  The complete contract requires eligible provenance as well and admits four
  strict sessions.
- The mode-`0700/0400`, 1,836,393-byte private report has SHA-256
  `ce7a30931ea71157d7ef4d116c4282eecc9085d7b9105ef312d39361838333f8`
  and logical fingerprint
  `4e65cee8d4c1697dcd8e1b589b0a81297dc2722a1dfc5dc39f30b393f01a16bb`.
  Eight-process build plus full transitive readback took 9 minutes 43.26
  seconds at 709,820 KiB maximum RSS; 260 SEC-focused tests and all 2,622 API
  tests passed with two unchanged dependency deprecation warnings.
- Issuer values, security/fact rows, daily panels, features, outcomes,
  performance, canonical `/data`, Membership, Candidate, publication,
  deployment, scheduling, credentials, and external requests remained absent.
  The engineering lane is complete, but the data gate remains rejected.

## 2026-09-13 — Parallelize the five-year SEC link formal reader

- Reworked the existing formal reader into one-to-eight session workers while
  preserving every canonical snapshot, source-custody, physical-hash, Arrow
  schema, row-order, stable-ID cardinality, knowledge-time, and disposition
  check. The parent still reproduces the exact ordered session index and global
  denominators; there is no manifest-only shortcut.
- The first real eight-worker reread completed in 6 minutes 32.49 seconds at
  804% aggregate CPU and reproduced all 1,255 sessions, 10,681,604 rows, and
  logical fingerprint
  `a71a6180f86228b7c80062c121da42e46a101d8f012e7f7a537147be0b609c71`.
  It wrote zero bytes and made no external request.
- Eleven focused tests pass. The optimization is complete; repeated transitive
  rereads of the same immutable input are not a new optimization program.

## 2026-09-13 — Register and census the first SEC issuer queries

- Accepted ADR 0225 and froze four exact issuer-level source queries: Assets,
  Stockholders' Equity, fiscal-year Net Income/Loss, and fiscal-year Operating
  Income/Loss. Revenue fallbacks, quarterly-flow derivation, per-share facts,
  IFRS forms, security features, and strategy authority remain excluded.
- Added a query-specific, worker-aligned readiness census with sequential
  rejection accounting and conservative duplicate, value, availability, and
  period-end ambiguity quarantine. It scans every source row but creates no
  daily Cartesian panel and publishes no fact values.
- The real eight-process run scanned all 41,619,407 normalized occurrences and
  targeted 1,569,275 concept occurrences. Filers with at least one clean period
  are 8,569 Assets, 8,175 equity, 7,634 annual net income, and 6,359 annual
  operating income. It quarantined 140 and 50 ambiguous annual semantic periods
  respectively and selected no conflicting duration by row order.
- The 5,685-byte owner-only report has logical fingerprint
  `5c803386e37576697fc8652197f932f26b559899cfe6d07c7ce5608d17f06bb8`.
  Scan plus built-in readback took 28.51 seconds at 543,840 KiB maximum RSS; a
  separate formal reread took 10.50 seconds. Five implementation tests, all
  247 SEC provider tests, and the complete 2,613-test API suite pass; the full
  suite retained two unchanged dependency deprecation warnings.
- External requests, credentials, `/data` writes, security projection,
  features, outcomes, performance, Membership, Candidate, publication,
  deployment, and scheduler changes remain zero. The next fundamental stage is
  a cutoff-aware issuer reader and exact projection census, not a feature table.

## 2026-09-13 — Reconcile and slim the default project recovery path

- Rebuilt current context, current status, and the roadmap around distinct
  authority: verified identities, actual capability, and future sequencing.
  Removed more than 800 lines of duplicated execution narrative while retaining its
  evidence in the changelog, ADRs, operations, and dated audits.
- Corrected the stale Candidate summary to the formally reread Production
  state: both Universes are Balanced and the display contains 870 Primary / 924
  Secondary records.
- Made the central boundary explicit: five-year price and Identity depth is
  complete, while the performance-eligible research foundation remains
  `data_blocked` by Membership, lifecycle/terminal, action/adjustment,
  knowledge-time, cost, and Historical Coverage gates.
- Shortened the documentation index to the current governing ADRs and evidence
  checkpoints. Historical files remain preserved and discoverable rather than
  being treated as default recovery material.

## 2026-09-13 — Gate SEC security projection by class and evidence time

- Accepted ADR 0224 after an outcome-blind selected-column scan of the complete
  filer/security candidate. Common stocks account for 6,244,758 admitted link
  row-sessions, 5,977 missing-CIK quarantines, and 9,129 rows on the two
  missing source sessions.
- The conservative session-local single-common-stock CIK class covers
  6,122,451 admitted rows, about 98.0%. The remaining 122,307 rows belong to
  59,440 multi-common-stock CIK/session groups, with at most seven common
  stocks in one group; they are not silently projected.
- The preliminary timestamp-only scan found 11 / 1,255 sessions with retained
  source observation no later than the next XNYS open. The later complete
  projection contract also enforced provenance and admitted only four strict
  sessions. ADR 0224 therefore keeps `as_operated_next_open` separate from
  `reconstructed_latest_vintage_development_only`; reconstructed links cannot
  enter sealed validation, holdout, headline performance, activation, or
  Production Candidate authority.
- The corrected session-streaming scan completed in 42.54 seconds at 182,808
  KiB peak memory and wrote zero bytes. No fact values, prices, outcomes,
  credentials, canonical data, features, research results, publication,
  deployment, or scheduler state were accessed or changed.

## 2026-09-13 — Build the complete SEC filer/security link candidate

- Extended the proven one-session SEC filer/security link path across all
  1,255 XNYS sessions from 2021-09-13 through 2026-09-11. Every one of the
  10,681,604 canonical stable-security rows has an explicit decision:
  9,456,209 unique-CIK admissions, 1,205,516 missing-CIK quarantines, and
  19,879 quarantines on the two exact missing source sessions 2026-08-13 and
  2026-08-19. Conflict and identity-mismatch counts are zero.
- Preserved 952 `eligible_at_source_observed_at`, 301
  `outcome_reconciliation_only`, and two `source_custody_missing` session
  states without backdating evidence. All rows retain
  `issuer_projection_authorized=false`; one-to-many CIKs remain visible rather
  than selecting a primary share class.
- The owner-only 1,256-file / 758,604,458-byte package has manifest SHA-256
  `2a432ff2ca92fdc912ba5712b7487feb905fc24d562e5f84301e3e98f86d3ab0`
  and logical fingerprint
  `a71a6180f86228b7c80062c121da42e46a101d8f012e7f7a537147be0b609c71`.
  The built-in full formal reread and an independent boundary/exception
  postflight passed; ownership/modes are exact and residue is zero.
- Added exact failed-build partial cleanup before the run. Eight-worker
  materialization plus strict single-process full reread completed in 56
  minutes 16.11 seconds, establishing the formal reader as the performance
  tail. No network or credential access occurred and canonical, Membership,
  analytics, research, publication, deployment, and scheduler authority remain
  unchanged. The complete API suite passes 2,608 tests with two unchanged
  dependency deprecation warnings.

## 2026-09-13 — Freeze the first-strategy source acceptance population

- Implemented ADR 0223's network-prohibited, provider-neutral sample builder
  and formal reader. It binds the exact blocker census and both inactive-
  lifecycle anchors, rejects missing occurrence lineage, and preserves all
  individual rows privately while its CLI emits aggregate counts only.
- The owner-only result contains every 20 unassigned action relations / four
  action IDs and every 64 five-session lifecycle-crossing IDs. It recovers 122
  exact lifecycle source occurrences, has zero overlapping IDs and 68 combined
  IDs, without ranking, subsampling, or opening outcomes.
- The one-file / 78,458-byte package has report SHA-256
  `17a1c177be65693786a410c1c2107c499e34a88960541a24339644e12ba01416`
  and logical fingerprint
  `f29da6a170f873b20a4ee57141cf1dc975f5a8f3a840dc19dc115283828c1a5a`.
  Built-in and separate formal rereads passed; permissions are `0700/0400`
  with zero symlink or staging residue. The build took 6.59 seconds and 22
  directly related tests pass. The complete API suite passes 2,607 tests with
  two unchanged dependency deprecation warnings.
- Provider requests, credentials, stable-ID assignments, terminal facts,
  outcomes, metrics, parameter/cohort selection, canonical writes, Historical
  Coverage, research admission, Candidate, publication, deployment, and
  scheduler changes remain zero. The next evidence action is a source-specific
  pilot and measured field-level gap report bound to this sample, not another
  global scan.

## 2026-09-13 — Scope first-strategy action and lifecycle blockers

- Accepted ADR 0221 and added an outcome-blind, network-prohibited census that
  binds the rejected Strong-Leader Pullback development population to retained
  corporate-action and inactive-lifecycle evidence. It revalidates all 287
  Membership partitions while materializing only the declared Primary rows,
  avoiding a redundant 5.7-million-row Python reconstruction.
- The real owner-only result reconciles all 437,402 included paths / 2,161
  stable IDs. It contains 4,643 action/instrument exposures: 4,623 exact
  event-date resolutions and 20 explicitly unassigned history-candidate
  relations. The latter comprise 19 cash dividends and one reverse split; 12
  have one history candidate and eight have multiple.
- Company actions touch 80,568 unique feature paths and 20,626 unique
  five-session label paths. Eighty-nine lifecycle candidates intersect 8,677
  included paths; 64 IDs / 252 paths cross the last observation inside the
  five-session label horizon. No terminal outcome is inferred.
- Accepted ADR 0222 after a formal canonical cross-read matched all 44 exact-
  resolved split-like exposures to active canonical facts and 6,859 clear
  fixed-basis ledger rows with zero quarantine. The one unresolved reverse
  split remains in the existing possible-impact quarantine. Future V2 features
  use a signal-local basis and labels an exit-local basis; no duplicate global
  ledger or neutral omitted row is authorized.
- The three-file / 231,752-byte package has manifest SHA-256
  `63fb6694ef0e6284bea3dc9cd5aafe431353e443a4239eff8f598f1d6baecb15`
  and logical fingerprint
  `4abebf27774d0da398f029f152ce51b66e925201506365cf7084d8294f75243d`.
  Built-in and separate formal rereads passed; permissions are `0700/0400`
  with zero symlink or residue. The final build took 256.59 seconds and 28
  focused tests pass. The complete API suite passes 2,602 tests with two
  unchanged dependency deprecation warnings.
- The canonical `/data` inventory remains exactly 18,175 files /
  7,022,164,015 bytes at fingerprint
  `eda858b1db23dc58f22cdd0faa290f2141691fecf15862dc5bd6d095354834ff`.
  Outcomes, metrics, parameter/cohort selection, identity assignment,
  canonical writes, Historical Coverage, research admission, Candidate,
  publication, deployment, scheduler and external requests remain zero. The
  next work is the measured adjustment/terminal-evidence subset, not another
  global scan.

## 2026-09-13 — Cross-census residual corporate-action evidence

- Accepted ADR 0220 and added a one-to-one, assignment-free residual evidence
  census over the current Corporate Action Resolution Shadow, unresolved
  ticker census, both retained inactive-lifecycle anchors, and the complete
  official FINRA OTC range.
- The real owner-only run accounted for all 112,943 unresolved typed rows.
  Only 19 row/candidate occurrences fall inside an observed canonical span;
  2,386 occupy an unverified terminal gap, 1,449 contradict retained temporal
  boundaries, and 20,208 have no lifecycle evidence.
- FINRA supplies 20,679 exact date/symbol and 10,261 exact numeric candidate
  matches. Inactive-provider evidence touches 9,445 rows. Combined evidence
  touches 29,127 rows while 83,816 remain without a cross-evidence lead.
- The two-file / 4,183,894-byte package has logical fingerprint
  `3fbcf2719047bf753ed4014017a82f6d3a659e2d90be724e2b35a90cbabce525`,
  passed built-in and separate formal rereads, and left no symlink or staging
  residue. The full API suite passed 2,596 tests with two unchanged dependency
  warnings.
- Stable-ID assignment, source mutation, `/data`, canonical action, Adjustment
  Ledger, Historical Coverage, analytics, Candidate, publication, deployment,
  scheduler, and external-request counts remain zero. The next step is a
  first-strategy cohort intersection, not another global scan.

## 2026-09-13 — Add bounded Identity-only family-evidence publication path

- Accepted ADR 0219 and added a one-to-16-session Identity-only evidence plan
  for explicit canonical Instrument/Identity/Resolver snapshots. It binds the
  snapshot completion markers and all partition manifest/payload bytes without
  creating redundant EOD evidence.
- Extended the existing exact-plan Apply engine through a distinct operation,
  one-family execution binding, ordered one-target recovery, outside-inventory
  protection, atomic publication and formal reread. Existing current and
  reconciled-EOD two-family contracts remain unchanged.
- Added CLI routing and tests for exact multi-session source binding, source
  drift refusal, one-target Apply and zero-write completed recovery. The full
  API suite passes 2,592 tests with two unchanged dependency deprecation
  warnings.
- A separate read-only audit of canonical 2026-09-08/09 Identity snapshots
  measured 206 exact ticker/date resolutions among the 343 post-boundary
  corporate-action rows. The real no-write plan was then built and revalidated
  at SHA-256
  `f099929d17c07695d3b468910e1c7233bed74bab1714a81ad1189dc9cfb7317a`.
  It binds two sessions / 19,964 instrument records / 14 source files and one
  3,623-byte target. Exact user authorization then published only that target;
  outside-inventory identity remained unchanged and zero-write recovery passed.
- Rebuilt the private corporate-action resolution shadow and unresolved census
  as immutable `build=20260913-v2` objects. Exact-date resolution increased by
  the predicted 206 to 129,292 and unresolved rows fell to 112,943. The census
  accounts for those residual rows as 89,074 zero, 23,676 one and 193 multiple
  historical-candidate rows while retaining zero stable-ID assignments.
- Canonical inventory is now 18,175 files / 7,022,164,015 bytes with fingerprint
  `eda858b1db23dc58f22cdd0faa290f2141691fecf15862dc5bd6d095354834ff`,
  zero symlinks and zero residue. No Historical Coverage, research, Candidate,
  Production, website, deployment or scheduler authority was granted.

## 2026-09-13 — Classify unresolved corporate-action history without assignment

- Accepted ADR 0218 and added a deterministic eight-process census over every
  Resolver already bound to the five-year Corporate Action Resolution Shadow.
  It retains per-ticker source counts and per-candidate first/last/count
  evidence while fixing stable-ID assignments at zero.
- The real census classified all 113,149 unresolved typed rows / 13,931
  tickers: 89,074 / 11,433 have zero historical candidates, 23,879 / 2,456
  have one, and 196 / 42 have multiple. It records 2,540 ticker/instrument
  relations across 2,515 distinct candidate instruments.
- Only 253 one-candidate rows occur inside the candidate's observed span;
  23,626 occur before or after it. Of 3,856 missing exact Identity dates,
  3,394 precede the bound range, 343 are the later 2026-09-08/09 sessions, and
  119 are non-session dates. These remain evidence gates, not fallbacks.
- The two-file / 3,842,904-byte owner-only package has logical fingerprint
  `0dd861364c083e0e54b4d3d6a76a0fd5eacb14ae125490ffb111a3ec984b0296`.
  Build/readback took 183.59 seconds; an exact rerun returned
  `already_present` in 184.26 seconds with zero inode, size, time, or mode
  change.
- Focused regression passed 89 tests and the complete API suite passed 2,586
  tests with two unchanged dependency warnings. No request, `/data` write,
  canonical action, Adjustment Ledger, Historical Coverage, analytics,
  Candidate, publication, deployment, or scheduler change occurred. See the
  [dated audit](../audits/five-year-corporate-action-unresolved-census-2026-09-13.md).

## 2026-09-13 — Retain the five-year corporate-action resolution shadow

- Accepted ADR 0217 and extended the exact-event-date resolution shadow to
  compose multiple formally published Identity evidence manifests only when
  every overlapping artifact is identical. The first real union contains
  1,251 unique sessions and 287 conflict-free overlaps.
- The complete baseline contains 242,242 source rows. The durable owner-only
  result has 242,235 typed rows: 129,086 resolved and 113,149 quarantined.
  Seven missing/invalid-ticker dividends are retained in a separate hashed
  unrepresentable artifact, so source accounting remains exactly one-to-one
  without a fabricated ticker.
- The 14-file / 17,110,708-byte candidate has logical fingerprint
  `c71e0e481d83a23161f7130e45a55eac0e4895345108440b15d627232f1dfac1`.
  Its build completed in 488.33 seconds; an independent formal reread completed
  in 41.10 seconds. Files are mode 0400, directories mode 0700, with zero
  symlinks or staging residue.
- Company-action focused tests passed 76 cases and the complete API suite
  passed 2,581 tests with two unchanged dependency warnings. No request,
  canonical `/data` write, Historical Coverage, research input, Candidate,
  publication, deployment, or scheduler change occurred. See the
  [dated audit](../audits/five-year-corporate-action-resolution-shadow-2026-09-13.md).

## 2026-09-13 — Census SEC fundamental semantics before feature registration

- Accepted ADR 0216 and added an eight-process, worker-aligned streaming census
  for the 41,619,407-row normalized Company Facts ledger. It merges filed-year
  streams by original occurrence order and never creates a fact-by-session
  Cartesian panel.
- The real owner-only Dell run measured 24,498,347 exact semantic keys,
  24,497,828 clean revision-eligible keys, 519 quarantined keys, 17,117,677
  later revision states, and 886,400 consecutive value changes. It retained
  100 bounded hashed samples for 206 same-availability conflict buckets.
- The bound common-stock pilot has 5,019 distinct CIKs; 4,990 have in-range SEC
  facts and 29 do not. This remains later-observed diagnostic coverage and
  grants no issuer-to-security projection.
- The build and built-in readback completed in 246.18 seconds; a separate
  formal reread completed in 10.58 seconds. The 288,328-byte report has logical
  fingerprint
  `8899aeb278f50861952d7308a815c62640a2ec274bb1d614ff07f8ba651e3e21`
  and zero partial/staging residue.
- The implementation-stage SEC suite passed 245 tests and the complete API
  suite passed 2,577 tests with two unchanged dependency deprecation warnings.
  No request, `/data` write, feature, analytics, Candidate, performance,
  publication, deployment, or scheduler change occurred. See the
  [dated audit](../audits/sec-companyfacts-semantic-census-2026-09-13.md).

## 2026-09-13 — Reconcile retained FINRA and SEC foundation into main

- Recovered a clean 23-commit data sequence stranded on the older
  `codex/strong-leader-pullback-v2-admission` worktree and adopted its FINRA and
  SEC implementation, tests, contracts, operations guides, and dated audits.
  The branch's later UI-only commit and stale authority documents were excluded.
- Accepted ADR 0215 instead of overwriting main's independently assigned ADR
  0202–0211 files. It preserves FINRA as OTC/candidate corroboration, Company
  Facts as sparse filer-level revisions, conservative SEC acceptance clocks,
  stable-ID-only security links, and explicit no-projection/no-research limits.
- Main formally reread the sealed FINRA range and action census, Company Facts
  and Submissions censuses, 172,265 filing-clock rows, and the 8,201-row link
  pilot with their recorded logical fingerprints. The 41,619,407-row normalized
  source passed its separate full transitive reread in 2,508.68 seconds. The
  complete main API suite then passed 2,574 tests with two unchanged dependency
  deprecation warnings.
- The retained scope contains 436 files / 6,849,867,479 bytes with zero
  symlinks or partial/staging residue. It remains private evidence outside
  canonical `/data` and changes no Historical Coverage, research, Candidate,
  Production, website, or scheduler state. See the
  [integration audit](../audits/retained-finra-sec-foundation-integration-2026-09-12.md).

## 2026-09-12 — Retain the full-history inactive-lifecycle resolution shadow

- Re-resolved both persistent inactive-listing source anchors against 1,216 /
  1,251 canonical Instrument sessions using ADR 0213's deterministic eight-
  process reread. The 2026-07-16 anchor now has 2,206 review candidates and
  21,054 quarantines; 2026-09-03 has 2,278 and 21,191 respectively.
- Across anchors, stable-ID deduplication yields 2,283 distinct review-
  candidate instruments: 2,201 shared, five earlier-only, and 77 later-only.
  Every candidate retains five required evidence limitations and remains
  noncanonical.
- Accepted ADR 0214 and added an exact private-custody reader while leaving the
  builder `/tmp`-only. Broader and unapproved persistent roots fail closed;
  directory and file ownership, modes, symlinks, manifests, hashes, row
  lineage, and aggregate counts are all checked.
- Retained the exact six-file / 9,005,301-byte result through an owner-only
  staging directory and atomic no-overwrite rename. Source/persistent file-hash
  lists matched fingerprint
  `10dbda320316af93399f91e707bff615e6800237f99f5ba3d2a82aed9568f004`;
  both anchors passed formal persistent reread with zero residue.
- The focused suite passed 12 tests and the complete API suite passed 2,540
  tests; the two warnings are unchanged dependency deprecations.
- No request, canonical `/data` write, Historical Coverage, research admission,
  Production change, or deployment occurred. Lifecycle and terminal outcomes
  remain blocking. See the
  [dated audit](../audits/five-year-inactive-lifecycle-resolution-shadow-2026-09-12.md).

## 2026-09-12 — Publish corrected-edition EOD and Identity family evidence

- Applied the exact ADR 0211 plan only after authorization matched its file
  SHA-256, logical fingerprint, and family-set fingerprint. The locked,
  network-prohibited executor published EOD then Identity: exactly two
  manifests / 2,673,980 bytes, with zero reuse, overwrite, deletion, or
  external request.
- The outside-target inventory fingerprint remained
  `8baec95b3a4e81cc2b4ca05f9f1fb24a8a112237c6c217bf88c09066462aa307`
  before and after. The complete post-state fingerprint is
  `87a2a573b3350918a90db3cea51faaa1839a4e5fb420e2f20278dfc3cb9aa244`.
- Immediate `verify_then_complete` formally reread and reused both targets with
  zero published files / bytes. Independent current-context postflight found
  18,174 files / 7,022,160,392 bytes, four family-evidence manifests, zero
  symlinks, and zero residue.
- Final Historical Coverage remains absent and research remains data-blocked.
  Membership, lifecycle, actions, adjustments, availability lineage, costs,
  real chronological inputs, and holdout custody remain independent gates.
  Production and website state did not change. See the
  [dated audit](../audits/reconciled-eod-family-evidence-apply-2026-09-12.md).

## 2026-09-12 — Prepare recoverable corrected-edition evidence Apply

- Accepted ADR 0212 and added an explicit reconciled-edition Apply entry while
  retaining the older rolling-current entry and its default CLI behavior. Each
  entry selects its own formal reader and exact operation; neither can accept
  the other's source scope.
- Reused ADR 0166's single EOD-first executor, canonical lock, immutable target
  custody, outside-target drift check, network prohibition, atomic rename,
  formal reread, and ordered-prefix recovery instead of copying a second
  mutation path.
- The 32-test focused family-evidence suite proved temporary-root edition
  publication, current-entry refusal, and completed zero-write recovery. The
  complete API suite passed 2,533 tests with the two existing dependency
  deprecation warnings.
- No real Apply was run. The two corrected-edition evidence targets remain
  absent; no `/data`, Historical Coverage, research, Production, or website
  state changed.

## 2026-09-12 — Seal the corrected-edition family-evidence publication plan

- Accepted ADR 0211 and added a backward-compatible, edition-specific no-write
  plan contract. It reuses the existing two-family custody and recovery
  mechanics while binding the exact corrected edition ID and interval
  fingerprint. The legacy rolling-current plan reader rejects the new source
  scope, and the existing Apply entry point remains unchanged.
- The real eight-worker build reread 1,234 EOD and same-session Identity
  sessions and sealed exactly two absent evidence targets / 2,673,980 bytes.
  Plan SHA-256 is
  `d328f1725dc4a74a6237d30e1ccdad6fa8c64765d45210a8cc7a76d6492f9168`,
  logical fingerprint is
  `443d80c7347b794b7f105c2d8b5dc8e57fbc4d4dd67442773983647d69d0fcfc`,
  and family-set fingerprint is
  `30722680a6d2f8448db0e895fed7e060ca8a81f2d5faebca3b4d23fbba2b0d8e`.
- Independent exact-SHA reread reproduced all plan, source, target, count, and
  fingerprint bindings. The full API suite passed 2,531 tests with the two
  existing dependency deprecation warnings. No provider request, `/data`
  write, evidence publication, Historical Coverage, research authority,
  Production change, or website deployment occurred. See the
  [dated audit](../audits/reconciled-eod-family-evidence-publication-plan-2026-09-12.md).

## 2026-09-12 — Validate corrected-edition EOD and Identity family evidence

- Accepted ADR 0210 and added an edition-scoped, offline adapter rather than
  forcing the immutable corrected EOD edition through the rolling current-EOD
  evidence semantics. The adapter requires an exact edition ID and interval
  fingerprint and binds the interval marker plus every session manifest and
  Parquet file.
- A bounded eight-process formal validation completed in 374.70 seconds. It
  validated 1,234 EOD sessions / 10,376,263 rows and the exact 1,234
  same-session Identity snapshots / 10,472,243 instrument-snapshot records.
- The proposed EOD and Identity evidence logical fingerprints are respectively
  `b65ee35bb65796dab501d4e59df132bffc566452c713bb18e8659401b632b0a5`
  and
  `faaa73bceace816d91a5a2483714055d20c48091fe4fc8bfbcde8c27d8b647db`.
  Both remain `validated_not_published`; the previously published 304-session
  current evidence was neither reused nor overwritten.
- The complete 2,529-test API suite passed with the two existing dependency
  deprecation warnings. No provider request, `/data` write, Historical
  Coverage, research authority, Production change, or website deployment
  occurred. Membership, actions, lifecycle, adjustments, and final Coverage
  remain separate blockers. See the
  [dated audit](../audits/reconciled-eod-historical-mechanics-evidence-2026-09-12.md).

## 2026-09-12 — Complete and plan the first corrected EOD edition

- Built the clean contract 1.2 successor from revision
  `c798e582b0ad3b49ada5fc7fde94125382ef9c06` without reusing any stopped
  predecessor. All 31 batches and the final formal reread completed: 1,234
  sessions, 10,376,263 records, 947 retained-original and 287 visibly
  later-reacquired sessions.
- The sealed diff contains 2,461 accepted additions, 50 source-proven expected
  absences, 2,648,128 source-proven ticker-case repairs, and no blocking
  session. Interval fingerprint is
  `098ff756a463c0bf142d9ce597375e3a0574db02ca641fcdcef9b6e72cb6b5e3`.
- Verified owner-only candidate custody of 2,469 files / 1,083,699,732 bytes,
  with zero symlinks and zero staging or temporary residue.
- Generated and reread the exact no-write Apply plan. It binds all candidate
  artifacts and canonical inventory fingerprint
  `a83136b65d76371a9932aa58fc142aa815d1303dc89f600d852cc177eea36d5e`;
  its file SHA-256 is
  `7e9c13b957ad9e2fceb850e9da645356c2e1930800d943f2af3927da31115505`
  and logical fingerprint is
  `6a09ef14c77c475d46f0ae1d20f89058ea1457e32a1e633179b642edccbcf1d5`.
  It grants no Apply, research, Production, or website authority. Canonical
  `/data` and Production remained unchanged at planning time.
- After explicit approval, atomically published all 2,469 files /
  1,083,699,732 bytes and formally reread all 1,234 sessions / 10,376,263
  records. No prior target was reused, no existing partition was overwritten or
  deleted, and no external request was made.
- Independent postflight found 18,172 canonical files / 7,019,486,412 bytes,
  inventory fingerprint
  `8baec95b3a4e81cc2b4ca05f9f1fb24a8a112237c6c217bf88c09066462aa307`,
  zero symlinks, and zero publication residue. Existing EOD/Identity alignment,
  Production release, and freshness remain unchanged; Historical Coverage and
  all research/Production authority remain false.

## 2026-09-12 — Bind expected EOD additions to price-payload collisions

- The first clean contract 1.2 build completed 26 batches and retained 39
  successful sessions from batch 27 before stopping on 2025-11-18. The
  incomplete candidate contains 1,079 partitions, no interval marker, and made
  zero external requests or `/data` writes.
- The stopped later-reacquisition day had 9,041 economically identical shared
  records, no absences, and three additions. `SRVR` was the sole unexpected
  addition: exact price source contains `SRVR` and `SRVr`, while same-session
  Identity resolves only `SRVR` as an ETF to its existing stable ID.
- Corrected the edition builder to feed ADR 0203's existing exact-symbol
  addition classifier from Grouped Daily price symbols rather than Identity's
  narrower collision set. Identity remains the security-form and stable-ID
  authority; no ticker heuristic can establish eligibility.
- A dedicated price-only collision fixture and the real 2025-11-18 replay pass.
  The real diff now has three expected additions, 9,041 later-source
  provenance-only changes, and zero unexpected, absent, or economic changes.
  All 2,522 API tests passed with two pre-existing dependency deprecation
  warnings.

## 2026-09-12 — Type exact provider-ticker provenance repairs

- The clean 1.1 corrected-edition run completed seven batches and retained 300
  sessions before batch eight stopped on 20 dates with no interval marker and
  zero `/data` writes.
- All 20 dates had zero economic changes and zero unexpected additions or
  absences. Their only blocker was 30 source IDs whose legacy forced-upper-case
  ticker was restored to exact provider case while stable ID, timestamp,
  observation time, economic, quality, revision, and schema fields remained
  identical.
- Accepted ADR 0209 and versioned session, interval, Apply-plan, batch-result,
  and build-result contracts to 1.2. Only an eight-condition retained-source,
  same-session Identity and stable-ID proof may classify that provenance-only
  repair as expected.
- A network-disabled four-worker replay of all 20 dates returned 86 accepted
  additions, five ADR 0208 expected absences, 30 expected provenance repairs,
  and zero blocking or economic changes. Fifty-seven focused and all 2,521 API
  tests passed. A new clean 1.2 candidate must replace, not mix with, both
  stopped predecessors.

## 2026-09-12 — Type source-proven legacy case-misbinding removals

- The first real corrected-edition build validated 275 sessions before its
  seventh batch stopped on five October 2022 dates. The stop was safe, retained
  completed work, wrote no interval marker, and made zero `/data` writes.
- All five absences were the same exact-source defect: a retained `ALpA`
  preferred-stock bar had been upper-cased and falsely bound to common stock
  `ALPA` in EOD V1. Each date had no economic change and four or five valid
  case-sensitive additions.
- Accepted ADR 0208 and versioned session, interval, and Apply-plan manifests
  to 1.1. Only a seven-condition retained-source proof may classify an absence
  as expected; later-reacquired or otherwise unproven removals still fail
  closed.
- Added expected/unexpected absence accounting through diff, persistence,
  batch, full-build, interval, and Apply-plan boundaries. Sixty-two focused
  tests and all 2,519 API tests passed. A temporary real candidate then
  published and reread all five dates under manifest 1.1 with 21 additions,
  five expected absences, zero unexpected absence, and zero economic change.
- The incomplete 1.0 candidate remains non-authoritative evidence and will not
  be mixed with the new clean 1.1 candidate. See the
  [dated build audit](../audits/reconciled-eod-edition-first-build-2026-09-12.md).

## 2026-09-12 — Bound the first corrected EOD edition at fully proven source custody

- Corrected the independent-gap diagnostic, reacquired the two additional
  Grouped Daily packages hidden behind Identity-source failures, and confirmed
  final owner-only custody of 307 sessions / 614 files / 384,055,489 bytes.
- The final four-worker census formally reread all 1,255 rolling sessions and
  reports 948 retained-original plus 305 later-reacquired selected sources,
  zero price gaps, zero conflicts, and only two Identity-source-invalid dates.
- Isolated later-Identity reconstructions for 2026-08-13 and 2026-08-19 passed
  price quality gates and had no economic changes, but omitted one and five
  canonical business keys. The no-removal gate remains unchanged.
- Accepted ADR 0207: the first real immutable corrected-price candidate is the
  maximal preceding continuous interval of 1,234 XNYS sessions from
  2021-09-13 through 2026-08-12. This grants construction scope only, not
  research, performance, canonical Apply, Production, or deployment authority.

## 2026-09-12 — Run the initial Reconciled EOD source reacquisition

- The first four-worker, network-disabled census formally reread all 1,255
  rolling target sessions and selected 948 retained-original source packages,
  with 305 Grouped Daily packages missing, two Identity-source bindings
  invalid, and zero conflicts.
- Reacquired the 305 dates explicitly exposed by that first census in eight
  bounded invocations: 305
  provider attempts, zero transient retries, and zero failures. Owner-only
  custody contains 610 files / 381,337,205 bytes with zero symlinks or staging
  residue; `/data` writes remained zero.
- The independent-gap correction and two additional price packages are recorded
  in the newer 2026-09-12 entry above; that entry is the authoritative final
  state rather than this initial execution checkpoint.
- Research admission, corrected-edition construction, canonical EOD,
  Production, publication, and deployment remain unchanged. See the
  [dated audit](../audits/reconciled-eod-source-reacquisition-2026-09-12.md).

## 2026-09-11 — Complete the rolling price foundation and deploy the fresh daily release

- Applied exact 2026-09-10 and 2026-09-11 Identity/EOD plans under the
  revision-bound data-only control. The 2026-09-10 MI plan was correctly left
  inactive after becoming stale by one session.
- The natural 20:30 UTC read-only wake selected 2026-09-11 without making a
  provider request or write. The guarded manual chain then completed nine
  offline stages, fresh MI 1.3 and Snapshot 1.11 / Dashboard 2.8 publication,
  a 61-file Serving Bundle, OCI dry-run, Apply, and independent postflight.
- Production now serves release `2026-09-11T211340Z-26cab64fabda` from clean
  source `26cab64fabdafca710d6471cb09ac8c62ef17c2d`. Guest and credential
  capability remain identical; no staging/failed release or failed service
  was found.
- The fresh rolling census confirms zero EOD/Identity gaps across 1,255 XNYS
  sessions from 2021-09-13 through 2026-09-11. It remains quarantined because
  Membership, lifecycle, complete actions/adjustments, classification,
  chronological evaluation, costs, and holdout evidence are incomplete.
- Candidate remained the daily performance hotspot at about seven minutes and
  one CPU core, with observed RSS peaking near 11.2 GiB. No performance or
  model-activation claim was added. See the
  [dated audit](../audits/daily-eod-publication-deployment-2026-09-11.md).

## 2026-09-11 — Align initial warm-up with the rolling Starter window

- Accepted ADR 0206 after the owner declined a deeper subscription solely for
  two fixed-run boundary dates and an external warm-up. The stopped 1,255-day
  run remains preserved as historical evidence and is not restarted.
- Normal daily updates, rather than an ad hoc deletion, will move the rolling
  five-calendar-year source target. Once latest canonical EOD reaches
  2026-09-11, the expected first XNYS target session is 2021-09-13; a fresh
  network-disabled census must verify that state.
- The first 20 available target sessions become explicit outcome-free feature
  warm-up. Signals and performance begin only afterward, so the product may
  claim five-year source scope but not a full five-year performance interval.
- Retained the optional external-warm-up contracts for future deeper data but
  removed that acquisition and the expired dates from the current action path.
  No provider request, `/data` write, research run, publication, Production
  change, or deployment occurred.

## 2026-09-11 — Qualify the live Flat File OHLCV boundary

- Strict owner-only S3 credential loading passed. A 2026-09-09 Day Aggregates
  Flat File succeeded in one request, while 2021-09-09 returned the newly
  classified access-denied stop. This proves current Flat Files access but not
  Starter depth beyond its rolling boundary.
- A newly fetched 2026-09-09 Grouped Daily REST control and the Flat File were
  rebuilt through the same case-sensitive Identity-bound path. All 9,945
  shared records matched exactly on OHLCV, trade count, currency, and
  adjustment fields. REST had 13 additional zero-volume records; Flat File had
  no VWAP values.
- The comparison explains the earlier same-evening canonical differences as
  source finalization rather than Flat File OHLCV disagreement. Flat Files
  remain an independent cross-check, not a silent field-equivalent substitute.
- Added a dated cross-source audit and updated the preferred remaining-gap
  route to temporary 10-year entitlement plus the existing REST schema, or a
  separately qualified alternative source. No `/data`, research, Production,
  publication, or deployment write occurred.

## 2026-09-11 — Classify Flat File transport stops safely

- Split the former generic S3 Flat File transport error into stable
  access-denied, object-not-found, and unclassified-transport error classes.
- Classification uses only the standard S3 error code and HTTP status. It does
  not retain or emit provider messages, request identifiers, response bodies,
  or credentials.
- Added fixture regression for 403, 404, 503, and non-provider transport
  failures. The focused suite passed 10 tests and the complete API suite passed
  2,514 tests with only the two existing dependency deprecation warnings. No
  provider request, data write, publication, or deployment was performed by
  this code change.

## 2026-09-11 — Preserve the terminal five-year EOD/Identity boundary

- The sole bounded `20260911g` continuation completed eleven full batches and
  most of its final batch before failing closed when Grouped Daily REST denied
  2021-09-10. All complete batches reported zero transient retries.
- A network-disabled post-stop census found 1,253 canonical EOD sessions,
  1,254 physical Identity sessions, and 1,253 EOD-aligned Identity sessions.
  The exact remaining gaps are EOD 2021-09-09/10 and Identity 2021-09-09.
- Direct quiescent checks found zero symlinks, zero staging/partial directories,
  and no remaining historical writer. The retained 2021-09-10 Identity package
  and Apply plan remain available for reuse; no 2021-09-10 EOD package and no
  2021-09-09 workspace were created.
- Grouped Daily REST retry is rejected because the independent exact-date probe
  already established the same denial. The next price route is the existing
  fixture-tested Day Aggregates Flat File adapter after separate S3 credential
  provisioning and a bounded live pilot.
- Added a dated terminal audit and clarified that the legacy 504-session
  planning CLI is not the verifier for the frozen 1,255-session interval. No
  provider request, canonical write, research run, publication, or deployment
  was performed by this documentation-only reconciliation.

## 2026-09-11 — Separate warm-up source custody from evaluation custody

- Reserved a distinct owner-only historical source workspace for the 20
  warm-up sessions instead of placing them beneath the legacy evaluation
  workspace whose name begins at 2021-09-09.
- Source Coverage now models `historical_warmup` as a distinct source origin,
  binds its exact retained Apply/package evidence, and can resolve it without
  ambiguous same-origin directory precedence. Retained-original provenance
  semantics remain unchanged.
- The existing bounded historical executor already accepts the separate direct
  child workspace; the runbook now records its exact warm-up invocation. No
  workspace, package, canonical partition, provider request, or candidate was
  created by this change.
- Focused coverage, build, and reacquisition regression passed 37 tests; the
  complete API suite passed 2,510 tests with only the two existing dependency
  deprecation warnings.

## 2026-09-11 — Preserve warm-up outside the five-year evaluation interval

- Extended Reconciled EOD Source Coverage to declare optional paired warm-up
  bounds separately from the evaluation bounds. Coverage now requires the
  complete ordered warm-up-plus-evaluation session inventory while retaining
  the exact evaluation-first session.
- The full-edition controller now carries those bounds into the final interval
  manifest and verifies them on formal completion. The coverage CLI exposes
  explicit warm-up arguments.
- The intended real scope remains 1,255 evaluation sessions from 2021-09-09
  through 2026-09-09 plus 20 warm-up sessions from 2021-08-11 through
  2021-09-08. The active service still covers only the exact evaluation run;
  no warm-up acquisition, coverage census, candidate build, or `/data` write
  was performed by this change.
- Focused coverage/complete-build regression passed 32 tests; the complete API
  suite passed 2,509 tests with only the two existing dependency deprecation
  warnings.

## 2026-09-11 — Automate resumable full Reconciled EOD candidate build

- Added a complete-interval controller and CLI that consume only one exact
  build-ready coverage artifact, bind its file hash and the clean 40-character
  source revision, and divide the declared sessions into bounded 1–40-session
  batches with at most four workers.
- Each batch revalidates selected sources, emits a safe checkpoint, and retains
  successful immutable partitions if another session fails. Reuse now also
  requires the same fixed candidate creation time, preventing one logical
  edition from silently mixing invocations.
- The controller publishes the sole interval completion marker only after
  every exact session succeeds and a full memory-bounded formal reread matches
  session, provenance, addition, and implementation bindings.
- Focused build, batch, source-coverage, and persistence regression passed 47
  tests; the complete API suite passed 2,506 tests with only the two existing
  dependency deprecation warnings. No real candidate build, `/data` write,
  provider request, Apply, research run, publication, or deployment occurred.

## 2026-09-11 — Prepare coverage-bound EOD source reacquisition

- Added exact owner-only custody for later-observed Grouped Daily packages and
  extended formal Grouped Daily package reread to accept that custody without
  broadening Identity-source paths.
- Added a source-reacquisition runner and CLI that require the exact sealed
  coverage file hash, accept only explicit 1–40-session source-only gaps,
  revalidate canonical EOD/Identity/source bindings, serialize provider
  requests, bound transient retries, and resume only from formally valid
  immutable packages.
- The result exposes dates, counts, hashes, provenance, and bounded failure
  codes while keeping credentials and provider response bodies out of output.
  It writes no `/data`, research result, publication, deployment, or authority.
- Focused custody, package, runner, and CLI regression passed 39 tests; the
  complete API suite passed 2,496 tests with only the two existing dependency
  deprecation warnings. No real provider request or source reacquisition ran;
  the active historical writer remained the sole `/data` writer.

## 2026-09-11 — Bind corrected EOD construction to exact source coverage

- Added a sealed Source Coverage 1.0 contract for every declared XNYS session:
  retained original, later reacquisition, missing, invalid, or conflict. The
  artifact contains package/canonical fingerprints and provenance but no home
  paths or response bodies.
- A retained original now requires a formal reread of its exact historical
  canonical Apply plan and matching package, EOD, and same-session Identity
  fingerprints. Multiple eligible originals fail as conflict; the daily
  workspace's Identity package is not mistaken for Grouped Daily.
- Added immutable 0400 coverage persistence, byte-hash reread, a network-free
  census CLI, and a candidate-batch CLI that requires the exact coverage hash,
  explicit 1–40 ordered sessions, and `--execute`. Incomplete coverage cannot
  feed construction, and each package is formally rebound before use.
- Implementation and batch-execution tests ran against temporary fixtures. One
  network-free real single-session coverage pilot ran, but no full-interval
  coverage census, source reacquisition, candidate build, `/data` write,
  provider request, interval completion, Apply, research admission,
  publication, or deployment ran.
- A separate lightweight read-only intersection found 777 retained Grouped
  Daily dates among 1,082 then-canonical EOD sessions and 305 canonical dates
  without a retained package. It found no package-only orphan and remains only
  a reacquisition-sizing diagnostic until the writer stops and formal census
  runs.
- Focused source-coverage and batch regression passed 32 tests; the complete
  API suite passed 2,486 tests with only the two existing dependency
  deprecation warnings.
- A real network-free 2026-09-08 pilot formally selected the daily-automation
  retained original with zero gaps/conflicts, external requests, or canonical
  writes. It also exposed stale editable-install metadata pointing at an older
  worktree. The active backfill was verified safe because its admin entry point
  already uses the canonical-source project Python wrapper; all Reconciled EOD
  runbook commands now use that wrapper as well.

## 2026-09-11 — Bound and resume corrected EOD session construction

- Added explicit preparation of one incomplete owner-only edition and a
  network-disabled batch primitive limited to 1–40 ordered sessions and 1–4
  spawned workers.
- Exact completed sessions are formally reread and reused only when the
  selected package fingerprints and provenance match. A failed session remains
  visible without discarding other completed partitions; no batch writes the
  interval marker or canonical `/data`.
- Kept source selection out of the builder. A formal post-acquisition coverage
  and selection plan remains required because current retained Grouped Daily
  custody does not yet cover every canonical session. No real candidate build,
  provider request, Apply, research admission, publication, or deployment ran.
- Focused Reconciled EOD regression passed 47 tests and the complete API suite
  passed 2,465 tests with only the two existing dependency deprecation warnings.

## 2026-09-11 — Implement whole-edition corrected EOD Apply custody

- Extended Reconciled EOD candidate custody from bounded `/tmp` tests to one
  direct owner-only child of the fixed Dell persistent base. Candidate
  directories/files remain 0700/0600 and retain no research or Production
  authority.
- Changed full-edition validation to process one complete daily cross-section
  at a time while retaining only manifest evidence, removing the five-year
  all-rows memory growth without weakening schema, hash, row-contract, content,
  or interval validation.
- Added a sealed exact Apply plan that binds every artifact, interval
  fingerprint, counts, revisions, absent target, and the full canonical
  pre-state. Added a shared-lock, network-disabled, no-overwrite executor that
  copies to adjacent staging, verifies bytes, publishes by one atomic directory
  rename, and formally rereads the completed target. Explicit recovery can only
  reuse the exact completed target; unknown staging is retained for diagnosis.
- Added an operator CLI whose Apply path requires the plan byte hash, logical
  fingerprint, expected pre-state fingerprint, and `--execute`. These mechanics
  were exercised only against temporary test roots; no real edition Apply,
  model admission, analytics, OCI publication, or deployment ran.
- Focused Reconciled EOD regression passed 34 tests and the complete API suite
  passed 2,452 tests with only the two existing dependency deprecation warnings.
- Started the sole bounded `20260911g` five-year continuation from clean source
  `6851d005bd9808d970e49988000223ff4898dd16`. At the 00:41:27 UTC live
  checkpoint it was active and EOD/Identity were aligned at 1,033 sessions
  through 2022-07-28; the run was not declared complete.

## 2026-09-11 — Bound missing-type rows in historical Identity reconstruction

- Accepted ADR 0205 after the five-year continuation stopped before
  2022-08-19 Identity with 168 missing-security-type rows among 12,172 source
  observations. All 168 remain rejected and absent from Instrument, Resolver,
  Universe, Membership, signal, and performance populations.
- Kept the prospective/current malformed ceiling at 1.0% and set only the
  explicit historical-reconstruction ceiling to 2.0%. All other quality gates
  remain unchanged.
- Confirmed from retained adjacent source that 94 rows were still untyped on
  2022-08-22, while 73 then carried `SP` and one `FUND`; none of those later
  labels is projected backward.
- A zero-request isolated replay produced 8,373 Instrument/Resolver rows and
  all five expected Identity targets. Focused regression passed 68 tests.
  After the added gate-evidence and immutable-edition boundary tests, the
  complete API suite passed 2,438 tests.
- Clean source `49ef83a4bc5ee70914eabb9930a8c9f7c6d78f3b` reused the
  2022-08-19 Identity package with zero requests, acquired EOD in one request,
  formally published and reread both families, and aligned 1,017 sessions
  through 2022-08-19. No analytics, publication, or deployment ran.

## 2026-09-10 — Choose a complete immutable corrected EOD research edition

- Accepted ADR 0204: repair the affected historical price family beside EOD V1
  as a complete, explicitly selected edition rather than overwriting immutable
  partitions or imposing a permanent sparse overlay on every research reader.
- Required per-session bindings to exact EOD source custody, canonical and
  source Identity fingerprints, mapper revision, base V1 comparison, and typed
  diff counts. Reacquired packages remain visibly later provenance.
- A final interval manifest is the only completion marker. Partial sessions,
  missing source, unexplained removals, and changed economic values carry no
  research authority.
- Implemented the sealed session/interval contracts, typed full-session diff,
  exact case-collision addition set, formal canonical-record reread, validated
  Grouped Daily package reader, and isolated one-session candidate builder.
  A fixture reproduces the historical defect and proves that only the expected
  missing common-stock bar is admitted. Focused regression passed 118 tests;
  the complete API suite passed 2,430 tests.
- Added owner-only isolated candidate persistence, atomic per-session writes,
  immutable rerun conflict checks, Parquet/schema/hash/fingerprint reread, and
  a final interval manifest as the sole completed-edition boundary. Partial,
  symlinked, tampered, or residue-bearing editions fail closed. The complete
  API suite passed 2,436 tests before the later ADR 0205 gate change.

## 2026-09-10 — Preserve Massive case-sensitive provider symbols

- Accepted ADR 0203 after the five-year continuation stopped on six false
  duplicate pairs in the retained 2022-10-07 Grouped Daily package. Massive
  symbol case is now preserved as an exact provider join key and bound to
  same-session Identity source evidence before EOD resolution.
- Kept the duplicate gate unchanged and prohibited mixed-case projection
  through the upper-case V1 Resolver when exact source evidence is absent.
  Exact provider spelling never establishes security eligibility by itself.
- A real zero-write replay passed all gates with 10,914 raw rows, 8,136
  canonical rows, 426 evidence-backed mixed-case exclusions, and zero false
  conflicts. Focused regression passed 92 tests and the complete API suite
  passed 2,417 tests.
- Confirmed a pre-existing historical defect: at least 1,862 resolved bars are
  missing across 676 published sessions whose retained packages were audited.
  Existing partitions remain immutable and research-quarantined pending a new
  corrected physical version or append-only correction family.
- Reused the retained 2022-10-07 EOD package with zero external requests,
  formally published and reread 8,136 rows, and started one unique bounded
  continuation. Its first live checkpoint aligned EOD and Identity at 984
  sessions through 2022-10-06.

## 2026-09-10 — Govern Massive VWAP float-tail normalization

- Accepted ADR 0202 after the retained 2022-12-05 package showed 314 VWAP
  values with provider-serialized scales 16–20 and a maximum scale-10
  round-half-even change of only `1E-16`.
- Normalize only over-scale Grouped Daily VWAP at the provider mapping
  boundary. Every affected canonical row is flagged, the session manifest and
  safe output retain the normalization count, and duplicate comparison uses
  the same canonical resolution.
- Preserved the exact immutable source package and the strict provider-neutral
  Decimal128 repository. OHLC, volume, missing values, quality gates, and
  persistence rejection semantics are unchanged.
- The real package passed a zero-write quality replay with 11,084 raw rows,
  8,156 canonical rows, and all 314 normalizations accounted for. Focused
  tests passed 87 cases and the complete API suite passed 2,413 cases.
- Reused the retained 2022-12-05 package in a zero-request recovery, formally
  published and reread that EOD partition, then started one bounded unique
  continuation from clean source. The live aligned checkpoint advanced to at
  least 944 EOD/Identity sessions through 2022-12-02.

## 2026-09-10 — Retain the five-year backfill VWAP precision stop

- The bounded `20260910d` continuation advanced to 942 contiguous EOD and 943
  Identity partitions before failing closed on 2022-12-05 EOD. The retained
  Identity-only edge is 2022-12-05; one provider VWAP exceeds the canonical
  decimal scale of 10 and was not silently rounded or skipped.
- A network-free quiescent report verified 12,216 files / 4,732,957,086 bytes,
  zero symlinks, zero publication residue, and inventory fingerprint
  `f89a02ad0625b8391dc46e383e8056567c64c94b682e29ab0395f63008501559`.
  The failed service remains stopped pending an explicit precision policy and
  regression fixture.

## 2026-09-10 — Recast the product workspace as an institutional research terminal

- Reworked the authenticated and equal-capability guest application without
  changing the public entry, data contracts, model authority, or analytics.
  The shell now exposes the current workspace in a compact utility bar and
  uses a quieter, denser navigation hierarchy.
- Introduced one bounded application-only visual system across Quant Research
  Lab, Model-Driven Equity Selection, and all three market tools. It replaces
  glow-heavy gradients, floating cards, oversized headings, pill overuse, and
  decorative motion with flat analytical surfaces, table-like groups,
  restrained status color, compact controls, and consistent responsive rules.
- Kept route-level code splitting and three-language behavior unchanged. The
  complete stylesheet remains below the build-failing size budget; no image,
  font, package, data, or runtime dependency was added.
- Aligned serving-bundle locale evidence and the default for future Market
  Intelligence publications with the implemented `en`, `zh`, and `es`
  interface. The active immutable analytics publication was not rewritten.
- Deployed immutable OCI release `2026-09-10T211413Z-030f75578668` from source
  `030f75578668`. Independent postflight matched release, source, bundle,
  manifest, checksums, protected routes, guest access, identical guest and
  credential policy, services, listeners, and zero staging/failed residue.
  Password login and final human visual review remain manual checks.

## 2026-09-10 — Bound frontend weight and add governed Spanish localization

- Split all five application workspaces into on-demand chunks and added
  intent preloading. The default Quant Research Lab path no longer downloads
  Candidate or ECharts-heavy Market Structure code before it is needed.
- Added build-failing raw-size budgets for entry JavaScript, asynchronous
  JavaScript chunks, and the shared stylesheet.
- Added a complete neutral-Spanish interface catalog, including the public
  entry and Quant Research Lab, with exact key and placeholder parity checks.
  The Spanish dashboard catalog loads only after explicit selection or a
  Spanish deep link; no English/Chinese user downloads it on first entry.
- Preserved English as default, exact query/Universe state, Session behavior,
  equal guest/credential capability, fail-closed data behavior, and all model
  and Candidate authority boundaries.
- Reduced the default Quant Research Lab path from about 297.6 KiB to 106.3
  KiB gzip JavaScript. The separately loaded Spanish catalog is about 23.3
  KiB gzip; the ECharts-heavy Market Structure chunk is deferred until use.
- Deployed immutable OCI release `2026-09-10T204516Z-d8c05139cdfd` from source
  `d8c05139cdfd`. Independent postflight matched release, source, bundle,
  manifest, checksums, protected routes, guest access, identical guest and
  credential policy, services, listeners, and zero staging/failed residue.
  Password login and final human visual review remain manual checks.

## 2026-09-10 — Make Quant Research Lab the default core workspace

- Replaced the five-item numbered peer navigation with two explicit groups:
  `Research system` and `Free market tools`.
- Made Quant Research Lab the default workspace, placed Model-Driven Equity
  Selection directly beneath it as the reserved consumer of activated models, and moved the
  three stable market-context workspaces into a visually secondary free-tools
  group.
- Preserved explicit deep links, Universe selection, bilingual state,
  Session behavior, equal guest/credential capability, and all existing page
  implementations. Baseline V1 Candidate data remains present and explicitly
  unvalidated; no model or ranking authority changed.
- Deployed the hierarchy as immutable OCI release
  `2026-09-10T195907Z-059a8cc3133d` from source `059a8cc3133d`; independent
  postflight matched release identity, source, manifest, checksums, protected
  routes, equal guest/credential policy, services, listeners, and zero
  staging/failed-release residue.

## 2026-09-10 — Reframe the public entry around transparent quantitative research

- Replaced the second-screen loose four-card mosaic with one dominant Quant
  Research Lab core and a connected vertical rail for the current research
  record, downstream model-driven selection, and planned research automation.
  Deployed the responsive hierarchy as immutable OCI release
  `2026-09-10T193258Z-ef702eb26d24`; independent postflight passed.
- Reworked the landing visual language from rigid bordered grids to a softer
  premium research surface: floating rounded navigation and access panel,
  layered light and depth, an animated non-representational signal path,
  asymmetric research cards, and responsive continuation cues. Tightened copy
  to distinguish preregistration, unavailable evidence, inactive authority,
  and the planned AI layer without adding claims or changing product behavior.
- Refined the first-viewport hierarchy after visual review: the conventional
  username/password login is primary, equal-capability guest access follows
  directly below it, and a visible animated continuation rail leads into the
  research narrative on desktop and mobile. The research dossier moved below
  the entry surface; authentication and authorization behavior did not change.
- Replaced the equal-weight nine-capability landing narrative with a compact
  research-first entry centered on Quant Research Lab, model-driven equity
  selection, and a governed research-automation extension.
- Added a truthful Strong-Leader Pullback V1 research dossier that shows the
  point-in-time foundation still building, the model specification locked,
  out-of-sample evidence unpublished, Candidate authority inactive, and no
  performance claim.
- Kept Market Regime & Opportunities, Sector ETF Rotation, and Market
  Structure & Activity visible as free supporting tools rather than the main
  product identity.
- Preserved English-default bilingual copy, the existing credential and guest
  Session behavior, equal capability, data-free public entry, and the shared
  WH Alpha favicon. No model, data, ranking, access, or authentication behavior
  changed.
- Replaced deployment checks for retired marketing copy and exact button
  capitalization with the stable `quant-research-v1` entry contract and
  structural controls after those stale gates safely rejected and rolled back
  the otherwise valid new page.
- Initially deployed the research-first entry as immutable OCI release
  `2026-09-10T184018Z-03c277579502`, then deployed the login-first refinement
  as `2026-09-10T185300Z-4c0719b9b4a4`, and the visually softened,
  copy-tightened refinement as `2026-09-10T190406Z-05ea9f79a4a9`.
  Independent postflight matched the latest exact source, bundle, checksums,
  protected routes, equal-capability guest Session, services, listeners, and
  zero active staging/failed-release residue.

## 2026-09-10 — Localize a historical Identity alias-revision stop

- The finite EOD/Identity continuation completed through 2025-01-23 and
  stopped aligned at 409 sessions before publishing 2025-01-22 Identity.
- Formally reread the retained package and isolated 58 collision observations
  in 29 two-ticker Share Class FIGI groups: 0.6199% of 9,356 eligible rows.
  The other 8,467 observations resolve independently at 90.4981% coverage.
- Accepted ADR 0201. Historical reconstruction now has an explicit 1.0%
  catastrophic collision ceiling; current/prospective snapshots retain 0.1%.
  Every conflicting row remains ambiguous and absent from Instrument and
  Resolver output, and the applied gate is persisted with the plan/manifest.
- No conflicting ticker was chosen, no lifecycle fact inferred, and no
  Production or OCI state changed.

## 2026-09-10 — Scale corporate-action source custody to five years

- Accepted ADR 0198 after the real 15-month dividend package used 14 of the
  original 16 pages, proving that the Basic-plan ceiling could not represent
  the selected five-year range.
- Added backward-compatible source-package 1.1 with finite 80-page / 400,000-
  row ceilings and an exact persisted 0.25-to-15-second serial interval. Zero
  automatic retry, immutable pages, formal resume reread, request-chain
  validation, secret stripping, 32-MiB page limits, and the 512-MiB package
  limit remain unchanged.
- Preserved formal read compatibility for real 1.0 custody and added tests for
  more than 16 pages, interval persistence, and interval-drift refusal.
- Acquired an initial five-year split source package for 2021-08-11 through
  2026-09-09: 2 pages / 6,491 records, natural pagination complete, zero
  invalid dates, duplicate source IDs, and unexpected fields. It remains
  source-observation-only and no canonical or Production state changed.
- Completed the matching five-year dividend package in 48 pages / 235,751
  rows. Six annual observations sum to the same count and match all unique IDs
  and payloads exactly; the 400,000-row and 512-MiB finite limits were not
  approached dangerously.
- Repeated both complete ranges. All dividend rows were unchanged. Five split
  source IDs were replaced while every non-ID payload field remained identical;
  annual split observations match the repeat IDs. Preserved this as an
  append-only source-revision requirement rather than five economic additions
  and deletions or an arbitrary first-non-null choice.
- Copied all 193 corporate-action baseline, annual, repeat, and diff files into
  Dell owner-only persistent historical-source state. Byte counts and recursive
  content match exactly; this is recovery custody, not canonical `/data` or
  research authority.
- Accepted ADR 0199 and added an exact-root persistent source-package reader.
  All 16 retained packages passed full reread; acquisition remains `/tmp`-only,
  arbitrary paths fail closed, and the resolution shadow can consume only an
  explicitly supplied owner-only custody root.
- Accepted ADR 0200 and retained both complete inactive-listing source anchors
  in owner-only Dell state. The exact-root reader formally reproduced all
  46,729 overlapping source rows and their original fingerprints without
  promoting a lifecycle or terminal fact.
- Formally recovered the 2025-04-23 EOD continuation after the prior whole-root
  CAS stop by preserving the stale plan/artifacts under explicit failed-attempt
  names, rebuilding against current inventory, reusing the verified package,
  and applying with zero external requests. The unique continuous unit then
  completed its first 20-session checkpoint through 2025-03-25 without retry.

## 2026-09-10 — Separate historical research Membership custody

- Accepted ADR 0197. Latest-vintage reconstructed historical Membership will
  use a durable research-only `/data` family and marker; the existing
  signal-eligible Membership and next-open publication reader remain unchanged.
- Bound the research marker to exact manifest/Parquet bytes and denied signal,
  validation, holdout, performance, Candidate, Production, and web authority.
- Identified the exact 20-session trailing-liquidity support interval required
  before the first five-year evaluation session: 2021-08-11 through
  2021-09-08. These sessions are warm-up custody, not part of the 1,255-session
  evaluation count.
- Started the finite Dell exact-interval EOD/Identity unit at 2026-09-10
  08:54:25 UTC. It has 24-hour, 2-GiB, serial-request limits and retains each
  completed session independently; no Production or OCI state changed.
- Implemented typed research-custody and exact Apply-plan contracts, a formal
  marker/Parquet reader, atomic no-overwrite Apply, resumable bulk archive, and
  census integration. Related fixture and regression tests pass.
- Applied and formally reread all 300 candidate sessions / 5,571,154 decisions
  from 2025-06-23 through 2026-09-03 with zero failures, overwrites, deletions,
  or external requests. Signal-eligible Membership paths remained untouched.
- The postflight five-year census reports 303/1,255 Membership sessions,
  including the three prospective sessions, at mixed evidence tier. It remains
  quarantined with fingerprint
  `c193895b7cb795fb5054c5e8493bb7c5e438e646c37e03d336a82d52f3a903e7`.
- The concurrent EOD/Identity unit correctly stopped on whole-data CAS drift
  after the research-family write. EOD reached 346 sessions; Identity reached
  347 with 2025-04-23 retained as the one Identity-only continuation point.
  No overwrite or staging residue occurred. Canonical writers will resume
  serially.

## 2026-09-10 — Adopt a Dell-owned five-year point-in-time foundation

- Accepted ADR 0196 and made a rolling five-calendar-year point-in-time
  foundation the first complete research-data target. Six- or twelve-month
  model windows remain calibration choices rather than database-retention
  limits.
- Kept Massive Stocks Starter as the primary price/reference input while
  assigning bounded corroboration roles to SEC EDGAR, FINRA OTC evidence,
  OpenFIGI, Alpha Vantage Listing Status, prospective Nasdaq Trader directories,
  and named official issuer/venue records.
- Superseded the mandatory LSEG-first implementation order without weakening
  the existing stable-ID, source-time, sample, permission, conflict,
  completeness, or quarantine gates. Paid expansion now follows a measured
  residual-gap census.
- Preserved the current 100%-complete session-cross-section admission rule and
  all research/holdout/activation boundaries. This entry records the decision
  only.
- Implemented the typed, fingerprinted, network-disabled five-year coverage
  census and ran it against Dell. The exact target is 1,255 XNYS sessions from
  2021-09-09 through 2026-09-09. EOD/Identity cover 306 sessions, normalized
  Identity source custody covers 304, and Membership covers three; lifecycle,
  PIT classification, PIT fundamentals, and complete Historical Coverage are
  absent. The result is `quarantined`, fingerprint
  `c19c520f202aacef0dada46cf82e984ccba6b77078d667363eccfcc152a81bfb`.
- The census made no provider request, `/data` write, performance result,
  publication, deployment, scheduler, or Production change.
- Made the existing Massive historical entitlement probe work from a saved
  Codex worktree by resolving the shared project Python runtime through the
  repository launcher; request limits and exact-authorization behavior are
  unchanged.
- Ran exact non-retaining Stocks Starter probes for 2021-09-09, 2021-09-10,
  and 2022-09-09. Grouped Daily REST denied the two 2021 sessions and returned
  11,063 rows for 2022-09-09; PIT Tickers, splits, and dividends were accessible
  on every tested date. Selected the documented five-year Day Aggregates Flat
  File route for bulk price history, while preserving REST as fallback and
  reconciliation evidence. No response body or data write was retained.
- Implemented the Dell-only Massive Day Aggregates Flat File fetch boundary.
  It retains the raw gzip and object evidence, normalizes the fixed CSV schema
  into the existing EOD package shape, and formally reparses/reconciles raw
  bytes before the existing offline plan may use them. Separate owner-only S3
  credentials and an optional boto3 dependency keep OCI and the REST secret
  boundary unchanged. The adapter is fixture-tested; no live S3 request or
  `/data` write occurred.
- Ran its first exact live attempt for the 2021-09-09 Day Aggregates object.
  The separate S3 credential was not configured, so the adapter stopped before
  transport with zero requests and zero writes. Retained this as a
  source-specific blocker rather than retrying REST or stopping other families.
- Extended the resumable EOD/Identity executor with a frozen-interval mode for
  2021-09-09 through 2026-09-09. It validates the exact 1,255 XNYS sessions and
  refuses boundary drift. Added an explicit 0.25-to-15-second serial interval
  for paid unlimited-call plans; provider concurrency remains disabled and the
  historical 300-session planning contract remains intact.
- Replaced the historical executor's reboot-sensitive `/tmp`-only limitation
  with one fixed owner-only Dell state boundary. Only a direct 0700 child of
  that base is accepted; `/tmp` remains available for bounded pilots.
- Unified historical session package, Apply-plan, and plan-artifact names with
  the existing persistent daily custody roles. A first real attempt exposed
  and then closed the nested source-custody validation gap before any
  canonical partition was written.
- Completed a four-session real EOD/Identity pilot through 2025-06-16. The
  postflight census now reports EOD/Identity 310/1,255 and normalized Identity
  source 308/1,255, with overall state still correctly quarantined. The
  three-session measured batch took 179.47 seconds and exposed repeated
  whole-root hashing as the dominant bounded optimization before scaling.
- Removed two duplicate whole-root scans per historical session by passing the
  already-computed pre-state into the plan builder. Generic daily calls remain
  backward compatible, and every Apply still recomputes the full-content
  fingerprint under lock before writing.
- The post-change three-session measurement completed without retry in 158.52
  seconds versus 179.47 seconds before the change, an 11.7% reduction. Closed
  the bounded optimization at that point; EOD/Identity now contain 313
  sessions and normalized Identity source contains 311.

## 2026-09-10 — Reject Massive Starter as the sole lifecycle source

- Reused the frozen ADR 0168 30-item diagnostic across ARCX, BATS, XASE, XNAS,
  and XNYS; every item had stable Composite and Share Class FIGIs plus a
  provider delisting date.
- Issued 30 serial, no-retry Ticker Events requests by Composite FIGI. Six
  instruments matched, 24 returned HTTP 404, and all nine returned events were
  `ticker_change` with no terminal, trading-status, successor, consideration,
  revision, or source-availability semantics.
- Retained Massive as the EOD, Identity, inactive-candidate, split, dividend,
  and sparse symbol-change source, but rejected it as the sole-primary
  lifecycle source under the already frozen gates. LSEG free-trial/sample
  evaluation remains the next external dependency.
- No raw response or provider identifier was retained. No canonical data,
  research outcome, publication, deployment, or scheduler state changed.

## 2026-09-10 — Prepare the exact LSEG lifecycle sample request

- Rechecked current official LSEG material: DataScope Select exposes a free-
  trial path, REST/SFTP extraction, Equity Corporate Actions, Equity Trading
  Status, active/delisted reference coverage, and deep history.
- Updated the existing provider inquiry packet rather than creating a parallel
  request document. The request now names the exact sample, data dictionary,
  identity, lifecycle, revision, delivery, retention, and itemized pricing
  evidence required before implementation or purchase.
- Public material still provides no exact price and does not prove mandatory
  last-tradable, successor/consideration, historical-vintage, or stable-ID
  mapping semantics. No form was submitted, account accessed, sample acquired,
  adapter implemented, or data/Production state changed.

## 2026-09-10 — Reject reconstructed development evidence under a frozen rule

- Accepted ADR 0195 and froze the admission unit as one 100%-complete Primary
  session cross-section, with the preregistered 252-session minimum and no
  coverage-based stable-ID selection.
- Added a typed missingness-only decision, pure builder, network-disabled
  command, owner-only atomic custody, and tamper/time-order tests.
- Bound the real 287-session census and rejected current evidence: zero of 267
  candidate sessions passed, 20 were zero-included warmup sessions, and no
  session, path, instrument, cohort, or development authority was admitted.
- The decision logical fingerprint is
  `543fdd10e6c7df087d077754674f49660fd558a9f2dafcd4fe9dfa2131af36e8`.
  It contains no trigger, outcome, performance metric, or parameter selection;
  no provider, `/data`, Production, publication, deployment, or scheduler
  action occurred.

## 2026-09-10 — Complete the fixed outcome-blind development census

- Formally reread all 287 fixed historical Membership partitions, their same-
  session normalized Identity source custody, the canonical split-only facts,
  and the sparse adjustment ledger from exact source revision `1f64471`.
- Reconciled 2,656,006 Primary decisions and 437,402 raw-complete included
  feature paths across 10,702 stable IDs. Counted 722 clear split exposures and
  retained 12 paths for one unresolved possible split impact in quarantine.
- Proved that every included path still lacks sparse-row neutrality and
  canonical lifecycle evidence. All-required completeness is zero; no
  threshold, cohort, outcome, backtest, or development authority was created.
- Wrote one atomically reread, owner-only `/tmp` report with logical
  fingerprint `09ffe4edc38aeaccb3f101f5b1b784eb0769af0de9fde0c28fafbc18fe32388f`.
  `/data` inventory, Production, provider, deployment, and scheduler state did
  not change.

## 2026-09-10 — Implement the outcome-blind development coverage census

- Added the fixed 287-session Strong-Leader Pullback V2 coverage contract,
  pure aggregator, formal Dell evidence reader, and atomic owner-only `/tmp`
  report custody required by ADR 0193.
- Bound complete three-state historical Membership to same-session normalized
  Identity source evidence and retained per-session and per-stable-ID coverage,
  missingness, quarantine, and reason counts.
- Kept split actions and the sparse adjustment ledger explicitly partial and
  outcome-only. Later split events cannot contaminate earlier feature windows;
  omitted adjustment rows never prove neutrality, and unavailable lifecycle
  evidence remains explicit.
- The census contains no strategy trigger, forward outcome, performance
  metric, threshold, cohort, parameter choice, or development authority. It
  performs no external request, `/data` write, Production write, publication,
  deployment, or scheduler action.
- This entry records the implementation boundary; real census execution and
  its evidence are recorded separately after exact-revision formal reread.

## 2026-09-10 — Reconcile the research-factory direction and documentation authority

- Accepted ADR 0193. Latest-vintage reconstructed Membership may support an
  outcome-blind Strong-Leader Pullback coverage census and, only after a
  separate missingness-based admission decision, development work. It cannot
  support validation, holdout, Candidate activation, or Production claims.
- Accepted ADR 0194. AI-assisted quantitative research is a bounded backend
  within Quant Research Lab: registered hypotheses, isolated data stages,
  append-only attempts, deterministic evaluation, adversarial falsification,
  and paper/shadow observation. Agent count or agreement is never evidence.
- Aligned Product Vision, Scope, Roadmap, Lab specification, research
  framework, open questions, architecture, application package guides, and
  data-boundary documents with one promotion lifecycle and one authority map.
- Replaced the 1,362-line daily EOD mixed runbook/history with a compact
  durable control-plane runbook. Dated execution evidence remains in audits,
  ADRs, the changelog, and Git history.
- Removed duplicated volatile Production identifiers and superseded current-
  state wording from default-path contracts and runbooks; Current Context and
  Current Status remain the authoritative recovery entry points.
- Documentation only: no model implementation, parameter search, backtest,
  provider request, `/data` write, publication, deployment, scheduler, or
  active Production state changed.

## 2026-09-10 — Add the transparent Lab model registry boundary

- Accepted ADR 0192 and added typed model-record, result-publication, and
  catalog contracts that keep method disclosure, fixture evidence, real signal
  studies, portfolio simulations, and Candidate activation separate.
- Added the canonical Strong-Leader-Pullback method projection with complete
  input/feature formulas, registered parameters, evaluation design, decision
  gates, counterevidence, blockers, and reproduction fingerprints.
- Rebuilt the Quant Research Lab page around the contract-validated record.
  Its compact view says method-only, not market-assessed, and not
  Candidate-eligible; the expanded view discloses all material fields.
- Corrected the page's stale company-action description: canonical split-only
  and sparse adjustment evidence exists, while availability, neutrality,
  revision, and total-return coverage remains incomplete.
- Added fail-closed tests preventing method/fixture performance claims,
  event-study portfolio metrics, portfolio results without frozen construction,
  and Candidate catalog entry without separate activation.
- No provider request, `/data` write, real backtest, Candidate formula change,
  Snapshot, deployment, scheduler, or active Production release changed.

## 2026-09-09 — Unify Product and Quant Research authority

- Accepted ADR 0191. Quant Research Lab is now the model registry, validation,
  result-evidence, and lifecycle authority; only one to three separately
  validated and activated models may later drive Stock Candidates.
- Froze the deployed Candidate score, Entry Geometry, and technical Strategy
  Channels as transparent, unvalidated Baseline V1. Their contracts remain
  truthful Production evidence, but direct parameter tuning and further
  heuristic extension are no longer the development path.
- Rewrote Product Vision, Scope, Roadmap, Lab specification, current context,
  current status, and architecture language around one promotion chain.
- Reduced the default documentation path by replacing duplicated chronological
  ADR/audit catalogs with curated authority maps, removing stale resolved
  questions and dated application-guide state, and moving historical detail
  behind dedicated records.
- No application code, formula, data, provider request, canonical Apply,
  publication, deployment, scheduler, or Production state changed.

## 2026-09-09 — Complete the first live Stocks Starter daily chain

- Verified the delayed provider profile after the 20:30 UTC stabilization
  boundary: 14 Identity requests and one Grouped Daily request completed, then
  exact-plan Apply published aligned 2026-09-09 Identity and 9,916 EOD rows.
- Completed the Dell-local analytics chain, Market Intelligence
  `2026-09-09T205635Z-e06bd62ecab3`, Snapshot/Serving Bundle
  `2026-09-09T211131Z-e06bd62ecab3`, and exact one-shot OCI deployment.
- Independent remote postflight matched source `e06bd62`, bundle and manifest
  hashes, services, routes, guest parity, and zero staging/failed releases.
- Published the third signal-eligible daily Membership partition with 19,964
  rows and proved exact-existing recovery with zero writes.
- The final full-source current-context report found 306 EOD sessions, aligned
  Identity, 4,311 `/data` files / 2,321,416,033 bytes, zero symlinks, and zero
  publication residue. Formal research readiness remains `data_blocked`.

## 2026-09-09 — Complete persistent daily workspace integration

- Accepted ADR 0190. Identity and EOD now have distinct governed persistent
  package/plan pairs while legacy generic and direct `/tmp` evidence remains
  compatible; mixed roles, sessions, or custody modes fail closed.
- Coordinator custody now accepts the exact same-session persistent Market
  Intelligence and Snapshot plans produced by the bounded offline runner.
- Membership post-action planning now uses action completion time, preventing
  a false knowledge-time inversion without changing candidate timestamps.
- Added focused regression coverage. No formula, Universe, provider request,
  canonical data, website content, scheduler authority, or research claim was
  changed by these repairs.

## 2026-09-09 — Preserve Stress in strategy research statistics

- Accepted ADR 0189 and advanced the fixture-only research-statistics contract
  to 1.1. Risk-on, Balanced, Defensive, and Stress now remain distinct through
  the evaluator, typed summaries, and independent Oracle.
- Added an end-to-end Stress fixture covering all 24 parameter combinations and
  corrected the product description to distinguish the existing pure input
  builder from the still-absent canonical filesystem orchestration.
- Recorded two interpretation limits without changing V1: leadership is
  measured through the signal close, and the volume cap describes only the
  signal session rather than a complete pullback path.
- The registered hypothesis, 24-combination grid, thresholds, chronological
  boundaries, data-readiness block, `/data`, Production, scheduler, and website
  behavior are unchanged. No real outcome or performance claim was created.

## 2026-09-09 — Bind Stocks Starter recency through the daily chain

- Accepted ADR 0188 after the owner supplied a successful Massive Stocks
  Starter purchase confirmation. The repository now carries an explicit
  Basic, 15-minute-delayed, or realtime profile through readiness, the
  coordinator, acquisition and canonical Apply custody, host verification,
  external preflight, scheduler planning/rehearsal, and immutable systemd
  candidate bytes.
- Basic remains the safe default and rollback profile. Starter uses
  `massive_stocks_delayed_15_minutes`, which removes only the Basic-specific
  initial availability review after the existing 30-minute stabilization
  window; it does not assert data completeness or weaken request, quality,
  custody, Apply, publication, or deployment gates.
- Advanced acquisition custody to 1.3, canonical Apply custody to 1.1,
  scheduler rehearsal to 1.2, and systemd Candidate/Review to 1.2. Reservation
  and recovery inputs now bind the readiness-policy fingerprint, and the
  systemd service renders the selected profile explicitly.
- All 2,348 API tests passed with the two existing dependency deprecation
  warnings. After the repository commit, a new owner-only exact-revision
  Starter data-control pair was provisioned for the same four standing
  Identity/EOD fetch/Apply operations and passed the data-only, zero-network
  preflight. No credential, provider request, `/data`, installed timer,
  Snapshot, bundle, deployment, or Production state changed. Live Starter
  entitlement, five-year endpoint depth, and same-evening completeness remain
  pending controlled observations.

## 2026-09-09 — Bound daily Membership workspace execution

- Accepted ADR 0187 and added
  `daily-universe-membership-bounded-run/1.0`, a separate Dell-local runner over
  the existing sidecar planner, candidate builder, and Apply-plan builder.
- The runner is review-only by default, permits at most the candidate and near-
  Apply-plan workspace actions, replans around each action, holds an owner-only
  session lock, and stops on waiting, blocked, failure, budget, completion, or
  Apply-review state.
- Added a network-prohibited administrator entry point and fail-closed tests for
  default review, one- and two-action progress, primary-pipeline waiting, Apply
  separation, budget exhaustion, no retry/recovery, and fingerprint tampering.
- The real 2026-09-08 default-review entrypoint returned `complete` / `none` in
  about 60 seconds with zero actions, requests, or writes. The 27-test focused
  suite and all 2,340 API tests passed with the two existing dependency
  deprecation warnings.
- Workspace-action execution remains fixture-only. The runner does not invoke
  or block the website pipeline, perform Membership Apply, write `/data`,
  access a provider, publish/deploy, or install/change a timer. The next live-
  session action observation remains pending.

## 2026-09-09 — Seal the first experiment's outcome-free input boundary

- Accepted ADR 0186 and added a pure, I/O-free Strong-Leader Pullback input
  adapter. It requires a matching research-ready assessment/Coverage manifest,
  signal-eligible point-in-time Membership, the complete Primary cross-section,
  stable-ID SPY, exact 21-session EOD, clear adjustments, and a same-session
  confirmed Regime; any missing required item rejects the entire session.
- Froze the actual feature definitions and fingerprint: same-session relative-
  return percentile, Candidate 1.1.1 trend-quality formula, simple ATR14,
  distance from the prior 20-session close high, prior-close/prior-high
  recovery, and signal-volume versus prior-20-session median.
- Widened the pre-real-data execution/observation contract to 1.1 so Stress is
  not relabeled and leaders above their prior high remain valid non-trigger
  controls through negative pullback depth. The registered positive signal
  bands and 24-combination experiment did not change.
- Added four deterministic/fail-closed fixtures; all 2,329 API tests passed
  with only the two existing dependency deprecation warnings. No real data was
  evaluated; no signal, forward return, parameter result, performance claim,
  `/data`, scheduler, Snapshot, bundle, deployment, or OCI state changed.
  Formal readiness remains `data_blocked`.

## 2026-09-09 — Consolidate the first research-model admission baseline

- Expanded the existing Quant Research Lab product definition rather than
  creating another parallel status document. It now records the exact frozen
  24-combination Strong-Leader Pullback grid, signal/control cohort rule, and
  requirement to bind composite input features to exact historical formulas.
- Added one family-by-family minimum data admission matrix. It separates the
  met 305-session price-length floor from still-blocking Membership, corporate
  action, lifecycle, adjustment, real feature-adapter, label, and transitive
  Historical Coverage evidence; costs and optional context remain separately
  classified.
- Recorded the main falsification risks without changing V1: static geometry
  may not represent an orderly path, leader controls may be imbalanced,
  next-open gaps and clustered concentration matter, and missing event context
  must remain visible. Possible V2 features are explicitly outside the frozen
  experiment.
- Corrected the stale product narrative from 1 of 304 to 2 of 305 canonical
  signal-eligible Membership sessions, aligned the current roadmap, and removed
  obsolete contract prose that denied already-published partial canonical
  families. Historical ADRs and audits retain their original dated facts. No
  formula, schema, code, `/data`, research stage, performance claim, Production
  bundle, scheduler, or OCI state changed.

## 2026-09-09 — Expose daily Membership as a read-only research sidecar

- Accepted ADR 0185 and added
  `daily-universe-membership-sidecar-plan/1.0`, a deterministic state machine
  for candidate readiness, primary-pipeline waiting, near-Apply planning,
  Apply review, formal completion, and research-only blocked states.
- Added an existing-candidate-only formal reader so sidecar inspection has no
  path that can create evidence. Daily EOD Pipeline Wake Plan 2.1 optionally
  projects the sidecar status/action/fingerprint while preserving the exact
  primary decision and `website_pipeline_blocked=false`.
- The real Dell read-only command formally returned `complete` / `none` for
  2026-09-08 with 19,964 decisions and publication fingerprint
  `f02a67923d60ea4293a87b0884f3fadb109e9cfc3956b3617a4c678648789bb8`.
  It made zero requests or writes and granted no Apply, scheduler, Historical
  Coverage, or performance authority.
- Thirty-one focused tests passed, followed by all 2,325 API tests with the two
  unchanged dependency deprecation warnings. No `/data`, OCI, website, timer,
  scheduler, candidate, plan, or canonical publication was changed.
- See the dated
  [audit](../audits/daily-universe-membership-sidecar-2026-09-09.md).

## 2026-09-09 — Publish prospective 2026-09-08 Membership

- Prepared one network-prohibited 19,964-row 2026-09-08 Membership candidate
  from aligned same-session EOD, Identity, and normalized Identity source
  evidence. It is signal eligible for the next open and retains the canonical
  2026-08-14 provider type-code catalog used by the existing methodology.
- The initial wrong 2026-09-08 catalog-date invocation failed before candidate
  or canonical writes. Formal source-fingerprint comparison proved the 8/14
  catalog binding before the corrected run; exact repeat returned
  `already_present` with no residue.
- The 27 directly related tests passed. Exact-plan Apply published 3 files /
  464,256 bytes, formally reread 19,964 decisions, and produced publication
  fingerprint
  `f02a67923d60ea4293a87b0884f3fadb109e9cfc3956b3617a4c678648789bb8`.
  Zero-write postflight reused both targets without overwrite or deletion.
- Canonical Membership now covers 2 sessions / 39,928 decisions; 303 EOD
  sessions remain missing. `/data` contains 4,253 files / 2,236,844,204 bytes
  with fingerprint
  `aad4f05da35422280160956192c3c431880751792002a08b602d321d7c5701b9`.
  Research readiness remains `data_blocked`; no website or scheduler changed.
- See the dated
  [audit](../audits/daily-universe-membership-publication-2026-09-09.md).

## 2026-09-09 — Publish and deploy the 2026-09-08 daily state

- Acquired one exact 2026-09-08 Grouped Daily package at 06:59 UTC, mapped
  9,964 canonical rows with zero duplicate business keys or orphan Identity
  references, and completed exact-plan EOD Apply. EOD and Identity now align at
  2026-09-08 across 305 contiguous sessions.
- Executed the first real bounded multi-action chain in the persistent Dell
  runtime workspace. Nine analytics/MI-plan actions completed in about 14.6
  minutes; Snapshot planning and Serving Bundle construction then completed
  under their separate review gates.
- Published fresh, lag-zero Market Intelligence
  `2026-09-08T071528Z-d6cc4ee57917` and Snapshot
  `2026-09-08T072146Z-d6cc4ee57917` with contracts 1.3 and 1.11/2.8.
- Recovered one persistent-bundle deployment reservation without replay after
  proving the old OCI release unchanged and the target absent. After the ADR
  0184 shell-boundary correction, deployed exact release
  `2026-09-09T075821Z-32321f0dadd5`; independent postflight passed release,
  source, checksums, access, listener, service, and residue checks.
- `/data` now contains 4,250 files / 2,236,379,948 bytes with zero symlinks or
  publication residue. Research readiness remains `data_blocked`; the
  installed timer remains read-only and no unattended write chain was enabled.
- See the dated
  [audit](../audits/daily-eod-publication-deployment-2026-09-09.md) for exact
  fingerprints, timings, recovery evidence, and remaining authority limits.

## 2026-09-09 — Retain Serving Bundle custody through OCI deployment

- Accepted ADR 0184 and aligned OCI deployment approval/custody with the exact
  persistent `daily-eod/sessions/session_date=YYYY-MM-DD/serving-bundle/<release>`
  layout already used by the bounded runner.
- Persistent deployment paths now share one validator across the capability,
  custody, and reviewed shell entrypoint for target-session, owner-only `0700`
  roots, no symlinks, and exclusion from Git, `/tmp`, and `/data`; the
  historical direct `/tmp` layout remains compatible.
- The change preserves the existing bundle reader, remote-state CAS, durable
  reservation, no-replay recovery, one-shot runtime binding, and postflight.
- The initial focused deployment and path-custody suites passed 14 tests; after
  the reviewed shell entrypoint was aligned, the final focused suite and shell
  syntax check passed 30 tests, and the full API suite passed 2,310 tests with
  only two existing dependency deprecation warnings. No OCI write
  occurred before this correction; read-only recovery inspection proved the
  old release unchanged, the new release absent, and zero staging or failed
  residue.

## 2026-09-09 — Quarantine ambiguous cash dividends before total return

- Accepted ADR 0183 and added a network-prohibited, write-free diagnostic over
  the exact canonical source-observation marker and 304-session EOD evidence.
- The clean-revision real run preserved all 68,150 dividend rows: 41,347 were
  resolved into 41,200 stable-ID/reported-date groups and 26,803 remained
  unresolved. It classified 40,454 groups as bounded arithmetic candidates
  only and retained 746 for review.
- Review reasons include 31 large distributions, 17 large-distribution date-
  order cases, 145 multiple-dividend dates, 13 same-date split/dividend groups,
  160 non-USD groups, and 399 groups without both adjacent EOD bars. Counts
  overlap and are not action classifications.
- Both VISN rows were isolated. The USD 10 row reconciles on the independently
  confirmed April 28 ex-date; the provider's USD 5 row reports August 17 while
  issuer evidence and the EOD cash discontinuity place ex-date on August 28.
  Provider cumulative factors remain audit-only.
- The focused and related suites passed 30 tests, followed by all 2,308 API
  tests with only the two existing dependency deprecation warnings. No
  `/data`, canonical action, Adjustment Ledger, analytics, Snapshot,
  deployment, timer, scheduler, or Production state changed.

## 2026-09-09 — Falsify split coverage with canonical price discontinuities

- Accepted ADR 0182 and added a network-prohibited, write-free diagnostic that
  compares adjacent XNYS-session open/prior-close ratios by stable
  `instrument_id`, cross-checks canonical active/quarantined/unresolved split
  evidence, and never promotes price behavior into a corporate-action fact.
- The clean-revision real scan covered 304 sessions, 2,816,903 EOD rows, and
  2,802,728 adjacent transitions in about 24 seconds. All 645 comparable active
  split groups had bounded adjusted residuals with zero extremes.
- It retained 387 unexplained severe discontinuities across 321 stable IDs, 20
  comparable quarantine flags, and 80 known event/date keys without comparable
  two-sided EOD. These remain review evidence; full action coverage, omitted-
  row neutrality, total return, Historical Coverage, and performance authority
  remain false.
- A stable-ID-only prioritization cross-check found 13 current Primary / 14
  current Secondary overlaps, 31 lifecycle-queue overlaps with no current-
  Universe intersection, 44 IDs with a fourfold/quarter-scale gap, and 57 IDs
  with repeated flags. Current Activation was not projected backward.
- Public first-party review of the 15 current-Secondary flags found 13 date-
  aligned issuer event contexts, one explicit VISN $10 special cash
  distribution with the exact ex-date, and one unresolved DFNS case. No split,
  causal label, historical identity, Membership, factor, or canonical data was
  inferred or changed.
- The expanded related suite passed 35 tests. `/data` remained 4,204 files /
  2,151,679,313 bytes with zero symlinks; no external request, canonical write,
  Snapshot, deployment, timer, or scheduler action occurred.

## 2026-09-09 — Make daily data custody restart-safe

- Accepted ADR 0181 and connected the exact persistent-session
  `acquisition-package` / `canonical-apply-plan.json` pair through fetch/plan,
  same-day Identity source custody, acquisition and operator review, canonical
  Apply custody, coordinator, authorized capabilities, and standing
  authorization.
- Persistent pairs must share the requested owner-only session, use exact
  governed names, avoid symlinks/Git/`/tmp`/`/data`, and keep prepared files
  inside `canonical-apply-plan.artifacts`. Mixed or cross-session custody fails
  closed.
- Legacy `/tmp` package and plan evidence remains readable, including renamed
  historical plans. No provider request, `/data` write, runtime migration,
  publication, deployment, credential access, or timer change was performed.
- All 176 focused and related regressions passed. The activated 2026-09-08
  session layout passed the new validator without creating a package or plan;
  `/data` remained 4,204 files / 2,151,679,313 bytes with zero symlinks.

## 2026-09-09 — Activate the persistent daily runtime workspace

- Activated one stable owner-only Dell workspace outside Git, `/tmp`, and
  `/data`. It retains an exact 192-event copy of the legacy journal and
  formally verified 2026-09-04 Phase 1b/Candidate priors for the next session.
- The copied prior fingerprints match their sources; the journal hash chain
  has no unresolved action or cadence reservation. The completed workspace has
  17 owner-only directories, 213 files / 927,439,505 logical bytes, zero
  symlinks, and zero staging residue.
- An execute-enabled runner preflight for 2026-09-08 performed zero actions and
  stopped at `eod_required`. `/data` remained exactly 4,204 files /
  2,151,679,313 bytes with zero symlinks. No provider, publication, deployment,
  service, timer, or credential action occurred.

## 2026-09-09 — Add a finite continuous runner for governed offline daily stages

- Accepted ADR 0180 and added a default-review, socket-guarded Dell command
  that can chain only formally successful offline actions under eleven-action
  and two-hour default budgets. Every action still uses the existing exact-plan
  executor, immutable journal reservation/result, postcondition reread, and
  no-replay recovery boundary.
- The runner stops at data, MI/Snapshot publication, deployment, blocked,
  failure, unknown-outcome, missing-current-state, and budget boundaries. It
  performs no provider request, canonical Apply, publication Apply, deployment,
  retry, recovery, polling, sleep, service installation, or timer change.
- The 17 focused tests passed; the expanded related automation suite passed
  165 tests in total. A real default-review replay against the retained
  2026-08-28 persistent workspace
  took about 28 seconds, executed zero actions, and correctly stopped at its MI
  publication-plan review. `/data` remained 4,204 files / 2,151,679,313 bytes
  with zero symlinks; the replay workspace had zero changed paths.

## 2026-09-09 — Isolate current-session EOD recency and freeze classification sample gates

- Ran a two-request, credential-safe Grouped Daily comparison at 02:27 UTC.
  The same credential, endpoint, transport, and `adjusted=false` parameter
  returned 12,510 results for canonical session 2026-09-04 and HTTP 403 for
  current completed session 2026-09-08. No response body was printed or
  retained and no package, `/data` write, calculation, publication, deployment,
  or scheduler mutation followed.
- Reconciled current official plan material: Grouped Daily is listed across
  Stocks plans, Basic is end-of-day, Starter is 15-minute delayed, and paid
  flat-file Day Aggregates are approximately next-day 11:00 ET. The evidence
  rules out a global credential/adapter failure and isolates current-account
  current-session recency; Basic's exact release minute remains unverified.
- Expanded the existing GICS/TRBC sample gate with an exact field-to-contract
  matrix, representative temporal/identity cases, and four explicit outcomes:
  historical-research primary, current-display only, corroborator only, or
  rejected. No vendor was contacted, selected, purchased, accessed, or adapted.

## 2026-09-09 — Deploy the market-to-candidate decision chain

- Built immutable bundle `2026-09-09T020802Z-d53e98832ef5` from clean source
  `d53e98832ef57f22e018f9f9b863f009eb355544`, reusing the exact active
  Snapshot 1.11 / Dashboard 2.8 and MI 1.3 bytes without recalculation or
  `/data` writes.
- Dry-run proved the expected prior release, absent target, healthy services,
  valid Nginx configuration, and safe promotion boundary. Apply completed in
  about 22 seconds.
- Independent inspection at 02:09 UTC matched release, source, bundle,
  manifest, and checksums; protected routes, temporary guest Session,
  guest/credential route parity, Nginx/Auth, localhost-only listener, and zero
  staging/failed-release/system-unit residue all passed. Password login and
  final human visual review remain manual.

## 2026-09-09 — Confirm the 2026-09-08 EOD entitlement blocker

- Performed one final bounded 01:48 UTC Grouped Daily fetch-only retry after the
  initial request and 22:52 UTC retry. It again returned provider HTTP 403
  before a package or staging path existed.
- No retry loop, package residue, `/data` write, canonical EOD change,
  calculation, publication, Snapshot, bundle, deployment, or scheduler change
  resulted from this fetch attempt. A short post-close delay is no longer the
  working explanation; same-day endpoint/account entitlement remains unresolved.

## 2026-09-09 — Implement the cross-workspace market-to-candidate decision chain

- Added a bilingual Sector Rotation decision view that aligns the selected
  Universe's confirmed Market Regime, five leading fixed-registry sector ETF
  price proxies, and eight Balanced-risk Candidate priorities to the same
  completed session.
- The join fails closed on session, publication, or Universe drift. It preserves
  the source 5/10/20-session ETF ranks and Candidate ranks, performs no score
  recomputation, and explicitly prohibits interpreting the hand-off as formal
  sector membership, fund flow, causality, or a trade instruction.
- The small Sector Rotation payload renders first; the Market Regime and
  Candidate summaries load asynchronously. No Candidate detail shard, model,
  parameter, analytics publication, `/data`, scheduler, bundle, OCI, or
  Production state changed in this implementation step. All 121 frontend tests
  and the Production build pass.

## 2026-09-09 — Deploy the strategy-channel decision map

- Built the clean-source bundle
  `2026-09-09T013946Z-dc939a9d0dbb` from commit `dc939a9d0dbb...`, reusing the
  exact active Snapshot 1.11 / Dashboard 2.8 and MI 1.3 evidence without
  recalculation or `/data` writes.
- Dry-run and preflight proved the expected prior release, absent target,
  healthy Nginx/Auth, protected routes, equal guest capability, and zero
  staging/failed residue. Apply completed and independently verified the new
  checksums, services, temporary guest Session, protected routes, and equal
  guest/credential policy. Password login and final human visual review remain
  manual.
- The first independent inspection exposed a control bug: it compared the UI
  bundle ID with the reused data Snapshot ID. The guest flow itself returned
  all expected statuses. The inspector now binds the served private manifest
  to `snapshot_manifest_sha256`, correctly supporting immutable Snapshot reuse
  in UI-only releases; focused regression and shell syntax checks passed.

## 2026-09-09 — Separate equity execution-cost mechanics from evidence

- Accepted ADR 0179 and implemented deterministic one-side equity execution-
  cost mechanics: commission, half spread, delay slippage, square-root impact,
  order participation, and an explicit capacity gate.
- Added immutable Decimal/fingerprint contracts that distinguish scenario-only,
  observed-spread, and observed-spread-plus-calibrated-impact evidence. Every
  result remains estimated, equity-only, and unauthorized for research,
  options, or performance claims.
- Current-context 1.10 now reports scenario mechanics as present while retaining
  absent quote/calibration evidence as a research blocker. No `/data`,
  analytics, Snapshot, bundle, Production, deployment, or scheduler state was
  changed.

## 2026-09-09 — Publish canonical sparse split adjustments

- Built and independently reread the exact ADR 0178 plan from clean main
  `bdb027a293a167962c24f4a8ec0bb28746e53b8e`. It preserved candidate revision
  `0c57560...`, rebound canonical action/EOD sources, and bound whole-data pre-
  state `6d6ef7c2...`, two absent target files, and all false authorities.
- The locked, network-prohibited Apply published 101,321 affected-path rows:
  98,291 clear and 3,030 quarantined. Exactly two files / 80,308 bytes were
  added with zero overwrite, deletion, external request, or outside-target
  change. Publication fingerprint is `7e08b8a8...`.
- An exact second Apply was zero-write and returned `verified_existing`.
  Current-context 1.9 formally reread the full publication and kept adjustment
  reconciliation incomplete, Historical Coverage absent, research
  `data_blocked`, and performance claims unauthorized.
- Postflight recorded 4,204 files / 2,151,679,313 bytes, fingerprint
  `af06b692cf1f9708e75cf44defd198cb25317b65403a2adbc503d9e03e1fa71f`,
  zero symlinks, zero residue, clean main, and unchanged Production.

## 2026-09-09 — Implement canonical sparse split adjustment publication

- Accepted ADR 0178 and added the exact Apply-plan contract, network-prohibited
  planner, shared-lock atomic Apply, formal canonical reader integration, and
  zero-write recovery for the ADR 0177 publication-exact candidate.
- The plan separates candidate derivation revision from planner revision and
  fully rederives all candidate rows from exact canonical split-action and EOD
  evidence before trusting the two source artifacts.
- Current-context contract 1.9 now formally distinguishes canonical sparse
  split-only outcome reconciliation from absent Adjustment Ledger custody while
  retaining incomplete reconciliation, `data_blocked`, and false research
  authority.
- Focused tests cover exact source rebinding, false authorities, inventory
  drift, atomic Apply, interruption cleanup, tamper failure, and exact-existing
  recovery. This implementation entry does not record a real `/data` Apply,
  Historical Coverage, research run, analytics, Snapshot, bundle, deployment,
  or scheduler change.

## 2026-09-09 — Reconcile real sparse split adjustment candidate

- Built the clean-revision ADR 0177 candidate on Dell against exact canonical
  split-action and EOD family evidence. It contains 101,321 affected-path rows:
  98,291 clear across 575 stable IDs and 3,030 quarantined across 31 IDs.
- Independently reconciled the 0.04–62,500 factor range, 285 exact reciprocal-
  cancellation rows, 18-decimal price/volume reciprocity, and both quarantine
  reason classes against canonical actions. No neutral placeholder was added.
- An exact second full derivation returned `already_present` with identical row,
  Parquet, manifest, and publication fingerprints. Candidate custody remains
  owner-only below `/tmp`.
- The network-prohibited postflight kept `/data` exactly unchanged at 4,202
  files / 2,151,599,005 bytes with fingerprint `6d6ef7c2...`, zero symlinks,
  zero residue, unchanged Production, absent canonical ledger, and research
  `data_blocked`. A separate inventory-bound Plan/Apply remains required.

## 2026-09-09 — Implement sparse affected-path split adjustment candidate

- Accepted ADR 0177 and refused a dense factor-one ledger while canonical
  action coverage remains bounded. Rows are emitted only when an observed EOD
  path crosses an active split fact, the quarantined multi-action group, or an
  unresolved possible-impact event.
- Added a source-bound publication manifest and deterministic Parquet custody
  over existing `AdjustmentLedgerEntryV1` rows. Exact canonical action and EOD
  family evidence, basis, methodology, source cutoff, counts, hashes, and all
  non-authority fields are preserved.
- Clear price/volume factors use exact event ratios and the strict
  `source_session < effective_date <= basis_session` rule. Quarantine takes
  precedence and carries no factors. Total return stays unavailable and absent
  rows do not imply neutral factors.
- A formal real-data sizing pass selected 622 stable IDs, scanned 175,033 EOD
  rows, and projected 101,321 rows: 98,291 clear across 575 IDs and 3,030
  quarantined across 31 IDs. All selected IDs had EOD observations.
- Fixture tests cover clear and quarantine math, basis-day exclusion,
  idempotency, source-range rejection, and tamper failure. This implementation
  passed as part of the complete 2,254-test API regression with only the two
  existing dependency deprecation warnings. This implementation stage writes
  only a future candidate below `/tmp`; no canonical ledger,
  Historical Coverage, research, analytics, Snapshot, bundle, deployment, or
  scheduler change is recorded here.

## 2026-09-08 — Publish canonical split-action facts

- Built and independently reread the exact ADR 0176 plan from clean main
  `cccbec4850736da90e24fc5277b4c8e61bffb3ab`. It bound source publication
  `7b13691e...`, candidate `026e9087...`, whole-data pre-state `f3117cea...`,
  two absent target files, and every false authority field.
- The locked, network-prohibited Apply published 709 provider-neutral rows:
  707 active single-action rows and two quarantined rows in one multi-action
  group. It retained 1,240 unresolved source rows and 43 possible-impact stable
  IDs without assigning them.
- Exactly two files / 118,592 bytes were added with zero overwrite, deletion,
  external request, or outside-target inventory change. Publication fingerprint
  is `76f017a1547e20b997e40cd1e61497b71c749a94e88a8632a3898fe84c106218`.
- An exact second Apply was zero-write and returned `verified_existing`. The
  network-free postflight reported 4,202 files / 2,151,599,005 bytes, fingerprint
  `6d6ef7c214087130290ae151a53b7f8b7be018ffcd1cb42c9912bbcf4c843915`,
  zero symlinks, zero residue, incomplete Corporate Action coverage, absent
  ledger, and unchanged `data_blocked` status.
- No raw EOD, analytics, Snapshot, bundle, OCI, scheduler, or Production state
  changed.

## 2026-09-08 — Implement canonical split-action publication

- Accepted ADR 0176 and separated provider-neutral split facts from the later
  basis-specific Adjustment Ledger. The immutable fact set preserves one row
  per resolved source action rather than collapsing multiple same-date rows.
- Added canonical row, publication, and exact Apply-plan contracts plus
  deterministic Parquet custody. Decimal logical hashing is invariant to the
  fixed physical Parquet scale.
- Added a clean-revision `/tmp` planner and a network-prohibited, inventory-
  bound atomic-directory Apply using the shared Dell data lock. Exact completed
  targets are formally verified as zero-write recovery; conflicting, partial,
  symlinked, or drifted states fail closed.
- The current-context reader now distinguishes absent canonical actions from a
  split-only bounded publication and retains incomplete-coverage and research-
  blocked status.
- Focused tests cover clear versus multi-action quarantine, source/candidate
  derivation, tamper detection, inventory drift, atomic publication, and exact
  rerun recovery. The complete API regression passed 2,250 tests with only the
  two existing dependency deprecation warnings. This implementation entry does
  not record or imply a real
  `/data` Apply, Adjustment Ledger, research run, analytics, Snapshot, bundle,
  deployment, or scheduler change.

## 2026-09-08 — Recheck same-session EOD after the close

- Made one bounded 2026-09-08 Grouped Daily fetch-only request at 22:52 UTC,
  roughly 2 hours 52 minutes after the regular XNYS close. The provider again
  returned HTTP 403 before package or staging creation.
- This later observation makes ordinary immediate-post-close delay a weaker
  explanation and leaves account/endpoint same-day entitlement as the leading
  unresolved boundary. No further retry was made.
- No package, staging path, approval plan, canonical EOD write, analytics,
  Snapshot, bundle, deployment, or scheduler change occurred. Identity remains
  2026-09-08 and EOD remains 2026-09-04.

## 2026-09-08 — Bind split candidates to canonical source custody

- Accepted ADR 0175 and added an owner-only candidate that transitively reads
  the canonical ADR 0174 source marker instead of depending on the temporary
  resolution-shadow path.
- Preserved exact stable-ID/date ratio composition and unresolved historical-
  ticker quarantine while making ledger admission explicit. Single-action
  groups are only candidates for clear admission; multiple same-date actions
  remain quarantined even when their diagnostic ratios cancel to one.
- Kept the candidate sparse and deferred any session expansion to an exact
  future research panel. Bounded source observation still does not authorize
  neutral factors for absent events.
- Added a clean-revision CLI, owner-only atomic output, formal reread, and
  network prohibition. This implementation stage performs no `/data` write,
  canonical Corporate Action or Adjustment Ledger publication, analytics,
  Snapshot, bundle, deployment, or scheduler change.
- The clean-revision Dell run on `c46cc3f4ee883ed7ef4c850ca146b6e3807f87bb`
  produced 707 clear event candidates, one multiple-event quarantine, and 43
  possible-impact stable IDs. Event math and unresolved-impact membership
  exactly matched the prior temporary candidate.
- The output is 602,491 bytes with SHA-256
  `8ef0f95dce94a041be7e5c18d69bb959ae037e52e6f22d41c2401ab92f160c83`
  and logical fingerprint
  `026e9087ad4ef7ec891036cbe84ee4b3bde47cb1b1349fa858fc2e090b74f132`.
  Postflight kept `/data` and Production unchanged and research `data_blocked`.

## 2026-09-08 — Publish bounded corporate-action source observations

- Built and independently reread the clean-revision ADR 0174 plan on Dell main
  `310593bd5a549dbcc95932410104ca03ad961699`. It bound the complete current
  `/data` fingerprint, two absent event-year partitions, one absent marker,
  both repeat diffs, exact Identity evidence, and 5,007,486 planned bytes.
- The locked, network-prohibited Apply published 70,099 rows: 42,056 resolved
  and 28,043 quarantined. It added exactly five files, overwrote/deleted
  nothing, and kept the outside-target inventory fingerprint unchanged.
- Publication fingerprint is
  `7b13691e22b7e815a773ed1d575ed580bbee897eb0dbf10c41e4e0862a95b1d1`;
  plan SHA-256 is
  `2e5c0a3915133e821dc8796d5329a55fa1fc0a9f742b0dbd00abfe04d0ee4b96`.
  A separate zero-write postflight reused both partitions and the marker and
  formally reread all 70,099 rows.
- The current-context reader now recognizes the bounded query-snapshot marker
  and reports exact partition bytes without reconstructing all rows on every
  routine status request. `/data` is 4,200 files / 2,151,480,413 bytes with
  fingerprint
  `f3117ceaab4ea25ea60c23886d171373ae15dfcee30cff6ac784af02b7e1670b`,
  zero symlinks, and zero publication residue.
- The data remains `first_observed_only` and
  `outcome_reconciliation_only`. Canonical Corporate Actions, Adjustment
  Ledger, final Historical Coverage, research performance, Snapshot, bundle,
  deployment, and scheduler state remain unchanged.

## 2026-09-08 — Implement bounded corporate-action source publication

- Accepted ADR 0174 and reused the existing Corporate Action Source
  Observation 1.1 partitions instead of creating a duplicate event family.
- Added a clean-revision, inventory-bound no-write plan that formally rereads
  the exact resolution shadow, both zero-delta repeat reports, and canonical
  Identity evidence. The publication marker preserves query-snapshot,
  observation-revision, and outcome-only semantics.
- Added a network-prohibited, physical-first/marker-last Apply with the shared
  Dell lock, exact-prefix recovery, outside-target drift detection, and an
  independent canonical reader. Fault injection proved recovery after all
  physical partitions but before the marker.
- Focused corporate-action, repeat-diff, persistence, and contract coverage
  passed 53 tests. The complete API regression passed 2,238 tests with only the
  two existing dependency deprecation warnings.
- No `/data` Apply, canonical Corporate Action, Adjustment Ledger, Historical
  Coverage publication, analytics run, Snapshot, bundle, or deployment is part
  of this implementation commit.

## 2026-09-08 — Add strategy priority-versus-chase-risk visualization

- Added a bilingual selected-channel decision map that places each displayed
  security by its published within-channel research score and published
  extension-risk category, colours the linked Candidate trade-review state,
  and marks stable-ID repetition across displayed channels.
- Kept strategy score, status, rank, thresholds, Candidate risk disposition,
  and data contracts unchanged. The view explicitly prohibits cross-channel
  score comparison, expected-return/probability interpretation, and treating
  extension as a forecast.
- The complete frontend regression passed 117 tests and the Production build
  passed. Deployment remains a separate exact Snapshot/bundle boundary.
- Completed the guarded 2026-09-08 Identity fetch, Plan 1.1, and canonical
  Apply: 14 bounded requests produced 13,155 provider identities and source
  observations plus 9,982 Instruments and Resolvers. Formal daily planning
  advanced to EOD.
- The same-session EOD request returned provider HTTP 403 before package or
  staging creation and made zero canonical EOD writes. Dell therefore remains
  at EOD 2026-09-04 with Identity/source custody ahead at 2026-09-08; no stale
  new Snapshot or deployment was produced.

## 2026-09-08 — Bound the GICS sample and permission dependency

- Confirmed from current official public material that GICS company sample
  data and its data dictionary require credentialed sign-in; the public
  taxonomy structure and methodology are not membership evidence.
- Recorded that display, derived-product, and distribution use require an
  explicit license rather than inference from public access.
- Added point-in-time classification and its identity, temporal, revision, and
  equal-capability display questions to the prepared, unsent provider inquiry
  packet.
- No account, credential, sample, contact, purchase, provider request, `/data`,
  analytics, Snapshot, bundle, OCI, or Production state changed.

## 2026-09-08 — Implement provider-neutral Classification V1.1 custody

- Implemented frozen provider source observations, canonical definitions and
  memberships, explicit per-instrument coverage decisions, current-display
  versus historical-research eligibility, knowledge time, revision state,
  stable identity evidence, and issuer-projection basis.
- Added one atomic immutable snapshot containing definitions, source
  observations, coverage, memberships, and a marker-last manifest with exact
  logical/physical hashes, counts, provider and permission identities, and
  explicit authorization state.
- The formal reader rejects wrong schemas, counts, hashes, file sets,
  hierarchy, parent coverage, overlapping traditional intervals, unresolved
  links, eligibility escalation, and denominator drift. Unknown source coverage
  remains visible rather than being dropped.
- The full API regression passed 2,237 tests, including 28 focused new
  classification tests. All new physical tests used temporary roots only.
- No provider, credential, sample, `/data`, Candidate score/rank, Snapshot,
  timer, scheduler, bundle, OCI release, Production route, or guest/credential
  capability changed.

## 2026-09-08 — Separate current and historical classification evidence

- Audited canonical Identity, the implemented Massive adapter, Classification
  V1, and official public material for Massive SIC, SEC SIC, S&P GICS, LSEG
  TRBC, and FactSet RBICS without accessing credentials, provider endpoints,
  samples, `/data`, OCI, or Production.
- Accepted ADR 0173. GICS History is the first specification/sample candidate,
  TRBC is second, RBICS is complementary business-exposure data, and Massive
  SIC is at most a current coarse diagnostic. No source was selected, licensed,
  purchased, sampled, acquired, implemented, published, or deployed.
- Advanced Classification V1 to logical contract 1.1 with provider source
  observations, distinct business-valid and knowledge-time fields, revision
  lineage, stable-ID resolution, and explicit issuer-to-security projection.
- Kept current-display eligibility separate from historical-research
  eligibility. Current classification may never be projected backward, and
  unknown mappings remain visible and quarantined.
- This design-only change modifies no application behavior, Candidate score or
  rank, canonical data, active pointer, timer, scheduler, Snapshot, bundle, OCI
  release, or guest/credential parity.

## 2026-09-08 — Reconcile and compact authoritative project context

- Recovered this task from the source-of-truth Dell `main`; the previously
  opened historical-backfill worktree had no unique commit and was 79 commits
  behind the clean main baseline.
- Re-ran the network-free current-context reader and the independent read-only
  OCI inspector. Repository, EOD, Identity, Activation, Market Intelligence,
  Snapshot, `/data`, services, protected routes, temporary guest Session, and
  guest/credential route parity matched the active release with zero residue.
- Corrected `current-context` OCI fingerprints that still described the prior
  release and reconciled historical-foundation text with the already published
  EOD/Identity family evidence and one canonical Membership partition.
- Removed long execution narratives from `current-context` and
  `current-status`; retained volatile facts, active risks, research-family
  boundaries, recovery steps, and links to the immutable ADR/audit history.
- Froze further segmented-Candidate optimization behind a new live-chain budget
  breach and one bounded design for both remaining gaps. Added formal
  security-level classification and Candidate concentration as the next
  decision-useful product/data objective, separate from ETF proxies and
  historical point-in-time research taxonomy.
- This documentation reconciliation changes no application code, canonical
  data, active pointer, analytics, timer, scheduler, bundle, OCI release, or
  guest/credential capability.

## 2026-09-08 — Deploy Strategy Channel decision-integrity presentation

- Kept every published strategy-channel status, score, rank, parameter, and
  threshold unchanged while separating channel-local research priority from
  linked Candidate trade-review readiness.
- Added explicit technical-review, wait-for-setup, all-risk-mode rejection,
  gap/realized-volatility review, and unavailable labels from existing typed
  Candidate summary/detail facts. Event timing remains a manual check rather
  than an inferred fact.
- Added a stable-ID display diagnostic for live channels, displayed slots,
  unique securities, cross-channel repeats, all-risk-mode rejection, missing
  bounded setup, and elevated extension. It explicitly does not present this
  as formal sector concentration or independent diversification.
- Strategy cards, rows, and detail now show cross-channel repetition and the
  research/readiness conflict without recomputing or silently reranking the
  source results. Guest and credential Sessions retain identical capability.
- The complete frontend regression passed 117 tests and both ordinary and
  isolated Production builds; the complete API regression passed 2,209 tests
  with only the two existing dependency deprecation warnings.
- Published fresh Snapshot 1.11 / Dashboard 2.8 release
  `2026-09-08T171914Z-ca2d34d50692` and deployed its 53-file immutable bundle
  from clean main `ca2d34d506922f75699c376391dd6a9191ef0ae9`. Independent
  inspection matched bundle, manifest, checksums, source revision, protected
  routes, temporary guest Session, and guest/credential route policy with zero
  staging, failed release, unexpected listener, or failed system unit.
- Final active-source reread kept canonical EOD and active Snapshot fresh at
  2026-09-04 with lag zero, zero publication residue, and `/data` at 4,186
  files / 2,143,226,489 bytes with fingerprint
  `3f4a5780a69a8d60688ce34b64f8df06fc0dd12070801f265b46f3f7a1f6ac49`.

## 2026-09-08 — Deploy cross-strategy decision desk and current readiness gates

- Added a bilingual cross-channel decision desk to Strategy Channels. It shows
  the first published record from each currently available channel in fixed
  channel order with channel-local rank, stage, score, extension risk,
  supporting reason, and rejection risk; it creates no cross-channel score or
  preferred-strategy inference.
- Opening a strategy record now joins by stable `instrument_id` to the exact
  same-Snapshot Candidate detail and fails closed on missing or mismatched
  identity. The combined review exposes the channel ledger, market-to-entry
  chain, price/level context, chase risk, contribution ledger, contrary
  evidence, and invalidation.
- Replaced Quant Research Lab's stale aggregate readiness display with separate
  family gates. The 304-session price-length floor is visibly met while
  Membership, corporate actions/adjustment, lifecycle, costs, and sealed
  evaluation remain incomplete or locked.
- The complete frontend regression passed 115 tests and the Production build;
  the complete API regression passed 2,209 tests with only the two existing
  dependency deprecation warnings.
- Published and deployed fresh Snapshot 1.11 / Dashboard 2.8 release
  `2026-09-08T160420Z-14a8bec70cff` from clean main
  `14a8bec70cff37080673e679f05c8ed6eb34d95b`. Independent OCI inspection
  matched release, source revision, bundle, manifest, and checksums; Nginx,
  localhost-only Auth, protected routes, temporary guest Session, and
  guest/credential capability parity passed with zero staging or failed-release
  residue.
- Final active-source reread kept 304 canonical sessions through 2026-09-04,
  lag zero, research status `data_blocked`, and `/data` at 4,102 files /
  2,054,208,593 bytes with fingerprint
  `b2f45c0dcee3a915aba8e7c932a747ac6698022cfb7f90b3f82b4bd828dca128`,
  zero symlinks, and zero publication residue.

## 2026-09-08 — Complete real split-adjustment candidate

- On clean Dell main `2e4e1f21f09c357180f3ac6f67ef82f709ed6b32`, formally
  reread 1,949 split-like source observations and all 304 evidence-bound
  historical Resolvers. The owner-only result contains 708 resolved event
  groups, one multiple-action date, and 43 possible-impact stable IDs without
  assigning an unresolved action.
- Forty-one unresolved rows have historical ticker presence, 1,199 have none,
  and two have multiple historical candidates. Total-return adjustment remains
  unavailable and ledger projection remains not built.
- The one 564,826-byte file has SHA-256
  `83e8a3722132bd2172e0546e3d8fb84a5a5cece6e289a2b1c3744e1e8d175618`
  and logical fingerprint
  `b3efa16da5570cddf41f7fc741d71a29e73e6a1f696f68828b2f5e67b596d226`;
  a separate formal reread passed.
- The post-run context report kept `/data` at 4,060 files / 2,009,699,645
  bytes, fingerprint
  `16033737d18cd8d34de3e8401ee0f3e5d195a49470a2cda384a604ed6f29db1e`,
  zero symlinks and zero residue. Production and the website were unchanged;
  research readiness remains `data_blocked`.

## 2026-09-08 — Implement split-adjustment candidate boundary

- Added an owner-only, network-prohibited split-adjustment candidate that
  formally rereads the exact-event-date resolution shadow and its historical
  Identity bindings. Historical ticker presence creates quarantine candidates
  only; unresolved events are never assigned.
- Resolved split-like actions are grouped by stable ID/effective date. Exact
  ratio numerators and denominators are composed before one final
  quantization, preventing reciprocal same-day actions from drifting away from
  a factor of one.
- The single-file contract binds source/Identity evidence, resolved groups,
  possible-impact stable IDs, source-action fingerprints, total-return
  unavailability, and the not-yet-built ledger projection. It is idempotent and
  formally reread with owner-only custody.
- Focused tests cover factor direction, reciprocal cancellation, resolution-
  bound historical ticker scanning, grouping, quarantine, idempotency, basis
  refusal, future-event refusal, and tamper detection. No real candidate,
  `/data`, analytics, publication, deployment, or website change occurred in
  this implementation step.

## 2026-09-08 — Complete corporate-action adjustment-readiness review

- Confirmed from current official provider semantics that historical split
  factors are cumulative to a later/current basis and split-adjusted dividend
  cash reflects subsequent splits. Neither may be copied into a ledger with a
  2026-09-04 basis.
- The real semantic census found 708 resolved split event groups, one reciprocal
  same-day pair, and 43 stable IDs conservatively exposed to unresolved split
  rows; only two of those IDs enter the active Universes. The historical ticker
  scan created quarantine candidates only and assigned no unresolved event.
- Dividend review found 160 CAD rows, 34 USD split-cash mismatches, 145 multi-
  event ex-date groups, and 13 same-date split/dividend groups. ADR 0172
  therefore stages split-only outcome reconciliation before dividend total
  return.
- Corrected the provider mapping status that still said the real range had not
  passed event-date stable-ID resolution. `/data`, analytics, Production, and
  the website were unchanged.

## 2026-09-08 — Complete first corporate-action repeat observation

- On clean Dell main `1f07c53893aa31366f057fd440ed82f9ed49ef87`, acquired
  one later identical-scope split package and dividend package. Both again had
  complete pagination, 1,949 / 68,150 rows, and zero invalid dates, duplicate
  provider IDs, or unexpected fields.
- The two ADR 0171 diffs found every payload unchanged. Same-ID changed, added,
  removed, event-date, ticker, and pagination-shape deltas were all zero.
  Independent formal rereads passed for both source packages and both diffs.
- This approximately 69–73 minute result is recorded only as short-interval
  stability; it does not claim historical immutability, provider revision
  numbers, correction/cancellation semantics, or point-in-time availability.
- The post-run network-prohibited report kept `/data` at 4,060 files /
  2,009,699,645 bytes, fingerprint
  `16033737d18cd8d34de3e8401ee0f3e5d195a49470a2cda384a604ed6f29db1e`,
  zero symlinks, and zero residue. No canonical, adjustment, analytics,
  publication, deployment, scheduler, or Production transition occurred.

## 2026-09-08 — Implement corporate-action repeat-observation diff

- Accepted ADR 0171 and added a disconnected, owner-only source repeat-diff
  for two complete Massive packages with identical kind and date scope.
- The comparator requires strict observation order and a unique nonempty
  provider action ID for every row. It compares page/order-independent payload
  fingerprints and classifies only unchanged, same-ID changed, added, or
  removed records; ticker/date heuristics are prohibited.
- The two-file output binds both package identities, content fingerprints,
  field-level delta counts, and exact physical/logical change metadata. It
  copies no raw source payload and assigns no provider revision, correction,
  cancellation, or availability meaning.
- Nine focused tests cover split and dividend deltas, no-change observations,
  idempotency, missing IDs, inverted observation order, tamper detection, and
  safe CLI output. The complete API regression passed 2,202 tests with only
  two existing dependency deprecation warnings. No real repeat acquisition/diff, canonical write,
  Adjustment Ledger, analytics, publication, deployment, or scheduler change
  occurred in this implementation step.

## 2026-09-08 — Complete real corporate-action resolution shadow

- On clean Dell main `51dd39405fe2576d8eacc553b9fe0f99f788646a`, mapped
  all 70,099 retained Massive split/dividend rows only through exact event-date
  Identity. The result resolves 42,056 rows and quarantines 28,043; 39 rows
  lack an exact Identity session and 28,004 lack a same-date ticker.
- All 304 used Resolver snapshots passed their published evidence bindings.
  Latest/nearest/name/Universe fallbacks remained zero. The formal mapper's
  trim-and-uppercase normalization resolved seven rows omitted by the earlier
  raw case-sensitive diagnostic; this difference is explicitly reconciled in
  ADR 0170 and the dated audit.
- The independent formal reread passed on two event-year artifacts and an
  owner-only five-file / 5,006,834-byte tree with zero symlinks. Shadow
  manifest SHA-256 is
  `547218cf639bf4e06daa216868bd669cd73e4b69a55f7da4fad072077ffcacb8`.
- The post-run network-prohibited current-context report kept `/data` exactly
  unchanged at 4,060 files / 2,009,699,645 bytes and fingerprint
  `16033737d18cd8d34de3e8401ee0f3e5d195a49470a2cda384a604ed6f29db1e`.
  No canonical action, Adjustment Ledger, analytics, publication, deployment,
  scheduler, or Production transition occurred.

## 2026-09-08 — Implement exact-event-date corporate-action resolution shadow

- Accepted ADR 0170 and added a network-prohibited, owner-only `/tmp` shadow
  that formally rereads both corporate-action source packages and one
  published point-in-time Identity family-evidence manifest.
- Each used Resolver is selected only for the exact event date and checked
  against its evidence-bound snapshot manifest, Resolver manifest, Parquet
  physical hash, schema, content fingerprint, provider, date, count, unique
  ticker, and stable-ID types. Latest/nearest/name/Universe fallbacks remain
  exactly zero.
- Missing exact Identity sessions and missing same-date tickers receive
  separate quarantine reasons. The builder stops rather than dropping an
  unrepresentable source row and requires one-to-one output business keys.
- Reused the existing provider-neutral Corporate Action Source Observation 1.1
  Parquet partitions by event year and added one manifest binding every input,
  output, aggregate count, and used-Resolver fingerprint. Local revision `1`
  remains an isolated observation baseline, not provider revision evidence.
- Focused disconnected mapping, persistence, idempotency, tamper, source-loss,
  all-quarantined, safe CLI, and fixture-mapper coverage passed 31 tests. The
  complete API regression passed 2,193 tests with only two existing dependency
  deprecation warnings. No real shadow
  execution, network request, `/data` write, canonical action, Adjustment
  Ledger, analytics, publication, deployment, or scheduler change occurred in
  this implementation step.

## 2026-09-08 — Complete real Massive V1 corporate-action source custody

- On clean Dell main `08eb33c60896be783547aae55704b57caafca49c`, completed
  the exact 2025-06-23 through 2026-09-04 Massive V1 source range: 1 split
  page / 1,949 rows / 440,130 sanitized bytes and 14 dividend pages / 68,150
  rows / 24,033,055 sanitized bytes. Natural pagination ended below every
  safety ceiling.
- Both sources had zero invalid/out-of-range dates, duplicate nonempty source
  IDs, and unexpected fields. A separate formal reread passed. The temporary
  owner-only tree has 19 files / 24,489,297 bytes, mode `0700` directories,
  mode `0400` completed files, and zero symlinks.
- Split events comprise 337 forward splits, 1,384 reverse splits, and 228 stock
  dividends. Dividend events span 13,759 provider tickers; the broad scope is
  retained for event-date stable-ID resolution rather than being filtered by
  current ticker or current active Universe.
- The post-run network-prohibited report kept `/data` unchanged at 4,060 files
  / 2,009,699,645 bytes, fingerprint
  `16033737d18cd8d34de3e8401ee0f3e5d195a49470a2cda384a604ed6f29db1e`,
  zero symlinks, and zero residue. No canonical action, adjustment, analytics,
  publication, deployment, scheduler, or Production transition occurred.

## 2026-09-08 — Stage corporate-action source before adjustment

- Accepted ADR 0169 and added one resumable temporary source-custody boundary
  shared by separate Massive V1 split and dividend packages. Each exact
  historical range is owner-only below `/tmp`, serially rate-limited, bounded,
  checkpointed per page, and fully reread before success or resume.
- Bound current V1 endpoints, date filters, ascending order, pagination host
  and scope, page/record/byte ceilings, valid-date range, physical hashes,
  request-chain hashes, modes, and file set. Provider request IDs, pagination
  URLs, credentials, and Authorization material are not retained.
- Preserved provider result fields as source evidence while reporting known-
  field presence and unexpected-field counts. Empty natural completion is
  representable; malformed dates remain measurable rather than coerced.
- Added a clean-revision CLI and disconnected tests for split/dividend shapes,
  recovery, exact orphan adoption, zero rows, schema additions, scope and host
  rejection, secret rejection, tamper detection, and safe failure output.
  Focused corporate-action/adjustment coverage passed 38 tests; complete API
  regression passed `2181 passed, 2 warnings`, with the two unchanged
  dependency deprecations.
- No real Massive V1 request, `/data` write, stable-ID resolution, canonical
  Corporate Action, Adjustment Ledger, analytics, publication, deployment, or
  scheduler change occurred in this implementation step.

## 2026-09-08 — Gate lifecycle adapter work on a real cross-venue sample

- Accepted ADR 0168 and completed a dated official-public-material comparison
  of LSEG, Nasdaq, NYSE, Cboe, ICE, and S&P lifecycle/corporate-action roles.
  LSEG is first in the inquiry/sample order; no source is selected, purchased,
  contacted, accessed, entitled, permission-cleared, or implemented.
- Fixed a deterministic 30-item diagnostic over the exact ADR 0167 queue: two
  date-edge items from each of 15 non-empty exchange/year/Identity-observation-
  gap strata, yielding six items per exchange, ten from 2025, and twenty from
  2026. It is a semantic diagnostic, not a population coverage estimate.
- Sole-primary qualification requires every item to pass stable-ID identity,
  explicit coverage disposition, revision, availability-clock, last-tradable,
  terminal, successor/consideration, and permitted-use gates. Partially useful
  sources remain corroborators; false identity, silent omission, fabricated
  knowledge time, destructive revision, or permission incompatibility stops
  the proposed role.
- Deliberately added no speculative adapter, request runner, vendor sample,
  credential, `/data` write, lifecycle promotion, Historical Coverage,
  research, Snapshot, bundle, OCI, scheduler, deployment, or Production
  transition.

## 2026-09-08 — Plan lifecycle corroboration without promoting candidates

- Accepted ADR 0167 and added a typed, network-prohibited planner that formally
  rereads the complete inactive-lifecycle shadow and emits one immutable
  stable-ID work item per review candidate. Ticker and name are not copied;
  provider exchange is locator-only.
- The real 2026-09-03 plan contains 547 unique source occurrences and 547
  unique canonical instruments. Its routing census is ARCX 92, BATS 86, XASE
  11, XNAS 271, and XNYS 87: XNAS requires a bounded Nasdaq Daily List pilot,
  while the other 276 rows remain blocked on all-exchange source selection.
- All work items retain five explicit evidence gaps and remain
  `first_observed_only`. Although provider last-updated is present for all 547,
  it is explicitly not treated as source availability. Point-in-time eligible
  count and ticker-locator retention are zero.
- The 687,382-byte owner-read-only plan has SHA-256
  `cb22c677df6fc220d00ead1326c19a3ec41fcd5de207c1b8797cf76a96a31ed3`
  and logical fingerprint
  `7d6ae3fa41aacba3ae03cf6e1a9485dd8b7eaaf9678317831240f8b122523736`;
  a separate exact-SHA reread passed.
- Complete API regression passed `2168 passed, 2 warnings`. The post-run
  network-free report kept `/data` at 4,060 files / 2,009,699,645 bytes,
  fingerprint
  `16033737d18cd8d34de3e8401ee0f3e5d195a49470a2cda384a604ed6f29db1e`,
  zero symlinks and zero residue. No acquisition, canonical lifecycle,
  Historical Coverage, research, Snapshot, bundle, OCI, scheduler, or
  deployment transition occurred.

## 2026-09-08 — Publish current EOD and Identity family evidence canonically

- Revalidated clean Dell main, the owner-read-only ADR 0165 plan, its physical
  SHA-256, all 304 sessions of bound source bytes, both absent targets, and zero
  residue before mutation.
- The ADR 0166 exact executor published EOD first and Identity second: two
  immutable manifests / 675,569 bytes, two formal family rereads, zero network
  requests, zero overwrites, and zero deletions. The outside-target fingerprint
  remained unchanged throughout the locked critical section.
- A separate completed-state `verify_then_complete` postflight reused both
  targets and wrote zero files/bytes. The authoritative read-only report now
  records 4,060 files / 2,009,699,645 bytes, inventory fingerprint
  `16033737d18cd8d34de3e8401ee0f3e5d195a49470a2cda384a604ed6f29db1e`,
  zero symlinks, and zero staging/partial residue.
- Current-context report 1.6 sees exactly two historical family-evidence
  partitions while final Historical Coverage remains absent. Research stays
  `data_blocked`; no model, analytics, Snapshot, bundle, OCI, scheduler,
  deployment, or Production web-serving state changed.

## 2026-09-08 — Prove recoverable EOD/Identity family-evidence Apply

- Accepted ADR 0166 and added one explicit executor for ADR 0165's exact two
  manifests. It requires the plan SHA-256, plan logical fingerprint, family-set
  fingerprint, and approved Dell root; shares the canonical-data lock; blocks
  network access; publishes EOD before Identity through atomic one-file
  directory renames; and compares outside-target inventory before and after.
- Recovery accepts only an exact completed EOD prefix or a completed pair. It
  rejects no-prefix, Identity-first, corrupt, partial, and staging-residue
  states without overwriting or deleting canonical partitions. A completed
  pair is a formal zero-write postflight.
- Disconnected temporary-root fault injection passed for ordered publication,
  interruption, zero-write replay, binding mismatch, corruption, staging,
  outside drift, formal reread, and socket/DNS prohibition. Adjacent historical
  Coverage, Membership Apply, and same-day catch-up regression also passed.
- The focused suite passed 24 tests, the adjacent suite passed 34 tests, and
  complete API regression passed `2160 passed, 2 warnings`; both warnings are
  unchanged dependency deprecations.
- The retained real 304-session plan passed another exact-SHA read-only reread
  with both targets absent. No `/data` Apply, final Historical Coverage,
  research result, analytics, Snapshot, bundle, OCI, scheduler, deployment, or
  Production state changed.

## 2026-09-08 — Plan current EOD and Identity evidence publication without writes

- Accepted ADR 0165 and added a typed deterministic plan for exactly the
  current `eod_price_bar` and `point_in_time_identity` evidence candidates.
  It embeds both evidence contracts, their canonical byte hashes, exact
  immutable targets, and explicit absent-target state while leaving every
  Apply, final Coverage, research, and performance authority false.
- Added network-prohibited `build` and exact-SHA `verify` commands. Plans are
  owner-read-only, canonical JSON direct children of `/tmp`; source drift,
  target collision, plan tampering, staging residue, and custody violations
  fail closed. No Apply executor was added.
- The real plan covers 304 sessions from 2025-06-23 through 2026-09-04. It
  proposes two manifests / 675,569 bytes, with family-set fingerprint
  `be67c6ec924809eca63dacf1130ec19d9df0d673f65b403a416de1f2be812377`,
  plan logical fingerprint
  `6ae6738181012b6f9364d5b624d7edaa81d992b7be623e6bd6b58c2854d5e663`,
  and plan SHA-256
  `dced91a98cf4a71fe28748c241f83aa31dcdb588a9f322245a9b14de6d4511ae`.
  A separate exact-SHA formal reread passed.
- Post-run context verification kept `/data` unchanged at 4,058 files /
  2,009,024,076 bytes with fingerprint
  `d7ddbace6669c1870e86d79fd48aa86ff99d276699d23b84939983f950b236b4`,
  zero symlinks, zero residue, and zero published Historical Coverage evidence.
- Thirteen focused tests and compilation checks passed. The complete API
  regression finished at `2147 passed, 2 warnings`; both warnings are unchanged
  dependency deprecations. No network, `/data`, formulas, analytics, Snapshot,
  bundle, OCI, scheduler, deployment, or Production state changed.

## 2026-09-08 — Validate complete EOD and Identity family evidence candidates

- Reran the existing ADR 0100 network-prohibited full-content adapter over all
  304 canonical sessions from 2025-06-23 through 2026-09-04. It completed with
  zero missing sessions, requests, evidence publications, Historical Coverage
  publications, or Production writes.
- EOD returned `validated_not_published` over 304 artifacts / 2,816,903 rows;
  point-in-time Identity returned `validated_not_published` over 304 artifacts
  / 2,825,403 canonical Instrument rows. Exact fingerprints are recorded in
  the authoritative current context.
- The combined result remains `mechanics_only`. A later family-evidence
  publication review is supported, but historical Membership, canonical
  corporate actions, lifecycle, adjustment reconciliation, and final
  Historical Coverage publication remain blockers. No research or performance
  claim is authorized.
- This was a read-only evidence run. Repository code, `/data`, Production,
  formulas, scheduler, website, and deployment state did not change.

## 2026-09-08 — Gate segmented Candidate downstream cutover

- Accepted ADR 0164 and added one read-only, exact-identity current consumer
  for an explicit segmented base plus append. It requires complete typed
  Candidate/state coverage and fails closed on incomplete legacy append input.
- The retained 9/4 proof returned two ordered Universe batches and 3,549 state
  rows. Exact V1 input comparison completed with zero mismatches. Entry Geometry
  and Strategy Channels then reproduced all four retained batch fingerprints
  with zero independent-Oracle mismatches.
- The segmented read took 43.43 seconds because it still rehashes the roughly
  840 MB base. Visual Context also requires cumulative state history absent from
  the current append. Entry/Strategy correctness is GO; whole-V1 replacement,
  CLI/executor exposure, and cutover are NO-GO.
- This phase is closed rather than extended into another incremental contract.
  Any resumed segmented work must use one bounded design for expected-head
  payload resolution and Visual state input.
- No network, `/data`, authoritative Candidate, formulas, parameters, ranks,
  MI, Snapshot, bundle, OCI, executor, coordinator, scheduler, deployment, or
  Production state changed.
- Targeted coverage passed, and the complete API regression finished at
  `2136 passed, 2 warnings`; both warnings are unchanged dependency
  deprecations.

## 2026-09-08 — Audit Candidate chain head against full lineage

- Accepted ADR 0163 and added a deterministic, zero-write periodic audit that
  reconstructs the active segmented Candidate head from the retained base and
  every ordered append, then requires exact parent, manifest, logical, and
  physical identity.
- The audit binds externally known family, pointer, active logical, and active
  physical fingerprints; it fully rereads the current state after the cold
  replay and fails on missing/reordered lineage, binding drift, or a mid-audit
  current change.
- Validation policy is now explicit: the daily fast path does not claim full
  lineage; periodic audit is required every five accepted append sessions or
  seven calendar days and after recovery; code changes additionally require V1
  semantic reconstruction, the independent Oracle, and affected tests.
- The retained real `/tmp` proof matched the exact simulated 11-session head in
  39.79 seconds / 2,079,080 KiB peak RSS with zero output files, requests,
  mismatches, canonical writes, and Production writes. Audit fingerprint is
  `8adc21deec2bda549f1bb142e482376d6c07183c997050fb008689affb761ca3`.
- `/data`, V1 Candidate, formulas, parameters, ranks, states, publication, MI,
  Snapshot, bundle, OCI, executor, coordinator, scheduler, and Production did
  not change. No canonical pointer exists; reviewed CLI/executor exposure and
  downstream compatibility are the next gates, not an authorized cutover.
- Candidate-focused coverage passed, and the complete API regression finished
  at `2136 passed, 2 warnings`; both warnings are unchanged dependency
  deprecations.

## 2026-09-08 — Prove disconnected Candidate chain-head Apply/recovery

- Accepted ADR 0162 and added a simulation-only exact-plan executor that
  explicitly refuses the Production root, repeats recovery state under a
  root-specific lock, publishes an immutable release first and the exact
  pointer last, then formally rereads the bounded family.
- Recovery recognizes only not-started, exact-release/pointer-pending, and
  complete states. Explicit verify-then-complete may finish only an exact
  release-only state or prove completion with zero writes; staging residue,
  corruption, conflicts, or CAS drift remain untouched and block diagnosis.
- Fixture coverage proves bootstrap, exact successor/rollback, interruption
  recovery, zero-write idempotency, corrupt-release and staging-residue
  preservation, and Production-root refusal before plan I/O.
- Corrected the repository-aware Python runner to include the API test-package
  root as well as application source, so the documented root-level full-test
  command resolves shared `tests.services` fixtures in a clean environment.
- The retained real ADR 0161 plan published 4,962 + 1,712 bytes only to its
  `/tmp` simulation root. Post-family fingerprint is
  `ab5ccd10017c7f14087c50f455a3212d3278e55d2efef1e8b7a4c2da92f30dac`;
  pointer-state fingerprint is
  `02dfb715872bec8cb11c1b51f7791b95fe24ede244f1d7d28da9f12dcab9a476`.
  Immediate postflight reused both exact objects and wrote zero files/bytes.
- No network, `/data`, authoritative V1 Candidate, formula/parameter/rank/state,
  publication, MI, Snapshot, bundle, OCI, executor, coordinator, scheduler, or
  deployment changed. Periodic full-lineage audit is the next gate.
- Candidate-focused coverage passed, and the complete API regression finished
  at `2136 passed, 2 warnings`; both warnings are unchanged dependency
  deprecations.

## 2026-09-08 — Plan segmented Candidate chain-head publication

- Accepted ADR 0161 and added a no-write publication plan for one
  content-addressed immutable chain head plus a pointer-last current-state
  switch. The plan binds exact source, target absence, bounded family
  inventory, current pointer, successor lineage, prospective pointer bytes,
  rollback reference, recovery states, and retention policy.
- First publication has no rollback; a later plan requires exactly one new
  session/append and moves the old active reference into rollback. All tiny
  immutable heads are retained, while automatic pruning and rollback remain
  prohibited.
- Fixture coverage proves bootstrap, successor, exact reread, target collision,
  non-successor rejection, family drift, and valid-but-changed pointer CAS.
- The real 9/4 11-session head produced a disconnected `/tmp` plan with SHA-256
  `d4785ff7526f65c4b91bc96d2e217f6b11ec21d4c6b86cbf99de4acb27f536c2`
  and logical fingerprint
  `fc155109b92a5b5e00f54ae9e2121f0330639866af3c26753534488d94c9797c`.
  It proposes a 4,962-byte release and 1,712-byte pointer.
- No `/data`, network, Production, Candidate formula/parameter/rank/state, V1
  authority, executor, coordinator, scheduler, downstream input, publication,
  Snapshot, bundle, OCI, or deployment changed. Apply/recovery and periodic
  cold-lineage verification remain separate prerequisites.
- Candidate-focused coverage passed, and the complete API regression finished
  at `2135 passed, 2 warnings`; both warnings are unchanged dependency
  deprecations.

## 2026-09-07 — Checkpoint segmented Candidate chain head

- Accepted ADR 0160 and added immutable, non-authoritative segmented lineage
  identity and chain-head contracts. The head embeds the exact current parent
  manifest and binds base/current identities, counts, source/Universe, chain
  tips, and a location-independent incremental lineage fingerprint.
- Added full-lineage cold construction, expected-prior-head plus one-append
  advancement, mandatory expected-fingerprint reads, exact custody,
  idempotency, completed-stage recovery, and fail-closed parent-mode pairing.
- The three-session fixture proved cold head and base → head-1 → head-2 produce
  identical output. With base/history readers disabled, head-1 produced the
  exact same second direct session and append as explicit lineage validation.
- Real cold head construction took 39.82 seconds / 2,078,196 KiB; base-head
  incremental advancement took 24.78 seconds / 1,733,656 KiB and produced the
  same final bytes. The final 4,962-byte head reads in 1.08 seconds and has
  logical fingerprint
  `653f6f3a47066094a32fbf5481e563eebb4a2c290344be7d5c6d20264c0400bc`,
  SHA-256
  `47c8636305f3f89f9fa03855e705b9063763313603b95ee7dc404a720d8e4ee0`,
  and lineage fingerprint
  `33971a2e205afec07aeadfbdcf4d00161bb555dfbb8dc2557f1654c4d3ca55a2`.
- The real head-backed composer took 21.18 seconds / 859,204 KiB versus 36.70
  seconds / 1,203,960 KiB for full parent validation; both append files were
  byte-identical.
- No canonical expected-head pointer, CLI/executor integration, network,
  `/data`, Production, Candidate formula/parameter/rank/state, coordinator,
  scheduler, publication, Snapshot, bundle, or deployment changed. Pointer
  CAS/recovery/rollback, retention, and periodic full-lineage policy remain
  open.
- Candidate/CLI focused coverage finished at `57 passed`; the complete API
  regression finished at `2135 passed, 2 warnings`. Both warnings are the
  unchanged Python `crypt` and Starlette/httpx deprecations.

## 2026-09-07 — Validate ordered multi-generation Candidate lineage

- Accepted ADR 0159 and added one generalized parent-evidence reader over an
  exact base shadow plus an explicitly ordered append sequence. Each generation
  checks the immediate parent manifest SHA/logical identity, session count,
  source contract, Universe, V1 source identity, and forward-chain tip.
- Extended the direct-session writer/reader and ADR 0158 composer with an
  optional parent-append sequence. The empty default preserves existing one-
  generation behavior and identities; later generations bind the exact prior
  append without adding filesystem paths to logical identity.
- A three-session fixture produced base → append-1 → append-2 from consecutive
  verified-prior V1 audits. Append-2 preserved all eight direct projections,
  advanced one ordinal, bound append-1's exact manifest and chain tip, and
  passed idempotent rereads. Missing and reordered ancestry failed closed.
- The real base-plus-ADR-0158 append reader returned the exact 11-session head,
  manifest SHA, and final chain tip in 39.79 seconds with 2,078,752 KiB peak
  RSS and zero external request or Production write.
- This is a cold correctness reader, not an O(current-session) performance
  claim: it validates the base and every supplied append. An immutable governed
  chain head/checkpoint with CAS, recovery, and periodic full-lineage audit is
  the next prerequisite before daily or downstream cutover.
- No real second-generation artifact, network, `/data`, Production, Candidate
  formula, parameter, score, rank, state, executor, coordinator, scheduler,
  publication, Snapshot, bundle, or deployment changed.
- Candidate/CLI focused coverage finished at `57 passed`; the complete API
  regression finished at `2135 passed, 2 warnings`. Both warnings are the
  unchanged Python `crypt` and Starlette/httpx deprecations.

## 2026-09-07 — Compose direct Candidate session into successor append

- Accepted ADR 0158 and added
  `opportunity-candidate-segmented-append/1.1`. The composer binds the exact
  ADR 0155 parent, ADR 0157 direct session, physically completed intended
  incremental V1 audit, and its manifest-committed validation ledger without
  reparsing cumulative V1 business rows.
- Version 1.1 preserves the exact direct payload bytes, names raw-fact order as
  session-local canonical, and binds its prefix through the exact parent chain.
  It does not claim the 1.0 global V1 raw ordinals or reuse the 1.0 chain tip.
- Added the shared 1.0/1.1 reader, recomputed current-projection validation,
  exact physical-copy custody, idempotency, completed-stage recovery, incorrect-
  source rejection, and a fixture guard that fails if composition invokes the
  cumulative V1 semantic reader.
- Real 9/3→9/4 composition completed in 36.70 seconds with 1,203,960 KiB peak
  RSS. The 86,608,577-byte payload is byte-identical to ADR 0157 and retains
  logical fingerprint
  `a62455909c0436ad07e4024c329c961dfec8e8cd85b9aa507f0b1144037cb515`
  and SHA-256
  `9c9af6fa03357f6135e83568d48c5c6f4355df7e9a903d5db8547e2a9642f967`.
- The 3,276-byte manifest has logical fingerprint
  `e7b0efce9a0e24d4ac242d10ec6c944c793f621c5bf568177b49d8b545bce7d6`,
  SHA-256
  `57895b6fd22fbe9f44ce2041c05c7e4c11a0a76f72adec5f8add4227ad90fbf8`,
  and final chain fingerprint
  `b0a43cd1affa3241562f424b67b32bb306ebc1be8c0213636ece27dfedf79ea1`.
- A separate full read took 40.36 seconds / 2,078,136 KiB. An 80.82-second
  1.0/1.1 comparison found all eight current fields and their fingerprints
  exact, the prior chain exact, and the final chain intentionally version-
  distinct.
- No network, `/data`, Production, V1 authority, Candidate formula, parameter,
  score, rank, state, executor, coordinator, scheduler, publication, Snapshot,
  bundle, or deployment changed. Repeated generations, generalized parent
  reading, downstream compatibility, retention, periodic cold audit, and
  cutover remain open.
- Candidate/CLI focused coverage passed, and the complete API regression
  finished at `2134 passed, 2 warnings`; both warnings are the unchanged Python
  `crypt` and Starlette/httpx deprecations.

## 2026-09-07 — Emit Candidate session directly from current objects

- Accepted ADR 0157 and added the non-authoritative Candidate segmented-session
  candidate/payload contracts. A daily verified-prior calculation may
  optionally emit its current panel, batches, states/transitions, raw and
  normalization records, risks, and Oracle without reconstructing them from
  the cumulative V1 audit.
- Bound the direct payload to the exact ADR 0155 parent chain, prepared V1
  manifest, and manifest-committed incremental validation. Raw-fact order is
  explicitly session-local and is not relabeled as V1's whole-history ordinal
  identity.
- Added owner-only deterministic staging, physical custody finalization,
  full semantic recovery/idempotency reads, paired daily-only CLI arguments,
  and resumed V1/sidecar consistency. Physical completion of the intended V1
  audit remains mandatory before any later append composition.
- The real 9/3→9/4 direct writer took 38.907 seconds and produced an
  86,608,577-byte payload while matching all eight ADR 0156 cold-append
  projections. The full proof process, including reconstruction of runtime
  objects from retained evidence, took 76.95 seconds and peaked at 2,079,760
  KiB. A final direct semantic read took 32.831 seconds and field-by-field
  comparison found zero mismatches.
- Payload logical fingerprint is
  `a62455909c0436ad07e4024c329c961dfec8e8cd85b9aa507f0b1144037cb515`;
  physical SHA-256 is
  `9c9af6fa03357f6135e83568d48c5c6f4355df7e9a903d5db8547e2a9642f967`;
  final manifest logical fingerprint is
  `232ecb6de9fcf412e6c532b8bb70127eac5330e87a57f9e812137dcb4b2b0359`.
- No network, `/data`, Production, Candidate formula, parameter, score, rank,
  state, MI, Snapshot, publication, scheduler, coordinator, executor, bundle,
  or deployment changed. V1 remains authoritative; append composition,
  repeated generations, downstream compatibility, retention, periodic cold
  audit, and cutover remain open.
- Direct-session/CLI focused tests passed, and the complete API regression
  finished at `2134 passed, 2 warnings`; both warnings are the unchanged Python
  `crypt` and Starlette/httpx deprecations.

## 2026-09-07 — Prove one-session Candidate append and recovery

- Accepted ADR 0156 and added non-authoritative segmented append and append-
  session contracts. One later V1 audit may extend the exact parent ledger by
  one session only; calculation, parameter, Universe, parent-chain, source-
  audit, physical, logical, count, Oracle, and per-session projection bindings
  fail closed.
- Added owner-only atomic staging, idempotent reuse, exact completed-stage
  recovery, and tests for unchanged parent bytes, non-successor rejection,
  tampering, and simulated final-delivery interruption. Ambiguous partial
  evidence is preserved rather than deleted.
- The real ten-session 9/3 parent extended through 9/4 with one
  86,610,428-byte segment and a 3,248-byte manifest. The append logical
  fingerprint is
  `dd3563f48370c81242f87f376f7156ed67a06e16a6dafdd82ffe786902cae630`;
  the new chain tip is
  `f68d55c17160ab4db98d26f4da0a0742568143e79e2910c804d9c04e306a793d`.
  The parent manifest stayed at
  `798fd208401fde9d85a5914dcb1dbe61c7cf491941b4add71cc5efbbcc7eb89f`,
  and no staging residue remains.
- Initial construction took 8 minutes 37 seconds / 13,073,092 KiB peak RSS.
  Independent cold equivalence took 8 minutes 30 seconds / 13,073,164 KiB,
  found zero mismatches, and produced fingerprint
  `0416ec637c00812e5d99d29e5e2745277d32bb3460db2c035bed836b5d64a202`.
  These intentionally heavy V1 rereads are correctness evidence, not a hot-
  append performance claim.
- No network, `/data`, Production, Candidate formula, parameter, score, rank,
  state, MI, Snapshot, publication, scheduler, bundle, or deployment changed.
- Focused segmented append/shadow tests passed, and the complete API regression
  finished at `2131 passed, 2 warnings`; both warnings are the unchanged Python
  `crypt` and Starlette/httpx deprecations.

## 2026-09-07 — Version segmented Candidate chain identity

- Accepted ADR 0155 and added
  `opportunity-candidate-segmented-chain-identity/1.0`, a distinct forward hash
  chain over the validated immutable session segments.
- Bound every node to prior identity, session order, exact segment logical and
  physical identity, record/scope counts, source audit identity, and frozen
  Candidate/state calculation, parameter, and Universe contract identity.
- Kept V1's cumulative `state_history_fingerprint` separate. No Candidate
  formula, score, rank, state, active contract, publication, scheduler, or
  Production behavior changed.
- The real ten-session 2026-09-03 shadow produced source-contract fingerprint
  `903eb2c7bb16a673e6313825a5f978ca4176081470c789f0ed749312affcce37`,
  final chain fingerprint
  `bababd41348f3ab0a15f6ce7af5e5868fd3ef32a3c91734d19e142be8f1518e0`,
  and assessment fingerprint
  `5b495eb37a0dca9dbaf17c037218122ce62276cda8e43793f0f240bcb75e19ab`
  in 16.4 seconds with zero external request, canonical write, or publication
  authority.
- Append construction, crash recovery, cold equivalence, downstream
  compatibility, retention, and cutover remain unproven.
- Focused segmented-shadow tests passed, and the complete API regression
  finished at `2128 passed, 2 warnings`; both warnings are the unchanged
  Python `crypt` and Starlette/httpx deprecations.

## 2026-09-07 — Prepare prospective daily Membership continuation

- Accepted ADR 0154 and added a network-prohibited daily preparation entry
  point that builds or reuses one V3 Membership candidate from the exact
  same-session canonical Identity source and EOD evidence.
- The preparation classifies next-open eligibility immediately, reuses an
  already canonical publication, refuses physical-only or marker-only
  canonical state, and grants no `/data`, Historical Coverage, research,
  website, deployment, or scheduler authority.
- Added deterministic persistent daily workspace paths for the candidate and
  its later Apply plan. Membership candidate and plan readers now accept only
  those exact owner-only session names in addition to governed temporary
  custody; persistent plan creation is fsynced and atomically renamed.
- Kept the inventory-bound Apply plan separate from early daily preparation so
  later MI or Snapshot writes cannot knowingly stale its pre-state. Membership
  remains an additive research sidecar until a new live session and
  coordinator-integration review pass.
- Corrected stale documentation that still called Membership absent or the
  current-context report contract 1.5. The true state remains one canonical
  signal-eligible Membership session out of 304.
- Focused preparation, custody, publication-plan, recovery, workspace, CLI,
  and administrator-script tests passed. The full API regression completed at
  `2127 passed, 2 warnings`; both warnings are the unchanged Python `crypt` and
  Starlette/httpx deprecations.

## 2026-09-07 — Implement recoverable canonical Membership publication

- Accepted ADR 0153 and implemented exact-plan-bound, network-prohibited
  physical-first/marker-last Apply plus a canonical reader that refuses raw
  Membership without its completion marker.
- Added explicit `verify_then_complete` recovery for exact physical-only and
  already-complete states. Corruption, marker-before-physical state,
  unrelated inventory drift, and staging residue fail closed without deleting
  ambiguous evidence.
- Added the administrator Apply entry point and fixture fault-injection tests.
  Exact real preflight then confirmed the unchanged plan, current-state
  fingerprint, target absence, and zero staging residue.
- Applied the exact 9/4 plan physical-first and marker-last: 3 files / 463,460
  bytes, 19,964 formally reread decisions, publication fingerprint
  `3f71cd40edd2ed6d7e215a95e0cb89c08c7e96dcb9a8fb543a4de34286c15518`,
  marker SHA-256
  `1aabc12560a0e7d0ed058c7a82aaa842e983bfd06e04595f8b1d560d94a4af09`,
  and post-state `/data` fingerprint
  `d7ddbace6669c1870e86d79fd48aa86ff99d276699d23b84939983f950b236b4`.
  No network request, overwrite, or deletion occurred.
- The separate recovery postflight reused both completed targets, wrote zero
  files/bytes, and preserved the post-state fingerprint. Independent canonical
  read and residue census passed. Historical Coverage, strategy results, OCI,
  and deployment remain unchanged and unauthorized by this publication.
- Advanced the network-prohibited current-context report to 1.6. Membership
  progress now requires each publication marker and transitive canonical read,
  reports the exact 1/304 coverage state, keeps raw physical-only partitions
  non-canonical, and bounds large missing-date output by count and range.
- Final verification completed with `2117 passed, 2 warnings` across the full
  API suite. The warnings remain the pre-existing Python `crypt` and
  Starlette/httpx deprecations.

## 2026-09-06 — Plan signal-eligible canonical Membership

- Accepted ADR 0152 and added immutable canonical Membership completion-marker
  and no-write Apply-plan contracts. Raw Membership directory presence is not
  canonical completion; a future Apply must publish physical bytes first and
  the source/timing-bound logical marker last.
- Planning reruns the formal Membership and Identity reads, requires ADR-0151
  `signal_eligible` status, binds both candidate files, the prospective marker,
  both absent targets, and the exact `/data` inventory. Outcome-only evidence
  is rejected before a plan file is written.
- The real 9/4 plan is 5,184 bytes at
  `/tmp/whalpha-membership-20260904-signal-eligible.plan.json`, mode `0600`,
  SHA-256
  `67cf92606ddc5a314a30df304d568f93c7c051d09925d89b81f3b20a964833c8`,
  and logical fingerprint
  `57a59eaf9bfe0b44ba3cf2257e710a59c8f90b6a93b7c34d34dd064bf77c30c4`.
  It proposes 3 files / 463,460 bytes against unchanged `/data` fingerprint
  `a49348fc48219771d96ddc8bafed4fc3d5b32774ac61e45f102eef4fc0bb4f56`.
- A real corrected-9/3 planning attempt was rejected because the partition is
  outcome-only; its requested plan path remains absent. The 9/4 plan keeps
  `apply_authorized=false`, and no canonical Membership, Historical Coverage,
  analytics, Production, deployment, or scheduler state changed.
- Verification completed with `2104 passed, 2 warnings` across the full API
  suite; the warnings are the pre-existing Python `crypt` and Starlette/httpx
  deprecations.

## 2026-09-06 — Gate Membership by next-open knowledge time

- Accepted ADR 0151 and implemented an immutable offline timing assessment
  that separates market information through session close from actual source
  availability, Membership completion, and next-session-open execution.
- The gate formally rereads Membership and canonical Identity source custody,
  proves their fingerprint binding, binds manifest/Parquet hashes and the
  offline XNYS calendar version, and performs no network request or canonical
  write. Temporary input roots must be owner-owned mode `0700`.
- The 2026-09-04 V3 partition is `signal_eligible`: its source cutoff
  `2026-09-06T11:14:35.992620Z` and evaluation
  `2026-09-06T13:15:00Z` both precede the next XNYS open on 9/8 at 13:30 UTC.
  Assessment fingerprint is
  `586cde811b9c26496584f56a89f489d6314dbc00e9ed7c112829238dfebdfedf`.
- The corrected 2026-09-03 partition is explicitly
  `outcome_reconciliation_only`: its Identity source retains the historical
  source policy and its Membership evaluation occurred after the 9/4 open.
  Assessment fingerprint is
  `be8b100a0bf595d31032220d62325a909fe9488ef060b313a83d8813279463ce`.
- The exact 9/3 temporary root was tightened from mode `0775` to `0700` after
  verifying owner, path, and zero symlinks; evidence bytes were unchanged.
  All 2,097 backend tests pass with the same two dependency warnings. No
  `/data`, analytics, Historical Coverage, Production, deployment, or scheduler
  state changed.

## 2026-09-06 — Bind daily Identity to normalized source custody

- Accepted ADR 0150 and advanced new same-day Identity approval plans to 1.1.
  They retain the existing three canonical Identity families, add the typed
  provider source-observation partition, and keep the logical completion
  marker last in one inventory-bound, network-prohibited Apply/recovery chain.
- Added Source Custody 1.1 with an explicit `same_day_identity_plan` origin,
  self-validating direct binding, actual observation-time eligibility, and no
  synthetic historical profile-map fields. Existing historical 1.0 manifests
  and legacy daily Plan 1.0 remain readable under their original contracts.
- Added an append-only source-repair plan and administrator entry point for an
  exact completed Identity. It has no fetch mode and cannot overwrite Identity,
  EOD, or an existing source partition.
- All 2,091 backend tests passed. The real 2026-09-04 no-write plan proved an
  exact 13,155-row / 14-page reconstruction and bound two prospective files to
  `/data` inventory fingerprint
  `81b2eaaa15efb82c27b6adbeeb3dc3861606f0359d3db1157e10fac37fd03056`.
  Exact Apply added only those 998,251 bytes; a verify-then-complete replay
  preserved file content and metadata unchanged. Formal reread reconstructed
  all three canonical Identity families exactly.
- Canonical source custody now has 302 partitions / 3,700,330 rows / 3,858
  page artifacts. Only the revised 8/13 and 8/19 dates remain absent. `/data`
  is 4,055 files / 2,008,560,616 bytes with fingerprint
  `a49348fc48219771d96ddc8bafed4fc3d5b32774ac61e45f102eef4fc0bb4f56`,
  zero symlinks, and zero publication residue. Research correctly remains
  `data_blocked`; no Membership, Historical Coverage, model, analytics,
  Production, deployment, or scheduler state changed.
- The first disconnected 9/4 Membership attempt exposed one legacy-only
  binding-field access before output publication. The shared accessor now
  resolves historical profile-map and daily direct bindings explicitly. A
  second physical audit found the new temporary root was initially `0775`;
  batch validation now creates or requires an owner-owned `0700` root and
  rejects symlinked or group-writable roots.
- The corrected 9/4 V3 shadow contains 19,964 decisions over a 9,982-Instrument
  evaluated base, with logical fingerprint
  `ea95ca155b1666392dc2a596d4ffa97c9edc9b4313501ed253f59419ad132130`
  and physical SHA-256
  `94411a02fff000eb2f6ea2288964ce22097cc4539433000ea665e0a9dd847532`.
  A repeat returned `already_present` with the full tree unchanged. Combined
  disconnected V3 evidence now covers all 302 available-source sessions and
  5,611,048 decisions; it remains temporary retrospective evidence.

## 2026-09-06 — Complete 9/4 daily chain and clarify freshness

- Completed guarded 2026-09-04 Identity and EOD acquisition/Apply, all nine
  offline analytics stages, fresh MI/Snapshot publication, exact serving-bundle
  build, OCI deployment, and independent postflight. No stale-review exception
  was required.
- Canonical EOD now has 304 sessions and the latest 9,962-row partition is
  aligned with a 9,982-Instrument Identity snapshot. After the final source-
  bound Snapshot, `/data` has 4,053 files / 2,007,562,365 bytes with zero
  symlinks and publication residue.
- Published MI 1.3 and Snapshot 1.11 / Dashboard 2.8 for 9/4. Both Universes
  remain Balanced; Candidate display counts are 880 Primary and 951 Secondary.
- Independent OCI proof matched the exact 51-file bundle and verified service,
  route, guest Session, protected-resource, logout, and capability-parity
  boundaries. Failed system units and deployment residue are zero.
- Accepted ADR 0149. Current-context report 1.5 now separates live operational
  freshness for canonical data and the active Snapshot from the immutable
  Snapshot publication assertion. The bilingual UI explicitly labels the
  static value as a publication-time check.
- Re-published the unchanged 9/4 MI and analytics through exact source-bound
  Snapshot/OCI release `2026-09-06T121300Z-ab1abf1afaaf`. Independent
  postflight matched the new bundle and passed services, protected routes,
  guest capability parity, zero failed units, and zero deployment residue.
- The daily Identity path did not add normalized historical source custody, so
  its explicit gaps are now 8/13, 8/19, and 9/4. Research remains data-blocked;
  no model, Universe, scheduler, or research-authority gate changed.

## 2026-09-05 — Disconnected inactive lifecycle resolution shadow

- Accepted ADR 0148 and added one-to-one source-observation and
  resolution-decision contracts plus an immutable owner-only `/tmp` builder
  and formal reader. Stable identity uses share-class then composite FIGI;
  ticker and CIK never create positive identity.
- Every missing, colliding, absent, malformed, future, ticker-conflicting, or
  temporally contradictory row is retained with explicit quarantine reasons.
  Passing rows remain review candidates with explicit missing terminal facts,
  not canonical delistings.
- All 2,088 backend tests passed with the same two dependency warnings; package
  integrity, contract, tamper, one-to-one, and reuse tests passed, and
  dependency inspection found no broken requirements.
- Real disconnected builds classified 471/23,260 rows at the 7/16 anchor and
  547/23,469 at the 9/3 anchor as review candidates. The later source adds 76
  candidates and 186 quarantined rows; no shared exact row changes disposition.
- The six-file temporary shadow is 8,892,156 bytes, owner-only, symlink-free,
  and residue-free. The network-prohibited postflight proved `/data` unchanged
  at 3,958 files / 1,877,724,006 bytes with the same inventory fingerprint.
  No analytics, publication, Production deployment, or scheduler change
  occurred.

## 2026-09-05 — Resumable inactive lifecycle source custody

- Accepted ADR 0147 and added a distinct owner-only `/tmp` source package for
  one historical Massive `active=false` anchor rather than weakening the
  existing active Identity or six-page Pilot contracts.
- The package streams and fsyncs each sanitized page, atomically checkpoints
  progress, resumes only after complete custody reread, adopts only an exact
  crash-window orphan page, detects cursor loops, and formally rereads the
  completed request chain, aggregates, file set, modes, sizes, and hashes.
- Hard ceilings are 100 pages, 100,000 rows, 8 MiB per page, and 512 MiB of
  sanitized page content. Provider request IDs, pagination URLs, credentials,
  and Authorization material are not retained.
- Twelve focused tests cover normal completion, network resume, checkpoint
  crash recovery, immutable reuse, pagination loops, scope violations,
  coexistence, tampering, safe CLI output, and the `/tmp`-only boundary.
- The clean-revision real package completed naturally at 24 pages / 23,260
  rows, passed independent formal reread across 26 owner-only files, and found
  22,754 `delisted_utc` observations plus 132 duplicate ticker values.
- A post-acquisition current-context report proved `/data` unchanged at 3,958
  files / 1,877,724,006 bytes with the same inventory fingerprint. No lifecycle
  conclusion, analytics, publication, deployment, or scheduler change was
  made.
- Completed the separate latest-EOD 2026-09-03 anchor in 24 pages / 23,469
  rows. An offline comparison found 262 added and 53 absent-or-revised source
  rows; all 262 additions have delisting dates in the 7/17–9/3 window, but only
  135 have a stable FIGI matching canonical Instrument history.
- A second post-acquisition report again proved the identical `/data`
  inventory, zero symlinks, and zero publication residue. Both source packages
  remain owner-only `/tmp` evidence and outcome-reconciliation-only.

## 2026-09-05 — Bounded inactive lifecycle completion census

- Accepted ADR 0146 after the 301-session active-source census proved that
  disappearances and ticker changes are review candidates, not governed
  lifecycle conclusions.
- Added and ran a no-write, aggregate-only Massive inactive-security census
  with 20-page and 25,000-record ceilings, strict pagination scope checks,
  serial pacing, no retries, and no identifier or response retention.
- The real 2026-07-16 anchor filled all 20 pages (20,000 rows) and still had a
  next page. `delisted_utc` was present on 19,565 rows; the exact state remains
  `truncated_at_ceiling`, so no lifecycle completeness is claimed.
- Replaced stale fixed 279/303 Identity source counts in the historical
  architecture document with the authoritative current-context reference.
- No `/data`, canonical dataset, analytics, publication, deployment, or
  scheduler state changed.

## 2026-09-05 — Remove false exact-duplicate Identity collisions

- Accepted ADR 0145. Provider Identity indexes now collapse only structurally
  identical references already retained as exact source duplicates. Any
  difference in ticker, status, canonical instrument, or stable identifiers
  remains a distinct conservative collision candidate.
- Localized the prior 2026-08-31 failure: eight of ten unique collision
  observations were exact duplicates, while the distinct unresolved AREN/PAAI
  pair remains a genuine collision. The corrected session maps 9,965/9,967
  join-eligible observations, passes the unchanged 0.999 gate at
  0.999799337815, and produces 19,930 temporary Membership decisions.
- All 303 Identity partitions contain exact duplicate rows on only 8/31 and
  9/3. A corrected five-session boundary passed 5/5; 8/28, 9/1, and 9/2 have
  zero business-decision change. On 9/3 only FAN changes in both Universes from
  false-collision quarantine to explicit ETF exclusion. Corrected single and
  batch outputs are byte-identical.
- Disconnected evidence now covers all 301 source-available sessions and
  5,591,084 decisions. The only source gaps remain 8/13 and 8/19. All 2,067
  backend tests passed with the same two warnings; no network request, `/data`
  or Production write, publication, deployment, or scheduler change occurred.

## 2026-09-05 — Consume canonical Identity source in Membership shadows

- Accepted ADR 0144 and added a V3 historical Membership path that formally
  rereads canonical normalized Identity source observations, rebuilds all
  accepted Identity families under the manifest-bound profile, and carries the
  canonical custody fingerprint into downstream lineage. The retained-package
  V2 path remains for compatibility review.
- Proved 2026-09-03 V2/V3 business-decision equality across 19,958 rows. Added
  exact non-localizable evidence failure reporting and kept the 0.999 linkage
  gate unchanged.
- Declared the missing PyArrow timezone runtime dependency. The same 9/3 output
  fell to 59.53 seconds without changing logical or physical hashes; the
  five-session boundary completed in 135.53 seconds.
- A network-disabled four-process preflight classified 300/303 sessions as
  eligible. The known 8/13 and 8/19 sources remain absent; 8/31 alone fails
  `identity_join_ratio_below_gate` because ten stable-ID collisions yield a
  0.998996689074 ratio.
- Ran all 300 eligible sessions into 62 disconnected `/tmp` batches using four
  Dell-local workers. All 5,571,154 decisions were formally reread with zero
  failure. The 600-file / 129,736,636-byte inventory fingerprint is
  `8afa4e188d006e5ac732447d0ca1042b6797b2af51bd3a3547a87a5167e886cf`;
  symlinks and staging residue are zero, and a repeated first batch reused all
  five partitions.
- All 2,066 backend tests passed with the same two dependency warnings. No
  provider request, `/data` or Production write, active-pointer change,
  Historical Coverage publication, OCI deployment, or scheduler change
  occurred. Research readiness remains `data_blocked` because the shadows are
  retrospective and three sessions remain blocked.

## 2026-09-05 — Separate Identity observation and replay provenance

- Accepted ADR 0143. Historical package and normalized-source equivalence now
  preserve actual package observation time while replaying the one non-null
  row-level ingestion timestamp shared by the accepted Instrument, Provider
  Identity, and Resolver families. Any missing, non-unique, family-divergent,
  unreadable, or wrong-count replay provenance fails closed; no content
  fingerprint gate was weakened.
- Advanced the profile map to backward-compatible contract 1.1 with an
  explicit unbound dual-profile-mismatch class. Such packages remain in the
  complete inventory fingerprint, receive no profile binding, cannot be
  normalized, and are distinct from physically missing source.
- The 303-session, 13-root, four-process real census found 58 current-profile
  exact sessions and 243 legacy-profile exact sessions. All 303 packages pass
  custody with no missing, duplicate, or unavailable snapshot; 301 are covered
  exactly once. Reacquired 2026-08-13 and 2026-08-19 remain unbound because
  their provider record sets and stable-identity fields differ from the
  accepted snapshots under both profiles.
- A `/tmp`-only 22-session normalized candidate completed 287,298 rows in 44
  read-only files / 21,785,110 bytes. Its exact append plan has SHA-256
  `f8f733aca792dc46279af937a8cb9c0165732eca10cbefa17f64a7ffd2fa1497`
  and binds pre-state
  `27dccc3039aed87dce903f41b55f488bd0b07a67c47885449b957c98b4ad49f5`.
- The ordinary Apply published and formally reread all 22 absent partitions
  with zero overwrite/delete/request. An independent `verify_then_complete`
  pass reused all 22 and wrote zero bytes. Canonical source custody is now
  301 partitions / 3,687,175 rows; whole `/data` is 3,958 files /
  1,877,724,006 bytes with fingerprint
  `12b35440e876f8f61fa0bccef8cc06b4c1721c0dc751ebdaa6c572c2df166345`,
  zero symlinks, and zero publication residue. The two revised source dates
  remain absent; membership, Historical Coverage, research, Production,
  publication, deployment, and scheduler state did not change.

## 2026-09-04 — Support explicit append-only Identity source plans

- Accepted ADR 0142 and extended the existing no-write source Apply planner
  with an optional exact session selection. The original all-profile-bindings
  behavior is unchanged when no selection is supplied.
- Explicit selections must be nonempty, unique, ascending, and profile-bound.
  Only selected candidates and absent targets enter the plan; existing
  unselected canonical partitions remain immutable and stay inside the fresh
  whole-`/data` compare-and-swap pre-state.
- A two-session fixture proved that a one-session candidate can be planned
  while another profile-bound session is already canonical and never becomes
  a target. Invalid empty, unordered, duplicate, and unbound selections fail
  closed.
- All 2,058 backend tests passed with the same two dependency warnings.

## 2026-09-04 — Add a bounded Identity source-gap fetch boundary

- Accepted ADR 0141 and added a Dell-only source-gap fetcher for an explicit,
  ascending set of at most 24 historical dates. It preflights canonical EOD,
  same-day Identity, and absent normalized source custody before the first
  provider request.
- The operation reuses the existing credential boundary, sanitized immutable
  package writer, custody reader, endpoint/page/record limits, and one shared
  serial 15-second limiter. Only timeout/unavailable failures receive the
  existing bounded 30/90-second retry policy; safe checkpoints omit source
  bodies, URLs, request identifiers, exception text, and secrets.
- The resumable output remains owner-only below `/tmp` and performs zero
  canonical, normalized-custody, membership, analytics, publication, or
  deployment writes. New packages still require independent current/legacy
  exact-equivalence proof before profile binding or normalization.
- Ten focused tests, the existing Same-Day fetch suite, and all 2,053 backend
  tests passed with the same two dependency warnings. No provider request or
  `/data` write occurred during implementation and validation.

## 2026-09-04 — Expose canonical Identity source custody in current context

- Accepted ADR 0140 and advanced the network-prohibited current-context report
  to contract 1.4. It now projects the `point_in_time_identity` source-
  observation layer separately from resolved canonical Identity snapshots.
- The routine reader validates fixed dataset/provider/session paths, canonical
  modes, exact two-file partition custody, typed self-consistent manifests,
  unique ordered dates, and alignment to the canonical EOD session index. It
  does not repeat the multi-minute full Parquet semantic pass during ordinary
  task recovery.
- The real Dell report identified 279 partitions, 279 manifests, 279 Parquet
  files, 3,399,877 rows, 3,536 source artifacts, zero source-only dates, and
  the exact 24 missing EOD sessions. State remains
  `canonical_partitions_observed_not_coverage_validated` with a distinct
  incompleteness blocker.
- Seventeen focused current-context tests and all 2,043 backend tests passed
  with the same two dependency warnings. `/data`, research readiness,
  Membership, Historical Coverage, scheduling, Production, publication, and
  deployment did not change during this reporting step.

## 2026-09-04 — Apply 279 historical Identity source partitions canonically

- Revalidated clean Dell main commit `3d73ccd1f62e6c7f0df011312456c327fbc4623b`,
  the exact plan SHA/logical/pre-state bindings, all 558 owner-only candidate
  files, all 279 absent targets, zero matching concurrent jobs, and more than
  729 GB available before executing the separately directed transition.
- The ordinary atomic Apply published 279 immutable partitions, 558 files, and
  258,394,518 bytes in 2:01.79 at 306% CPU. All 279 partitions passed the
  canonical typed reader. External requests, overwrites, and deletions were
  zero.
- Physical postflight found 279 manifests plus 279 Parquet files with exact
  bytes and modes, zero symlinks, and zero staging residue. A separate
  `verify_then_complete` pass formally reread all sessions, reused all 279,
  wrote zero files/bytes, and again reported zero overwrites/deletions.
- `/data` now contains 3,914 files / 1,855,938,896 bytes with inventory
  fingerprint
  `27dccc3039aed87dce903f41b55f488bd0b07a67c47885449b957c98b4ad49f5`.
  The exact 24-session source gap remains. Research readiness stays
  `data_blocked`; Membership, Historical Coverage, performance, scheduling,
  Production, publication, and deployment did not change.

## 2026-09-04 — Prove atomic historical Identity source Apply and recovery

- Accepted ADR 0139 and added an explicitly invoked executor for the exact
  `historical-identity-source-apply-plan/1.0` boundary. It requires the plan
  file SHA-256, logical fingerprint, expected `/data` pre-state, and approved
  root; repeats all plan/source/inventory checks under the shared publication
  lock; prohibits network access; and never overwrites canonical targets.
- Added immutable same-parent staging, canonical modes, fsync/hash checks,
  atomic per-session rename, a strict canonical typed reader, and complete
  post-publication formal reread with bounded local process parallelism.
- Added explicit `verify_then_complete` recovery. It accepts only exact
  completed or absent planned partitions, compares the inventory outside the
  complete planned target set to the original pre-state, reuses exact targets,
  and publishes only absent ones. Partial, changed, extra-file, symlinked,
  wrong-mode, staging-residue, and unrelated-drift states fail closed without
  overwriting or deleting evidence.
- Disposable `/tmp` tests proved ordinary Apply, exact CLI binding, pre-write
  drift rejection, an injected post-rename interruption, mixed completed/absent
  recovery, ordinary replay refusal, partial-target preservation,
  staging-residue preservation, and parallel canonical reread.
- A post-implementation real no-write preflight revalidated the 279-session
  plan, all 558 candidate files, all absent targets, and the unchanged `/data`
  pre-state in 4.76 seconds; status remained `ready_for_separate_review` with
  `apply_authorized=false`.
- The focused historical-Identity suite passed 32 tests and all 2,041 backend
  tests passed with the same two dependency warnings. The real 279-session
  plan was not invoked: `/data`, Production, scheduling, membership, Historical
  Coverage, research readiness, and deployment remain unchanged.

## 2026-09-04 — Normalize and plan durable historical Identity source custody

- Accepted ADRs 0137–0138 and added typed complete-result source observations,
  immutable owner-only Parquet custody, formal readers, a bounded socket-free
  batch runner, and one combined complete-candidate census / no-write Apply
  plan. Raw response envelopes, URLs, request IDs, credentials, and
  Authorization material are not promoted.
- The four-process real candidate completed all 279 profile-bound sessions in
  26:11.52 at 399% CPU and 486,728 KiB peak RSS. It preserves 3,399,877 rows
  and 3,536 page records in 279 Parquet plus 279 manifest files totaling
  258,394,518 bytes, 25.49% of the represented 1,006,791,465 response bytes.
  All files, modes, schemas, row/page counts, fingerprints, profile bindings,
  accepted Identity reconstructions, and an independent full reader pass
  reconciled; symlink, staging, and forbidden-flag counts are zero.
- The inventory-bound plan binds all 558 candidate files, 279 absent targets,
  candidate inventory
  `a75a421ce8daf3b4170dfa06e61b86c2200ce3d371de9e37f36a89a19cd69881`,
  and `/data` inventory
  `2928d804ea48cf076b0a589d09b0e150cf07810dc4dd0cef503121d53d95d794`.
  Its 639,375-byte file SHA-256 is
  `97e22c62bc8554f1229a41925970a365d189a5ad05bbf802e984fc9f3885c1a0`
  and logical fingerprint is
  `6310b845d83ead27e949d66bae158c021be010ccd7565b724f55e5a20d20f87d`.
- Four-process plan construction reduced wall time from 5:17.38 to 1:30.46
  while producing byte-identical plan files. The CLI now reports bounded
  aggregates instead of emitting hundreds of per-session rows.
- The plan is only `ready_for_separate_review`; Apply authorization is false.
  External requests, `/data` writes, membership writes, Production,
  scheduling, formulas, Universes, research readiness, publication, and
  deployment did not change. The 24 physical source gaps remain separate.
- Twenty-four related focused tests and all 2,033 backend tests passed with
  only the two unchanged dependency warnings.

## 2026-09-04 — Bind historical Identity profiles before membership

- Accepted ADR 0136 and added the typed, owner-only
  `historical-identity-rebuild-profile-map/1.0` contract. The builder formally
  parses the complete current/legacy census reports, independently recomputes
  their canonical-session and package-inventory fingerprints, requires one
  complementary exact profile per retained session, and keeps common missing
  sessions unbound.
- The real map binds 279/303 sessions: 58 to `current_v1`, 221 to
  `pre_etv_governance_v1`, and the same 24 physical gaps to neither. Its
  276,471-byte owner-only report has physical SHA-256
  `4fcc1a5eb23c9615e3478ad1b9dd477c906e587cf760cff3ac4b74383030c289`
  and logical fingerprint
  `20e8b8f5b360d8a4ad4a78f0add69fb5eb88e1bc3ab5c6059dd87ca1035e0028`.
- Single-session and bounded membership commands now require the validated map
  and have no free-form profile override. The calculation path revalidates the
  selected profile, package locator/manifest/content/observation bindings, and
  all accepted Identity-family fingerprints; binding provenance enters every
  reconstructed record's source fingerprints.
- A real adjacent 2025-09-09/10 batch crossed from current to legacy profile,
  read 22 shared EOD partitions, and completed 17,728/17,764 records in 2:03.60
  with zero failures. An independently generated-map repeat produced identical
  binding fingerprints, manifests, logical fingerprints, and Parquet bytes.
- External requests and canonical writes were zero. `/data`, Production,
  scheduler state, active pointers, analytics, and research readiness did not
  change. Durable package custody, 24 source gaps, broad membership, and
  Historical Coverage remain separate gates.
- Eighteen focused checks and all 2,023 backend tests passed with the two
  unchanged dependency warnings.

## 2026-09-04 — Prove versioned legacy ETV Identity compatibility

- Accepted ADR 0135 and added the explicit `pre_etv_governance_v1` historical
  comparison profile without changing the default current builder. It changes
  only strictly validated non-instrument ETV Identity rows from the current
  excluded representation to the prior rejected representation and keeps
  Instrument Master and Resolver records unchanged.
- The real serial positive/negative sample made 2025-09-10 and 2026-08-31
  exact while correctly rejecting legacy equivalence for current-rule 9/3. A
  two-worker repeat was byte-identical after excluding only worker metadata and
  reduced wall time from 29.57 to 19.93 seconds.
- The four-worker full legacy census completed 303 sessions in 12:22.98 at
  398% CPU: 221 exact, 58 Identity-only mismatches, and 24 missing. All 279
  packages passed custody; all other failure classes were zero. The 443,879-
  byte report SHA-256 is
  `ac68b70a7119c1d88c6bda9ce3b10f352f3eaa4ebb550200d0d16dc306735776`.
- Current and legacy exact sets are disjoint and cover all 279 retained
  packages exactly. Current mismatches equal the legacy exact set, current
  exact sessions equal legacy mismatches, and both missing sets are the same 24
  dates. Profile selection must be fingerprint-bound rather than date-based.
- External requests and canonical writes were zero. `/data`, Production,
  scheduler, analytics, formulas, current ETV classification, Universes, and
  research readiness did not change.
- Thirteen focused checks and all 2,018 backend tests passed with the two
  unchanged dependency warnings.

## 2026-09-04 — Census retained Identity package equivalence

- Accepted ADR 0134 and added a network-disabled, read-only census that
  formally inspects canonical same-day Identity, rereads every retained package
  artifact, rebuilds all three Identity families, and refuses to choose among
  duplicate sources. Reports are atomic, owner-only, `/tmp`-only, and contain
  no payload rows, tickers, credentials, or source paths.
- A serial three-session real sample correctly separated missing 7/17,
  mismatched 8/31, and exact 9/3. A two-worker repeat was byte-identical after
  excluding only declared worker-count metadata and reduced wall time from
  26.09 to 15.99 seconds.
- The four-worker full census completed 303 sessions in 12:25.56 at 399% CPU:
  58 exact, 221 current-builder Provider Identity mismatches, and 24 missing.
  All 279 discovered Identity packages passed custody; duplicate, unroutable,
  outside-index, and canonical-snapshot failures were zero. Every mismatch
  preserved exact Instrument Master and Resolver fingerprints.
- Four representative row-level checks found stable keys equal and changed-row
  counts exactly equal to ETV counts. The sole sampled transition was the
  governed 2026-09-03 ETV change from unknown/rejected to exchange-traded-
  vehicle/excluded. The 221 packages are therefore retained for a full
  versioned compatibility proof rather than being discarded or reacquired.
- The 447,255-byte report has SHA-256
  `e07ee30c025467950942f734546ededcd2904f7ed939e5b56423addf02c3c79d`.
  External requests and canonical writes were zero; `/data`, Production,
  scheduling, analytics, formulas, Universes, and research readiness did not
  change.
- Twelve focused checks and all 2,017 backend tests passed with the two
  unchanged dependency warnings.

## 2026-09-04 — Bound and accelerate historical membership shadows

- Accepted ADR 0133 and replaced the single-session duplicate EOD inspection /
  reread path with one fully validated panel shared across at most five adjacent
  XNYS sessions. The completion index selects dates only; all consumed
  partitions remain deeply validated.
- Reused exact package-rebuilt Identity records for provider join indexes only
  after their Instrument, Identity, and Resolver fingerprints match the
  canonical snapshot. One completed provider type catalog is also shared per
  batch.
- The exact 2026-09-03 replay remained byte-identical and fell from 149.72 to
  111.18 seconds, a 25.7% reduction. The exact 9/2–9/3 batch read 22 EOD
  partitions, matched independent logical/physical fingerprints, and took
  139.71 seconds instead of 222.47 seconds for the two optimized single runs.
- The five-session boundary read 25 partitions in 195.04 seconds and peaked at
  1,296,388 KiB. It completed 9/1–9/3 while isolating 8/28 and 8/31 as exact
  Identity-snapshot mismatches. This proves that 279 custody-valid retained
  packages are not equivalent to 279 reconstructable sessions; a complete
  exact-equivalence census is now the next gate.
- All outputs remained under `/tmp`, with zero network requests and zero
  canonical writes. Production, `/data`, formulas, Universes, scheduling,
  publication, deployment, and research-readiness state did not change.
- Source compilation, 77 expanded focused checks, and all 2,014 backend tests
  passed with the two unchanged dependency warnings.

## 2026-09-04 — Prove complete-base historical Universe reconstruction

- Accepted ADR 0132 and added a network-disabled, `/tmp`-only adapter from a
  custody-validated sanitized Identity reference package to complete same-day
  Primary/Secondary membership ledgers.
- The adapter formally rereads same-session Identity and EOD, reuses the
  provider-type catalog only as a code dictionary, exactly rebuilds all three
  accepted Identity-family fingerprints from the retained package, applies
  current/previous bar and 20-session liquidity gates, and covers every
  canonical stable ID.
  Known policy failures are explicit exclusions; missing, conflicting,
  incomplete, material-quality, and material-return inputs are quarantined.
- Record-level ambiguity/collision is localized while non-localizable source
  failures remain whole-session blockers. The 2026-09-03 real Dell shadow
  covered 9,979 IDs and formally reread 19,958 rows: Primary 1,682 included /
  8,235 excluded / 62 quarantined; Secondary 1,797 / 8,107 / 75. One source
  collision affected one stable ID and did not invalidate unrelated records.
- The offline package census found 279/303 available sessions and an exact
  24-session gap from 2026-07-17 through 2026-08-19. Retained packages remain
  ephemeral evidence, not canonical custody. The real output remains
  mechanics-only because the source cutoff follows the session.
- Folded 21 EOD component hashes into one deterministic source-envelope
  fingerprint and added reusable formal history reads so the liquidity audit
  does not reopen the same partitions. No provider request, credential read,
  raw-body copy, `/data` write, publication, deployment, or scheduler change
  occurred.
- Source compilation, focused shadow regressions, and all 2,008 backend tests
  passed with the two unchanged dependency warnings.

## 2026-09-04 — Expose family-specific historical research readiness

- Accepted ADR 0131 and advanced the authoritative, network-free current-context
  report to contract 1.3 with an explicit `research_readiness` section.
- The real Dell report confirms that the 252-session price floor is satisfied:
  all 303 contiguous EOD dates from 2025-06-23 through 2026-09-03 have
  same-date completed Identity manifests. Both remain acquired canonical facts,
  not published Historical Coverage evidence.
- Provider-action, canonical-action, daily-membership, lifecycle,
  adjustment-ledger, and Historical Coverage evidence/final roots are absent
  from `/data`.
  Costs/liquidity, complete revision lineage, real chronological evaluation,
  and sealed real holdout remain absent or fixture-only.
- Updated stale Pilot/backfill wording without rewriting dated ADR evidence or
  changing the fingerprinted, superseded Pilot-plan contract.
- The report remains `data_blocked`, never promotes partition presence to
  readiness, and grants no research-development or performance authority. No
  provider request, `/data` write, research run, publication, deployment, or
  scheduler action occurred.

## 2026-09-04 — Prove lossless segmented Candidate shadow custody

- Accepted ADR 0130 and added a socket-free, `/tmp`-only segmented-shadow
  writer, full equivalence reader, bounded current-checkpoint reader, admin
  CLI, custody/tamper tests, and an explicit non-authority contract. Candidate
  V1 remains the sole daily, planning, publication, and Production input.
- The real 842,945,142-byte 2026-09-03 V1 audit converted into ten immutable
  session segments plus a manifest. The 840,660,184-byte shadow has logical
  fingerprint
  `f2f253f14deeca3ee4d8eebb60c1ee0b1edbbaab82934cadde7b35ed71e4fc8e`
  and reconstructed all eight V1 business projections exactly.
- Complete conversion and reread took 548.57 seconds and 11,008,352 KiB peak
  RSS. The bounded current reader rehashed all segment bytes, parsed only the
  86,537,118-byte current segment, and completed in 16.53 seconds with 855,712
  KiB peak RSS. It returned two Candidate batches, 3,549 current state rows,
  and six risk results.
- The first real attempt failed closed because date concatenation changed V1's
  whole-history canonical raw-fact order. The final format records exact source
  ordinals and restored exact equality; no comparison gate was relaxed.
- A separate V1/current-checkpoint sufficiency audit found exact panel,
  batches, 3,549 states, six risks, and all Primary 1,718 / Secondary 1,831
  prior-state support rows. Only the cumulative V1 state-history fingerprint
  differed. It is evidence identity rather than a score/state input, but must
  receive an explicit chain/version contract before any append cutover.
- Candidate audit/shadow focused tests passed 27 checks, and all 1,996 backend
  tests passed with the two unchanged dependency warnings.
- All real work was offline and under `/tmp`, with zero external requests and
  Production writes. No `/data`, MI, Snapshot, scheduler, bundle, deployment,
  formula, parameter, rank, Universe, or active state changed.

## 2026-09-04 — Bind Snapshot rollback and CAS to one active observation

- Accepted ADR 0129. Snapshot approval planning now derives its rollback
  reference and expected current-state fingerprint from the same fully
  validated active Snapshot. Apply, verify-then-link, rollback, and recovery
  retain fresh independent current-state reads.
- On unchanged 2026-09-03 inputs, Snapshot 1.11 / Dashboard 2.8 candidate plus
  Plan 2.6 fell from 135.00 to 121.57 seconds, saving 13.43 seconds or 9.9%.
  Peak RSS remained effectively unchanged at 994,052 KiB.
- All 42 Snapshot files totaling 43,406,568 bytes were byte-identical. Plans
  differed only in the required temporary candidate path and derived plan
  fingerprint; rollback, CAS, target pointer, aggregate, manifest, and all
  business bindings matched exactly.
- The current MI 1.3 candidate-plus-plan path was separately measured at 53.84
  seconds and reproduced the active logical and downstream bindings; its older
  approximately nine-minute journal interval is no longer representative.
- The focused Snapshot publication suite passed 18 tests, and all 1,992
  backend tests passed with the two unchanged dependency warnings.
- All activity was offline and under `/tmp` with `production_writes=0`; no
  `/data`, Production, scheduler, publication, deployment, formula, parameter,
  rank, contract, or Universe state changed.

## 2026-09-04 — Separate daily Candidate commit from semantic audit

- Accepted ADR 0128. Daily verified-prior Candidate completion now combines
  the writer's complete semantic/source/Oracle validation with post-write
  physical custody and atomic delivery. Periodic, code-change, and direct
  finalization retain the complete semantic reread by default.
- On unchanged 2026-09-03 Dell inputs, completion fell from 521.21 seconds and
  8,886,376 KiB peak RSS to 294.99 seconds and 7,534,432 KiB, a 226.22-second
  or 43.4% wall-time reduction. All ten business artifacts were byte-identical,
  logical fingerprint remained
  `b6945f58b4766fd2e110415a7fa45816447205a61caf1085f9fe759c2d89f12f`,
  and Oracle mismatch remained zero.
- A separate explicit full semantic reread of the optimized audit passed in
  228.285 seconds with 8,737,080 KiB peak RSS, the same logical fingerprint,
  zero Oracle mismatches, and completed status. The bounded custody reader
  alone took 1.595 seconds and peaked at 152,816 KiB.
- Candidate-focused 45 tests, source compilation, difference checks, and all
  1,991 backend tests passed with the two unchanged dependency warnings.
- Follow-up instrumentation assigned 193.525 seconds of a 294.30-second replay
  to the cumulative audit writer, including 88.528 seconds across overlapping
  fingerprint calls. Finalization was only 1.739 seconds and explicit garbage
  collection 0.061 seconds. A separate prefix decomposition found all four
  prior business fingerprints still matched and confirmed that cumulative
  canonical projection/fingerprinting, not the finalizer, is the scaling
  boundary.
- No `/data`, Production, scheduler, publication, Snapshot, bundle, OCI,
  formula, parameter, rank, contract, or Universe change occurred.

## 2026-09-04 — Bound Strategy Channels to current Candidate evidence

- Accepted ADR 0127. Strategy Channels now uses the finalized current-batch
  projection instead of reconstructing cumulative Candidate batches, states,
  raw facts, and normalization rows that the stage does not consume.
- On unchanged 2026-09-03 Dell inputs, the prior complete Candidate read alone
  took 225.978 seconds and peaked at 8,737,108 KiB. The optimized complete
  Strategy replay took 33.82 seconds and peaked at 2,538,356 KiB; its current-
  batch projection took 12.588 seconds.
- All four Strategy business artifacts were byte-identical, audit logical
  fingerprint remained
  `440fb9db9d1d3b09bf53a5ba5677f2461c881c45642ccc94720c107c82096e28`,
  Oracle mismatch remained zero, and the permutation gate passed.
- Candidate Visual Context was independently replayed at 51.11 seconds and
  left unchanged. Its two business artifacts were byte-identical and its
  logical fingerprint and zero-mismatch Oracle matched the prior audit.
- The focused 56-test set, source compilation, and all 1,986 backend tests
  passed with the two unchanged dependency warnings. No `/data`, Production,
  scheduler, publication, Snapshot, bundle, OCI, formula, parameter, or
  Universe change occurred.

## 2026-09-04 — Reuse exact panel and current Candidate evidence downstream

- Accepted ADR 0126. Entry Geometry and ETF Relationships now receive the
  existing content-addressed formal panel cache from the daily executor and
  select an entry only through a formally reread upstream source ledger. A
  cache miss retains the formal cold reader and exact source comparison;
  malformed or mismatched cache evidence fails closed.
- Entry Geometry now consumes the finalized current-Candidate and governed
  state projections instead of fully reconstructing the cumulative Candidate
  audit and then decoding the large histories again. No Candidate or Entry
  formula, parameter, contract, rank, or source binding changed.
- On unchanged 2026-09-03 Dell inputs, Entry completed in 49.67 seconds versus
  an approximately 19-minute prior uninstrumented stage interval. All three
  business artifacts were byte-identical, the audit logical fingerprint
  remained `0e2f024489e2c77a6368e2d5af744405c0a1e37dd40c38a4d92021b182e6975f`,
  and Oracle mismatch remained zero.
- ETF completed in 15.36 seconds; its pre-write time fell from 154.178 to
  14.193 seconds and panel loading from 148.666 to 8.423 seconds. All eight
  business artifacts were byte-identical, audit/history logical fingerprints
  remained unchanged, and all equivalence and Oracle gates passed.
- The focused 31-test set, source compilation, difference checks, and all 1,985
  backend tests passed with the two unchanged dependency warnings. These were
  offline `/tmp` replays with no canonical `/data`, Production, scheduler,
  publication, Snapshot, bundle, OCI, formula, or Universe change.

## 2026-09-04 — Separate session discovery from deep partition validation

- Added ADR 0125 and advanced the network-free current-context report to 1.2.
  Normal recovery now validates the immutable completion index and fully
  inspects the latest EOD partition; `--full-history-validation` retains the
  explicit all-partition audit.
- Replaced deep all-history reads only where MI/Snapshot freshness, Candidate
  discovery, Market Regime window presence, application activation, or return
  analytics needs completed dates. Partitions that feed calculations and the
  descriptor/research evidence boundaries still receive full validation.
- On the unchanged 303-session Dell state, the default context report completed
  in 27.65 seconds instead of the observed 7–8 minutes. The explicit deep mode
  completed in 478.01 seconds and reproduced the same current data facts.
- Passed all 1,983 backend tests with the two unchanged dependency warnings.
  No formula, parameter, Universe, canonical `/data`, publication, Snapshot,
  scheduler, bundle, OCI release, or access-capability change occurred.
- Replaced the historically accumulated README and Roadmap execution narratives
  with compact current-purpose and forward-sequencing documents. Historical
  implementation evidence remains in this changelog and the ADRs.
- Removed stale "current" 29/31-session, pre-Activation, and older Snapshot/MI
  claims from long-lived product, architecture, contract, frontend, provider,
  and operations documents. Stable rules remain local to those documents;
  volatile operational facts now link to the authoritative current context.
  Dated audits and historical ADR evidence were not rewritten.

## 2026-09-04 — Complete 9/1–9/3 catch-up and deploy fresh 9/3 state

- Completed canonical Identity/EOD for 2026-09-01, 2026-09-02, and 2026-09-03.
  The formal reader now reports 303 contiguous XNYS sessions from 2025-06-23
  through 2026-09-03; latest EOD contains 9,956 rows and is aligned to the
  same-day 9,979-Instrument Identity snapshot.
- Completed the full 9/3 analytics chain and activated Market Intelligence
  `2026-09-03T070700Z-f506e025475e`, fresh with zero lag. It publishes MI 1.3,
  16 registered ETF relationships, Candidate 1.1, Strategy Channels, Candidate
  Visual Context, and Sector ETF Rotation.
- Activated final Snapshot `2026-09-03T090150Z-a4f10a02b6ae`, Snapshot 1.11 /
  Dashboard 2.8, then built and checksum-validated its 51-file OCI bundle.
- Deployed that exact bundle after correcting the failed-unit gate described
  below. Independent postflight matched the local and remote manifest/checksum
  hashes, verified equal-capability guest access and all protected lazy
  resources, and found no staging or failed-release residue.
- Replaced the oversized, historically mixed current-context/current-status
  files with compact authoritative current-state baselines. Historical detail
  remains in this changelog, ADRs, and dated audits.

## 2026-09-04 — Scope OCI failed-unit postflight to deployment regressions

- A 2026-09-03 release deployment passed local validation and remote preflight
  but rolled back at the final postflight because OCI already had the unrelated
  failed `fwupd-refresh.service`; the deployer had allowed that baseline before
  mutation but required globally zero failed units afterward.
- Corrected the postflight to reject any newly failed system unit while still
  requiring Nginx and the WH Alpha Auth Service to be healthy through their
  existing dedicated checks. The deployment does not reset, restart, or alter
  unrelated failed units.
- Added regression assertions and retained the existing rollback, release
  residue, listener, route, guest-session, checksum, and service gates.

## 2026-09-04 — Preserve unavailable Candidate state in Visual Context

- The first post-backfill 2026-09-01 daily replay exposed two current
  Candidate rows whose state was correctly unavailable after a prior
  stable-identity quarantine. Their state records therefore carried no live
  Candidate fingerprint, as required by the state contract.
- Corrected Candidate Visual Context to require the exact Candidate fingerprint
  only for available state and to require `null` for unavailable state. Price
  path evidence remains descriptive while observed state age remains explicitly
  unavailable; available-state lineage checks are unchanged.
- Added regression coverage for that boundary. The focused 65-test set and all
  1,974 API tests passed with the two unchanged dependency warnings. The failed
  daily action left no target or staging residue; no publication, Snapshot,
  bundle, deployment, formula, Universe, or canonical-data change was made by
  this fix.

## 2026-09-03 — Exclude catalog-known ETV without inferring ETF

- Diagnosed the Historical Research Backfill stop at the 2025-09-09 Identity
  quality gate: 68 catalog-known `ETV` observations plus 113 missing-type
  observations had jointly exceeded the unchanged 1% malformed threshold.
- Added ADR 0124's prospective rule that `ETV` is a known unsupported expected
  exclusion, while its canonical security form remains unknown and no
  Instrument, Resolver, or Universe eligibility can be created from it.
- Kept missing provider type malformed/quarantined and retained every existing
  quality threshold. Completed immutable historical snapshots are not
  rewritten.
- Passed all 1,973 API tests and three-date offline replay, fast-forwarded clean
  revision `4d820c7205f090d4d8602435a4da41f400d87261` to `main`, and resumed the
  finite 300-session process from 245/300 under transient unit
  `whalpha-historical-backfill-continuous-20260903-02.service`.
- Formal readers verified the formerly failing 2025-09-09 Identity and its
  8,836-row EOD partition; canonical history reached 246/300 while the service
  remained active. No analytics, publication, Snapshot, bundle, or deployment
  was performed.

## 2026-09-02 — Chain bounded historical batches to the exact target

- Added a finite Dell-local continuous controller and shell entrypoint so one
  explicit start can run through the remaining 300-session EOD/Identity target
  without manual restarts every 20 dates.
- Preserved the 20-session internal ceiling, one shared serial provider limiter,
  per-date atomic Apply/formal reread, canonical resume authority and ADR 0122
  transient-retry limits.
- Added flushed revision-bound JSON checkpoints after every completed batch,
  final aggregate completion, safe partial-batch stop evidence, zero-progress
  rejection and a target-derived finite loop bound.
- Added simulated cross-batch, already-complete, failure-resume, CLI redaction,
  shell and provider-boundary regression coverage. No provider request,
  `/data` write, analytics, publication, bundle or deployment occurred during
  implementation and testing.
- Fast-forwarded the three reviewed branch commits to clean `main` at
  `e7d3cf3bdf6ac4eda97a965133c3c4e84343dd7f` after 1,970 API tests passed.
  Started one transient user service at 2026-09-02T09:31:19Z for the exact
  300-session target from the 147-session checkpoint. Immediate verification
  found it active/running; no analytics, publication, bundle or OCI deployment
  is part of that service.

## 2026-09-02 — Bound transient recovery inside historical batches

- Advanced the Historical Backfill result contract to 1.1 and added at most
  two same-session retries for transport timeout or provider-unavailable
  failures, with default 30- and 90-second delays.
- Counted every provider-call attempt, including failed calls, and added safe
  structured stop evidence containing completed-session details and the exact
  resumable failed session when the retry budget is exhausted.
- Kept 429/other HTTP responses, data, pagination, quality, custody, inventory,
  plan, Apply and formal-reread failures at zero retry. Added ADR 0122 and
  regression coverage for recovery, exhaustion, non-retry errors, policy
  bounds and secret-free CLI output.
- This is worktree source only. It did not alter the currently running
  clean-main backfill service, make a provider request, write `/data`, run
  analytics, publish, bundle, or deploy.

## 2026-09-02 — Establish the professional quantitative research action framework

- Added a standalone, source-neutral action manual for the complete research
  lifecycle from point-in-time data, feature and label governance through
  chronological validation, costs, capacity, portfolio construction, shadow
  operation, monitoring and retirement.
- Separated stock signal research from option-expression research, fixed the
  role of cross-asset variables as a separately validated condition layer, and
  made paid-data selection depend on measurable uncertainty reduction rather
  than a free-source constraint.
- Included practical research, data-source, model-report and promotion
  templates plus a staged strategy queue. The maintained Markdown source and
  print-ready PDF are documentation artifacts only; they change no runtime,
  data, model, publication or deployment state.

## 2026-09-01 — Complete the three-session Historical Pilot

- Applied the user's ADR 0120 direction: missing written Massive permission no
  longer blocks Dell-local acquisition and remains a non-publication
  limitation rather than a false cleared-permission claim.
- Fetched, planned, atomically applied and formally reread point-in-time
  Identity plus unadjusted EOD for 2026-07-14, 2026-07-15 and 2026-07-16.
- Identity completed in 14 pages each day. Canonical EOD contains 9,843 / 9,852
  / 9,854 rows with zero duplicate keys and zero orphan references.
- Canonical history is now 35 contiguous sessions through 2026-08-31; `/data`
  is 858 files / 655,639,204 bytes at fingerprint
  `f00bf90a1cac51a1ce35950cafe0417d33a62b2adfe260012b3015523b60fdcb`.
- Added ADR 0121's newest-to-oldest, fail-stop and canonical-resume batch runner
  before continuing the remaining history.

## 2026-09-01 — Exact 300-session historical backfill plan

- Added ADR 0119 and `historical-research-backfill-plan/1.0`.
- Fixed the first operating interval to 2025-06-23 through 2026-08-31 from the
  formally reread 32-session Dell inventory.
- Partitioned 268 missing sessions into 90 deterministic, resumable batches;
  the existing 2026-07-14 through 2026-07-16 Pilot remains first.
- Added a socket-guarded, write-free operator CLI and deterministic tests.
- The real plan made zero external requests and zero Production writes and
  remains blocked on permission and complete lifecycle/research families.

## 2026-09-01 — Link Candidate evidence into a decision path

- Added a bilingual five-step Candidate detail path from Market context through
  the registered ETF price proxy, stock leadership and entry posture to an
  explicit re-underwrite boundary.
- Kept the ETF relationship labelled as price-derived rather than sector
  membership or fund flow, and fails closed instead of inventing a sector when
  no registered proxy qualifies.
- Separated technical re-underwrite conditions from Candidate eligibility
  failures. The most actionable published support/trend condition is summarized
  first, while the complete ledgers remain visible; no condition is presented
  as an automatic sell order.
- Full frontend regression passed 113 tests, the production build passed, and
  the active Snapshot 1.11 / Dashboard 2.8 release passed formal reread
  compatibility.
- Fresh lag-zero Snapshot and OCI release
  `2026-09-01T123500Z-579a26759a9e` now bind exact source commit
  `579a26759a9e24c6faf246be343af9e68b9b5ed9`. Formal bundle reread, remote
  preflight, atomic Apply, deployment postflight and independent read-only OCI
  inspection all passed; guest Session and protected routes were verified.

## 2026-09-01 — Make Candidate score contributions decision-readable

- Replaced the Candidate drawer's ambiguous component bars with a bilingual
  ledger whose widths and labels explicitly represent published contribution
  points relative to each component's effective weight, including any explicit
  published score cap.
- Added an exact base-score reconciliation, largest score support, largest
  weighted shortfall, configured evidence availability, and a folded ledger of
  raw and normalized submetrics. “Shortfall” is explicitly not a causal claim
  or trade signal.
- Preserved all Candidate formulas, weights, ranks, risk modes, contracts and
  guest/authenticated capability parity. The active 2026-08-31 Snapshot 1.11 /
  Dashboard 2.8 release passed formal reread compatibility.
- Full frontend regression passed 111 tests and the production build passed.
  Fresh lag-zero Snapshot and OCI release
  `2026-09-01T121730Z-52934c47db45` now bind exact source commit
  `52934c47db454adc2708b6d2dd9c300d85321ca2` without changing the 8/31
  business fingerprints.
- The first local bundle candidate used a release ID different from its source
  Snapshot and the independent formal reader rejected it before remote access.
  The corrected same-ID bundle passed complete reread, remote preflight, one
  atomic Apply, deployment postflight, and an independent read-only remote
  inspection. Guest Session and protected-route checks passed; credential and
  visual browser checks remain manual.

## 2026-09-01 — Bound Snapshot session discovery to the completion index

- Accepted ADR 0118. Snapshot Overview and CLI freshness now select session
  dates through the canonical completion index instead of fully reconstructing
  all historical Parquet partitions twice. Current and previous input
  partitions still receive the unchanged complete validation.
- On identical real 2026-08-31 inputs, deployed source took 251.79 seconds and
  the indexed path took 121.43 seconds, a 51.8% reduction. Business payloads
  were exact across both outputs.
- A same-process Activation reuse prototype saved only another 1.78 seconds
  and was removed to preserve simpler independent reader boundaries.
- Focused Snapshot/Overview regression passed 42 tests; the full backend
  regression passed 1,939 tests with two unchanged dependency deprecation
  warnings.
- No `/data`, pointer, provider, scheduler, publication, bundle, OCI, frontend,
  formula, parameter, Universe, or contract change was made.

## 2026-09-01 — Remove duplicate daily Candidate and Snapshot validation work

- Accepted ADR 0117. The daily Candidate append now rehashes the complete
  immutable prior audit, then parses those verified bytes once instead of
  repeating canonical serialization and every already-finalized historical
  fingerprint derivation. Finalization and periodic/code-change full
  validation remain unchanged.
- The real 2026-08-31 prior-audit read fell from 133.871 seconds to 28.18
  seconds while preserving the exact audit fingerprint and append-input row
  counts.
- Snapshot validation now reuses decoded contract values for cross-file checks
  and removes the redundant per-file validation immediately before complete
  staging validation. Staging/post-rename validation and SHA-256 gates remain.
- Focused backend regression passed 72 tests; the full backend regression
  passed 1,938 tests with two unchanged dependency deprecation warnings. No
  `/data`, scheduler, provider, publication, bundle, OCI, formula, parameter,
  or product-state change was made.

## 2026-09-01 — Complete and deploy the 2026-08-31 daily chain

- Replanned and applied the frozen 13,141-observation Identity package under
  committed ADR 0116. The two stable-identity collision observations remained
  quarantined; 9,965 instruments/resolvers were published.
- Made exactly one custody-reserved 2026-08-31 Grouped Daily request and
  published 9,939 canonical EOD rows with zero duplicate business keys and
  zero orphan references. Identity and EOD now align through 2026-08-31.
- Completed the eleven ordered Dell-local offline stages, including Candidate,
  Entry Geometry, ETF Relationships, Strategy Channels, Candidate Visual
  Context, Sector ETF Rotation, MI and Snapshot planning. Candidate and
  Snapshot-plan execution remained visible single-core performance hotspots.
- Published fresh MI `2026-08-31T101550Z-44b052419be8` and Snapshot 1.11 /
  Dashboard 2.8 release `2026-08-31T102009Z-44b052419be8`.
- The first serving-bundle attempt failed before build because its direct
  `/tmp` basename lacked the lower-level builder's required `tip-` prefix; it
  left no residue. A newly planned compliant path built and formally reread.
- Remote preflight observed the actual prior release
  `2026-08-28T141747Z-83f9b629279c`, then one CAS-bound OCI Apply deployed the
  new release. Independent postflight verified source revision, manifest and
  checksums, Nginx/Auth health, localhost-only listener, protected routes,
  equal-capability guest Session, and zero staging/failed residue. Credential
  login and browser visual inspection remain manual.

## 2026-09-01 — Quarantine isolated stable-identity collisions

- One separately authorized 2026-08-31 Identity fetch-only operation completed
  14 serial pages/13,141 records and produced a frozen owner-only `/tmp`
  package. Custody recorded the package as ready; no `/data` write occurred.
- Offline planning failed closed on one stable-identifier collision group/two
  observations. Aggregate diagnosis showed identical stable identifiers,
  exchange and status but old/new ticker/name observations; no identifier or
  ticker was output.
- Accepted ADR 0116. Collisions remain ambiguous and produce no Instrument or
  Resolver row. They now enter coverage, and only a collision-observation ratio
  at or below 0.1% may be quarantined without blocking unrelated securities.
- Focused Identity/Catch-Up regression passed: 20 tests; full backend
  regression passed 1,938 tests with two unchanged deprecation warnings. The frozen real
  package has not yet been replanned under the new committed rule, and Apply,
  EOD, analytics, publication and deployment remain unauthorized.

## 2026-09-01 — Migrate the read-only timer to the immutable runtime

- The exact systemd review fingerprint was separately authorized. Only the
  owner-only user service bytes changed; the enabled timer bytes and calendar
  remained unchanged.
- Installed service SHA-256 is
  `0e96fc999ea858ff753f570de5c8821c6ea0c1357d62b7518c3ffd8ece3b98ab`;
  timer SHA-256 remains
  `19347d553ad3300c01a03f56337bd31ee9bd9e0b7e16b05b95b58b983512da0b`.
- A controlled start from detached runtime revision
  `fe90cd4d105620a67ad1104bac3cb426586ad29f` exited successfully with
  `runtime_verified=true`, selected missing 2026-08-31, and stopped at
  `review_one_transition_wake`.
- Coordinator, credential, external-request, filesystem-write and
  Production-write counts were all zero. The timer remains enabled/active;
  its next observed trigger is 2026-09-01 17:30 UTC.

## 2026-09-01 — Create and verify the immutable scheduler runtime

- The exact fingerprint-bound runtime plan was separately authorized and
  created as a detached Git worktree at revision
  `fe90cd4d105620a67ad1104bac3cb426586ad29f`.
- Post-creation inspection proved the exact revision, detached HEAD, clean
  worktree, runtime-local imports, executable entrypoint, canonical Python
  resolution and detached runtime verification. Runtime custody was tightened
  to owner-only directories/files without changing Git content.
- A network- and write-free systemd candidate 1.1 review returned
  `review_ready`: service SHA-256
  `0e96fc999ea858ff753f570de5c8821c6ea0c1357d62b7518c3ffd8ece3b98ab`;
  unchanged timer SHA-256
  `19347d553ad3300c01a03f56337bd31ee9bd9e0b7e16b05b95b58b983512da0b`.
- No service or timer was changed or started. No `/data`, credential, provider,
  publication or deployment action occurred.

## 2026-09-01 — Bind scheduler verification to the immutable runtime

- Accepted ADR 0115 and advanced the systemd candidate to 1.1 with explicit
  `main` or `detached` checkout mode.
- Detached verification requires the exact revision-derived runtime path,
  detached HEAD, clean worktree, exact commit and canonical Python executable;
  the expected mode is rendered into the service invocation.
- Main-mode compatibility remains. No runtime was created and no service,
  timer, `/data`, credential, network, publication or deployment state changed.
- Full backend regression passed: 1,936 tests with two unchanged deprecation
  warnings.

## 2026-09-01 — Plan an immutable Dell scheduler runtime

- Accepted ADR 0114 and added
  `daily-eod-scheduler-runtime-plan/1.0` for an exact detached Git worktree on
  Dell, using the canonical project Python environment.
- The deterministic plan fixes revision, paths, proposed worktree command,
  required post-creation checks and a logical fingerprint while granting no
  creation, data, credential, systemd, network or Production authority.
- No runtime directory was created and no timer, service, `/data`, provider,
  publication or deployment state changed.
- Full backend regression passed: 1,933 tests with two unchanged deprecation
  warnings.

## 2026-09-01 — Recoverable degraded user-systemd review

- The 2026-08-31 natural timer trigger correctly rejected its stale pinned
  revision with zero requests or writes, leaving the user manager degraded.
- Candidate review now treats reachable `running` and `degraded` managers as
  review-available while rejecting non-operational and unknown states.
- Added ADR 0113 and regression coverage. No unit, timer, credential, provider
  or Production state was changed.
- Full backend regression passed: 1,922 tests with two unchanged deprecation
  warnings.
- The exact reviewed candidate was subsequently authorized and installed by
  changing only the stale service revision pin; timer bytes were unchanged.
  One controlled read-only start succeeded, selected missing 2026-08-31, and
  stopped before coordination with zero credentials, requests or writes.

## 2026-09-01 — Six-page inactive lifecycle pagination census

- Added a distinct six-page census within the Historical Pilot's existing
  inactive-request ceiling while preserving the two-page ADR 0111 contract.
- Added independently bound exact authorization, same-host/path pagination,
  15-second serial pacing, no retries and aggregate-only output.
- Added ADR 0112, contract documentation and completed/ceiling/error simulated
  coverage. No real census request has run.
- Full backend regression passed: 1,917 tests with two unchanged deprecation
  warnings.
- The subsequently authorized census filled all six pages/6,000 inactive rows
  and still had another page. All rows were explicitly inactive; 5,879 had a
  delisting date, all had update times, and 48 ticker duplicates reinforced the
  stable-ID requirement. The existing Pilot allocation is therefore
  insufficient. No body/identifier was retained and no data was written.

## 2026-09-01 — Inactive-security lifecycle coverage probe boundary

- Added an exact-revision, exact-date two-page inactive All Tickers probe with
  same-host/path pagination enforcement and 15-second serial pacing.
- Output contains aggregate status/field-presence counts only; no response body,
  ticker or identifier is retained, and no data or Production state is written.
- Added ADR 0111, contract documentation and seven simulated tests. No real
  request has run under this boundary.
- Full backend regression passed: 1,912 tests with two unchanged deprecation
  warnings.
- The subsequently authorized 2026-07-16 probe read two pages/2,000 inactive
  rows and stopped `truncated_at_ceiling` with another page present. All rows
  were explicitly inactive; 1,965 had delisting dates, all had update times,
  and 14 ticker duplicates reinforced the stable-ID boundary. No body or
  identifier was retained and no data was written.

## 2026-08-31 — Historical endpoint entitlement probe boundary

- Added a four-request, exact-session Massive technical capability probe for
  Grouped Daily, active point-in-time Tickers, Splits and Dividends.
- Added exact clean-revision acknowledgement review, safe status-only output,
  no response retention, zero writes and zero Historical Pilot authority.
- Added ADR 0110, contract documentation and deterministic fake-transport
  coverage. No credential was read and no real provider request was made.
- Full backend regression passed: 1,905 tests with two unchanged deprecation
  warnings.
- The subsequently authorized clean-main probe made exactly four requests for
  2026-07-16. All four endpoint classes were accessible: unadjusted Grouped
  Daily returned 12,454 rows, while active Tickers, Splits and Dividends each
  returned one deliberately limited result. No body was retained and no data
  was written. This is technical entitlement evidence, not coverage or
  permission evidence.

## 2026-08-31 — Separate data readiness from research activation

- Accepted ADR 0109 and added
  `strategy-research-development-activation-review/1.0`.
- The review formally reconciles readiness and binds the experiment,
  Historical Coverage, code revision, execution/statistics versions,
  independent inference Oracle, single-use holdout custody and zero prior real
  results/activations/holdout uses.
- Current 31/252 readiness remains blocked and produces no authorization text.
  A complete synthetic fixture only prepares an exact fingerprint-bound user
  acknowledgement; activation, real evaluation, parameter selection, holdout
  access and performance authority remain false.
- No CLI, real adapter, result, `/data` write, provider call, activation,
  publication, deployment or scheduler state changed.
- The complete backend suite passes 1,899 tests with only the two existing
  dependency deprecation warnings.

## 2026-08-31 — Independently reproduce research inference

- Accepted ADR 0108 and extended the independent Oracle beyond descriptive
  statistics to the fixed circular moving-block Bootstrap, percentile interval,
  centered-null probability and Holm adjustment.
- The Oracle uses an independently implemented integer MT19937 state machine
  and separate Decimal accumulation/quantile code; it does not call the primary
  evaluator, private Bootstrap helpers or Python `random.Random`.
- Exact outputs match on nonconstant series of 1, 2, 5, 20, 37 and 53
  observations, the full 72-summary development family, and all 24 validation
  Holm values. Final partial blocks are explicitly covered.
- This is fixture-only implementation evidence. No real input, `/data` write,
  model result, parameter change, stage transition, performance claim,
  publication, deployment or scheduler state changed.
- The complete backend suite passes 1,890 tests with only the two existing
  dependency deprecation warnings.

## 2026-08-31 — Reserve the sealed holdout before evaluation

- Accepted ADR 0107 and added `candidate-strategy-holdout-custody/1.0` as a
  durable external seam around future holdout evaluation.
- Custody binds the experiment, mechanics, passed validation report, immutable
  parameter lock and selected combination, then writes its reservation before
  invoking a capability.
- Completion is reread without reevaluation; failure, invalid evidence and an
  interrupted/ambiguous reservation permanently prohibit replay. Owner-only
  permissions, symlink rejection, exact inventory and chained fingerprints
  fail closed.
- Current proof remains fixture-only under temporary roots. No real label,
  `/data` write, provider call, CLI, installed custody root, stage transition,
  performance claim, publication, deployment or scheduler state changed.
- The complete backend suite passes 1,883 tests with only the two existing
  dependency deprecation warnings.

## 2026-08-31 — Expose Quant Research Lab without performance claims

- Accepted ADR 0106 and added Quant Research Lab / 量化研究实验室 as the
  fifth bilingual first-level workspace with equal guest and credential
  Session capability.
- The page displays the preregistered Strong-Leader Pullback hypothesis,
  lifecycle, chronological design, fixed 24-combination family, comparison
  group, outcome horizons, advancement gates and missing foundations.
- The current 31/252 state is explicitly data coverage rather than model
  confidence. Result panels remain unavailable and contain no synthetic
  returns, win rate, chart or implied performance.
- No research API, real evaluator, data contract, `/data` write, publication,
  bundle, deployment, scheduler or Production state changed.

## 2026-08-31 — Adversarially audit research statistics

- Accepted ADR 0105 and added an independent descriptive Oracle that does not
  call the primary evaluator or its private helpers. It reproduces counts,
  dispositions, coverage, paired sessions, Regime cells, evidence floors,
  return summaries, hit rate, MFE/MAE and session-balanced contrasts.
- Added synthetic stable, null, validation-reversal, one-session-crowding,
  one-extreme-session, differential-missingness, cross-split, unlocked-holdout
  and failed-validation-holdout cases. The Oracle reconciles all 72 development
  summaries; constant-series bootstrap expectations and adversarial inference
  behavior are checked without duplicating the random bootstrap implementation.
- The audit found that missing labels were visible but not independently
  transition-blocking. Validation and holdout now add a fail-closed complete-
  evidence quality gates: the full 24-member validation family must have
  complete three-session inference and signal/control coverage, and the locked
  holdout contrast must have `1.0000` signal/control outcome coverage.
- Durable single-use holdout custody and a formal arbitrary-series inferential
  Oracle remain explicitly unimplemented. No real data, `/data` write, provider
  call, model result, UI, publication, deployment or scheduler state changed.
  The complete backend suite passes 1,880 tests with only the two existing
  dependency deprecation warnings.

## 2026-08-31 — Freeze session-balanced research statistics

- Accepted ADR 0104 and added
  `candidate-strategy-research-statistics/1.0` as a fixture-only analysis-plan
  addendum to the unchanged first Strong-Leader Pullback preregistration.
- The evaluator compares equal-weight signal and control means within each
  session, then applies a deterministic five-session moving-block bootstrap
  with 2,000 replicates. Inference requires 60 available signal observations,
  60 controls and 20 comparable sessions; sparse results retain descriptive
  coverage but remain inconclusive.
- Development evaluates the fixed 24 combinations and locks at most one using
  the primary three-session 90% contrast lower bound. Validation cannot change
  the lock and applies Holm-Bonferroni across all 24 hypotheses. Holdout can
  expose only the locked combination and only after every validation gate
  passes.
- Reports include quarantine/unavailable coverage, underlying/SPY-relative
  returns, hit rate, MFE/MAE and 0/10/25/50 bps-per-side scenarios. Fixture
  labels have separate content and record fingerprints; cross-split inputs,
  unlocked holdout records and failed-validation holdout access fail closed.
- No real label, model selection, `/data` write, provider call, canonical
  dataset, UI, publication, deployment or scheduler state was created. The
  complete backend suite passes 1,873 tests with only the two existing
  dependency deprecation warnings. The experiment remains 31/252
  `data_blocked` and every report denies transition and performance-claim
  authority.

## 2026-08-31 — Freeze chronological research execution mechanics

- Accepted ADR 0103 and added
  `candidate-strategy-research-execution/1.0` for the exact preregistered
  Strong-Leader Pullback experiment.
- The fixture-only executor enforces 252 contiguous XNYS sessions, fixed
  50/25/25 chronology, 20-session warm-up, five-session purge and embargo,
  final five-session outcome maturity, and all 24 frozen combinations.
- Signal assignments compare only point-in-time leaders with same-session
  eligible-leader non-signals and are sealed without outcomes. Pending 1/3/5-
  session labels mature only from the exact later path; corporate-action review
  is quarantined without numeric values. Results remain explicitly underlying-
  stock outcomes, not option returns.
- Independent synthetic tests rederive every cohort role and exact outcome
  arithmetic. The complete backend suite passes 1,866 tests with only the two
  existing dependency deprecation warnings. No real data, `/data` write,
  provider call, canonical dataset, model selection, performance result, page,
  publication, deployment, or scheduler state was created. The experiment
  remains 31/252 `data_blocked`.

## 2026-08-30 — Freeze provider-neutral Historical Source packages

- Accepted ADR 0102 and added `historical-source-package/1.0` as the immutable
  `/tmp` boundary between a future authorized provider transport and canonical
  historical-data mapping.
- The package binds the exact Pilot plan/inventory, permission, account-
  entitlement, lifecycle-review, and authorization fingerprints; every
  non-empty planned scope must complete within its request ceiling and every
  response byte is content-addressed.
- Added atomic owner-only publication and complete formal reread. Unplanned or
  incomplete scopes, credential-bearing fields/URLs, budget excess, path drift,
  writable files, symlinks, extra files, and byte changes fail closed.
- Prepared a concise Massive permission and entitlement inquiry for manual user
  sending. It asks separately about Dell acquisition/retention/derivation,
  equal guest/login display and browser delivery, historical endpoint
  entitlement, lifecycle coverage, deletion duties, and fees. It was not sent.
- The focused source-package suite passes 6 tests and the complete backend
  suite passes 1,859 tests with only the two existing dependency deprecation
  warnings. Only synthetic JSON and pytest temporary directories were used; no
  provider, credential, `/data`, canonical Apply, publication, deployment, or
  scheduler state changed.

## 2026-08-30 — Bind current history to a blocked pilot review

- Accepted ADR 0101 and added `current-historical-pilot-baseline/1.0`. The
  network-prohibited command joins formally validated current EOD/Identity,
  the complete physical inventory, exact preceding XNYS sessions, repository
  mapping/invariant evidence, and dated Massive permission conclusions.
- Closed a cross-source trust gap: Historical Pilot Approval 1.1 now requires
  the permission-review `source_id` to equal the plan `provider_id`. The current
  plan uses `massive_stocks_basic` consistently.
- The baseline can satisfy only a fresh exact-inventory gate. It cannot emit an
  authorization acknowledgement while account endpoint entitlement,
  equal-capability source permission, and complete lifecycle/terminal coverage
  remain unresolved.
- Focused pilot regression passed 40 tests, and the complete backend regression
  passed 1,853 tests with only the two existing dependency deprecation warnings.
  No network request, data write, pilot execution, publication, deployment, or
  scheduler change occurred.
- The first clean-main real run at 2026-08-30T17:02:52Z bound revision
  `017ab5657edaa4bf3bd90ac2437448a7486f7b4b`, inventory fingerprint
  `b32d70ae94098bf753282ff2eaa89f241bedc469995bfcd2ac97c2568ddb35ca`,
  and exact targets 2026-07-14 through 2026-07-16. The 75-request plan
  fingerprint is
  `ea6faae1d7f5cd3cd80ce349915a8094bc9e78e7e201f72638a06773f4e01899`;
  the blocked baseline fingerprint is
  `7a8ab595707844fb57f4e64651a9e2db16f16246984a945cce3897ee031d7f28`.
  No acknowledgement was generated; requests and writes remained zero.

## 2026-08-30 — Adapt current EOD and Identity into unpublished family evidence

- Accepted ADR 0100 and added a formal read-only Identity snapshot reader that
  validates the logical snapshot, all three component manifests, exact file
  sets, Arrow schemas, counts, and recalculated content fingerprints.
- Added `current-historical-mechanics-evidence/1.0` and a socket-guarded CLI.
  It converts formally read current EOD and EOD-bound Identity into deterministic
  in-memory family evidence and transitively validates every completion
  manifest and payload SHA without publishing.
- The real Dell run covered 31 sessions from 2026-07-17 through 2026-08-28:
  EOD has 306,539 rows and evidence fingerprint
  `d7def47ee1fba89760a016ba52d79313bf3729aed2fee421c4e05a2596299cd5`;
  Identity has 307,466 canonical instrument rows and fingerprint
  `a69530ea830f448ecb90949c3f2a4a871a87ae015d2c2d8e0e6ae0582e5d4e76`.
  The combined report fingerprint is
  `6ef8da023b0b92c96147e9e11f530c361a3c24a23ff4b6c8a39ec38d6bc12228`.
- Both families are `validated_not_published`. `/data` remained exactly 694
  files / 503,568,026 bytes and contains neither family-evidence nor Historical
  Coverage directories. No network, provider request, `/data` write, model
  run, publication, deployment, or scheduler change occurred.
- Focused adapter/persistence regression passed 19 tests, and the complete
  backend regression passed 1,845 tests with only the two existing dependency
  deprecation warnings.

## 2026-08-30 — Bind Historical Coverage to transitive physical evidence

- Accepted ADR 0099 and added self-fingerprinted Dataset Coverage Evidence 1.0
  plus immutable Historical Coverage publication and formal reread custody.
  Each family evidence binds source completion manifests and every payload file
  by safe relative path and physical SHA-256; one changed byte fails closed.
- The strategy-readiness CLI may now select an exact immutable `coverage_id`
  below the canonical root. It still accepts no arbitrary manifest path and
  advances only after complete transitive reread.
- A 252-session six-family fixture proved the complete mechanics through
  `ready_for_development_review` while retaining both development and
  performance-claim authority as false. All physical tests used temporary
  roots.
- A real socket-guarded Dell reread confirmed that `/data` has no Historical
  Coverage publication and current state remains the same 31/252-session
  `data_blocked` result, fingerprint
  `4d3b5a1b472f710638f024443e2ad6c1dea1f4dd25920c2cd9eb1d3a51802116`.
  No network request, `/data` write, backfill, model run, deployment, or
  scheduler change occurred.
- Focused coverage/readiness regression passed 43 tests, and the complete
  backend regression passed 1,838 tests with only the two existing dependency
  deprecation warnings.

## 2026-08-30 — Bind strategy development to formal readiness evidence

- Accepted ADR 0098 and added deterministic, network-prohibited Strategy
  Research Readiness 1.0. It binds the frozen experiment to formally read
  canonical EOD/Identity evidence and typed Historical Coverage requirements;
  it never grants development or performance-claim authority.
- Corrected the adjusted-OHLCV feature warm-up from 252 to 20 sessions. The
  separate total research-history floor remains 252 sessions. The frozen
  experiment fingerprint is now
  `1b8752d67615d997f5bfa070c3222a7b036840063c2ccc46411a768265197d6f`.
- A real socket-guarded Dell read-only assessment reread 31 sessions through
  2026-08-28 and returned `data_blocked`: daily membership, corporate actions,
  lifecycle, adjustment reconciliation, and mature outcome coverage remain
  unproven. Result fingerprint is
  `4d3b5a1b472f710638f024443e2ad6c1dea1f4dd25920c2cd9eb1d3a51802116`.
- The operational command accepts no arbitrary coverage JSON; a future formal
  physical reader must provide that evidence. No network request, `/data`
  write, model run, publication, deployment, or scheduler change occurred.
- Focused contract/readiness coverage passed 42 tests, and the complete backend
  regression passed 1,830 tests with only the two existing deprecation
  warnings.

## 2026-08-30 — Preregister the first personal quantitative research program

- Accepted ADR 0097 and named the future first-class workspace Quant Research
  Lab / 量化研究实验室, explicitly separate from current Strategy Channels and
  Production ranking.
- Added immutable Candidate Strategy Research Experiment 1.0 and the first
  Strong-Leader Pullback registration. It asks whether an orderly pullback and
  close-based recovery add information beyond prior leadership, using a same-
  session eligible-leader non-signal control, three sessions as the primary
  horizon, and one/five sessions as secondary views.
- Froze 8 feature requirements, a maximum 24-combination development-only
  parameter grid, validation multiplicity control, untouched holdout gates,
  personal-model ownership, model-decay warnings, and the stock-versus-option
  result boundary. Contract identity is
  `3ab7175302bbcfb6894233d1db05534aa69bbab83935fa5d31dc9a916002b5d0`;
  logical fingerprint is
  `1b8752d67615d997f5bfa070c3222a7b036840063c2ccc46411a768265197d6f`.
- The experiment remains `preregistered_data_blocked`. It creates no provider
  request, `/data` write, backtest result, signal/outcome dataset, page,
  publication, deployment, or scheduler transition.
- The focused strategy-contract suite passed 23 tests and the complete backend
  suite passed 1,820 tests with only the two existing deprecation warnings.

## 2026-08-30 — Resume persistent-workspace planning after physical proof

- Accepted ADR 0096 and advanced the read-only Automation Plan contract to
  1.8. It removes only the superseded
  `persistent_workspace_cli_custody_unreconciled` early stop after the exact
  persistent lineage crossed analytics, MI/Snapshot Apply, formal bundle
  reread, OCI deployment, and postflight.
- Preserved the exact workspace validator, all stage readers and lineage gates,
  the single-next-action result, and the separate publication, deployment, and
  scheduler authority boundaries. No provider request, `/data` write,
  publication, deployment, or scheduler transition was performed by this
  revision.
- Formally reread the retained 2026-08-27 Phase 1b and Candidate evidence into
  the exact owner-only prior-session workspace. Two socket-guarded real
  2026-08-28 Plan 1.8 replays then reread all 18 current/prior observations and
  deterministically returned `analytics_ready` /
  `review_bundle_deployment`, fingerprint
  `0782f8793a8564b7b17f354eb81e602afe49c1fe8154bcc371e39ebacee51d83`,
  with zero external requests, Production writes, or operational authority.
- The focused planner, workspace, pipeline scheduler, cadence, executor, and
  coordinator regression passed 119 tests before the real replay. The
  complete backend regression then passed 1,813 tests with only the two known
  deprecation warnings. The installed timer remains read-only and is not
  connected to the coordinator.

## 2026-08-30 — Prove persistent custody through the analytics chain

- Accepted ADR 0095 and added one shared offline-artifact custody policy that
  preserves direct-child `/tmp` reviews while permitting only exact named
  artifacts under an owner-only dated `daily-eod` session outside `/tmp` and
  Git.
- Migrated Phase 1a, Sector ETF Rotation, Phase 1b, Candidate recovery/final,
  Entry Geometry, ETF Relationships, Market Preview, Strategy Channels, and
  Candidate Visual Context writers and formal readers.
- A real Dell 2026-08-28 persistent rehearsal completed all nine analytics
  outputs with `0700` directories, `0400` files, no symlink or recovery
  residue, zero Oracle mismatch, zero external request, and zero Production
  write. An initial Candidate finalization rejection exposed and fixed the
  exact distinction between internal `candidate-work` reread and public final
  `opportunity-candidate` reread without rerunning the completed calculation.
- Automation Plan 1.7 intentionally remains blocked until MI, Snapshot, and
  serving-bundle paths and readers are reconciled and physically rehearsed.
  No `/data`, publication, deployment, provider, credential, scheduler, or
  Production state changed.
- Static checks passed and the complete backend suite passes 1,811 tests. The
  two warnings remain the existing Python `crypt` and Starlette TestClient
  deprecations.
- Extended the same boundary through MI 1.3 candidate/Plan 1.3 and Snapshot
  1.10/Plan 2.5 candidate/plan contracts and formal readers. Real persistent
  rehearsals produced MI plan fingerprint `d943ea1cbe13118418112550e5c7c5c9edc259e69782cbbc7d532eb61f272a84`
  and Snapshot plan fingerprint `b555e488f1623df091dd89935c4ef94607097ca0810e2c032af2c3b201f05c5b`,
  both fresh with zero Production writes. Snapshot persistent files are sealed
  `0400` under `0700` directories.
- The active MI 1.2 correctly rejected Strategy/Visual evidence from the new
  persistent Candidate lineage. A second Snapshot rehearsal used its exact
  legacy-bound audits only to prove Snapshot custody. No MI/Snapshot Apply was
  inferred, so one-lineage bundle construction remains blocked.
- Added a narrow shared-custody preflight to the OCI bundle administrator. An
  exact persistent `serving-bundle` root is accepted alongside the existing
  repository and safe `/tmp` roots; completed persistent bundle directories
  are sealed `0700` with `0400` files. Real bundle rehearsal remains gated by
  the separately authorized Snapshot Apply that creates its immutable source.
- A first real persistent MI Apply attempt stopped before any Production write
  because the CLI loader still imposed its superseded `/tmp`-only check after
  the formal Plan 1.3 reader had adopted shared custody. The loader now uses
  the same governed-location validator as the writer and reader while retaining
  exact-path, regular-file, immutable-mode, full-file SHA, and canonical Plan
  checks. Focused publication and custody regressions pass.
- The authorized MI 1.3 and Snapshot 1.11 / Dashboard 2.8 Applies then
  completed from the same persistent lineage. The first OCI switch was safely
  rolled back by postflight because its shell validator still stopped at
  Snapshot 1.10; review also found that the Candidate and Strategy browser
  adapters stopped at 1.10. All three consumers now accept the exact 1.11/2.8
  pair, and deployment postflight additionally fetches and source-binds the
  Sector Rotation resource through the temporary guest Session. The exact
  failed remote release was removed only after rollback and manifest identity
  were verified; the prior release remained active throughout correction.
- The regenerated source-bound release
  `2026-08-28T141747Z-83f9b629279c` then passed OCI dry-run, atomic Apply,
  temporary-guest Candidate/Strategy/Sector Rotation postflight, logout, and
  independent remote inspection. Standard and persistent bundles share logical
  fingerprint `6e2e08f1e3e9c3d06c3c069e751fce1b9ac2433837952aa2f95186f27c1721e0`.
  Final `/data` contains 694 files / 503,568,026 bytes with fingerprint
  `b32d70ae94098bf753282ff2eaa89f241bedc469995bfcd2ac97c2568ddb35ca`,
  zero symlinks, and zero publication residue.

## 2026-08-30 — Block unproven persistent-workspace execution

- Accepted ADR 0094 and advanced Automation/Coordinator contracts to 1.7/1.14.
- After exact Identity and canonical EOD verification, a persistent-workspace
  plan now stops with `persistent_workspace_cli_custody_unreconciled` instead
  of proposing a real CLI action that older `/tmp`-only custody would reject.
- Direct-child `/tmp` review workflows remain available. No path policy was
  loosened and no persistent directory, `/data` write, network request,
  publication, deployment, or scheduler capability was created.

## 2026-08-30 — Add Candidate Visual Context to daily planning

- Accepted ADR 0093 and advanced the daily planner/executor/coordinator
  contracts to 1.6/1.5/1.13. Candidate Visual Context is now a distinct stage
  after Strategy Channels and before MI planning.
- The planner strictly rereads same-session Candidate, Entry Geometry, ordered
  Universe, Phase 1a history, and zero-Oracle evidence. Snapshot planning
  passes the exact audit and requires Plan 2.6 to bind its fingerprint.
- A real Dell `/tmp` executor-stage run completed 3,541 rows in about 27
  seconds, made zero external requests and Production writes, and reproduced
  logical fingerprint
  `3b8ddbf3cc7d35cf0ea2b8f257939d23cec6f1d463e0d16efce9b5fb1f23961f`.
- The persistent-workspace path policy remains incompatible with several
  older real audit CLIs. Planner/mock execution did not prove that boundary;
  it is explicitly blocking unattended activation rather than being hidden.

## 2026-08-30 — Project Sector Rotation through Snapshot 1.11 / Dashboard 2.8

- Added Snapshot 1.11 / Dashboard 2.8 and Approval Plan 2.6. The immutable
  Snapshot binds the exact MI 1.3 Sector Rotation audit/product lineage and
  writes one checksum-bound lazy `sector-etf-rotation.json` while preserving
  the complete Strategy and Candidate Visual Context chain from Snapshot 1.10.
- Added strict browser parsing and a bilingual Sector Rotation workspace. It
  shows separate 5/10/20-session ETF-relative views, 20-session leadership
  versus five-session acceleration, persistence, and descriptive posture; it
  exposes no composite score, fund-flow claim, constituent breadth, official
  sector membership, or Theme output.
- Extended OCI bundle validation and the public product story to recognize the
  new pair. Guest and credential Sessions retain identical capabilities.
- A real Dell tmp-only build produced 40 checksummed product files and a
  formally reread 42-file Plan 2.6 with fingerprint
  `d31e9c487665cc14fd5cdec7b0a7ccae46a532565e13da1b31e3f0f2afcb24e9`.
  No `/data` Apply, bundle, deployment, or network action occurred; active
  Production remains Snapshot 1.10 / Dashboard 2.7.
- The unattended executor still lacks Candidate Visual Context generation.
  This is now an explicit fail-closed blocker for complete MI 1.3 to Snapshot
  1.11 automation, not permission to omit the visual evidence.

## 2026-08-30 — Bind Sector Rotation into Market Intelligence 1.3

- Added Market Intelligence payload/manifest and Approval Plan 1.3 with one
  market-wide Sector ETF Rotation product. The builder accepts only the strict
  typed audit reader and binds its Phase 1a/history lineage, calculation and
  parameter identity, 11 records, product fingerprint, Theme-unavailable
  state, and zero-mismatch Oracle.
- Apply-time source validation formally rereads the same audit and rejects
  custody or lineage drift. Older Market Intelligence 1.0–1.2 publications
  remain readable.
- Advanced the daily Automation Plan to 1.5. It now observes the derived
  Sector Rotation audit after Phase 1a and fails closed on missing, invalid,
  or mismatched evidence; MI planning must return Approval Plan 1.3 bound to
  the same audit and product.
- A real read-only 2026-08-28 `/tmp` rehearsal produced a fresh, lag-zero MI
  1.3 candidate and Plan 1.3 with plan fingerprint
  `8555bd9d27bdab99fc9006d3945b0b2f35c5dfa12a1ec050aba1591698753181`,
  11 Sector records, zero Oracle mismatch, and zero Production writes. Nothing
  was applied or published.
- Snapshot 1.11 / Dashboard 2.8 remains the required next consumer. Active
  Production stays on MI 1.2 and Snapshot 1.10 / Dashboard 2.7.

## 2026-08-30 — Reuse Phase 1a for the Sector Rotation audit

- The normal Phase 1a administrator CLI now requires a distinct Sector ETF
  Rotation audit target. It calculates the product and independent Oracle from
  the already loaded formal panel after Phase 1a custody completes.
- The offline daily executor supplies that exact second target automatically.
  The command summary records one source-panel load and both audit/product
  fingerprints; verify-only mode formally rereads both completed audits.
- Both targets are preflighted before the expensive source load. The new path
  performs no second canonical scan, external request, `/data` write,
  publication, Snapshot activation, bundle, or deployment.
- The real 2026-08-28 combined run recorded one panel load, Phase 1a elapsed
  time 204.085 seconds, rotation calculation 0.012778 seconds, and rotation
  Oracle 0.008185 seconds. Formal reread found zero mismatches, all files
  owner-only `0400`, and no partial residue. The stable product fingerprint is
  `bce93211b6aec748d41db7a4c7f2e34226941e2a4f4ceee29b7a7d6adf51bbf7`;
  the exact source-bound audit fingerprint is
  `060932af8da939d30f0c59482ed525387fc007b1fdde78a0f272eb2e04dfbce7`.
- The complete backend suite passes 1,797 tests. The two warnings remain the
  pre-existing Python `crypt` and Starlette TestClient deprecations.
- The normal path is complete, but the Automation Plan does not yet model the
  second audit as a separately recoverable observed stage. An interruption in
  the narrow two-audit gap must stop at the future MI gate; automatic repair or
  skipping is not inferred.

## 2026-08-30 — Define the lazy Sector Rotation publication boundary

- Accepted ADR 0092: one market-wide Sector ETF Rotation product will extend
  Market Intelligence 1.3 rather than create another active publication or
  duplicate output by Universe.
- Snapshot 1.11 / Dashboard 2.8 will expose a dedicated
  `sector-etf-rotation.json` file that the browser fetches only when its
  workspace opens. Guest and credential Sessions remain identical.
- The UI contract retains separate 5/10/20-session facts, acceleration,
  leadership duration, descriptive quadrants, and explicit proxy warnings. It
  adds no total score, fund-flow claim, or provisional Theme membership.
- Normal daily Phase 1a emission of the formally bound audit is a prerequisite;
  this decision does not authorize publication Apply, Snapshot activation,
  bundle creation, or deployment.
- Added one strict downstream reader that returns the typed rotation product
  and Oracle only after complete file custody, fingerprints, lineage, and zero
  mismatch have been reread. Publication code will not parse loose audit JSON.

## 2026-08-30 — Add immutable Sector ETF Rotation audit custody

- Accepted ADR 0091 and added atomic tmp-only
  `sector-etf-rotation-audit/1.0`. It formally rereads Phase 1a, freezes source
  manifest hashes/fingerprints, the product and all 11 record fingerprints,
  and the independent Oracle result.
- The audit writer accepts the already loaded Phase 1a panel and explicitly
  performs no canonical rescan, external request, `/data` write, publication,
  or Snapshot integration. Completed canonical JSON files are owner-only
  `0400` and appear only after an atomic staging rename.
- The real 2026-08-28 audit passed formal independent reread with product
  fingerprint
  `bce93211b6aec748d41db7a4c7f2e34226941e2a4f4ceee29b7a7d6adf51bbf7`,
  audit fingerprint
  `df02d96806a7681380f4c79c609771c26009b8f0e988c62c3af6da7a01947bbb`,
  Oracle mismatch zero, four `0400` files, and zero partial residue.
- The run measured 200.729 seconds for the deliberately standalone formal
  panel load, 0.012 seconds for calculation, and 0.008 seconds for the Oracle.
  Daily integration must reuse Phase 1a in process; repeated loading is not an
  accepted implementation.
- The complete backend suite passes 1,796 tests. The two warnings remain the
  pre-existing Python `crypt` and Starlette TestClient deprecations.

## 2026-08-30 — Start score-free Sector ETF Rotation V1

- Accepted ADR 0090 and added a fixed 11-sector ETF proxy registry with SPY as
  the comparison benchmark. The contract exposes separate 5/10/20-session ETF,
  benchmark, and arithmetic relative returns and within-window ranks; it has no
  aggregate score.
- Added five-session relative acceleration, leadership-run duration, and the
  factual four-quadrant posture: leading/improving, leading/weakening,
  lagging/improving, or lagging/weakening. Missing data is not imputed and is
  excluded only from the affected rank.
- Added an independent raw-panel Oracle and shared the fixed registry with the
  existing one-session Dashboard sector ETF list. Forty-seven related Sector,
  Dashboard, ETF Relationship, and Market Regime tests pass; the complete
  backend suite passes 1,794 tests.
- A read-only real 2026-08-28 review returned all 11 records. Formal panel
  loading took 215.446 seconds and the rotation calculation took 0.012777
  seconds, so future integration must reuse Phase 1a rather than rescan
  canonical history.
- This development slice does not create an audit publication, Snapshot/API
  resource, new navigation item, or Production deployment. Themes remain
  unavailable without governed effective-dated membership.

## 2026-08-30 — Unify the authenticated and guest workspace identity

- Aligned all three first-level workspaces with the public WH Alpha entry:
  deep navy surfaces, cyan/green signal accents, a persistent WH mark,
  translucent utility navigation, and consistent cards, tables, drawers, and
  mobile navigation. The first viewport remains a dense decision workspace,
  not a marketing hero.
- Kept credential and guest Sessions on the same application shell with no
  role branches or capability difference. Analytics, ranking logic, data
  contracts, and fail-closed behavior are unchanged.
- All 103 frontend tests and the Production build passed. The existing large-
  chunk advisory remains an explicit later performance optimization.
- Published ordinary-fresh Snapshot 1.10 / Dashboard 2.7 as
  `2026-08-30T092455Z-1894b9c9b95e` through Plan 2.5 and exact `/data` Apply,
  then formally reread the source-bound 51-file OCI bundle with logical
  fingerprint
  `caf507a04fc3be7609a0880223f363c7da13d25a49d6295fed2b69c0e4146cd2`.
- OCI preflight, atomic deployment, temporary guest Session postflight,
  public entry/redirect checks, and independent remote inspection passed with
  identical guest/credential route policy and zero staging/failed residue.
  Remote state fingerprint:
  `794795e03fa939816ed3a9b6537747a8d306c1e3f67eecdc280e29b074432f5f`.
- The post-deployment Dell report recorded 608 files / 404,002,859 bytes,
  inventory fingerprint
  `be0846beeee56bbac1856056ab23b2c03c26c4972d479d7fcc44e2e2e64a3db6`,
  zero symlinks, and zero publication residue. Password-based and browser
  visual verification remain manual checks.

## 2026-08-30 — Redesign and deploy the public WH Alpha entry

- Replaced the compact authentication split-screen with a mature bilingual
  public brand entry using the selected dark WH mark, institutional navy/cyan
  visual language, and immediate credential or equal-capability guest access.
- Added a data-free product narrative around the complete decision chain. A
  central alternating signal path separates four live capabilities, four
  planned capabilities, and later position management; planned features are
  explicitly unavailable rather than implied to be live.
- Made explainability, counterevidence, market context, participation-versus-
  fund-flow terminology, and stock-versus-option-return boundaries visible on
  the public page. Added locale-completeness and live/planned status tests.
- Published ordinary-fresh Snapshot 1.10 / Dashboard 2.7 as
  `2026-08-30T085601Z-6c732e9cd602` through Plan 2.5 and exact `/data` Apply,
  then built and formally reread the source-bound 51-file bundle with logical
  fingerprint
  `04b4063c21fdc53a7ff7d1a88d8be33d1d2d8d13364031cd69279c94f4b8541e`.
- OCI preflight, atomic deployment, guest Session postflight, direct public
  content verification, and independent remote inspection passed with no
  staging/failed residue. The remote state fingerprint is
  `b21cf8883e971ee6ad55161c4380c975177faf2427c19bafc2d525bb9080e598`.
- All 102 frontend tests and the Production build pass. Password-based and
  visual browser verification remain a manual user check.

## 2026-08-30 — Publish WH Alpha favicon and Candidate Visual Context

- Adopted the user-selected dark-background WH mark as the default browser,
  bookmark, Apple touch, and search-result favicon. The mark is optically
  enlarged for small display while retaining the white WH, cyan rising line,
  and dark navy field.
- Added one shared PNG source to the login and Dashboard metadata, a public
  `/favicon.png` route, branded search description and theme color, exact
  bundle custody, square/minimum-size validation, identical root/Dashboard
  hashes, and live deployment checks for HTTP status, MIME type, and PNG
  signature.
- Published ordinary-fresh Snapshot 1.10 / Dashboard 2.7 as
  `2026-08-30T082200Z-6a8a37e79970`, including the previously reviewed
  Candidate Visual Context path and state-age detail. Plan 2.5 fingerprint is
  `bea5e854002ef956eaa14ee8a65e396cd0dcd42288c9ced3d08759d3b0c6dd7b`.
- Built and formally reread the 51-checksummed-file serving bundle with logical
  fingerprint
  `c32fa8b9f58291b1231b8e42dc5d1e5ee3ce45436845b23d4882488adfda3fc2`,
  then passed OCI preflight, atomic Apply, guest Session postflight, and an
  independent remote inspection with zero staging/failed residue.
- The public favicon SHA-256 is
  `9645feb8261c234e6efd644960f50ac1431191dba37b19026242c5bc299e0e00`.
  All 1,779 backend tests and 101 frontend tests pass; the Production-mode
  frontend build passes with the existing chunk-size advisory only.

## 2026-08-30 — Integrate Candidate visual context into lazy product delivery

- Accepted ADR 0089 and added detail-shard 1.1, Snapshot 1.10 / Dashboard 2.7,
  Approval Plan 2.5, strict web parsing, bilingual 20-session path/state-age
  rendering, and OCI bundle/postflight validation.
- The summary contract remains unchanged and opening one Candidate still makes
  one detail request. Every visual row binds the matching stable ID, Candidate
  score fingerprint, Entry Geometry fingerprint, and formal visual audit.
- A real Dell `/tmp` dry-run produced a formally readable 1.10/2.7 candidate
  and Plan 2.5 with zero Production writes. The 2,061,314-byte first-load
  summary had zero byte growth; 32 lazy shards increased by 3,724,116 bytes in
  total to a 671,118–1,432,204-byte range.
- All 1,778 backend tests and all 100 frontend tests pass; the Production-mode
  frontend build also passes. Nothing was published or deployed, and active
  Production remains 1.9/2.6.

## 2026-08-30 — Bind Candidate visual context to real Dell history

- Accepted ADR 0088 and implemented Candidate Visual Context 1.0 with exact
  20-session canonical close paths, Entry Geometry reference levels, and
  left-censor-aware observed Candidate-state age.
- Added an independent raw-source validator, input-permutation gate, formal
  owner-read-only `/tmp` audit, network-prohibited CLI, and a bounded formal
  Candidate state-history reader.
- The real 2026-08-28 Dell audit assessed 3,541 Candidate rows: all have complete
  paths; 3,382 have observed state age and 159 current unavailable/stale states
  remain explicitly unavailable. Both Oracles have zero mismatch.
- The optimized 38.81-second run made zero external requests and zero Production writes.
  No score, rank, state, strategy, `/data`, publication, Snapshot, bundle,
  deployment, OCI, or scheduler state changed. All 1,778 backend tests pass.

## 2026-08-30 — Add a truthful Candidate decision-position map

- Accepted ADR 0087 and added a bilingual position map to the lazy Candidate
  detail drawer using only already-published Entry Geometry facts.
- The map compares current close, SMA10/SMA20, prior five-session close
  high/low, and selected reference support on one price scale, followed by
  explicit breakout/support/SMA20 distances and state-confirmation progress.
- It explicitly distinguishes a reference-level map from price history,
  Candidate confirmation from signal age, reference support from a stop price,
  and underlying-stock position from return or option-performance prediction.
- Missing geometry fails closed. No score, rank, state, strategy, API contract,
  data, publication, deployment, or Production state changed. All 98 frontend
  tests and the Production-mode frontend build pass.

## 2026-08-30 — Prove one point-in-time Daily Universe Membership partition

- Accepted ADR 0086 and advanced the membership-only physical manifest to
  `1.1`, binding the exact stable-ID evaluated base, complete per-Universe
  included/excluded/quarantined totals, sorted source fingerprints, origin, and
  cutoff/evaluation clocks.
- Added a formal adapter from completed reviewed full-base decisions. It rejects
  omitted/extra IDs and future-dated evidence, maps missing critical inputs to
  quarantine, and never projects current Activation backward.
- A real Dell read-only 2026-08-19 pilot wrote only `/tmp` and formally reread
  9,130 decisions over 4,565 IDs: Primary 1,718 included / 2,775 excluded / 72
  quarantined; Secondary 1,831 / 2,645 / 89.
- No provider or credential was accessed; no `/data`, active artifact, website,
  scheduler, publication, bundle, deployment, or Production state changed.
- The reviewed source cutoff is 2026-08-21, after the 2026-08-19 session;
  therefore all otherwise valid rows carry an explicit later-known-source
  warning and the output is mechanics-only for chronological evaluation.
- All 1,771 backend tests pass with the two existing dependency warnings.

## 2026-08-30 — Diagnose unresolved cadence wakes without replay

- Accepted ADR 0085 and added pure Cadence Diagnosis 1.0 over an already-read,
  exact-session run-journal chain.
- It separates no nested action evidence, an unresolved action routed only to
  existing no-replay recovery, a matching formal terminal exposed only as a
  later disposition candidate, and unsupported/conflicting blocked evidence.
- The report fingerprints its evidence and declares zero request, write,
  replay, retry, recovery, automatic-resolution, publication, deployment, and
  scheduler authority. It never infers a coordinator result or retry time.
- No CLI, real journal read/event, capability, timer change, request, `/data`
  write, publication, deployment, or Production operation occurred. All 1,764
  backend tests pass with the two existing dependency warnings.

## 2026-08-30 — Reserve and compose one pipeline wake

- Accepted ADR 0084; advanced the owner-only run journal to 1.8 and cadence
  custody to 1.1 with a durable pre-invocation reservation and matching known
  terminal record.
- Added default-off Pipeline Runtime 1.0. Exact enabled Pipeline/cadence plans
  may invoke exactly one scope-matched supplied capability; there is no loop,
  retry, recovery, publication, deployment, or inferred success.
- Exceptions, invalid results, interruptions, and retention ambiguity leave an
  unresolved reservation that blocks replay and later sessions. Existing
  action custody runs between reservation and resolution without nested locks.
- Preserved readable journal 1.2–1.7 and direct 1.7 cadence evidence, including
  intermediate-version MI, Snapshot, OCI, and operator-review events.
- No CLI, real cadence event/root, capability, timer change, credential,
  request, `/data` write, publication, deployment, or Production invocation was
  added or performed. All 1,754 backend tests pass with the two existing
  dependency warnings.

## 2026-08-30 — Reuse run journal for cadence evidence

- Accepted ADR 0083; extended the existing owner-only run journal to 1.7 with
  a standalone cadence evidence event while preserving 1.2–1.6 readability.
- Evidence 1.2 now binds the immutable cadence start, formal next-eligible time,
  and exact enabled cadence and Pipeline plans; the journal retains and rereads
  the complete cadence plan rather than only an opaque hash.
- Added exact coordinator/offline result adapters and fail-closed persistence
  for sequence, duplication, interval, four-hour, 16-wake, terminal-failure,
  unknown-outcome, and unresolved-action boundaries.
- Advanced coordinator to 1.12: provider waiting remains waiting, and known
  provider/offline failure is blocked rather than reported as executed.
- No second store, real journal event/root, runtime bridge, timer change,
  request, `/data` write, publication, deployment, or Production change was
  made. All 1,746 backend tests pass with the two existing dependency warnings.

## 2026-08-30 — Bound distinct pipeline wake cadence

- Accepted ADR 0082 and added a pure, non-installed bounded-cadence contract
  above Pipeline Scheduler V2.
- The widest candidate permits 16 distinct transition wakes over four hours
  with a five-minute completion-to-next-start floor; callers may only narrow
  those limits.
- Added immutable prior-wake evidence, exact budget reporting, two-layer
  candidate enablement, and terminal handling for known failure, unknown
  outcome, manual review, blocked state, and exhausted budgets.
- Strengthened Pipeline Scheduler V2 verification to reject re-fingerprinted
  semantic and authority conflicts.
- No evidence store, runtime bridge, scheduler installation/change,
  coordinator/offline invocation, credential, request, `/data` write,
  publication, deployment, or Production change was made. All 1,731 backend
  tests pass with the two existing dependency warnings.

## 2026-08-30 — Add pipeline-aware wake and persistent workspace contracts

- Accepted ADR 0081 and added a repository-only Pipeline Scheduler V2 plan
  that combines the canonical-session wake with an exact same-session
  Automation Plan 1.4.
- Current canonical EOD with a missing offline stage now proposes one bounded
  offline transition instead of incorrectly waiting for the next session.
  MI, Snapshot, deployment, blocked, and inconsistent states still stop for
  review or diagnosis.
- Added a deterministic Dell-local per-session workspace layout outside Git,
  canonical `/data`, and `/tmp`. It derives paths only and preserves the old
  direct-`/tmp` validation boundary for prior controlled runs.
- No directory, timer, coordinator capability, credential, request, `/data`
  write, publication, deployment, or Production state was created or changed.
  All 1,718 backend tests pass with the two existing dependency warnings.

## 2026-08-29 — Separate scheduler operation from installed host state

- Accepted ADR 0080 and replaced the misleading planner-level
  `scheduler_installed=false` with
  `scheduler_installation_performed=false`. The latter proves only that the
  current invocation performed no installation; it does not claim the Dell
  timer is absent.
- Advanced the planner, scheduled-wake, rehearsal, and systemd-review
  contracts to 1.1, removed the redundant host-state-like review field, and
  added regressions that reject its return.
- The five-scenario rehearsal now has fingerprint
  `51133b39e01eeb5aacdc0686eb00b612180a7a4ba45a448802de99b859759412`
  with the same four fake calls, one-call maximum, and zero credential,
  network, filesystem-write, or Production-write activity.
- No coordinator, provider, `/data`, publication, deployment, or Production
  capability changed. Installed/enabled timer state remains separately
  verified through read-only host inspection.

## 2026-08-29 — Install the read-only user scheduler

- Accepted ADR 0079 after the user explicitly selected user-systemd persistence.
  Enabled `hui` linger and installed the owner-only read-only service/timer;
  no coordinator or data-transition capability was connected.
- The first controlled start failed before project execution with systemd
  `218/CAPABILITIES`. Kept the timer stopped while removing unsupported
  `PrivateNetwork`, capability-changing `PrivateDevices`, and explicit empty
  capability bounding from the candidate and installed unit.
- The compatible unit retained exact revision/Python custody, read-only
  system/home, `NoNewPrivileges`, `AF_UNIX`, the planner socket guard, and the
  timeout. A controlled start then passed in about three seconds with EOD
  current through 2026-08-28 and zero coordinator, credential, external
  request, filesystem-write, or Production-write activity. The timer is enabled
  only for future read-only calendar wakes.

## 2026-08-29 — Render a non-installed read-only systemd wake

- Accepted ADR 0078 and added an exact Dell/hui user-systemd candidate whose
  oneshot service can execute only the credential-free ADR 0076 planner.
- Pinned clean `main`, exact Git revision, canonical data root, planner
  entrypoint, unit names/content hashes, and New York 13:30/16:30 weekday
  calendars. The planner CLI now supports the actual UTC system clock and an
  exact Dell runtime-verification mode. The service clears inherited Python
  overrides and pins/rechecks the project launcher and resolved interpreter.
- Default and explicitly enabled candidate review perform no installation,
  activation, coordinator call, credential access, networking, filesystem or
  Production write, publication, or deployment. Dell systemd 255 and the user
  manager are available, but `hui` linger remains disabled and was not changed.
  All 1,701 backend tests and 44 focused scheduler/systemd tests pass, including
  parsing both rendered units with Dell's systemd 255 parser.

## 2026-08-29 — Compose one default-off scheduled wake

- Accepted ADR 0077 and added an exact-plan bridge that can call one supplied
  coordinator callable only when both the wake candidate and invocation are
  explicitly enabled.
- Recomputed the complete wake-plan fingerprint before the call and the formal
  coordinator-result fingerprint afterward, retained the accepted result
  identity, and rejected content or target drift plus scheduler/publication/
  deployment authority drift.
- Added five separate credential-free synthetic wakes for current,
  oldest-missing, retry-wait, unresolved-interruption, and alert-required
  states. No scenario retried, routed recovery, delivered an alert, or invoked
  the coordinator more than once.
- The rehearsal made zero real credential accesses, network requests,
  filesystem writes, and Production writes. No systemd unit or timer was
  created, installed, or enabled. All 1,690 backend tests and 63 focused
  coordinator/scheduler tests pass.

## 2026-08-29 — Add a default-off daily scheduler-wake plan

- Accepted ADR 0076 and added a credential-free plan that selects the oldest
  missing XNYS session and the next close-plus-stabilization review time.
- Added a lightweight canonical EOD completion index and retained a full
  formal Parquet/Identity reread for the latest session, avoiding full-history
  Parquet reconstruction on frequent scheduler reviews.
- Current Dell review fell from more than 30 seconds with the first full-list
  prototype to about 2.8 seconds and returned current through 2026-08-28, next
  target 2026-08-31, and next check 20:30 UTC.
- Default and explicitly enabled-candidate reviews both made zero coordinator
  calls, credential reads, network requests, filesystem writes, and Production
  writes. No service or timer was installed or enabled. All 1,671 backend tests
  and the 28 focused persistence/scheduler tests pass.

## 2026-08-29 — Deploy ETF relationship change evidence and timeline

- Corrected prior-Snapshot backend compatibility after the first write-free
  candidate preflight stopped before Plan creation; the failed `/tmp` candidate
  was removed and no Production state had changed.
- Activated fresh Snapshot 1.9 / Dashboard 2.6
  `2026-08-29T133847Z-1490b37f25b3` from unchanged 2026-08-28 Market
  Intelligence, then built and deployed the matching 50-file OCI release.
- Independent postflight matched local/remote manifest and checksum hashes,
  proved Nginx/Auth health, localhost-only Auth, protected routes, temporary
  guest access, role-free guest/credential parity, and zero residue.
- Fixed the read-only inspector for the remote Python version by using
  `datetime.timezone.utc`; no redeployment was needed. Password login and human
  visual acceptance remain manual. See the
  [deployment audit](../audits/etf-relationship-explanation-deployment-2026-08-29.md).

## 2026-08-29 — Add a bounded ETF relationship state timeline

- Accepted ADR 0075 and projected the latest ten frozen Phase 2 state records
  per pair into an additive API/Snapshot presentation contract.
- Added a bilingual horizontal relationship path with session, state-change
  marker, and selected-window relative return. Retained count/start and older-
  point compaction are explicit.
- Verified 1,656 backend tests and 96 frontend tests, plus the frontend
  production build. The dependency deprecation and bundle-size warnings are
  unchanged.
- The formal read-only active-publication reader also projected all 16 pairs
  from the 2026-08-28 Market Intelligence payload: each exposed 10 of 21
  retained sessions and reconciled its final session/state to current.
- No state recomputation, formula, threshold, score, rank, Market Intelligence
  payload, `/data`, network, deployment, or scheduler state changed.
- A write-free publication preflight exposed and corrected a backend reader
  compatibility defect: prior Snapshots may omit both additive relationship
  projections, while newly rendered responses still contain them. The failed
  preflight stopped after `/tmp` candidate generation and made no Production
  or `/data` write and no OCI request. The corrected contract passed the full
  backend suite and a formal reread of the active pre-projection Snapshot.

## 2026-08-29 — Add descriptive ETF relationship persistence and acceleration

- Accepted ADR 0074 and added a compact API/Snapshot change summary derived
  from the existing formally bound Phase 2 history.
- Added current-state run start/count with explicit history-boundary handling,
  plus exact one-/five-session changes for rolling 5/10/20 relative returns and
  threshold-free strengthening/weakening/reversal descriptions.
- Added strict frontend validation and bilingual presentation in relationship
  highlights and detail. Old Snapshots without the additive field retain the
  prior-state fallback.
- Verified 1,654 backend tests and 95 frontend tests, plus the frontend
  production build. The two backend warnings are pre-existing dependency
  deprecations.
- No relationship formula, state, threshold, score, rank, highlight order,
  Market Intelligence source payload, `/data`, network, deployment, or
  scheduler state changed.

## 2026-08-29 — Reconcile current deployment and retention documentation

- Re-ran the credential-free full-source context reader on clean Dell `main`.
  It reconfirmed aligned 2026-08-28 Identity/EOD, 31 canonical sessions, the
  active fresh MI/Snapshot lineage, 444 `/data` files, and zero symlink or
  publication residue without networking or writes.
- Corrected README, current-status, infrastructure, OCI runbook, retention, and
  roadmap text that still described older 2026-08-26/28 releases or the
  29-session audit as current. The roadmap now stops before a next-session
  controlled deployment and keeps scheduler activation subsequent to its
  operational review.
- Verified all eight retained local OCI bundles against their checksum
  inventories. Their combined size is below 110 MiB, so no reviewed rollback
  evidence was deleted merely for cosmetic cleanup. Remote inventory was not
  inferred from local names and OCI was not accessed.
- No source behavior, `/data`, Snapshot, bundle, deployment, external config,
  credential, network, scheduler, or Production state changed.

## 2026-08-29 — Rehearse composed OCI custody and review runtime candidate

- Added a true coordinator-to-capability-to-custody-to-journal integration
  rehearsal using temporary local custody, exact structured pre/post states,
  and a fake transport. It proves inspect/reserve/Apply/inspect ordering and the
  exact `oci_deployment_started` / `oci_deployment_succeeded` hash-chain events.
- Added a network- and write-prohibited runtime-candidate review service and
  CLI. It discovers the clean Dell `main` revision, validates the two reviewed
  scripts, emits the exact future config-file SHA, and defaults the candidate to
  `capability_enabled=false`.
- `--review-enabled-candidate` changes only the in-memory review candidate. The
  report still records zero installation, credentials, external requests,
  filesystem or Production writes, deployment/rollback authority, and
  scheduler enablement.
- No external config was installed and no OCI/public-site connection, upload,
  switch, reload, rollback, credential access, `/data` write, Production
  mutation, or scheduler action ran.
- All 1,653 backend tests pass with only the two existing deprecation warnings;
  no frontend source changed.

## 2026-08-29 — Custody one exact OCI Dashboard deployment

- Accepted ADR 0073 and added a default-off one-shot OCI deployment capability
  after exact Serving Bundle review.
- Added a canonical non-secret remote-state inspection contract covering the
  current/target release identities, remote manifest and checksum hashes,
  service/listener health, protected routes, temporary role-free guest access,
  and staging/failed-release residue. Password login is explicitly not tested.
- Added an owner-only external deployment runtime contract pinned to clean Dell
  `hui`, `main`, the exact source revision, run root, `whalpha-oci`, and the two
  reviewed scripts. Absence or `capability_enabled=false` keeps deployment
  unavailable.
- Extended the deployer with exact direct-child `/tmp` bundle-path and expected-
  current-release guards. It now rejects any preexisting staging/failed residue
  and never silently removes an ambiguous target stage before mutation.
- Corrected the Serving Bundle reader's source-revision validator to accept the
  repository's real 40-character Git SHA-1 (and Git SHA-256) instead of
  incorrectly requiring a 64-character content fingerprint; the fixture now
  uses the real revision shape.
- Advanced coordinator/recovery/journal contracts to 1.11/1.3/1.6. The journal
  reserves before remote mutation; success requires an independent post-state
  proof. Recovery performs one read-only inspection, never replays Apply, and
  separates exact success, unchanged/not completed, and partial/ambiguous
  blocked state.
- No OCI/public-site connection, upload, switch, reload, rollback, credential
  access, `/data` write, Production mutation, external config installation, or
  scheduler action ran.
- All 1,647 backend tests pass; the only warnings are the existing Python
  `crypt` and Starlette/httpx deprecations. No frontend source changed.

## 2026-08-29 — Custody exact active-Snapshot serving-bundle construction

- Accepted ADR 0072 and added `build_serving_bundle` as the tenth offline daily
  action only after the exact planned Dashboard Snapshot pointer is active.
- Added Serving Bundle 1.0 formal validation for clean source/release identity,
  exact Snapshot aggregate and manifest hashes, full checksum inventory,
  analytics lineage, bilingual policy, equal guest/credential capability, and
  prohibited-content flags.
- Made build time and a new direct-child `/tmp` bundle root explicit custody
  inputs; added partial/staging, changed-source, symlink, unchecksummed-file,
  postcondition, and no-implicit-deployment gates.
- Removed the obsolete `--snapshot-release` builder shortcut. The builder now
  accepts only an exact immutable V2 Snapshot path, cleans bounded staging on
  ordinary failure, and runs the frontend build with a minimal offline
  environment.
- Planner/executor/coordinator/recovery contracts advance to
  1.4/1.4/1.10/1.2, preserve the exact bundle build time through recovery, and
  stop at `review_bundle_deployment`. No OCI capability or scheduler was added.
- No real candidate bundle, `/data` write, network request, deployment,
  rollback, or scheduler operation ran.
- All 1,633 backend tests and all 94 frontend tests pass; the snapshot-mode
  production build passes with the existing greater-than-500-KB chunk warning.

## 2026-08-29 — Add default-off one-shot Dashboard Snapshot Apply custody

- Accepted ADR 0071 and extended the daily run journal to backward-readable
  1.5 with a separate Dashboard Snapshot Apply start/terminal family; prior MI
  Apply events under journal 1.4 remain readable.
- Added exact reservation gates for the unchanged Snapshot-review plan, strict
  Plan 2.4 whole-file SHA, current Snapshot and Activation state, freshness or
  exact review acknowledgement hash, and absent target/staging state.
- Added an explicit, mutually exclusive coordinator/CLI capability that invokes
  the existing atomic Snapshot publisher and records success only after the
  exact active release and planned pointer formally reread.
- Added inspection-only interruption recovery. It never applies or links;
  exact active state reconciles, provably untouched state closes safely, and
  inactive/partial/changed/ambiguous state blocks.
- Preserved `snapshot_generated_at` when routing recovery for an interrupted
  offline Snapshot Plan action.
- The capability remains uninstalled and uninvoked. No real Snapshot plan,
  `/data` write, publication, bundle, deployment, or scheduler change ran.
- All 1,622 backend tests pass; the only output is two existing dependency
  deprecation warnings.

## 2026-08-29 — Add custody-tracked daily Snapshot Plan preparation

- Accepted ADR 0070 and added `prepare_dashboard_snapshot_plan` as the ninth
  one-transition offline action after exact MI activation.
- The planner now distinguishes an MI plan ready for Apply from that exact
  planned publication being active. Only the latter can advance to Snapshot
  planning; older/absent active MI stays at publication review and mismatched
  active state blocks.
- Reused the existing offline Snapshot V2 administrator with exact UTC time,
  target session, active MI publication, same-session Strategy Channel audit,
  and new `/tmp` output/Approval Plan paths.
- Added a public strict reader for canonical, owner-controlled, read-only
  Snapshot plans and required Plan 2.4 plus exact MI/strategy lineage before
  stopping at `review_snapshot_publication`.
- No real Snapshot, `/data` write, Apply, bundle, deployment, or scheduler
  operation ran.
- All 1,610 backend tests pass; the only output is two existing dependency
  deprecation warnings.

## 2026-08-29 — Add default-off one-shot MI Apply custody

- Accepted ADR 0069 and extended the daily run journal to backward-readable
  1.4 with a separate Market Intelligence Apply start/terminal family.
- Added exact reservation gates for the unchanged publication-review plan,
  whole-file MI plan SHA, current inventory and consumer state, current
  freshness or exact stale-review acknowledgement hash, and absent target/
  staging state.
- Added an explicit, mutually exclusive coordinator/CLI capability that uses
  the existing offline publication administrator and records success only
  after the exact active pointer and publication formally reread.
- Added inspection-only interruption recovery. It never applies or links;
  exact active state reconciles, provably untouched state permits a later
  separately authorized retry, and partial/changed/ambiguous state blocks.
- The capability remains uninstalled and uninvoked. No real plan, `/data`
  write, publication, Snapshot, bundle, deployment, or scheduler change ran.
- All 1,603 backend tests pass; the only output is two existing dependency
  deprecation warnings.

## 2026-08-29 — Add custody-tracked daily MI Plan preparation

- Accepted ADR 0068 and added `prepare_market_intelligence_plan` as the eighth
  one-transition daily action after all seven analytics artifacts.
- Reused the existing offline MI `--plan` administrator. The action binds an
  explicit UTC creation time, expected `/data` inventory fingerprint, exact
  source paths, and a new `/tmp` output root/approval-plan pair; it performs
  zero external requests and zero Production writes.
- The planner formally rereads MI plan 1.2 and its immutable candidate, checks
  the exact session, paths, Phase 1a/1b/2, preview, Candidate, and Entry
  Geometry fingerprints, and distinguishes freshness-ready from freshness-
  blocked review evidence.
- Partial output, invalid custody, source/path drift, or missing execution
  bindings fail closed. Completion stops at `review_publication`; MI Apply,
  Snapshot, bundle, deployment, rollback, and scheduler remain unauthorized.

## 2026-08-29 — Extend daily custody through all offline publication inputs

- Accepted ADR 0067 and extended the fixed daily offline order from four to
  seven stages: ETF Relationships, Market Preview, and Strategy Channels now
  follow Entry Geometry before publication review.
- Added exact-session and source-fingerprint lineage gates for all three new
  stages. Missing artifacts select one exact offline action; invalid, stale,
  mismatched, or out-of-order artifacts fail closed.
- Reused the existing offline administrators under the same Dell global lock,
  immutable run journal, unchanged-plan check, one-action postcondition, and
  no-replay recovery model.
- At this historical boundary, `analytics_ready` required all seven offline
  analytics artifacts. Publication, Snapshot, bundle, OCI deployment, `/data`
  writes, credentials, and scheduler activation remained outside that change
  and unauthorized.

## 2026-08-29 — Complete and deploy the 2026-08-28 daily round

- Completed and formally aligned canonical Identity and EOD through 2026-08-28:
  9,981 instruments, 13,151 provider identity rows, 9,981 resolvers, and 9,942
  canonical EOD rows.
- Completed same-session Phase 1a/1b, Candidate, Entry Geometry, all 16 ETF
  relationships, Market preview, and Strategy Channels. Every declared Oracle
  returned zero mismatch; offline analytics made zero external requests and
  zero Production writes.
- Published fresh, lag-zero Market Intelligence
  `2026-08-29T080431Z-785ab49dfedd` and Snapshot 1.9 / Dashboard 2.6
  `2026-08-29T080928Z-785ab49dfedd`, with 686 / 744 bounded Candidate records,
  32 detail shards, and the lazy strategy-channel product.
- Built and deployed the 50-file OCI release
  `2026-08-29T080928Z-785ab49dfedd` from source commit `785ab49dfed`. Remote
  preflight, Nginx validation, atomic switch, protected routes, and the
  equal-capability temporary guest Session postflight passed. Human browser
  visual acceptance remains pending.
- The final credential-free reader reports 444 files / 267,872,129 bytes,
  inventory fingerprint
  `15de69875692824412df3da29afc9dad12e470c326cec2936633dee5dcae1ea3`,
  zero symlinks, and zero publication residue. No scheduler or standing access
  was enabled. See the
  [complete audit](../audits/daily-eod-complete-deployment-2026-08-29.md).

## 2026-08-29 — Review 2026-08-28 acquisition readiness

- The exact-session planner selected only `prepare_identity_catchup` for the
  oldest missing XNYS session, 2026-08-28. Its fingerprint is
  `3bf65e5b57284b48df6fb6cfd26b983f035cdfd5505cb380877ad57cf94821c2`.
- At `2026-08-29T06:12:50+00:00`, the network-free readiness plan returned
  `missed_session_recovery` / `review_fetch_authorization`, with zero attempts,
  requests, writes, or provider-completeness assertion. Its fingerprint is
  `4e26699abd653a611e3f2e1f4e117b099789dd6da92fd538da992ea6a7959e69`.
- Full local readers reconfirmed aligned 2026-08-27 Identity/EOD, the unchanged
  392-file `/data` inventory, and unchanged active MI/Snapshot. Every proposed
  8/28 target and journal directory is absent; no matching timer, service, or
  residual calculation process exists.
- No current-revision external control was supplied or preflighted. The next
  possible authorization is exactly one 2026-08-28 Identity fetch followed by
  a separate canonical Apply review; EOD and downstream work remain outside
  that boundary.

## 2026-08-29 — Review 2026-08-27 publication and fail closed on freshness

- Completed and formally reread the missing 2026-08-27 Phase 2 and preview.
  Phase 2 fingerprint is
  `1d0efadf75579c2487696fe5933bccfcdc56e40680433a790a9600b3776ec41f`,
  with zero Oracle mismatch and all replay/permutation/prefix gates; preview
  payload fingerprint is
  `da5b9364ab4e84955c82d3c8666b125e293108dd0093c692830bfef2ccf3d52c`.
- The first two MI Plan attempts found duplicated cold-only Candidate evidence
  field access and failed before approval-plan creation or Production write.
  ADR 0066 now shares one explicit verified-prior/current-Oracle projection
  between Candidate construction and MI approval recheck. Commits `54b1d09`
  and `211c1a5` pass all 1,573 backend tests.
- The final MI 1.2 review plan SHA-256 is
  `a5732db20555cc0e873fb184302e401e825fab9f65d81e7e6d6bbdecd472e2ea`.
  It passes full source validation and contains 558 / 599 Candidate records at
  fingerprint
  `d81479e4e332865f5d4c6312033a66095febe3b018a8e54376668d3e8f36ac47`.
- Activation is correctly blocked: actual 2026-08-27, expected 2026-08-28,
  lag one, and no applicable exact review authorization. No MI Apply,
  Snapshot, bundle, deployment, acquisition, notification, or scheduler action
  ran. Active serving remains the 2026-08-26 stale-review release and `/data`
  remains unchanged.
- The review exposed an end-to-end automation gap: the four-action daily
  coordinator stops at Entry Geometry and does not include Phase 2, preview,
  Strategy Channels, publication, or Snapshot.

## 2026-08-29 — Complete 2026-08-27 daily Entry Geometry

- Executed exactly one Dell-local `calculate_entry_geometry` transition from
  the completed same-session Candidate audit, with zero external requests and
  zero Production writes.
- Audit fingerprint
  `3aa78cb694a4c06835f19fb6165cd721e62b7fe16f921240ce8a601fcd83c11a`
  assesses all 1,714 Primary / 1,827 Secondary current comparable rows, passes
  both independent Oracles with zero mismatch, and preserves input-permutation
  equivalence.
- Primary/Secondary technical-review-ready counts are 70 / 73; monitor-for-
  trigger 1,303 / 1,393; wait-for-reset 104 / 110; and deprioritized 237 / 251.
  Entry Geometry remains a shadow entry-location/chase-risk axis and does not
  alter Candidate score/rank or claim option returns.
- Journal event 21 is successful. The post-plan is `analytics_ready` with sole
  next boundary `review_publication`; no publication, Snapshot, bundle,
  deployment, notification, or scheduler action followed.
- The action took 338.217438 seconds and reached an observed 4,418,900 KiB
  high-water RSS. Current-session extraction from the cumulative Candidate
  score artifact is the next bounded performance opportunity. `/data` remains
  unchanged and all 98 focused tests pass.

## 2026-08-29 — Bound daily planning to Candidate completion evidence

- Accepted ADR 0065 and replaced planner/postcondition full Candidate history
  reconstruction with exact immutable artifact hashing plus canonical parsing
  of the small incremental lineage ledger.
- Candidate calculation retains the full typed prior append-input reader;
  current output still requires daily tier, zero current-session Oracle
  mismatch, all-true reuse/equivalence gates, parameters, hashes, and exact
  prior/current lineage.
- The real 422,786,554-byte current audit now plans in 9.45 seconds at 221,640
  KiB maximum RSS while preserving plan fingerprint
  `eb19d7790605fae6d2467f6996b9411fb5fc6653f28f27b6e60c9fdd6b41811f`
  and sole next action `calculate_entry_geometry`.
- The initial legacy-tier compatibility mismatch failed closed with no state
  change. Historical `None`/`daily` reads now match the existing full-reader
  contract while current daily advancement still requires explicit `daily`.
  All 157 related and all 1,571 backend tests pass; no analytics, `/data`,
  publication, deployment, or scheduler state changed.

## 2026-08-29 — Complete 2026-08-27 daily Candidate append

- Executed exactly one Dell-local `calculate_candidate_daily` transition from
  the corrected Phase 1b and verified-prior Candidate lineage, with a panel-
  cache hit, zero external requests, and zero Production writes.
- Audit fingerprint
  `0fa85ae742ef47e7278c444c12f05f2082e38a5071068a5787655a11271eb4e4`
  passes the current-session independent Oracle and every daily incremental
  prefix/restart/permutation gate. Current batches contain 1,714 Primary and
  1,827 Secondary comparable securities.
- The cumulative audit is 422,786,554 bytes. Business work before write took
  152.944168 seconds and streaming write took 22.201208 seconds, but repeated
  full formal rereads expanded the journaled action to 576.027031 seconds and
  about 6.1 GB observed post-plan RSS.
- Publication-level immutable custody reread the same completed audit in 1.8
  seconds. The next engineering priority is eliminating redundant planner and
  postcondition historical reconstruction without weakening full append-input,
  typed-current, Oracle, lock, hash, or fail-closed gates.
- The journal ends in `action_succeeded`, the planner advances only to
  `calculate_entry_geometry`, `/data` remains unchanged, and all 135 related
  tests pass.

## 2026-08-28 — Complete 2026-08-27 incremental Phase 1b

- Formally rejected the legacy Production-bound V1.0.0 prior audit as an
  ineligible prefix; the failed attempt created no target and left no
  unresolved event.
- Replanned against the corrected V1.0.1 2026-08-26 incremental audit and
  completed exactly one Dell-local `calculate_phase1b_incremental` action with
  zero external requests and zero Production writes.
- The new audit fingerprint is
  `6a3a530280dbe9eea6617d76e980ed453b47e087d9e35fe588e8f7b6fe630801`.
  Primary/Secondary remain confirmed Balanced at composites 67.4134 / 67.5471,
  with zero independent-Oracle mismatch and all prefix/restart/source gates.
- `/data` remains exactly 392 files / 203,931,663 bytes at fingerprint
  `ddbe1ab03d5b945e9c3e2be975218c830f10e1ca615571e9616e131c847c7749`.
  The planner now selects only `calculate_candidate_daily`; the focused suite
  passes all 92 tests.

## 2026-08-28 — Complete 2026-08-27 daily Phase 1a

- Executed exactly one socket-guarded Dell-local `calculate_phase1a` action
  through the daily coordinator. It made zero external requests and zero
  Production writes and closed its journal event normally.
- The 26-session audit has zero missing metrics, 100% configured weight, and
  zero independent-Oracle mismatch. Primary/Secondary composites are 67.4134 /
  67.5471; Phase 1b state classification remains pending.
- Wrote and formally reread the content-addressed 257,202-bar panel cache for
  reuse by later stages. Phase 1a took 218.315399 seconds and peaked at
  1,838,572 KiB.
- The planner now selects only `calculate_phase1b_incremental`. `/data`, active
  analytics, Snapshot, Dashboard, OCI, notification, and scheduler state remain
  unchanged. The related suite passes all 114 tests.

## 2026-08-28 — Complete authorized 2026-08-27 canonical EOD Apply

- Exercised the user's exact `AUTHORIZE_2026_08_27_EOD_CANONICAL_APPLY`
  boundary after the reviewed-retry custody correction. Fresh controls allowed
  only `apply_eod` at revision `6256bf3`.
- One canonical transition completed with zero external requests. The exact
  9,945-row Parquet and manifest match the reviewed plan hashes, and the journal
  ends in `canonical_apply_succeeded` with no unresolved event.
- Latest EOD and Identity are now both 2026-08-27 and aligned. `/data` contains
  392 files / 203,931,663 bytes at fingerprint
  `ddbe1ab03d5b945e9c3e2be975218c830f10e1ca615571e9616e131c847c7749`,
  with zero symlink/staging/partial residue.
- The planner now selects only offline `calculate_phase1a`. No analytics,
  publication, Snapshot, bundle, deployment, notification, or scheduler action
  followed. All 1,569 backend tests pass; only two existing dependency
  deprecation warnings remain.

## 2026-08-28 — Reconcile reviewed fetch retries in Apply custody

- Fixed canonical Apply reservation to project immutable acquisition operator
  reviews from the same journal evidence already used by the coordinator and
  acquisition custody.
- This closes the fail-closed integration gap where a reviewed terminal
  failure followed by a successful retry was Apply-reviewable to the
  coordinator but rejected by the second custody check.
- Added a regression covering permanent failure, exact terminal review,
  bounded successful retry, and canonical Apply reservation. The focused
  readiness/coordinator/capability/custody suite passes all 59 tests.
- The rejected real invocation created no Apply reservation, canonical target,
  provider request, or Production write. Apply remains separately bound to the
  user's exact authorization and a fresh exact-revision runtime control.

## 2026-08-28 — Complete the 2026-08-27 EOD offline Apply Plan

- Built and formally reread the offline plan from the frozen one-request
  package and exact same-day Identity. No network request or `/data` write
  occurred.
- The plan converts 12,552 raw results into 9,945 canonical rows with zero
  duplicate business keys and zero orphan references. It proposes two files
  totaling 1,056,432 bytes under the absent 2026-08-27 EOD partition.
- Independent Parquet inspection confirmed 9,945 unique business keys, zero
  null instrument IDs, and only session 2026-08-27. Manifest and plan content
  fingerprints agree.
- Canonical Apply, analytics, publication, Snapshot, bundle, deployment,
  notification, and scheduler actions remain separately unauthorized.

## 2026-08-28 — Complete one authorized 2026-08-27 EOD fetch retry

- After the immutable terminal review boundary, exercised the user's separate
  `AUTHORIZE_ONE_2026_08_27_EOD_FETCH_ONLY` approval at exact revision
  `dd314db3074934f5ee20a4f03f3c46c5187ebacc`.
- Installed short-lived owner-only controls limited to `fetch_eod`; one Massive
  request returned a formally readable 12,552-result grouped-daily package.
- The session journal ends in `acquisition_package_ready` with no unresolved
  start. Formal readiness is now `ready_for_apply_review`.
- `/data` remains unchanged at 390 files, 202,875,231 bytes, and inventory
  fingerprint `7d66bc02fe88410a4ed6f000f74875aa135e11d10318ff010a148d03ba08a0de`.
  No Apply plan, canonical EOD write, analytics, publication, deployment,
  notification, additional provider request, or scheduler action occurred.

## 2026-08-28 — Deploy explicit Momentum Breakout stages

- Built and deployed the 50-file OCI release
  `2026-08-28T162136Z-2737f81` from source commit
  `2737f8171c3c47247568fc8de818b005a2355697`, reusing the existing audited
  Snapshot 1.9 / Dashboard 2.6 stale-review payload without any `/data`,
  publication, Snapshot, EOD, Identity, or Activation write.
- The live Momentum Breakout list now distinguishes confirmed, near-trigger,
  and extended/reset-first stages; exact formula and contribution explanations
  from ADR 0061 are also included.
- Remote dry-run, atomic Apply, temporary equal-capability guest Session
  postflight, checksums, Nginx/Auth health, unauthenticated protection, logout,
  and post-logout protection passed. Public `/` returns 200, unauthenticated
  Dashboard redirects, private data returns 401, and no staging residue exists.
- Password-based login and human visual acceptance remain manual checks. No
  credential content was read or printed.

## 2026-08-28 — Separate breakout stage and add breakout-anatomy facts

- Accepted ADR 0064. The Momentum Breakout UI now distinguishes a confirmed
  trigger, a near trigger, and an overextended leader waiting for reset; the
  combined Advance + Watch pool is explicitly not presented as a list of
  completed breakouts.
- Advanced the descriptive fact layer to Continuation Facts 1.1 with six
  t-1-normalized breakout-anatomy facts covering preceding range, ATR
  contraction, broader-high position, current move, and single-session path
  concentration. Strategy score, status, and rank remain unchanged.
- The formal 2026-08-26 offline audit assessed 3,543 rows with zero unavailable
  facts, zero independent-Oracle mismatch, exact input-permutation equivalence,
  and audit fingerprint
  `6e4b996cd7b75d49bf5f60fda94dfb6942da33d049c9b8589eb5f5fe455247a8`.
- Primary contains 10 Advance and 232 Watch breakout records; 98 Watch records
  are high/extreme-extension reset cases. This descriptive cross-section did
  not select new gates or make an outcome claim.

## 2026-08-28 — Formalize and profile the continuation-fact audit

- Accepted ADR 0063 and added an immutable tmp-only Continuation Facts audit,
  formal reader, and offline CLI. Candidate, Entry Geometry, panel-cache,
  parameter, fact-batch, and independent-Oracle identities are bound before an
  atomic completion marker is delivered.
- Added a bounded current Candidate projection that rehashes completed custody
  and validates only the exact current typed batches and panel lineage instead
  of reconstructing unrelated historical Candidate objects.
- The optimized real 2026-08-26 audit completed in 24.15 seconds versus 33.59
  seconds before removal of duplicate 196 MB canonical re-encoding. Candidate
  projection fell from 16.48 to 7.16 seconds; facts plus independent Oracle
  took 6.65 seconds and audit write/formal reread took 0.52 seconds.
- The real audit assessed 3,543 rows with zero unavailable facts, zero Oracle
  mismatch, exact permutation equivalence, and logical fingerprint
  `3e1226c676f19d95876c8bda96a4739ec551d4be83cfe83cbc1854cf5fafe976`.
  No Candidate main-audit schema change is justified by the remaining profile.
- No `/data`, Strategy Preview, publication, Snapshot, Dashboard, deployment,
  provider, credential, scheduler, or Production change occurred. All 1,567
  backend tests pass.

## 2026-08-28 — Add a descriptive continuation fact layer

- Accepted ADR 0062 and added a frozen source-bound contract for twelve
  separate continuation facts covering path continuity, trend persistence,
  recent/preceding price structure, volatility, position, and volume context.
  The facts carry no combined score, status, rank, threshold, or outcome claim.
- Added a pure Dell-local calculator plus an independent raw-panel Oracle that
  does not import the Production calculator. Missing or invalid history fails
  closed, every value uses fixed Decimal arithmetic, and input permutation is
  tested explicitly.
- A real offline 2026-08-26 review assessed all 1,715 Primary and 1,828
  Secondary Candidate rows with zero unavailable facts, zero Oracle mismatch,
  and exact permutation equivalence. Path discreteness and largest-day share
  barely separated the frozen continuation groups, while trend structure did;
  no parameter was selected from this cross-section.
- Existing Strategy Preview 1.0, Snapshot, Dashboard, and Production remain
  unchanged. No `/data`, provider, credential, publication, deployment, or
  scheduler action occurred. All 1,565 backend tests pass.

## 2026-08-28 — Bind strategy explanations and audit channel distinctness

- Accepted ADR 0061 and bound the browser methodology renderer to the exact
  frozen strategy parameter fingerprint. The UI now exposes formula weights,
  underlying component definitions, entry-geometry mapping, Advance/Watch
  gates, deterministic ranking order, and each displayed security's input,
  weight, and weighted contribution.
- Added fixed-point, round-half-even browser reconstruction of every displayed
  channel score. Unknown parameters, missing evidence, malformed inputs, or a
  score mismatch fail closed; status and rank remain Dell-calculated facts.
- Moved extension into a neutral position/chase-risk review block so a low
  extension label is not presented as automatic counterevidence. Published
  contracts, evidence rows, scores, and strategy calculations are unchanged.
- Added a deterministic full-population overlap diagnostic. On 2026-08-26,
  every qualifying breakout and pullback member was also in trend continuation
  in both Universes. Continuation is now explicitly labelled a broad
  provisional trend filter pending continuation-specific facts and
  chronological validation. No channel scores or outcomes were compared.
- All 1,558 backend and 94 frontend tests and the frontend Production build
  pass. The current Dell-published strategy payload also passes the new exact
  parameter and score reconstruction path for both Universes.
  No `/data`, publication, deployment, provider, credential, scheduler, or
  Production state changed.

## 2026-08-28 — Publish and deploy Snapshot 1.9 / Dashboard 2.6 review release

- Used the user's exact `production-review-deployment/1.1` authorization to
  publish MI `2026-08-28T131700Z-eeccc22` and Snapshot
  `2026-08-28T132100Z-eeccc22` for actual 2026-08-26 versus expected
  2026-08-27, lag one. The active payload explicitly reports `stale_review`;
  no 2026-08-27 EOD freshness is claimed.
- Deployed OCI release `2026-08-28T132100Z-eeccc22` from source commit
  `eeccc2242a3414aba3b761915c4e146022b3b9fe`. Snapshot 1.9 / Dashboard 2.6,
  the Candidate summary/detail split, and strategy-channel product are now
  active; the prior 1.7/2.4 Snapshot remains the rollback target.
- Remote preflight, atomic switch, checksums, Nginx and service checks,
  unauthenticated protection, temporary equal-capability guest Session,
  Candidate summary/detail, strategy lineage, logout, and post-logout
  protection all passed. Password login and human visual acceptance remain
  manual checks; no credential content was read.
- Post-deployment local reconciliation found a clean source repository, 390
  `/data` files / 202,875,231 bytes, inventory fingerprint
  `7d66bc02fe88410a4ed6f000f74875aa135e11d10318ff010a148d03ba08a0de`,
  zero symlinks, and zero publication residue. See the
  [deployment audit](../audits/stale-review-publication-deployment-2026-08-28.md).

## 2026-08-28 — Reuse Candidate completion evidence during publication

- Accepted ADR 0060 and separated research validation from publication
  custody validation. Candidate audit finalization retains full semantic and
  Oracle validation; MI build/Plan/Apply now rehash the immutable artifact
  ledger and parse only bounded publication inputs instead of recreating all
  historical typed rows three times.
- MI 1.1/1.2 plan creation requires an exact in-process evidence object from
  candidate construction. Apply still rechecks every artifact SHA/size,
  parameters, Oracle/equivalence gates, Entry Geometry lineage, frozen MI
  output, Production inventory/freshness, target absence, and pointer state.
- On the real 2026-08-26 audit, custody-only validation completed in 1.55
  seconds at 145,632 KiB peak RSS. The complete Candidate 1.1 + Entry Geometry
  product completed in 11.29 seconds at 1,097,512 KiB and retained the exact
  `286d4eebcb2e0489f33b03894bec8c7c58c1641f113719a014f296db42c2f07a`
  fingerprint and 496/532 counts.
- Extended the same boundary to MI source custody. Publication now rehashes
  the completed Phase 1a 26-session EOD ledger and validates its EOD/Identity
  manifests without rebuilding price rows, and rereads immutable Activation
  membership without replaying its historical liquidity calculation. The real
  source-binding step fell from 53.74 to 2.98 seconds with unchanged source
  and preview fingerprints; whole-`/data` inventory CAS and the optional deep
  context-report validation remain intact.
- This repository change has not yet published, activated, uploaded, or
  deployed anything.

## 2026-08-28 — Second exact stale-review authorization

- Accepted ADR 0059 after the user supplied the exact
  `I_ACKNOWLEDGE_2026_08_26_STALE_REVIEW_LAG_1` acknowledgement for actual and
  analysis session 2026-08-26, expected session 2026-08-27, and lag one.
- Added `production-review-deployment/1.1` without changing or invalidating the
  historical 1.0 authorization. Backend contracts, plans, readers, freshness
  gates, Snapshot validation, and browser parsers accept only the two exact
  version/date/acknowledgement combinations.
- This change authorizes the bounded review publication path only; it does not
  claim fresh data, authorize provider acquisition, or by itself publish,
  activate, bundle, upload, or deploy anything.

## 2026-08-28 — Candidate strategy workspace continuity review

- Made Candidate subview and strategy-channel selection URL-addressable, so
  direct links, refresh, and browser history restore the exact research view.
- Moved the Candidate subview selector ahead of contextual controls and removed
  the disabled risk-mode selector from strategy mode. Its headline now reports
  the selected channel's Advance + Watch pool rather than an entry-risk count.
- Made the three evidence-incomplete channels visibly unavailable with their
  affected population instead of presenting an unexplained zero. English and
  Chinese remain one behavior with presentation-only translation.
- The focused interaction tests, all 91 frontend tests, and Snapshot-mode build
  pass. A Dell-local real 2026-08-26 payload preview was prepared for human
  review. No `/data` write, publication, deployment, OCI access, or Production
  change occurred.

## 2026-08-28 — Carry strategy identity through publication and bundle

- Accepted ADR 0058 and added Approval Plan 2.4 exclusively for Snapshot 1.9 /
  Dashboard 2.6. It extends every 1.8 binding with exact strategy product,
  audit-manifest, audit, parameter, and filename identity.
- Plan construction, CLI loading, formal revalidation, apply, and verify-then-
  link now fail closed on changed strategy bindings while Plans 2.0–2.3 remain
  readable.
- Extended the OCI bundle validator through 1.9/2.6. It independently checks
  the strategy file hash and logical identity, source lineage, fixed Universe/
  channel order, complete counts, bounded contiguous ranks, zero-mismatch
  Oracle evidence, and research-only/equal-capability boundaries.
- Extended deployment postflight to retrieve and validate the protected
  strategy resource through a temporary guest Session. Added an explicit test
  that guest and credential entry create the same role-free Session shape.
- A Dell-local 1.9 bundle build and extracted guest-postflight validator passed
  without OCI access. A real read-only formal dry-run then completed in about
  285 seconds and correctly returned `stale_blocked` at actual 2026-08-26 versus
  expected 2026-08-27, lag one, with zero Production writes. No plan
  approval/apply, `/data` write, upload, deployment, rollback, provider request,
  or Production change occurred. See the
  [publication/bundle review](../audits/candidate-strategy-publication-bundle-review-2026-08-28.md).

## 2026-08-28 — Lazy Candidate strategy-channel product and UI

- Accepted ADR 0057 and added the source-bound
  `candidate-strategy-channel-product/1.0` projection. It retains complete
  counts and at most eight Advance/Watch explanations per channel without
  enlarging the default Candidate summary or copying full deprioritized rows.
- Added repository build/read support for Snapshot 1.9 / Dashboard 2.6. The new
  strategy file binds the exact Candidate publication, Entry Geometry,
  strategy audit, parameters, consumers, and zero-mismatch independent Oracle.
- Added a strict browser parser and bilingual lazy Strategy Channels workspace.
  Rankings are visibly same-channel only; reasons, first rejection risk,
  counterevidence, review conditions, invalidation, manual event/options checks,
  and unavailable channels remain explicit. Guest and credential Sessions use
  the same capability contract.
- A Dell-local temporary-root build formally reread the 195,211-byte product
  with logical fingerprint
  `45bad6eb7fd014c0cc36b1244be7274dc98b92d23fa57d9ddcabe10b271ca3cd`
  and unchanged 496/532 Candidate counts. This is mechanics evidence only.
- No provider, credential, `/data`, publication, activation, bundle, deployment,
  scheduler, or Production state changed. Publication-path support remains a
  separate authorization.

## 2026-08-28 — Explainable Candidate strategy-channel preview

- Accepted ADR 0056 and replaced the taxonomy-only strategy shadow with a
  source-bound offline preview for momentum breakout, strong-stock pullback,
  and trend continuation. Each channel has its own fixed formula, status,
  within-channel rank, reasons, counterevidence, invalidation, and missing-data
  handling; no cross-channel total exists.
- Kept market/sector fit outside technical scores and kept technical reversal,
  fundamental value reversal, and defensive rotation explicitly unavailable.
  Strong-stock pullback relies on Entry Geometry's quiet-pullback fact instead
  of rewarding the general volume-participation component.
- Added a bounded consumer that retains complete counts but exposes at most the
  top eight Advance/Watch explanations per channel.
- Completed a read-only calculation over the formal 2026-08-26 Candidate and
  Entry Geometry audits. It found 10/43/130 Primary and 11/47/138 Secondary
  Advance rows across breakout/pullback/continuation respectively; the first
  view remains capped at eight per channel. This is mechanics evidence, not
  historical validation or option performance.
- Added deterministic and input-permutation tests. No provider, `/data`,
  publication, Snapshot, frontend, deployment, scheduler, or Production state
  changed.
- Added an independent Oracle that does not import the Production strategy
  calculator and recomputes score, status, and rank. Added an atomic, immutable
  `/tmp` audit bound to both formal source manifests. The real 2026-08-26
  Primary and Secondary run passed with zero mismatch and input-permutation
  equivalence; audit fingerprint is
  `1c2036a6266647482de12d1ed7a1f9adf0f41311bc886979324ba3a0859c2877`.

## 2026-08-28 — Family-specific source resolution closure

- Accepted ADR 0055 and added executable Source Resolution Governance V1.
  Exact family/fact policies now bind source roles, contiguous precedence,
  permission-review fingerprints, and matching thresholds while structurally
  prohibiting ticker joins and first-non-null selection.
- Added a pure stable-ID/fact-fingerprint resolver. Missing anchors or required
  corroboration return unavailable; any usable resolving contradiction
  quarantines without majority vote; crosswalk-only and unresolved-quality
  evidence cannot establish a canonical fact. Resolution grants no operation.
- Prepared—but did not send—the exact provider permission, retention,
  deletion, coverage, correction, availability, and pricing inquiry packet for
  EOD, lifecycle/action, SEC evidence, and identifier-crosswalk lanes.
- This closes the planned general data-governance design pass before Candidate
  feature development. Concrete sources, real adapters, physical historical
  acquisition, and performance claims remain gated by permission and coverage.
- No provider, credential, `/data`, publication, deployment, scheduler, or
  Production state changed.

## 2026-08-28 — Source permission governance and official-source composition

- Added ADR 0054 and executable Source Permission Governance V1. Source reviews
  now independently cover Dell acquisition, raw retention, derived analysis,
  equal-capability raw/derived display, and machine delivery. Missing, stale,
  blocked, separate-agreement, or unsupported uses fail closed; assessment
  never grants operational authority.
- Added a dated official-source compatibility review. It found no single
  complete and cleared source, selected a provider-neutral hybrid direction,
  separated SEC filing evidence and open identifiers from security/lifecycle
  completeness, and kept current Massive, Alpha Vantage, and Alpaca standard
  paths out of the equal-capability shared product. Twelve Data remains only a
  future permission/pricing inquiry.
- Added synthetic tests for full clearance, blocked shared display, separate-
  agreement ambiguity, review expiry, family coverage, complete use matrices,
  and safe public evidence URLs. No account, provider request, credential,
  `/data`, publication, deployment, or scheduler changed.
- Upgraded Historical Pilot approval review to 1.1. The source-permission gate
  is now derived from exact same-time assessments for EOD, point-in-time
  Identity, and corporate-action source observations, all covering the six
  Dell/equal-capability uses under one source and review. Callers cannot submit
  a manual satisfied permission gate or override a blocked review with forged
  cleared assessments; passing still grants zero authority.
- Added an immutable explicit-root repository for typed source reviews and
  assessments. It uses content-addressed partitions, atomic rename, fsync,
  formal reread, and idempotency, while rejecting conflicts, corruption,
  partial targets, cross-review bindings, and symlink paths. Tests use only
  temporary directories; no `/data` review or allowlist was created.

## 2026-08-28 — Default-deny historical Pilot approval review

- Accepted ADR 0053 and added a pure approval-review package that binds the
  implementation revision, exact plan/inventory, unified governance and access
  policy, repository fixture evidence, request details, three caller-supplied
  external gates, and one derived source-permission gate.
- Required effective-dated external evidence: inventory and account entitlement
  remain valid for at most 24 hours, lifecycle review for 30 days, and source-
  permission review for 90 days. Stale evidence cannot generate acknowledgement.
- Added deterministic selection of the three XNYS sessions immediately before
  a contiguous EOD inventory. The documented 29-session boundary selects
  2026-07-14 through 2026-07-16; without named Ticker Events the preliminary
  ceiling is 75 serial requests and 1,125 transport seconds.
- Review output can only be `blocked` or ready to request a separate exact user
  authorization. It always records zero authority, provider requests, writes,
  publication, deployment, and scheduler capability. Unnamed requests cannot
  be inserted after review.
- Current external gates remain unresolved and no real acknowledgement is
  emitted. No provider, credential, `/data`, `/tmp`, authentication,
  publication, deployment, or OCI state changed.

## 2026-08-28 — Unified record governance and shared-content parity

- Accepted ADR 0052 and added Data Record Governance V1 with separate data-
  layer, disposition, evidence, quality, coverage, point-in-time eligibility,
  retention, content-scope, and web-serving dimensions. Similar domain states
  are mapped, not flattened into one ambiguous status.
- Added an executable standard registry for 16 current core data families and
  fail-closed validation for family, layer, stable-key grain, retention, scope,
  quarantine, exclusion, supersession, historical availability, and serving
  policy.
- Reaffirmed guest/credential shared-product parity as a fixed policy. There is
  no owner-only market-analysis serving state; incompatible sources are blocked
  from future shared publications for both entry paths. Future user-private
  records require a real identity boundary.
- Replaced the historical planner's obsolete unresolved-product-posture blocker
  with the narrower unresolved equal-capability source-permission blocker.
- No existing dataset was migrated, rewritten, deleted, published, or deployed;
  no provider, credential, `/data`, authentication, or OCI state changed.

## 2026-08-28 — Read-only historical pilot planner

- Added `historical-research-pilot-plan/1.0`, a pure planner that accepts only
  caller-supplied fingerprinted inventory and exact XNYS target sessions; it
  performs no filesystem scan, credential access, provider call, or write.
- Enforced one-to-three targets, the reviewed 80-request hard ceiling, zero
  automatic retry, no faster than 15-second serial pacing, bounded action and
  experimental lifecycle scopes, and automatic subtraction of completed EOD
  and same-session Identity inputs.
- Added deterministic fingerprints, inventory summaries, request-class
  ceilings, transport-time estimates, exact future `/tmp` package-relative
  paths, proposed canonical partition candidates, and explicit unresolved
  action-year/Coverage-ID templates.
- The planner permanently returns `not_authorized`, `review_plan_only`, zero
  external requests, and zero data writes. It cannot authorize acquisition,
  Apply, publication, deployment, or scheduling. A real pilot remains blocked
  on terms/product posture, entitlement, lifecycle-source coverage, and a
  separate exact authorization.

## 2026-08-28 — Synthetic Massive action mapping and adjustment invariants

- Rechecked the current public Massive Stocks V1 Splits and Dividends response
  shapes and added saved synthetic fixtures; no account endpoint, API request,
  credential, or real response was accessed.
- Advanced only the corporate-action source-observation contract to 1.1 for
  separately named provider adjustment/distribution evidence; the other
  historical row contracts remain 1.0.
- Added a transport-free mapper for split, reverse-split, stock-dividend, and
  cash-dividend observations with point-in-time stable-ID resolution,
  first-observed-only knowledge, Decimal normalization, deterministic fallback
  IDs, and explicit typed quarantine or safe unmapped issues.
- Preserved provider cumulative adjustment factors only as source evidence.
  Added independent split price/volume direction, cash-dividend backward
  continuity, composition, reverse-to-raw, and explicitly same-basis provider
  reconciliation invariants.
- No provider capability, canonical Corporate Action, real Adjustment Ledger,
  `/data` write, formula tuning, publication, deployment, scheduler, or
  notification occurred.

## 2026-08-28 — Historical fixture Parquet repositories

- Added explicit PyArrow schemas and immutable Parquet partition repositories
  for corporate-action source observations, instrument lifecycle observations,
  daily Universe membership decisions, and adjustment-ledger entries.
- Added deterministic ordering and logical fingerprints, physical file hashes,
  staged atomic completion manifests, idempotent rereads, and fail-closed
  duplicate, conflict, corruption, path, and symlink validation.
- Separated provider corporate-action observations from the required canonical
  Corporate Action research family. A source observation can never satisfy the
  canonical readiness gate; zero-event source partitions are representable
  without inventing rows.
- All physical tests wrote only isolated temporary roots. No provider adapter
  or request, credential access, `/data` write, real history, formula,
  publication, deployment, scheduler, or notification occurred.

## 2026-08-28 — Historical research typed foundation contracts

- Added immutable provider-neutral Pydantic records for corporate-action
  source revisions, effective-dated instrument lifecycle evidence, explicit
  included/excluded/quarantined daily Universe decisions, adjustment-ledger
  entries, dataset references, and bounded coverage readiness.
- Enforced stable-ID resolution, action-specific evidence, correction lineage,
  effective/source-available/first-observed/ingested timing, Decimal-only
  financial factors, separate split and total-return semantics, and null
  factors for unavailable or quarantined adjustments.
- `research_ready` now requires at least 252 sessions, all six completed
  families covering the declared interval, and a mature-signal count bounded
  by feature warm-up and forward horizon. Synthetic contract tests cover valid,
  ambiguous, incomplete, and prohibited states.
- No PyArrow schema, Parquet repository, provider adapter/request, credential
  access, `/data` write, formula, publication, deployment, scheduler, or
  notification occurred.

## 2026-08-28 — Massive historical source and Dell pilot review

- Rechecked official public Stocks Basic pricing, Grouped Daily, All Tickers,
  Splits, Dividends, experimental Ticker Events, Day Aggregates flat files, and
  Market Data Terms without accessing an account endpoint or credential.
- Confirmed the public Basic shape: five calls/minute, two years history,
  end-of-day/reference/corporate actions, no flat files; Grouped Daily is one
  date/request, All Tickers is point-in-time with 1,000/page, and current
  Splits/Dividends allow 5,000/page.
- Recorded `NOT_READY_FOR_PROVIDER_PILOT_AUTHORIZATION`. Official individual-
  use terms describe owner-only application use, restrict third-party Market
  Data/Derived Works display and non-display/derivative use, and require
  deletion on termination. This conflicts with equal-capability guest/friend
  use and requires account-specific clarification for retained research.
- Measured current Dell families and projected EOD plus Identity at about
  0.83 GB for 252 sessions and 1.66 GB for 504. Identity pagination dominates:
  roughly 13–19 serial hours for the missing 223-session floor or 28–40 hours
  for the missing 475-session target under observed/ceiling page counts.
- Added a proposed 10 GiB canonical plus 10 GiB staging budget, physical family
  layout, fixture-first implementation order, and an 80-request maximum future
  pilot. No provider request, credential access, `/data` write, access change,
  deletion, publication, deployment, or scheduler action occurred.

## 2026-08-28 — Point-in-time historical research foundation

- Accepted ADR 0051 and defined the six-family source-neutral foundation:
  unadjusted EOD, point-in-time Identity, daily Universe membership, corporate
  actions, lifecycle/terminal evidence, and explicit adjustment ledgers with a
  separate coverage manifest.
- Required effective, source-available, and ingested clocks; unknown historical
  availability cannot become a sealed-signal feature. Current constituents,
  current classifications, ticker resolvers, and successor maps cannot be
  projected backward.
- Fixed 252 sessions as the acquisition floor and 504 as the preferred first
  target while making feature warm-up, outcome maturity, membership,
  lifecycle, adjustment, and quarantine coverage separate readiness gates.
- Added the repository-evidenced source capability matrix. Existing Massive
  Identity/Grouped Daily mechanics are verified, but historical entitlement,
  corporate actions, delisting/lineage completeness, and governed adjustments
  remain unverified or missing.
- No network/provider request, credential access, `/data` write, backfill,
  physical dataset, formula, publication, deployment, scheduler, or deletion
  occurred.

## 2026-08-27 — Strategy-evaluation historical readiness audit

- Formally read all 29 canonical EOD sessions and their same-date Identity
  bindings: 286,652 bars, 10,048 unique instruments, 9,672 present throughout,
  and SPY present under one stable ID in 29/29 sessions.
- Verified that only one Activation/full-base membership session and one
  provider security-evidence date exist; no physical daily Universe Membership
  V1 or corporate-action dataset exists.
- All retained bars are valid but carry `adjustment_factors_unverified`; split,
  dividend, and total-return factors are all one. First/latest Identity
  snapshots retain only active rows, with 84 first-only and 187 latest-only IDs
  but no inactive/delisted or terminal-date records.
- Recorded `NOT_READY_FOR_PERFORMANCE_EVALUATION`. No provider request,
  credential access, `/data` write, backfill, evaluation dataset, formula,
  publication, deployment, scheduler, or notification occurred.

## 2026-08-27 — Sealed strategy signals and later forward outcomes

- Accepted ADR 0050 and added fixed Candidate strategy evaluation policy 1.0:
  chronological 50/25/25 development/validation/holdout, 1/3/5-session labels,
  five-session purge/embargo, no random split, and point-in-time membership for
  any performance-eligible signal.
- Added separate typed contracts for outcome-free sealed signals and later
  forward outcomes. Signal IDs bind session, Universe, stable instrument,
  channel, and assessment; future source sessions and current-constituent
  performance claims fail closed.
- Available outcomes reconcile next-open/horizon-close underlying-stock return,
  benchmark difference, and MFE/MAE. Pending labels must remain null and
  corporate-action uncertainty cannot feed numeric evaluation.
- No physical dataset, writer, formula, real signal/outcome, backfill, provider
  request, credential access, `/data` write, publication, or deployment
  occurred. Current 29-session history remains below the 252-session minimum.

## 2026-08-27 — Independent Candidate strategy-channel shadow contract

- Accepted ADR 0049 and fixed six Candidate research archetypes: momentum
  breakout, strong-stock pullback, trend continuation, technical reversal,
  fundamental value reversal, and defensive rotation.
- Added the typed `candidate-strategy-channel-shadow/1.0` contract with a fixed
  taxonomy fingerprint, explicit result for every security/channel, same-
  channel-only scores/ranks, separate market fit, source-dated evidence, first
  rejection, counterevidence, reviewability, invalidation, and logical
  fingerprints.
- The contract fails closed on future evidence, omitted channels, cross-channel
  rank misuse, primary event evidence, price-only value reversal, and
  unlabelled relationship proxies. Fundamental/valuation absence remains an
  unavailable result instead of a technical substitute.
- This is taxonomy and validation infrastructure only. No formula, threshold,
  real-data assessment, Candidate/MI/Snapshot/frontend integration,
  publication, deployment, provider request, credential access, or `/data`
  write occurred.

## 2026-08-27 — Lossless Candidate summary and on-demand detail

- Accepted ADR 0048 and added Snapshot 1.8 / Dashboard 2.5 as a consumer-only
  extension over unchanged Market Intelligence 1.2 and Candidate publication
  1.1.
- Replaced the new-contract monolithic Candidate delivery with one typed list
  summary and deterministic Universe/stable-ID detail shards. Summary rows bind
  exact score and entry fingerprints; the manifest and approval plan freeze
  every shard filename, logical fingerprint, and file SHA-256.
- Added formal lossless reconstruction of the full Candidate publication,
  strict frontend summary parsing, and one-shard detail loading with
  summary/detail identity checks. Snapshot 1.5–1.7 remain readable rollback
  contracts; no browser-side scoring or explanation logic was introduced.
- A real `/tmp` 2026-08-26 Snapshot produced the same 496 Primary and 532
  Secondary records. Initial Candidate bytes fell from 20,367,627 to 1,490,756
  (92.68%); 32 detail shards range from 474,940 to 1,028,834 bytes. Full formal
  reread and reconstruction passed. A second lag-zero real build also produced
  and validated approval plan 2.3 with all 32 files bound; the plan was not
  applied.
- No provider request, credential access, `/data` write, MI/Snapshot
  publication, bundle publication, OCI access, deployment, scheduler, or
  notification occurred. Production remains Snapshot 1.7 / Dashboard 2.4.

## 2026-08-27 — Real EOD terminal review recorded without retry

- Reviewed public Massive plan and endpoint documentation plus the local
  exact-date `adjusted=false` adapter and immutable run journal. The evidence
  supports Stocks Basic EOD access and correct local endpoint construction but
  does not establish an exact same-day REST publication minute or the unknown
  HTTP status from the legacy failure event.
- Appended exactly one offline terminal-failure review bound to terminal event
  `cb8cf64d212fe5da269e7936eb18b7f2a354962db27dfd8fd127760f7cfee297`.
  Review event fingerprint is
  `83b641f17c3897544f6c1a962add51f27d7e63b9097825618a7c70db2de01489`;
  logical review fingerprint is
  `61a5c1b559b83d10f15dd675910eee7f657980d1523e50fedae9dde03ca1a499`.
- Selected the conservative `not_before=2026-08-28T16:00:00Z`, one hour after
  the provider's approximate next-day 11:00 ET flat-file completion guidance.
  That separate flat-file guidance is operational evidence only, not a
  Grouped Daily REST availability guarantee.
- Formal offline reread returned `waiting_to_retry` / `wait` with reason
  `operator_review_not_before_pending`, one attempt, one review, no alert, zero
  external requests, and zero Production writes. Package and staging paths
  remained absent. No credential access, fetch, retry, Apply, analytics,
  publication, bundle, deployment, scheduler, or notification occurred.

## 2026-08-27 — Plan-aware EOD readiness and immutable operator review

- Accepted ADR 0047 and advanced readiness to 1.1 with an explicit Massive
  Stocks Basic EOD recency profile. Identity retains the provisional 30-minute
  review point, while first current-session Basic EOD now requires a separate
  bounded operator availability review.
- Added immutable initial-availability and exact-terminal failure reviews with
  allow-once-after or keep-blocked decisions, controlled evidence codes, and a
  seven-day maximum `not_before` horizon.
- Advanced acquisition custody to 1.2, the one-transition coordinator to 1.4,
  and the shared journal to backward-compatible 1.3. Existing 1.2 events remain
  readable and hash-chained; package-ready history cannot be reopened.
- Added an offline, explicit-acknowledgement administrator command. Review
  records zero requests/writes and grants no fetch, Apply, scheduler,
  publication, or deployment authority.
- Added plan-profile, wait/release, exact-failure binding, duplicate, legacy-
  journal compatibility, redaction, and no-network tests. At implementation
  time the real 2026-08-27 failure remained status-unknown and unreviewed; the
  later bounded real review is recorded above. Its HTTP status is still
  unknown and no retry has been performed.

## 2026-08-27 — First controlled data rehearsal and safe failure evidence

- Installed seven-day owner-only data controls at exact revision `c3af030`;
  data-only preflight 1.1 completed without credential access, networking, or
  Production writes.
- Completed the 2026-08-27 Identity chain: 14 provider requests, 13,148
  provider-identity rows, 9,982 instrument/resolver rows, offline plan review,
  and one canonical Apply.
- The following EOD fetch made one request and formally ended
  `permanent_failure`. Package, staging, approval-plan, and canonical EOD
  targets remained absent; no retry or downstream action followed.
- Accepted ADR 0045 and advanced acquisition custody to 1.1 so future failures
  retain only bounded request count and numeric HTTP status, never response
  content, URLs, headers, provider messages, request IDs, or credentials.
- The original EOD event predates 1.1 and its exact HTTP status remains
  unverified. Stocks Basic is publicly described as end-of-day, so the
  30-minute post-close boundary remains review timing rather than a readiness
  assertion.
- Accepted ADR 0046 and advanced the read-only context report to 1.1 so latest
  canonical Identity and latest-EOD-bound Identity are separate, with an
  explicit alignment state.

## 2026-08-27 — Explicit no-email data-control preflight

- Accepted ADR 0044 and advanced external-control preflight to 1.1 with an
  explicit `daily_data_only` mode after the user deferred SMTP configuration.
- Kept enabled Host Runtime, all four active Identity/EOD operations, exact
  revision/SHA/path/policy binding, credential isolation, socket prohibition,
  and zero-write evidence mandatory while omitting all email reads and claims.
- Added contract and CLI tests for data-only success, null email/alert fields,
  zero credential/network/write counts, and rejection of implicit or mixed
  email omission.
- A read-only Dell check at 20:18Z selected 2026-08-27
  `prepare_identity_catchup` but remained in the stabilization window until
  20:30Z. The network-free check at exactly 20:30Z then returned only
  `ready_for_fetch_review` / `review_fetch_authorization`, with zero attempts,
  requests, or writes. Daily run/alert roots and a matching user timer were
  absent.
- An in-memory Host/authorization candidate was not written and no credential,
  network request, canonical write, external config, service, timer, email,
  publication, deployment, or scheduler state was created or changed.

## 2026-08-27 — Explicit post-coordination email delivery

- Accepted ADR 0043 and added explicit one-transition CLI composition from a
  formal alert intent through ADR 0040 custody to the ADR 0041 SMTP adapter.
- Required intent emission, absolute external Host/email configs, independent
  whole-file SHA pins, exact Dell/runtime/root identity, and separate provider/
  SMTP config and credential custody.
- Preserved the coordinator socket guard independently from later SMTP access;
  normal states perform no credential load, alert write, or delivery.
- Added fake-transport tests for default zero access, normal null delivery,
  first delivery, duplicate suppression, known credential failure, disabled
  config, ambiguous SMTP outcome, redaction, and complete explicit arguments.
- No real config, credential, alert root, network request, email, provider
  transition, `/data` write, publication, deployment, service, timer, or
  scheduler state was created or changed.

## 2026-08-27 — Joint external daily-control preflight

- Accepted ADR 0042 and added a read-only command that reconciles the host-
  runtime, standing data-authorization, and SMTP artifacts under independent
  whole-file SHA pins at one verified clean Dell revision.
- Added exact cross-artifact host/revision/repository/data/run/policy/path/SHA
  checks, complete four-operation scope validation, and distinct non-nested
  config and credential custody rules.
- Installed a socket guard for the entire preflight and excluded credential
  paths from its bounded report. Git verification disables optional locking;
  success grants no controlled rehearsal, publication, deployment, or
  scheduler authority.
- Added config-drift, disabled/incomplete scope, expiry, nested custody,
  absent-credential, zero-write, socket-guard, and redacted-rejection tests.
- No real config, authorization, credential, run/alert root, provider request,
  email, transition, `/data` write, deployment, service, timer, or scheduler
  state was created or changed.

## 2026-08-27 — Default-disabled external SMTP alert adapter

- Accepted ADR 0041 and added an exact-revision, externally SHA-pinned SMTP
  configuration that is absent/disabled by default and grants no scheduler,
  publication, or deployment authority.
- Added separate owner-only two-key credential custody, implicit TLS 465 and
  STARTTLS 587 enforcement, deterministic bilingual operational content, and
  a stable Message-ID/deduplication header.
- Bound the adapter to the verified Dell runtime and ADR 0040 roots. Known
  pre-request credential failure records zero requests; initiated transport
  exceptions or partial acceptance remain unresolved and cannot auto-replay.
- Added synthetic config, permission, secret-redaction, rendering, TLS,
  success, deduplication, known-failure, and ambiguous-outcome tests.
- No external config, credential, alert root, command, real SMTP request,
  notification, `/data` write, deployment, service, timer, or scheduler state
  was created or changed.

## 2026-08-27 — At-most-once alert delivery custody

- Accepted ADR 0040 and added a separate owner-only immutable alert journal
  keyed by the ADR 0039 deduplication identity.
- Added pre-transport `delivery_started`, bounded delivered/failed evidence,
  canonical hash-chain reread, global concurrency locking, and exact channel/
  intent binding.
- Formally delivered alerts become idempotent without another transport call;
  known failure, invalid evidence, or crash-ambiguous outcome blocks automatic
  replay and requires review.
- Added permission, tamper, channel drift, concurrency, duplicate, failure, and
  interruption tests using only temporary directories and fake capabilities.
- No real alert root, transport, channel configuration, credential read,
  external request, notification, `/data` write, deployment, timer, or scheduler
  state was created or changed.

## 2026-08-27 — Channel-neutral daily alert intent

- Accepted ADR 0039 and advanced the coordinator to 1.3 with an exact
  `alert_required` field included in its logical fingerprint.
- Added deterministic, channel-neutral warning/critical intents for blocked,
  interrupted-transition, and missed-session attention states.
- Added explicit CLI intent emission with a stable deduplication key and
  `delivery_attempted=false`; normal states emit no intent.
- Deferred exact-revision external authorization provisioning until remaining
  alert/rehearsal code is stable, retaining manual approvals.
- No alert was persisted or delivered; no transport, channel credential,
  provider request, `/data` write, publication, deployment, service, timer, or
  scheduler state was created or changed.

## 2026-08-27 — Exact one-transition recovery routing

- Accepted ADR 0038 and added an explicit coordinator/CLI recovery port for
  exactly one unresolved acquisition, canonical-Apply, or offline-action event.
- Required an exact locked journal reread and immutable start-event bindings;
  canonical recovery cannot substitute a new plan SHA or inventory fingerprint.
- Kept recovery mutually exclusive with authorized capabilities and offline
  execution under the socket guard, with zero requests, zero canonical writes,
  no action replay, and no loop.
- Added family, mismatch, malformed-binding, blocked-state, no-network, and
  invalid-evidence tests.
- No real run root, recovery, credential read, provider request, Apply, `/data`
  write, publication, deployment, service, timer, alert, or scheduler state was
  created or changed.

## 2026-08-27 — Host-gated one-transition CLI

- Accepted ADR 0037 and added an owner-only, externally SHA-pinned host-runtime
  config contract whose absence or disabled flag keeps capabilities uninstalled.
- Added a one-transition CLI and admin wrapper with explicit capability and
  offline-execution opt-ins; it never loops or grants publication/deployment.
- Added independent actual hostname, executing source-root, clean Git HEAD, and
  readiness-policy verification instead of trusting configured assertions.
- Added tests for disabled/default behavior, config custody, dirty/revision/host
  mismatch, explicit installation, incomplete Apply bindings, and recovery exit.
- No host config root/artifact, authorization, credential read, provider request,
  run root, Apply, `/data` write, publication, deployment, service, timer, alert,
  or scheduler state was created or changed.

## 2026-08-27 — Authorized daily data capability composition

- Accepted ADR 0036 and added explicitly installed fetch/Apply adapters that
  compose standing authorization, acquisition/Apply custody, and the existing
  Massive execution boundaries.
- Corrected the authorized canonical root to
  `/data/trading-intelligence-platform`, advanced the transition request to 1.1
  with `canonical_apply_started`, and advanced coordinator evidence to 1.1.
- Preserved actual bounded Identity pagination HTTP request counts instead of
  reporting every fetch as one request.
- Added authorization artifact/content and decision fingerprints to custody,
  plus fail-closed tests for expiry, rate limits, unexpected fetch errors, and
  ambiguous Apply outcomes.
- No capability was installed; no real authorization, host pin, credential
  read, provider request, Apply, `/data` write, publication, deployment, or
  scheduler state was created or changed.

## 2026-08-27 — Canonical daily Apply custody

- Accepted ADR 0035 and extended the still-unactivated shared journal to 1.2
  with a third terminal-family-isolated canonical-Apply state machine.
- Added exact Apply reservation bound to completed acquisition hashes, a formal
  frozen plan, whole-file SHA, expected inventory, absent targets, session,
  operation, data root, package, and automation paths.
- Added post-Apply formal success proof and no-write interruption recovery that
  distinguishes completed, provably untouched, and partial/changed/ambiguous
  state without replaying Apply.
- Exposed a bounded formal plan-evidence reader without raw responses or staged
  artifact content and added journal/custody/coordinator recovery tests.
- No real journal root, authorization artifact, credential read, provider
  request, Apply, `/data` write, publication, deployment, or scheduler state
  was created or changed.

## 2026-08-27 — One-transition daily coordinator core

- Accepted ADR 0034 and added a deterministic coordinator that joins the exact
  automation plan, shared journal, acquisition readiness, recovery, offline
  execution, and publication-review stop without looping or retrying.
- Provider fetch and canonical apply are explicit capabilities absent by
  default. Returned evidence must match operation, target, precondition, event,
  and maximum one-request/one-write bounds.
- Added coverage for wait, manual authorization, fetch/apply capability,
  unresolved recovery, offline opt-in, diagnosis, publication stop, and unsafe
  custody paths.
- No real capability adapter, CLI, run root, authorization artifact, host pin,
  credential read, provider request, `/data` write, publication, deployment, or
  scheduler state was created or changed.

## 2026-08-27 — Default-deny standing daily data authorization

- Accepted ADR 0033 and added an expiring, exact-revision authorization
  contract limited to Massive Identity/EOD fetch and approved canonical apply.
- Required a separately activated whole-file SHA pin plus exact host, provider,
  `/data`, run-root, readiness-policy, custody, package, plan, and current-state
  bindings. Publication, deployment, scheduler, SEC, options, and orders remain
  explicitly unauthorized.
- Added canonical owner-only artifact validation and one-transition decisions
  with one-request/one-write maximums and fail-closed scope, expiry, revision,
  mode, hash, and stale-request tests.
- No real authorization directory, artifact, host pin, provider request,
  credential read, `/data` write, publication, deployment, or scheduler state
  was created or changed.

## 2026-08-27 — Durable provider-attempt custody

- Accepted ADR 0032 and extended the unused real-world run-journal contract to
  1.1 with disjoint provider-acquisition and offline-action event families
  under one global lock and cross-session SHA-256 chain.
- Added exact-readiness reservation, bounded outcome recording, persistent
  retry projection, and no-request recovery. Package-ready evidence must
  formally match operation, session, path, type, request count, hashes, and a
  reservation-to-result time interval.
- Exposed a non-sensitive formal fetch-package evidence reader and added a
  worktree-safe custody administrator entry with duplicate, concurrency-family,
  stale-plan, time, residue, wrong-package, recovery, and network-guard tests.
- No credential, provider request, fetch package, real run root, `/data` write,
  apply, notification, publication, deployment, OCI, Production, or scheduler
  state changed.

## 2026-08-27 — Market-close-aware daily readiness policy

- Accepted ADR 0031 and added a deterministic, network-free readiness plan
  separating XNYS close from unguaranteed provider EOD stability. The first
  fetch review is provisionally 30 minutes after actual close, including early
  closes and daylight-saving transitions; it never claims completeness.
- Added bounded 15/30/60/120-minute retry, provider `Retry-After` handling,
  five-attempt and six-hour limits, terminal failure diagnosis, explicit alert
  state, separate fetch/apply review, and oldest-missing-session recovery.
- Added a worktree-safe read-only administrator entry and calendar, policy,
  CLI, malformed history, backoff, exhaustion, and network-guard tests.
- No credential, provider request, `/data` write, fetch package, apply,
  notification, publication, deployment, OCI, Production, or scheduler state
  changed.

## 2026-08-27 — Single-action offline daily execution custody

- Accepted ADR 0030 and added an executor limited to one exact, unchanged
  planner action across Phase 1a, verified-prior Phase 1b, daily Candidate, or
  Candidate entry geometry. It holds a global lock, records start before
  calculation, validates returned evidence, formally re-plans, and records
  success only after the named immutable stage completes and the plan advances.
- Added an owner-only append-only Dell run journal with immutable canonical
  events, cross-session SHA-256 chaining, strict permissions/symlink/sequence
  validation, unresolved-prior-session blocking, and non-blocking concurrency
  rejection. Interrupted recovery inspects formal state and never re-executes.
- Added a worktree-safe administrator entry and failure, interruption,
  tampering, stale-plan, concurrency, recovery, evidence, and network-guard
  tests. No durable real run root was provisioned and no real action ran.
- No provider request, credential access, `/data` write, publication, Snapshot,
  bundle, deployment, OCI, Production, or scheduler state changed.

## 2026-08-27 — Read-only daily EOD automation control plane

- Accepted ADR 0029 and added a deterministic exact-session planner across
  same-day Identity/EOD, Phase 1a, verified-prior Phase 1b, daily Candidate,
  and Candidate entry geometry. Missing evidence yields one next action;
  corruption, lineage mismatch, or downstream residue blocks the run.
- Added worktree-safe planner and entry-geometry administrator scripts and
  corrected both Massive Identity/EOD administrator wrappers to use the shared
  project runner rather than a checkout-local virtual-environment path.
- A real 2026-08-26 read-only rehearsal selected `calculate_entry_geometry`
  after formally rereading the corrected daily incremental development chain.
  Plan fingerprint was
  `5f5f5be7a0e219ca21acaa01afc889f1397ca216ef7e8daab692686ee55cf21d`.
- No provider request, `/data` write, publication, Snapshot, bundle,
  deployment, OCI, credential, or scheduler state changed.

## 2026-08-27 — Deterministic cold-replay Oracle process parallelism

- Accepted ADR 0028 and added bounded 1–8 worker `forkserver` execution across
  independent cold-replay session Oracles. Workers disable network/DNS and the
  parent retains chronological state, ordered merge, aggregate fingerprints,
  and audit custody. Worker failures propagate without fallback.
- Four workers reduced the real 2026-08-26 cold Oracle stage from 117.09 to
  76.23 seconds and end-to-end cold replay from 597.70 to 560.02 seconds. Nine
  business/Oracle files, the audit logical fingerprint, and Oracle fingerprint
  were exact; Oracle mismatch was zero.
- Rejected a one-session Universe-level process prototype after real serial,
  2-worker, and 4-worker runs took 277.81, 286.99, and 291.22 seconds. Daily
  therefore retains one effective Oracle worker.
- No `/data`, publication, Snapshot, bundle, deployment, OCI, credential,
  provider, or scheduler state changed.

## 2026-08-27 — Explicit Candidate validation tiers

- Accepted ADR 0027 and added executable `daily`, `periodic`, and
  `code_change` gates. Daily requires verified-prior append; periodic and
  code/model change require cold replay. Invalid mode/input combinations fail
  before calculation.
- Periodic verification formally rereads both same-session audits and compares
  eight schema-neutral business projections. It deliberately does not compare
  incremental and cold Oracle containers, whose declared session scopes differ;
  both Oracles and all mode-specific equivalence gates must pass independently.
- A real 2026-08-26 cold reference completed in 597.70 seconds. Formal
  comparison with the final incremental audit took 197.20 seconds and all eight
  projections matched; Oracle mismatch, external requests, and Production
  writes were zero.
- No `/data`, publication, Snapshot, bundle, deployment, OCI, credential,
  provider, or scheduler state changed.

## 2026-08-27 — Streaming and resumable Candidate audit delivery

- Accepted ADR 0026 and retained Candidate audit schemas 1.0/1.1 plus exact
  completed business bytes while streaming canonical JSON, physical SHA-256,
  and logical hashes through bounded buffers. Formal reread no longer retains
  duplicate raw and canonical artifact copies.
- Added an explicit owner-controlled `/tmp` recovery directory with a canonical
  journal bound to the final path, artifact and typed-record fingerprints,
  source base, Oracle, equivalence gates, and prior audit. Verified contiguous
  prefixes resume; gaps, unexpected files, source drift, and corruption fail
  closed. A prepared interruption finalizes before reopening calculation data.
- The final real 2026-08-26 development run recorded 111.636 seconds before
  writing, 17.921 seconds for ten streamed artifacts, 3,343,112 KiB peak RSS,
  and an approximately 164-second recovery-directory-to-delivery boundary.
  Nine source/business/Oracle files were byte-identical to the prior panel-
  cache result; all equivalence gates passed and Oracle mismatch was zero.
- No `/data`, publication, Snapshot, bundle, deployment, OCI, credential,
  provider, or scheduler state changed.

## 2026-08-27 — Formally validated Phase 1a/Candidate panel reuse

- Accepted ADR 0025 and added the optional
  `market-regime-formal-panel-cache/1.0` Dell-local stage. Phase 1a may persist
  its already validated exact 26-session panel under a content-derived key;
  Candidate may reuse it only when the current Phase 1b source ledger binds
  the same EOD, Identity, Activation, session, and ordered-Universe custody.
- Cache absence uses the unchanged formal reader and populates the exact entry.
  A present unsafe, malformed, corrupt, or source-mismatched entry fails closed.
  Entries have canonical fixed-schema bars, physical/logical fingerprints,
  stable-ID memberships, owner-only custody, no `latest` pointer, and no OCI or
  Production role.
- On final V1.0.1 2026-08-26 development inputs, panel load fell from 217.409
  to 8.837 seconds and total time before audit writing from 310.008 to 101.792
  seconds. All nine source/business/Oracle files were byte-identical and both
  independent Oracles had zero mismatch. Cache evidence and physical timings
  intentionally changed only the audit container fingerprint.
- No `/data`, publication, Snapshot, bundle, deployment, OCI, credential,
  provider, or scheduler state changed.

## 2026-08-27 — Verified-prior Phase 1b and Candidate append

- Accepted ADR 0024 and added Phase 1b audit schema 1.1
  `verified_prior_incremental`. It formally rereads current Phase 1a and the
  immediately prior corrected Phase 1b audit, validates date/version/
  Activation/membership/prefix custody, appends one row per Universe, and runs
  a separate one-session state Oracle without reopening `/data`.
- Final V1.0.1 real-data audits covered a cold 2026-08-25 prefix and separate
  incremental/cold 2026-08-26 results. State history, explanation, transition,
  current-summary records, and both Universe history fingerprints were exact;
  both Oracles had zero mismatch. Incremental time before writing was 0.237
  seconds versus 302.736 seconds cold.
- Strengthened formal Phase 1a and Phase 1b readers to reject failed Oracle
  gates and inconsistent typed/container bindings while retaining successful
  legacy V1.0.0 state-audit compatibility. No `/data`, publication, Snapshot,
  bundle, deployment, provider, credential, or scheduler state changed.

- Added Candidate audit schema 1.1 execution mode
  `verified_prior_incremental`. It formally rereads an immediately prior audit,
  validates calculation/parameter/Activation/Universe/Phase 1b compatibility,
  calculates only the new session, independently Oracles score/risk/state
  append, and writes a cumulative immutable audit with an explicit validation
  ledger. Legacy cold audits remain readable.
- Real 2026-08-25 to 2026-08-26 validation first failed closed because legacy
  Phase 1b daily audits changed historical confirmed states when their rolling
  26-session input window advanced. The differences were business semantics,
  not container-only fingerprints, and were not bypassed.
- Accepted ADR 0023 and added state calculation V1.0.1 / parameter set
  `mrom-regime-state-v1-stable-prefix-2`. Phase 1b cold replay now retains the
  first contiguous canonical session as its state-history boundary while each
  Phase 1a Composite continues to use at most its exact trailing 26 sessions.
  Legacy V1.0.0 audits remain formally readable.
- Corrected 2026-08-25 and 2026-08-26 Phase 1b development audits retained all
  16 prior rows exactly and added only the two 2026-08-26 Universe rows, both
  with zero Oracle mismatch. This real-data rehearsal preceded freezing the
  corrected identifiers as V1.0.1; final versioned source passed the complete
  backend regression and did not create a new Production-bound audit.
- On corrected sources, incremental and cold 2026-08-26 Candidate development
  audits matched every source, raw-fact, normalization, score, state,
  transition, risk record, and business fingerprint; both had zero Oracle
  mismatch. Incremental took 309.02 seconds before writing versus 461.67
  seconds cold. Formal panel reread remains the dominant 216.57-second cost.
- Restored formal EOD session-directory validation to the cold path after
  proving that a Phase 1b 26-session source ledger is not the complete
  canonical EOD history. No `/data`, publication, Snapshot, bundle, OCI,
  credential, provider, or scheduler state changed.
- Routed the Market Regime and Phase 1b administrator wrappers through the
  repository-aware Python runner so linked Dell worktrees cannot silently
  import main-checkout source.

## 2026-08-27 — Candidate pipeline measurement and repeated-work removal

- Added physical per-stage wall/CPU timings plus process I/O, invocation, and
  context-switch counters to the Candidate audit manifest. Runtime evidence is
  excluded from the logical fingerprint and older audits remain readable.
- Added a repository-aware Dell Python runner and formal Candidate wrapper.
  Linked Codex worktrees may reuse the main checkout's virtual environment
  without silently importing main-checkout source.
- Replaced per-candidate full-panel scans with one stable-ID bar index per
  panel and reused the already Oracle-checked final risk results.
- Added a formal multi-panel reader that validates the union of overlapping
  immutable 26-session inputs once, then reconstructs the exact source-bound
  panel for each Candidate session.
- On the same complete 2026-08-26 inputs, the instrumented baseline took
  1840.44 seconds before audit writing; the optimized path took 461.88 seconds.
  Panel validation fell from 837.98 to 226.57 seconds and state update from
  773.19 to 4.50 seconds. Process character reads fell from about 734 MB to
  221 MB and the pre-writer RSS sample from about 3.0 GiB to 2.0 GiB.
- Both real-data audits produced Candidate fingerprint
  `34e97758863658bfd710e74b312481e5d9f0d170396882dcf2b9c5c63f7eb6d7`
  with zero Oracle mismatch and passed all replay-equivalence gates. No
  `/data`, publication, Snapshot, bundle, deployment, or OCI state changed.

## 2026-08-27 — Fresh 2026-08-26 publication and Candidate entry deployment

- Published and formally reread same-day 2026-08-26 Identity and EOD through
  their approval-bound workflows: 9,974 canonical instruments, 13,141 provider
  identities, 9,974 resolvers, and 9,953 EOD rows. Local history now contains
  29 sessions from 2026-07-17 through 2026-08-26.
- Completed and formally reread the 2026-08-26 Regime Phase 1a/1b, all 16 ETF
  relationships, preview, Candidate, and Entry Geometry audits. Candidate
  fingerprint is `34e97758863658bfd710e74b312481e5d9f0d170396882dcf2b9c5c63f7eb6d7`;
  Entry Geometry fingerprint is
  `b3e54546f297bcca9e9a23bb011e0137342777dedc979eca1b4cda71f173ff46`.
  Oracle mismatches are zero and Entry Geometry input-permutation equivalence
  is true.
- Published ordinary-fresh MI 1.2 publication
  `2026-08-26T050254Z-6c60502e4473` and Snapshot 1.7 / Dashboard 2.4 release
  `2026-08-26T053233Z-6c60502e4473`. Expected and actual session are both
  2026-08-26, lag is zero, and review mode is false.
- Built and deployed OCI release `2026-08-26T053233Z-6c60502e4473` from source
  commit `6c60502e4473a7ee7512b720f71a135a665f2f34`. Dry-run, remote preflight,
  Nginx checks, atomic apply, unauthenticated protection, and temporary guest
  Session postflight passed. Password-based visual behavior remains a manual
  user check.
- Post-deployment full-source reconciliation reports 340 `/data` files /
  156,415,379 bytes, no symlink or publication residue, and exact MI, Snapshot,
  Candidate, Entry Geometry, bundle, and source-commit bindings.
- Observed the heavy Candidate audit using roughly one logical CPU for about
  30 minutes and reaching about 2.7 GiB RSS on the 8-core / 16-thread Dell.
  Deterministic incremental processing, shared immutable panels, resumable
  stages, and then bounded process parallelism are the next performance work;
  provider requests retain their serial request gates.
- The active Candidate payload is about 20.4 MB. Summary/detail separation,
  compression, and on-demand loading are now explicit payload-efficiency work.

## 2026-08-27 — 2026-08-25 data and additive Candidate entry consumer

- Published and formally reread same-day 2026-08-25 Identity and EOD through
  their approval-bound workflows: 9,974 canonical instruments, 13,141 provider
  identities, 9,974 resolvers, and 9,954 EOD rows. Local history now contains
  28 sessions from 2026-07-17 through 2026-08-25.
- Completed and formally reread the 2026-08-25 Regime Phase 1a/1b, all 16 ETF
  relationships, preview, Candidate, and entry-geometry audits. Candidate
  fingerprint is `32c0647ae18e165052a4fdb5ea00a0ae7f3cec5306daecdc4360ef7de829e626`;
  entry fingerprint is
  `3875872f719537170f17aab04b0715c86ffb67259f75adf0ee796b4a8f0c182b`.
  Oracle mismatches, external requests, and Production writes are zero.
- Added fixed `candidate-entry-lane-consumer/1.0` selection from the complete
  hard-risk-qualified population. It preserves leadership ranks, reuses
  concentration caps, and provides bounded review-now, watch-trigger,
  wait-reset, and other-research lanes.
- Added Candidate publication 1.1, MI 1.2/plan 1.2, Snapshot 1.7 / Dashboard
  2.4/plan 2.2, strict bundle/deployment validation, bilingual frontend parsing,
  and the default quality-by-entry-location workspace while preserving older
  read and rollback contracts.
- Full validation passed: 1,104 backend tests, 84 frontend tests, and the
  production frontend build. Production remains on the 2026-08-24 MI 1.1 /
  Snapshot 1.6 / Dashboard 2.3 release until the separate freshness and
  deployment gates are satisfied.

## 2026-08-26 — Candidate entry geometry and chase-risk shadow

- Accepted ADR 0021 and added the fixed `candidate-entry-geometry/1.0` shadow
  contract. The original Candidate score, state, and risk ranks remain the
  leadership/research-priority axis and are not penalized or reordered.
  Parameter set `candidate-entry-geometry-v1-fixed-baseline-1` has fingerprint
  `e531ffdc18d334329ac906cbe89f0cc88fc2e8932412ff0b6d8ce0b732cc25a1`.
- Added deterministic SMA10/SMA20, ATR14, three-/five-session move,
  volatility-scaled extension, consecutive-up, gap/range/close-location,
  volume-ratio, prior-high/low, and reference-support facts. Added explicit
  breakout, breakout-watch, pullback, strong-but-extended, no-setup, extension,
  first-rejection, review-posture, counterevidence, and manual-check semantics.
- Added a second raw-panel Oracle, input-permutation gate, socket-guarded CLI,
  and four-file owner-read-only canonical `/tmp` audit. Focused tests cover
  additive source binding, high-extension chase rejection, Oracle equivalence,
  and audit reread/custody.
- Formally completed `/tmp/whalpha-candidate-entry-baseline1-20260824`,
  fingerprint
  `6b013f948d5c6d1011cab0685f661907739b77f1cd1fbfa4307d4789a8638bee`,
  with zero Oracle mismatch, no external request, and no Production write.
- Primary Balanced top 50 contains 41 wait-for-reset high/extreme extensions,
  two technical-review-ready structures, four breakout watches, and three
  no-viable-setup rows. This is current-distribution evidence, not predictive
  validation or a reason to tune thresholds.
- No `/data`, Market Intelligence, Snapshot, frontend, bundle, OCI release,
  provider, credential, or scheduler state changed.

## 2026-08-26 — Phase 6 production publication and OCI deployment

- Published and activated MI 1.1 publication
  `2026-08-24T142500Z-1f3eb5512eb0` from the baseline-3 Candidate audit under
  the exact one-session stale-review authorization.
- Published and activated Snapshot 1.6 / Dashboard 2.3 release
  `2026-08-24T144500Z-1f3eb5512eb0`, including the 5.14 MB bounded Candidate
  file with 146 Primary and 155 Secondary display/review cards.
- Built and deployed OCI release `2026-08-26T151600Z-1f3eb5512eb0` from source
  commit `1f3eb5512eb0d1ba67112395450c2783221596da`. Remote preflight, Nginx,
  current symlink, public entry, guest Session, protected Dashboard, exact
  Snapshot 1.6, Candidate contract, logout, and unauthenticated boundaries
  passed. Password-based visual behavior remains a manual user check.
- Post-publication reconciliation reports 312 `/data` files / 107,298,545
  bytes, no symlink/staging/partial residue, and a clean `main` repository.

## 2026-08-26 — Phase 6 Candidate consumer and Snapshot contract

- Added a bounded, language-neutral `opportunity-candidate-publication/1.0`
  projection. It formally rereads the Candidate audit, requires zero Oracle
  mismatch and all replay/permutation gates, joins score/state/risk facts by
  stable `instrument_id`, and publishes only the three fixed risk-mode display
  unions plus Prepare/Enter/invalidated review rows.
- Added Market Intelligence 1.1 and plan 1.1 while preserving 1.0 reader,
  pointer, namespace, revision, and rollback compatibility. The new contract
  binds Candidate audit, EOD, Identity, Activation, parameter, state, Oracle,
  batch, and risk-result lineage without copying raw audit or provider data.
- Added Snapshot 1.6 / Dashboard 2.3 and plan 2.1 with exact Candidate file-set,
  hash, publication, audit, parameter, Universe, and displayed-count checks.
  Existing Snapshot 1.5 / Dashboard 2.2 remains readable unchanged.
- Added the third first-level `Stock Candidates` / `个股候选` workspace with
  Balanced default, Conservative/Balanced/Aggressive formal ranks, stage and
  ticker filters, short-history explanation, seven-component visualization,
  structured support/counterevidence, visible invalidation, raw facts, human
  review checklist, bilingual copy, mobile layout, and fail-closed parsing.
- Extended the OCI bundle and guest postflight gates for the exact 1.6/2.3
  contract. A pre-publication `/tmp` build reread 146 Primary and 155 Secondary
  cards; the Candidate file is about 5.14 MB.

## 2026-08-26 — Phase 5 candidate state, Oracle, and canonical audit

- Upgraded the candidate contract to `opportunity-candidate/1.1` and the
  calculation to `market-regime-opportunity-candidate-v1.1.1`, with fixed
  parameter set `mrom-candidate-v1-fixed-baseline-3` and fingerprint
  `4e44d58430c82f95c6e612c5227db0b050acfff29615e6fec4e49b139087d347`.
  The full formula, normalization, confidence, risk, anomaly, and source-
  quality policy now enters the parameter fingerprint.
- Added a typed prior-state source so current confidence can use only the
  immediately preceding compatible candidate-state row. Added deterministic
  Watch/Prepare/Enter/invalidated replay, missing-session hold/null behavior,
  breakout facts, stable-ID ticker-change handling, and separate state/history
  fingerprints. Candidate invalidation remains explicitly distinct from a
  position Exit or sell instruction.
- Added stable registered-ETF driver IDs, preserved EOD adjustment/quality
  facts through the formal reader, and separated known source-level degraded
  flags from security-specific quarantine. Unknown quality flags, non-valid
  status, non-unit factors, and extreme returns/gaps still fail closed.
- Added an independent raw-panel Oracle for scores, risk rankings, and state
  replay, plus a socket-guarded CLI and exact ten-file canonical `/tmp` audit.
  The reader verifies custody, file and logical hashes, typed record hashes,
  Primary-first ordering, source panels, transitions, and replay equivalence.
- The first formal baseline-2 audit correctly exposed an over-broad quality
  rule that quarantined every scored member because all canonical bars carry
  the known source-level `adjustment_factors_unverified` flag. Baseline-3
  separates that visible degraded limitation from unknown/security-specific
  quality failures; it does not suppress or relabel the source flag.
- Completed and formally reread the 2026-08-24 baseline-3 audit at
  `/tmp/whalpha-candidate-phase5c-baseline3-20260824.0JaMYi`, fingerprint
  `1f25a1c9060d459e372903ad116579973c709363f365f19fa66bb515774c93df`.
  Two candidate sessions produced 7,090 score rows and 7,098 state rows with
  zero Oracle mismatch and all append/restart/permutation/future-prefix gates
  true. Current Primary/Secondary each retain 20 quarantined extreme-move rows;
  no Prepare/Enter state is possible from the two-session evidence. Each
  Universe reaches the fixed 25/50/100 risk-mode display caps.
- The full audit took about 928 seconds and 1.9 GiB peak memory. This is
  acceptable for a development audit but not the intended daily hot path;
  incremental state/source reuse is required before scheduler integration.
- This slice remains offline and read-only with no `/data`, publication,
  Snapshot, API/frontend, OCI, scheduler, position, or option boundary.

## 2026-08-26 — Phase 5A candidate scoring and risk-mode domain core

- Added strict opportunity-candidate fact, component, submetric, confidence,
  batch, risk-assessment, and risk-mode result contracts. Candidate score facts
  remain separate from risk eligibility and rank.
- Added the immutable seven-component/three-risk-mode parameter set
  `mrom-candidate-v1-fixed-baseline-1`, fingerprint
  `2256e94a45d979bf818cdc048939c4650c10f9312099f83756e321ceee910b6f`.
  The parameter fingerprint fixes Decimal Type-7 5th/95th percentile
  interpolation and inclusive average-tie 0–100 percentile fallback.
- Implemented a pure, source-bound 26-session scorer over active stable-ID
  memberships. It preserves as-of bar coverage, same-session ticker metadata,
  CS/ADRC separation, the V1A registered-ETF price-proxy cap, missing-component
  reweighting, exact displayed-contribution reconciliation, and explicit
  underlying-not-option/proxy-not-sector caveats.
- Implemented separate Conservative/Balanced/Aggressive gates and deterministic
  concentration-aware ranks without changing base facts or score. Extreme
  return/gap observations quarantine a row and remain visible even when its
  score is otherwise unavailable.
- Added focused coverage for missingness, proxy absence/cap, CS/ADRC isolation,
  anomaly quarantine, risk-mode separation, concentration caps, source failure,
  deterministic fingerprints, and outer Decimal precision/trap invariance.
- A no-write 2026-08-24 formal-source memory rehearsal covered 1,716/1,718
  Primary and 1,829/1,831 Secondary members, produced scores for every covered
  member, selected registered-ETF proxies for 1,475/1,552, and quarantined 20
  extreme-move rows in each view. Balanced/Aggressive retained their fixed
  50/100 caps; Conservative retained zero because Phase 5A correctly lacked
  state-confirmation history rather than bypassing its 0.75 confidence floor.
  Reusing per-instrument log returns preserved both batch fingerprints; the
  two-Universe formal read/calculation remained about 219 seconds, so source
  validation and shared Primary/Secondary fact reuse remain optimization work.
- This slice makes no network request and adds no `/data`, API, frontend,
  Snapshot, publication, bundle, deployment, scheduler, position, or option
  boundary. Candidate state history, independent oracle, and canonical `/tmp`
  audit remain the next Phase 5 work.

## 2026-08-26 — Daily decision layer and equal-capability guest entry

- Built and deployed OCI release `2026-08-26T103119Z-f344a589a8c9` from source
  commit `f344a589a8c93e527e63470335d88d293141aee1`, reusing the exact active
  Snapshot 1.5 / Dashboard 2.2 and Market Intelligence publication. Dry-run,
  checksums, service/listener checks, atomic switch, unauthenticated boundary,
  temporary guest Dashboard/Snapshot access, and logout postflight passed.
- Added a conclusion-first Daily Decision Brief using the existing immutable
  Regime payload: broad Risk-on confirmation, one-/five-session Composite
  changes, exact supporting/conflicting dimensions, and remaining distance to
  both Risk-on and Defensive boundaries. No analytics score, threshold,
  publication, or fingerprint is recalculated in React.
- Replaced generic support/drag sentences with evidence-consistent copy,
  selected relationship highlights across six fixed economic decision lanes,
  added current-versus-prior state markers, consolidated the global
  short-history reliability warning, and collapsed the complete 16-pair audit
  table by default. Returns remain excluded from highlight selection/ranking.
- Renamed the second user-facing workspace to `Market Structure & Activity` /
  `市场结构与活跃度`; formal Dashboard contract identifiers remain unchanged.
- Accepted ADR 0019 and added same-origin, rate-limited `POST /auth/guest`.
  Guest entry creates the same opaque role-free Session, cookie, Nginx
  authorization result, Dashboard, and private-data access as credential
  login. It accepts no credential or role and does not create a second data
  path.
- Extended login, Auth Service, Nginx, deployment postflight, bilingual copy,
  and regression coverage. Deployment postflight now proves a temporary guest
  Session can read both the Dashboard and bound Snapshot, logs it out, and
  removes local cookie material without printing it.
- Exact first-seen dates, multi-session relationship run lengths/evidence
  acceleration, stock candidate scoring, trade-state publication, portfolio
  state, options analytics, data acquisition, and automated execution are not
  fabricated by this interface slice and remain separate contract work.

## 2026-08-26 — First-level workspace and current-market hierarchy

- Built and deployed OCI release `2026-08-26T094339Z-f9711d5403f6` from source
  commit `f9711d5403f60cd70a93b50ee314ab38a6af24a2`, reusing the active immutable
  Snapshot and Market Intelligence publication. Dry-run, apply, checksum,
  service, listener, and unauthenticated access-boundary checks passed;
  authenticated visual verification remains manual.
- Promoted Market Regime & Opportunities to the first navigation item and
  default workspace; Market Dashboard is the second explicit route.
- Replaced the small sticky view tabs with a persistent desktop left rail that
  treats Market Dashboard and Market Regime & Opportunities as first-level
  workspaces. Universe, language, and private Session controls now share one
  opaque sticky utility header; narrow layouts retain explicit workspace
  navigation without overlaying content.
- Renamed the user-facing Chinese workspace from the literal
  `市场状态与机会图谱` to `市场风向与机会`; English is shortened to `Market Regime &
  Opportunities`. Machine contract IDs and URLs remain compatible.
- Added a first-screen factual market read using existing one-session breadth,
  share-volume participation, sector-ETF leadership, and comparison coverage.
  It explicitly does not claim to be Market Regime or a trade signal and
  explains 1,718 Universe members versus 1,716 comparable observations.
- Increased fixed-priority relationship highlights from four to six while
  retaining all 16 preregistered pairs and the existing non-return-based order.
- Added shared-shell, history, locale, coverage-explanation, and presentation
  tests. Production build/demo-isolation checks pass. No analytics formula,
  API/data contract, authentication, formal data, Snapshot, bundle, OCI
  release, or deployment changed.

## 2026-08-26 — Authoritative context and status reconciliation

- Replaced the mixed historical/current 572-line status ledger with a concise
  current-state summary and moved recovery-critical IDs, fingerprints,
  verification scope, product guardrails, and Windows/Mac continuity into one
  authoritative current-context handoff. Historical execution detail remains
  in this changelog and dated audits.
- Reconciled AGENTS, README, roadmap, Market Regime product/contract status,
  private API governance, and the OCI runbook with active EOD/Identity,
  Activation V2, Market Intelligence, Snapshot 1.5 / Dashboard 2.2, bilingual
  presentation, and the last recorded OCI release.
- Added a fixed-root, network-prohibited, credential-free current-context
  report. It formally reads active contracts, verifies `/data` inventory and
  residue, validates the matching local bundle checksums, and offers a slower
  explicit full-source reread without exposing a write or network mode.
- Defined a minimal local build retention set and removed superseded/failed
  ignored private-Snapshot and OCI bundle directories plus transient Vite
  output. Canonical `/data`, the legacy fallback, the deliberate rollback
  bundle, and current bundle were retained.
- Live-verified the OCI current symlink, manifest boundary, Nginx, Session Auth
  Service, localhost-only listener, and unauthenticated routes without reading
  credentials or using a public endpoint. Removed 21 exact superseded/failed
  remote release directories after pointer/type checks; current and one
  rollback release remain with no staging/partial residue.
- Replaced historical troubleshooting in current operations documents with a
  concise current deployment, access, retention, and verification baseline.

## 2026-08-26 — Production Dashboard demo isolation

- Removed the synthetic Dashboard fixture from the production static dependency
  graph. Explicit demo mode remains available only in development through a
  guarded lazy import.
- Formal API/snapshot failures remain visible errors with retry and never fall
  back to synthetic data. The formal Dashboard parser now rejects synthetic
  response status.
- Added source-graph and emitted-bundle gates that fail a production build if
  any JS chunk or asset contains a known Dashboard fixture marker. Snapshot 1.5,
  Dashboard 2.2, stale-review display, authentication, and analytics semantics
  are unchanged.

## 2026-08-25 — Market Intelligence Production publication preparation

- Added immutable publication/manifest/pointer/plan contracts, source-validating
  reader, offline administrator, CAS/fsync, recovery, rollback, and fault guards.
- Added Snapshot 1.5 / Dashboard 2.2, explicit OCI binding, formal API cache,
  and bilingual snapshot-mode integration without changing analytics.
- Generated a deterministic historical 2026-08-21 candidate and stale-gated
  `/tmp` plan; Production remained unchanged and no deployment occurred.

## 2026-08-25 — English and Simplified Chinese interface

- Added a typed React `en`/`zh` catalog, shared locale provider, fixed domain
  terminology/reason mappings, and accessible global language selector. The
  static login surface uses the same URL/storage/default policy without
  changing its session or redirect security boundary.
- Localized the current Market Dashboard and Market Regime & Opportunity Map,
  including loading/error/empty states, full 16-pair map, five dimensions,
  pair details, tooltips, audit labels, limitations, and warnings. Raw IDs,
  reason codes, exact values, and fingerprints remain unmodified.
- Added deterministic URL > explicit localStorage > English resolution,
  invalid-value canonicalization, history/deep-link preservation, dictionary
  parity, data-invariance, login, and bilingual page tests.
- This remains local preview work. No analytics formula, API numeric semantics,
  Production data, snapshot, Activation, guest access, network, credential,
  OCI, or deployment boundary changed.

## 2026-08-25 — Market Regime local-preview UX refinement

- Reordered the local preview around the confirmed market state, fixed-rule
  support/drag context, and transition distance; Composite is now supporting
  information rather than the dominant visual.
- Added display-only precision, score bars, Support/Neutral/Drag labels, and
  compact short-viewport behavior while retaining exact calculation ledgers in
  expandable audit sections.
- Expanded relationship highlights and pair detail with both-leg returns,
  relative spread, deterministic investor-readable evidence, and clearer
  state-versus-relative-performance separation. All 16 preregistered pairs
  remain visible.
- No API payload, formula, parameter, threshold, state, fingerprint,
  Production data, snapshot, authentication, network, or deployment boundary
  changed.

## 2026-08-25 — Market Regime read-only API and desktop preview

- Added the canonical, source-bound `/tmp` preview bundle and formal reader,
  plus a socket-guarded no-apply CLI. Payload identity excludes `generated_at`
  and binds all three completed offline audits.
- Added default-disabled private overview and relationship-detail endpoints.
  The configured bundle is validated once at startup; default Production
  behavior never depends on `/tmp` and no request scans the EOD panel.
- Added the desktop Market Regime & Opportunity Map with both Universes, five
  auditable dimensions, full 16-pair 5/10/20 map, fixed highlights, filters,
  URL navigation, pair detail, evidence/counterevidence, and methodology.
- Real local 2026-08-21 data reconciled exactly. Production data, snapshot,
  Activation, authentication, guest access, network, credentials, OCI, and
  deployment were unchanged.

## 2026-08-25 — Market Regime Phase 2 offline ETF relationship map

- Added the immutable 30-ETF/16-pair registry, typed relationship contracts,
  deterministic 5/10/20-session calculations, explicit state precedence,
  confidence/missingness, and fixed evidence/counterevidence explanations.
- Added a genuinely independent raw-panel Oracle, chronological replay/append,
  permutation and future-prefix checks, nine-case Decimal context matrix, and a
  socket-guarded no-apply CLI with canonical `/tmp` artifacts.
- The formal 2026-08-21 run produced 336 history rows and all 16 current pairs.
  Oracle mismatch was zero; two runs had logical fingerprint
  `e5acfa29771d965e9bdf21d1bfab24148220217ac474327cdc60e2212532e3a5`
  and byte-identical non-time artifacts.
- Confidence is `low` for every pair because only 26 sessions exist. Regime
  comparison is contemporaneous and non-causal. No EOD/Identity/Activation,
  Production, API, frontend, snapshot, network, credential, bundle, or OCI
  state changed.

## 2026-08-25 — Market Regime Phase 1b deterministic state classification

- Added an immutable state parameter contract, typed candidate/confirmed state
  records, deterministic bootstrap and hysteresis state machine, chronological
  replay/append boundary, and complete transition and explanation ledgers.
- Added a genuinely independent state Oracle plus exact threshold, reversal,
  missingness, XNYS gap, restart, future-prefix, cross-Universe, and global
  Decimal-context coverage. The offline CLI is socket guarded and writes only
  canonical `/tmp` review artifacts.
- The formal 2026-08-21 trajectory had six calculable sessions per Universe.
  Both Universes initialized Balanced provisionally on 2026-08-17, cleared it
  on 2026-08-18, held Balanced in the 2026-08-20 hysteresis band, and ended
  candidate/confirmed Balanced on 2026-08-21 with zero Oracle mismatch.
- Two full runs produced byte-identical non-time artifacts. No Phase 1a
  formula, EOD, Identity, Activation, API, frontend, snapshot, Production,
  network, credential, bundle, or OCI state changed.

## 2026-08-25 — Market Regime Phase 1a offline core

- Added typed Phase 1a analytics contracts, immutable fixed V1 parameters, a
  formal 26-session EOD/same-day-Identity/Activation source reader, pure five-
  dimension calculation service, and a complete raw/normalized/weight/
  contribution/missingness/explanation ledger.
- Added an independently implemented raw-panel oracle, stable-ID permutation
  checks, no-future/no-cross-Universe gates, explicit local Decimal precision
  50 arithmetic, outer precision/trap invariance, and contribution
  reconciliation.
- Added a socket-guarded offline CLI and canonical `/tmp` artifact reader. The
  path boundary rejects `/data`, repository paths, symlinks, traversal, and
  existing non-empty targets; no apply or Production writer exists.
- The formal 2026-08-21 calculation produced Primary/Secondary Composites
  `63.9102`/`64.8167`, with all 18 metrics available per Universe and zero
  oracle mismatch. State/hysteresis is explicitly deferred to Phase 1b; ETF
  relationships, sectors, candidates, API, frontend, snapshot, bundle, and OCI
  remain unimplemented.

## 2026-08-25 — Market Regime & Opportunity Map V1 design

- Added the product specification, proposed data contract, implementation
  architecture, and ADR for a transparent four-layer Market Regime &
  Opportunity Map.
- Defined five exact regime dimensions and fixed composite weights, hysteretic
  regime and candidate states, a 16-pair registered ETF ledger, seven-component
  candidate score, three visible risk modes, evidence templates, and a
  walk-forward anti-overfitting framework.
- Recorded the formal data feasibility boundary: 26 completed EOD sessions
  support 5/10/20-session analytics; point-in-time sector taxonomy, 40/60-session
  history, market cap, fundamentals, options, corporate-action reconciliation,
  and true fund flows remain deferred.
- Split V1A existing-data analytics from V1B taxonomy-dependent sector
  transmission and recommended an offline `/tmp` Phase 1a ledger as the next
  minimum implementation slice. This change is documentation only; no
  Production, network, snapshot, frontend, bundle, or OCI action occurred.

## 2026-08-23 — Approval-bound same-day Identity and EOD catch-up

- Split both Massive administrator entrypoints into fetch-only `/tmp` package,
  offline deterministic approval plan, approval-bound offline apply, and
  formal reread stages. Disabled the old direct network-to-production Python
  functions.
- Bound EOD to the exact same-day logical Identity fingerprint and made the
  Identity logical marker last. Added immutable-component
  verify-then-complete recovery with baseline CAS and fail-closed partial or
  changed state.
- Added HTTPS host/path/date pagination controls, duplicate/loop ceilings,
  credential-bearing URL sanitization, package/plan custody, apply socket
  prohibition, durable atomic publication, and replay/symlink/traversal gates.
- Completed the two-session 2026-08-20/21 workflow only in `/tmp` with fake
  transport. Provider, credential, external network, Production apply, `/data`,
  Dashboard snapshot, Activation, frontend bundle, and OCI changes were zero.

## 2026-08-23 — Formal Dashboard Funnel and durable Snapshot V2 readiness

- Added Dashboard contract 2.1 with ten source-backed, sequentially closed Funnel stages for each active public Universe; API/snapshot carry them directly and React switches the matching ledger with the existing stable URL selection.
- Added snapshot contract 1.4 plus immutable publication, active pointer with V1 no-pointer compatibility, canonical approval plan, lock/CAS, fsync, completed-target verify-then-link, and independent rollback.
- Added an XNYS freshness gate at plan creation and inside the apply lock. The formal candidate is 1,718/1,831 with all 20 stages, but actual EOD 2026-08-19 trails expected 2026-08-21 by two sessions, so publication is blocked.
- Production snapshot, Activation pointer, Dashboard deployment, and OCI release were unchanged; `/data` and external-network writes were zero.

## 2026-08-22 — Versioned Activation V2 readiness

- Bound the main Activation V2 apply to a canonical dry-run approval package. Bare apply is rejected; the immutable plan freezes time/IDs and binds current state, sources, paths, catalog, rollback, fingerprints, and exact Parquet/manifest/pointer hashes. Apply requires the separately approved plan digest and current-state token, revalidates them under lock before production directory creation, and verifies the published bytes against the plan.
- Closed the four authorization-review findings: completed inactive targets now have a verify-then-link path, first-created directories receive durable parent-entry fsyncs, rollback apply requires the dry-run-approved pointer digest, and the public catalog is contractually Primary-first.

- Added a revisioned immutable Activation V2 contract/repository and a fingerprinted atomic active/default pointer. Formal consumers now use one active reader, with compatibility fallback only when no pointer exists and fail-closed behavior for malformed or inconsistent pointers.
- Added a separately authorized rollback boundary, exclusive lock and compare-and-swap concurrency protection, explicit crash-boundary behavior, existing/partial-target rejection, final formal reread, and default-dry-run CLIs.
- The production-root dry-run binds only superseding publication `51403e939930265ba1a273e9f8bc2113cb455f22e8437c1d2775005fd293ee97` and plans 1,718 CS plus 1,831 CS+ADRC. Apply count was zero; production remains 1,641/1,747 and no pointer, snapshot, Dashboard, frontend, or OCI change occurred.

## 2026-08-21 — HSAI historical security-form interval correction

- Corrected the unpublished HSAI reviewed-form plan so ADR/ADS is effective from the 2023-02-09 Nasdaq listing, not the 2026-07-10 ADS ratio adjustment. The frozen four-source ledger separates security-form effective time, source document/covered-fact time, and UTC review/record time. Two production-root dry-runs of immutable revision `authoritative-security-form-v2` were identical and yielded 1,718 CS / 1,831 CS+ADRC with zero oracle, V1, type, duplicate, orphan, conflict, or funnel errors. No apply, `/data` write, production/Shadow mutation, Activation, Dashboard, snapshot, network, credential, or OCI action occurred.

## 2026-08-21 — HSAI authoritative security-form readiness

- Added an offline-only reviewed security-form evidence contract and immutable superseding full-base revision strategy. HSAI is corrected by stable instrument ID from provider CS to reviewed ADR/ADS without bypassing quantitative gates. The dry-run plans 1 reviewed-form row, 4,565 metrics, 9,130 decisions, 3,549 memberships/diffs, and 20 funnels; Primary is 1,718 CS and Secondary is 1,831 (1,718 CS + 113 ADRC). AKR, UNIT, and DFNS warnings remain accepted and non-blocking. No apply, production data, Activation, Dashboard, snapshot, network, credential, or OCI change occurred.

## 2026-08-20 — Full-base trailing-liquidity scope correction

- Proved by formal reader and code-path review that Trailing Liquidity V1 was scoped to candidates already passing the old previous-session USD 20M dollar-volume gate.
- Reproduced all frozen V1 decisions and fingerprints before calculating the correction.
- Added a provider-evidence-first builder, complete decision ledger, sequential/overlapping funnel contract, versioned Parquet repository, formal reader, offline CLI, and scope-regression fixtures.
- Corrected shadow results are 1,719 CS and 1,831 CS+ADRC; current activated members are fully retained, with 78/84 additions and zero prohibited-type leakage.
- Recorded completed authenticated desktop selector validation without claiming mobile, tablet, or keyboard acceptance.
- No provider request, credential access, canonical-data mutation, Dashboard/API/frontend/snapshot change, OCI access, or deployment occurred.
- The sole shadow apply exited 1 before staging on an audit-only Decimal scale violation. No target or residue was created and no second apply ran. The offline contract now persists an exact threshold-state boolean instead of narrowing the daily Decimal product; publication remains pending separate authorization.
- Strengthened the future publication gate to compare every immutable V1 metric as well as every V1 decision before a corrected shadow can be published.
- Added exact Decimal-threshold boundary coverage and corrected the V1 metric reproduction gate to compare Decimal values independently of harmless trailing-zero scale; the full backend now passes 838 tests with two existing warnings.
- The newly authorized dry-run exited 0 and exactly reproduced all expected counts, fingerprints, and 20 closed funnel stages. Its one apply exited 1 before staging because a remaining metric Decimal exceeded `decimal128(38,10)`; no target, staging residue, Activation, Dashboard, snapshot, or OCI change resulted, and no second apply ran.
- Diagnosed the failure completely offline: only two of 3,218 non-null metric medians exceeded scale 10; previous close had zero violations. Canonical Decimal128(38,10) inputs imply a theoretical 76/20 product and 77/21 exact even median, exceeding Decimal256's precision-76 ceiling.
- Finalized the unpublished full-base V1 physical contract with Decimal128(38,10) previous close and a bounded exact Decimal tuple for medians. The final no-apply dry-run round-tripped all 4,565/8,758/3,550/3,550/20 planned rows through temporary Parquet, preserved V1 and corrected fingerprints, and left `/data`, production 1,641/1,747, Dashboard, snapshot, and OCI unchanged.
- Audited Python Decimal context semantics and found a latent silent-rounding risk in daily multiplication and even-median arithmetic despite zero mismatches in the 2026-08-19 dataset. Replaced eligibility arithmetic with signed integer coefficients and explicit scales, made ratio gates exact by cross multiplication, isolated audit analytics in a derived precision-78 local context, and added an independent `Fraction` oracle to the dry-run gate.
- Verified context invariance at precisions 9/28/50, alternate rounding modes, and trapping `Inexact`/`Rounded`. The final dry-run reconciled 90,506 available daily observations, 4,435 complete medians, all decisions/memberships, and 1,864 immutable V1 metrics with zero mismatch; corrected memberships remain numerically unchanged. No apply, `/data` write, provider request, credential access, Dashboard/snapshot change, OCI access, or deployment occurred.
- Removed the final authorization blockers: EOD fingerprint Decimal rendering now uses context-free tuple encoding, the Fraction oracle rebuilds every decision and membership from raw canonical inputs, and nonmembership analytics uses a fresh explicit precision-78 context without inherited traps or leaked flags.
- Repeated the complete production-root dry-run at precisions 9, 28, and 50 and with outer `Inexact`/`Rounded` traps. All four runs exited 0 with zero stored-EOD fingerprint, daily-product, median, decision, membership, or V1 mismatch; corrected counts/fingerprints remain 1,719/1,831. No apply or production change occurred.

## 2026-08-19

- Accepted Dashboard Universe Activation V1: `Common Shares` is the sole default and `Common Shares + ADRs` the optional view. Legacy remains formally readable for rollback and is not an ordinary selector option.
- Added the versioned activation contract/repository/formal reader and default-dry-run administrator CLI, with explicit Arrow schema, atomic publication, final logical marker, source validation, and a regression that requires successful apply postflight to return exit 0.
- Integrated stable-ID activation selection across private market APIs, multi-Universe private snapshots, and the React Dashboard. URL selection is allowlisted and all Universe-dependent modules use one fingerprint; failures do not silently fall back to Legacy or demo.
- Published the two-row 2026-08-19 activation in one `--apply` invocation that completed formal reread and exited 0. Dataset/logical fingerprints are `a4e76ddc328f3d971d8c66ed305640b6c9810b82bbb6b9849fc9f353ffd0e504` and `f9018502a57dc859c83ce843872c8119b3fb855980cd143a2da8d0a8bbc1e0ca`; the prior 240-file inventory remained byte-identical.
- Exported private snapshot contract 1.3, built the 13-file versioned bundle, and deployed OCI release `2026-08-19T083341Z-7ed7fdc21686`. Public login and unauthenticated protection checks passed; authenticated selector/visual verification remains manual.

- Implemented Reviewed Eligibility Override V1, stable-ID Legacy/A/B comparison, explicit Parquet schemas, atomic shadow repository, formal reader, and a default-dry-run administrator CLI. VCX receives an authoritative closed-end-fund exclusion and AKAN an authoritative operating ordinary-share allow; allow cannot bypass upstream gates.
- Published 2 overrides and 3,388 pre-activation decisions plus a final logical marker. The sole apply atomically wrote all targets but exited 1 during final reread because of a missing reader import; no second apply occurred, and the repaired reader subsequently validated all sources, schemas, counts, fingerprints, and hashes read-only.
- Legacy is 1,864; Candidate A/B passed and final shadows are 1,641/1,747. A removes 223 from Legacy (including 113 ADRCs); B removes 117; B minus A is 106 passed ADRCs. Ten incomplete/missing-previous records retain their data-derived exclusions.
- Recommended Provider-Classified Common Shares (Provisional) as primary, the ADR-inclusive view as optional secondary, and Legacy for compatibility/rollback only. Production Universe and Dashboard remain unchanged; network, credential, provider, OCI, snapshot/bundle, and deployment operations were zero.

- Accepted ADR 0016 and implemented versioned `decimal128(38, 10)` Parquet contracts, a provider-neutral metric/decision service, atomic repository, formal reader, and default-dry-run administrator CLI for Trailing Liquidity V1 shadow publication.
- Published one 1,864-row union metric dataset and one 3,615-row Candidate A/B decision dataset after one successful dry-run and one authorized apply. The final logical marker binds the exact 20 EOD/identity sources, 2026-08-14 membership evidence, thresholds, counts, hashes, and fingerprints.
- Reconciled Candidate A to 1,641 passed, 97 below-liquidity, 4 below-price, 1 missing-previous, and 8 insufficient-history records; Candidate B reconciles to 1,747/103/4/1/9. Ten unique incomplete/missing-previous instruments were audited only from local bar and identity evidence.
- Preserved all 223 canonical protected files byte- and metadata-identically; five derived artifacts were added with zero staging/raw residue. External requests and credential accesses were zero, and production Universe, Dashboard/API/frontend, snapshot/bundle, OCI, and deployment state did not change.

- Used the existing XNYS 4.13.2 freshness service at the execution instant to authorize exactly 2026-08-17, 08-18, and 08-19 after finding actual latest 08-14, expected latest 08-19, and lag three. The weekend generated no request.
- Published and formally reread three same-day identity snapshots and three adjusted=false EOD partitions in strict order: 9,939/9,947/9,947 canonical instruments and 9,916/9,909/9,926 bars. All six entrypoints exited 0; total Massive requests were 45 and retries were zero.
- Preserved the original 196-file inventory content and metadata; exactly 27 authorized files yielded 223 files and digest `e453c759200cdf1dfb603a38b4eb519a74092c0f594865c226c233a92d2306d2`. Canonical freshness is now lag zero at 2026-08-19.
- The rolling 07-22 through 08-18 window is 20/0/0 and `ready`. With membership evidence fixed as-of 08-14, A/B have 1,738/1,850 non-null medians, 1,641/1,747 passes, and 8/9 insufficient histories. No derived dataset, Dashboard/API/frontend, Universe activation, SEC/OCI access, snapshot/bundle, or deployment occurred.

## 2026-08-16

- Completed the separately authorized final Massive backfill batch for 2026-08-10 and 08-11 in strict order. Each Instrument Master entrypoint ran once with 14 reference pages and each same-day Grouped Daily entrypoint ran once with adjusted=false; all four exited 0 with zero retries and at least 15 seconds between adjacent entrypoints.
- Published and formally reread two same-day identity snapshots with 9,913/9,924 canonical instruments and two EOD partitions with 9,892/9,885 bars. Schema, count, ordering, fingerprint, physical hash, same-day identity reference, conflict isolation, atomic publication, and staging cleanup passed.
- The original 178-file inventory remained content- and metadata-identical; 18 authorized files yielded 196 files and digest `eb86f69336e567019b7e1553501e38e8545be6a60e5c43e2da0544b7b04c98c0`. The 20-session descriptor is `ready`: A/B have 1,742/1,854 complete medians and 9/10 insufficient-history members.
- No production derived publisher exists, so no trailing dataset, Dashboard result, Universe activation, snapshot, bundle, or deployment was created. Only 30 authorized Massive requests occurred; SEC, OCI, other services, other dates, and retries were zero.

- Completed the separately authorized fifth three-session Massive backfill batch for 2026-08-05, 08-06, and 08-07 in strict order. Each Instrument Master entrypoint ran once with 14 reference pages and each same-day Grouped Daily entrypoint ran once with adjusted=false; all six exited 0 with zero retries and at least 15 seconds between adjacent live entrypoints.
- Published and formally reread three same-day identity snapshots with 9,898/9,907/9,907 canonical instruments and three canonical EOD partitions with 9,869/9,875/9,877 bars. Existing quality, schema, count, ordering, fingerprint, physical-hash, identity-reference, atomic-publication, and staging-cleanup gates all passed.
- The original 151-file protected inventory remained content- and metadata-identical; exactly 27 authorized files were added, yielding 178 files and digest `6033cd1b1dad4f74d62dec4d8addcdd64af4b73b8b3b99ab976f1c4eed65e2df`. The history window now has 18 completed and two missing sessions, remains `insufficient_history`, and emits no 20-session median.
- Reached only the authorized Massive reference and three Grouped Daily endpoints: 45 requests total, zero retries. No SEC/OCI/other service, later session, scheduler, API/frontend, Dashboard, snapshot/bundle, deployment, or Universe activation occurred. Final state: `completed_three_session_batch`.

- Completed the separately authorized fourth three-session Massive backfill batch for 2026-07-31, 08-03, and 08-04 in strict order. Each Instrument Master entrypoint ran once with 14 reference pages and each same-day Grouped Daily entrypoint ran once with adjusted=false; all six exited 0 with zero retries and at least 15 seconds between adjacent live entrypoints.
- Published and formally reread three same-day identity snapshots with 9,886/9,882/9,896 canonical instruments and three canonical EOD partitions with 9,853/9,858/9,877 bars. Existing quality, schema, count, ordering, fingerprint, physical-hash, identity-reference, atomic-publication, and staging-cleanup gates all passed.
- The original 124-file protected inventory remained content- and metadata-identical; exactly 27 authorized files were added, yielding 151 files and digest `e775d09906593cd15bc5d324dac73d9042cbc46645d012d9e5bcaf66dd77a040`. The history window now has 15 completed and five missing sessions, remains `insufficient_history`, and emits no 20-session median.
- Reached only the authorized Massive reference and three Grouped Daily endpoints: 45 requests total, zero retries. No SEC/OCI/other service, later session, scheduler, API/frontend, Dashboard, snapshot/bundle, deployment, or Universe activation occurred. Final state: `completed_three_session_batch`.

- Completed the separately authorized third three-session Massive backfill batch for 2026-07-28, 07-29, and 07-30 in strict order. Each Instrument Master entrypoint ran once with 14 reference pages and each same-day Grouped Daily entrypoint ran once with adjusted=false; all six exited 0 with zero retries and at least 15 seconds between adjacent live entrypoints.
- Published and formally reread three same-day identity snapshots with 9,881/9,882/9,888 canonical instruments and three canonical EOD partitions with 9,848/9,851/9,855 bars. Existing quality, schema, count, ordering, fingerprint, physical-hash, identity-reference, atomic-publication, and staging-cleanup gates all passed.
- The original 97-file protected inventory remained content- and metadata-identical; exactly 27 authorized files were added, yielding 124 files and digest `1187d3de85c668dbb459e3808640b86325daf9e5f247a553b99785bfe465e9b1`. The history window now has 12 completed and eight missing sessions, remains `insufficient_history`, and emits no 20-session median.
- Reached only the authorized Massive reference and three Grouped Daily endpoints: 45 requests total, zero retries. No SEC/OCI/other service, later session, scheduler, API/frontend, Dashboard, snapshot/bundle, deployment, or Universe activation occurred. Final state: `completed_three_session_batch`.

- Completed the separately authorized second three-session Massive backfill batch for 2026-07-23, 07-24, and 07-27 in strict order. Each Instrument Master entrypoint ran once with 14 reference pages and each same-day Grouped Daily entrypoint ran once with adjusted=false; all six exited 0 with zero retries and at least 15 seconds between adjacent live entrypoints.
- Published and formally reread three same-day identity snapshots with 9,881/9,879/9,881 canonical instruments and three canonical EOD partitions with 9,844/9,833/9,859 bars. Existing quality, schema, count, ordering, fingerprint, physical-hash, identity-reference, atomic-publication, and staging-cleanup gates all passed.
- The original 70-file protected inventory remained content- and metadata-identical; exactly 27 authorized files were added, yielding 97 files and digest `27fe6529ca6b7789f5901065f0d9dad405c8532a835be04846022437e7c330dc`. The history window now has nine completed and 11 missing sessions, remains `insufficient_history`, and emits no 20-session median.
- Reached only the authorized Massive reference and three Grouped Daily endpoints: 45 requests total, zero retries. No SEC/OCI/other service, later session, scheduler, API/frontend, Dashboard, snapshot/bundle, deployment, or Universe activation occurred. Final state: `completed_three_session_batch`.

- Completed the separately authorized first three-session Massive backfill batch for 2026-07-20, 07-21, and 07-22 in strict order. Each Instrument Master entrypoint ran once with 14 reference pages, and each same-day Grouped Daily entrypoint ran once with adjusted=false; all six exited 0 with zero retries and at least 15 seconds between adjacent live entrypoints.
- Published and formally reread three same-day identity snapshots with 9,880/9,879/9,879 canonical instruments and three canonical EOD partitions with 9,858/9,846/9,847 bars. Existing quality, schema, count, ordering, fingerprint, physical-hash, identity-reference, atomic-publication, and staging-cleanup gates all passed.
- The original 43-file protected inventory remained content- and metadata-identical; exactly 27 authorized files were added, yielding 70 files and digest `b2537a2d3627f1915c38540ea7af32a93b960a8c826ef1913151c426ae169fe3`. The history window now has six completed and 14 missing sessions, remains `insufficient_history`, and emits no 20-session median.
- Reached only the authorized Massive reference and three Grouped Daily endpoints: 45 requests total, zero retries. No SEC/OCI/other service, later session, scheduler, API/frontend, Dashboard, snapshot/bundle, deployment, or Universe activation occurred. Final state: `completed_three_session_batch`.

- Completed the separately authorized 2026-07-17 single-session Massive backfill pilot. The Instrument Master entrypoint ran once with 14 reference pages and zero retries, then the Grouped Daily entrypoint ran once after a 52-second interval with one adjusted=false request and zero retries.
- Published and formally reread the same-day identity snapshot (13,024 observations, 9,879 canonical instruments/resolver entries) and canonical EOD partition (9,844 bars). Existing schemas, quality gates, fingerprints, Parquet hashes, identity references, atomic publication, and staging cleanup all passed; raw provider payload was not retained.
- The original 34-file protected inventory remained content- and metadata-identical; nine authorized identity/EOD files were added. The 20-session window now has three completed and 17 missing sessions, remains `insufficient_history`, and emits no 20-session median.
- Reached only the authorized Massive reference and 2026-07-17 Grouped Daily endpoints: 15 requests total, zero retries. No SEC/OCI/other service, later session, scheduler, API/frontend, Dashboard, snapshot/bundle, deployment, or Universe activation occurred. Final state: `completed_single_session_pilot`.

- Added provider-neutral frozen contracts and services for bounded multi-session canonical EOD reads, XNYS 20-session planning, exact Decimal median dollar-volume proxy calculation, readiness reconciliation, and a planning-only historical backfill plan. Analysis-day bars are structurally excluded from their own eligibility window.
- Added a stable-ID history reader that validates only requested partitions, manifest/schema/count/content fingerprints, physical Parquet SHA-256, identity references, revisions, path containment, and symlinks without calling a ticker resolver. `current_as_of_constituent_liquidity` is implemented; the distinct `point_in_time_historical_panel` remains unimplemented.
- Read-only production audit computed the 2026-07-17 through 2026-08-13 XNYS window: 08-12 and 08-13 completed, 18 missing, zero corrupt. Candidate A/B have zero 20/20 results and all 1,751/1,864 records are `insufficient_history`; no median or Dashboard result was generated.
- Produced a no-execution plan for 18 same-day identity plus Grouped Daily sessions: estimated 270 requests, conservative ceiling 378, retry zero, fixed 15-second spacing, a separately authorized pilot, then at most six three-session batches. No network, credential, `/data` write, production dataset/API/frontend/snapshot/bundle, OCI, deployment, backfill, scheduler, or Universe activation occurred.

- Added a provider-neutral, frozen offline audit service for two non-production shadows: 1,751 Massive-`CS` Provider-Classified Common Shares and a separate 1,864-member CS+ADRC comparison containing 113 ADRCs. Classification uses only stable `instrument_id` evidence; the sequential USD 5/USD 20M Decimal filter is labeled `one_session_liquidity_provisional`.
- Reread the completed 25-code catalog, 13,110 observations, 9,939 canonical evidence records, 9,939-member identity snapshot, and 2026-08-13/14 EOD partitions through existing manifest/schema/count/fingerprint/hash gates. All shadow hard gates passed; memberships and fingerprints are order-independent, and Legacy reconciles as 1,751 CS plus 113 ADRC.
- Recorded provider-form limitations and edge evidence for VCX, AKAN, BCPC, TPC, VXT, and AZ. Known reviewed conclusions are report-only because no completed reviewed-override dataset exists; no ticker exception changes membership. SEC B2 remains paused and Core/Broad activation remains deferred.
- The audit was fully offline: zero SEC/Massive/other network requests, zero credential access, read-only `/data`, tmp-only test/audit output, and no production dataset, API, frontend, Dashboard Universe, snapshot, bundle, OCI, deployment, EOD/backfill/scheduler, or production activation change.

- Executed the final authorized SEC B2 entrypoint exactly once from `2026-08-16T10:39:44Z` through `2026-08-16T10:39:51Z`. It made six SEC requests and zero retries, progressed through Series/Class landing/selected-CSV validation and CEF landing selection, then failed during the selected CEF CSV attempt with `sec_transport_or_source_validation_failure`; BDC and submissions were not reached.
- Retained one 329-byte sanitized diagnostic with request/retry counts and the generic failure code. Its empty quality summary and cleaned staging do not preserve the successful schema `3.0` landing selections or a narrower sixth-request subcondition, so no candidate counts, selected dates/paths, artifact hashes, or new exception are inferred. No second live run occurred.
- Published no SEC source cache, observations, canonical evidence, logical manifest, or Core/Broad shadow audit. Four targets remain absent, staging is zero, and the protected 34-file/12,942,699-byte inventory digest is unchanged. No Massive/OCI/EOD/Dashboard/snapshot/bundle/deployment or Universe activation occurred. SEC B2 is paused for the current product stage.

- Formalized the SEC source cache as exactly nine private provenance artifacts: two official ticker JSON files, three official landing HTML pages, three selected CSV files, and `submissions.zip`. Each artifact now records its role, official URL, byte size, and SHA-256; all are reread before the completion manifest is written last and staging is atomically published. Landing HTML remains private and is never Dashboard/public content.
- Hardened synthetic-only submissions ZIP validation for encryption, duplicate and normalized-duplicate names, absolute/traversing/backslash/percent-encoded paths, symlink/non-regular/nested/unapproved members, count and expansion bounds, compression ratio, zero compressed-size metadata, bounded reads, JSON parsing, CIK consistency, and basic filings schema. No extracted content is persisted.
- Added offline fake-transport and `tmp_path` regressions for exact manifest reconciliation, manifest secrecy, landing Content-Type/signature, atomic publication, cleanup, existing/symlink targets, malicious ZIPs, and socket prohibition. No live SEC/Massive request, credential metadata/content access, `/data`, OCI, snapshot/bundle, deployment, EOD/backfill/scheduler, Dashboard, or Universe activation occurred.

- Replaced SEC landing discovery's all-history exact-template gate with a two-stage policy: every CSV candidate must pass Baseline URL Safety, selection uses all structurally/date-valid cutoff candidates, and only the unique latest selected source must pass its dataset-specific Exact Dataset Template before download. There is no fallback to an older allowlisted source.
- Added strict nonblocking handling only for baseline-safe, explicitly dated, file-year-consistent candidates strictly older than the selection whose sole exact-rule failure is `path_template_mismatch`, plus a separate strictly older undated warning. The observed 2022 path was not added to the allowlist and is never a transport target; the existing exact 2023/2024 rules and CEF/BDC rules are unchanged.
- Upgraded new landing diagnostics to schema `3.0` with explicit baseline/template/temporal/action fields, warning and blocking aggregates, selected template, status/failure/warnings, and deterministic fingerprint. Historical schema `2.0` diagnostics remain unchanged and audit-readable. Source acquisition now revalidates the structured selected object, counts, fingerprint, baseline safety, and exact template before transport is called.
- Added a local 2026–2022 fixture and offline regressions for row/XML order independence, multiple unknown old filenames, selected/same/newer/future hard failures, undated history, date integrity, complete baseline URL safety, dataset isolation, warning/blocking counts, schema compatibility, redaction, socket prohibition, and selected-only fake transport behavior. No live run, credential metadata/content access, `/data`, OCI, snapshot/bundle, deployment, EOD/backfill/scheduler, Dashboard, or Universe work occurred.

- Executed the separately authorized post-2023-remediation SEC entrypoint exactly once. The run used cutoff 2026-08-14, request ceiling 12, made three SEC requests and zero retries, accepted the 2026/2025 modern, exact 2024 legacy, and exact 2023 underscore Series/Class candidates, then failed closed on a fifth 2022 underscore basename with `path_template_mismatch`.
- Schema `2.0` reported five candidates, four allowlisted/cutoff-eligible, one rejected, and zero selected. No CSV, CEF, BDC, or submissions request followed. The 2022 path was not approved, no rule was changed, and no second run occurred.
- Published no SEC source cache, observation, canonical evidence, or logical manifest. Staging residue was zero, the 34-file protected inventory remained unchanged, and only the 5,674-byte sanitized diagnostic was retained. No Massive/OCI access, snapshot, bundle, deployment, EOD, backfill, scheduler, Dashboard, or Universe activation occurred.

- Added one exact offline Series/Class filename contract based only on the fifth run's schema `2.0` evidence: the modern directory plus `investment_company_series_class_2023.csv` is accepted only for parsed file year 2023. No rule is inferred for 2022 or earlier, and underscore basenames for 2024 and later remain rejected.
- Added a four-candidate official-shape fixture and regressions proving four allowlisted/cutoff-eligible candidates, zero rejected, exactly one deterministic 2026 selection, row-order independence, exact relative/absolute acceptance, URL-security rejection coverage, CEF/BDC isolation, duplicate stability, aggregate consistency, sentinel redaction, and zero external socket attempts.
- Preserved the modern Series/Class template, exact 2024 legacy-directory rule, CEF/BDC paths, cutoff, live retry setting, generic SEC transport, diagnostic schema `2.0`, and candidate-derived aggregates. No live run, credential metadata/content access, `/data` or OCI access, snapshot/bundle, deployment, EOD, backfill, scheduler, Dashboard, or Universe work occurred.

- Executed the separately authorized post-remediation SEC entrypoint exactly once. The run used cutoff 2026-08-14, made three SEC requests and zero retries, accepted the 2026 and 2025 modern Series/Class candidates plus the exact 2024 legacy candidate, then failed closed on a fourth 2023 underscore-style basename with `path_template_mismatch`.
- Real schema `2.0` aggregates remained consistent with candidate states: four CSV candidates, three allowlisted/cutoff-eligible, one rejected, and zero selected. No CSV, CEF, BDC, or submissions request followed; no rule was changed and no second run occurred.
- Published no SEC source cache, observation, canonical evidence, or logical manifest. Staging residue was zero, the 34-file protected inventory remained unchanged, and only the 4,798-byte sanitized diagnostic was retained. No Massive/OCI access, snapshot, bundle, deployment, EOD, backfill, scheduler, or Universe activation occurred.

- Added one exact offline Series/Class legacy-path rule based only on the fourth run's schema `2.0` evidence: the observed 2024 directory and 2024 basename are accepted only for file year 2024. The modern template remains valid; 2023-or-earlier, 2025, 2026, future legacy paths, neighboring spellings, CEF, and BDC remain rejected or unchanged.
- Made candidate diagnostics the single source for CSV candidate, allowlisted, parsed-date, future, historical-undated, rejected, cutoff-eligible, and selected aggregates. Added `selected_count` within compatible schema `2.0` and explicit duplicate exclusion so normal and mid-stream fail-closed diagnostics cannot drift from candidate states.
- Added an official-shape three-candidate fixture and regression coverage for deterministic 2026 selection, row reversal, relative/absolute exact-legacy acceptance, year/basename/directory and all URL safety rejections, aggregate consistency, other-dataset isolation, sentinel redaction, and socket prohibition. No live run, credential or `/data` access, provider request, OCI access, snapshot, bundle, deployment, EOD, backfill, or scheduler work occurred.

- Executed the separately authorized post-schema SEC evidence entrypoint exactly once with cutoff 2026-08-14. It ran from `2026-08-16T07:46:45Z` to `2026-08-16T07:46:51Z`, returned exit code 1, made three SEC requests and zero retries, and stopped at Investment Company Series/Class landing discovery; CEF, BDC, submissions, Massive, OCI, and all other endpoints were not reached.
- Captured sanitized schema `2.0` evidence for three Series/Class CSV candidates. The 2026 and 2025 candidates matched the current path template; the 2024 candidate used the public `investment-company-series-and-class-information` directory variant and failed with `path_template_mismatch`. Query, fragment, and userinfo were absent. The allowlist was not changed and no second run was performed.
- Published no SEC source cache, observation, canonical evidence, or logical completion manifest. Staging residue was zero; the pre/post 34-file protected inventory remained 12,942,699 bytes with unchanged deterministic digest `398d3c8eb8a986ffc34a7f2fe19c50961eca0d9ed52bd980da95217561333f17`. Existing identity, canonical EOD, and Massive evidence data were unchanged.
- Retained only the sanitized 3,903-byte failed diagnostic (`9abd62a6ef9dc4f61e41b6e32c9dde54b594d33dbf8b640c5673b764ede05c50`). No credential value, raw response, production snapshot/bundle, deployment, Universe activation, or OCI access occurred.

- Reconciled repository status documentation against current code, Git history, read-only `/data` metadata, completed logical manifests, and the SEC run audits. Corrected stale claims that real Massive ingestion, canonical EOD persistence, private analytics/Dashboard APIs, static Dashboard publication, and deployment tooling were absent.
- Recorded the last known OCI deployment strictly as Git/documentation history; OCI was not accessed and current live health was not asserted. Recorded ignored build/dist/snapshot/bundle artifacts, the open retention policy, undocumented `/data` child group-write policy, and the non-overwriteable `accepted_with_provenance_exception` 2026-08-14 identity snapshot.
- Clarified Event Engine design history in ADR 0004 and the Event Layer document: `Subject` is a Domain Object; `Observation` is a possible processing stage but not a core Domain Object; `Candidate` is temporary; `Event` is validated behavior; `Knowledge` is durable learning; full implementation remains deferred. This is distinct from SEC `SecEvidenceSubject`.
- Revalidated the documentation-only change with the offline backend, SEC, bulk-discovery, frontend, build, compile/import/health, shell syntax, Markdown-link, network-prohibition, and sensitive-information checks recorded in Current Status. No provider request, credential read, `/data` write, OCI access, snapshot/bundle generation, deployment, or artifact deletion occurred.

### SEC diagnostic remediation history

- Added landing-discovery diagnostic schema `2.0` with candidate/table/row ordinals, parsed year/date, bounded Size, public path structure, selection state, and finite URL rejection codes while retaining the compatible top-level `href_rejected` reason.
- Preserved all Series/Class, CEF, and BDC URL allowlists and selection semantics. Query, fragment, userinfo, external-host, raw HTML, headers, User-Agent, and contact values remain excluded from diagnostics. This offline work made zero network requests and did not access credentials, `/data`, OCI, snapshots, bundles, or deployment.
- Disabled retries specifically for the bounded SEC evidence live entrypoint and added a transport regression proving a recoverable first failure makes one request with zero retries; other provider retry behavior was unchanged.
- Executed the single newly authorized SEC run with cutoff 2026-08-14: three requests, zero retries, then a fail-closed `href_rejected` result in Investment Company Series/Class landing discovery. CEF, BDC, CSV files, and submissions were not requested.
- Published no SEC source cache, observation, canonical evidence, or logical completion manifest. Staging was clean and the 34-file protected canonical/identity/provider-evidence inventory was unchanged; no Massive access, snapshot, bundle, OCI access, or deployment occurred.

- Reworked SEC dated-CSV discovery around the official multi-table `File / Format / Size` DOM shape, including anchor-tail dates, deterministic two-digit year expansion, historical-undated exclusions, exact per-dataset paths, and row-order independence.
- Replaced the collapsed discovery failure with bounded structural reason codes and counts, and limited `application/octet-stream` acceptance to an already selected, non-empty CSV with matching dataset headers.
- Added three minimal synthetic official-shape fixtures and offline network-prohibition regression coverage. No SEC/Massive request, credential or `/data` access, snapshot, OCI access, or deployment occurred; the production Legacy Liquid Screen remains unchanged.

- Replaced the SEC landing-page single-CSV assumption with deterministic table-row selection by dataset year and effective/update date, including cutoff filtering, tied-URL rejection, URL containment, candidate statistics, and multi-year offline fixtures.
- Ran the separately authorized dated-selection B2B attempt once: three SEC requests, zero retries, then a safe stop at the first landing-page discovery gate. No CSV/submissions download, completed cache/evidence, shadow audit, snapshot, production Universe change, or OCI deployment occurred.

- Added the bounded Phase B2B SEC streaming transport, atomic source-cache safety checks, safe submissions ZIP reader, observation/canonical Parquet layers, logical completion marker, and offline tests.
- The first authorized run made three SEC requests and zero retries. It failed closed at the first official-CSV landing-page discovery gate; no completed cache/evidence partition, production snapshot, Universe switch, or OCI deployment was produced.

- Added the offline SEC issuer-structure evidence boundary with immutable point-in-time contracts, authoritative evidence grades, stable identity reconciliation, filing cutoff, BDC state-machine rules, deterministic Core/Broad decisions, and atomic tmp-only Parquet persistence.
- Added a private SEC User-Agent loader and interactive workstation helper plus an HTTPS allowlist, redaction, serial two-request-per-second ceiling, and bounded retry policy. No real contact value was configured and no SEC/Massive request, `/data` write, snapshot, OCI deployment, or production Universe change occurred.

## 2026-08-16

- Executed the separately authorized corrected Phase B1B run: one Ticker Types request plus 14 point-in-time All Tickers pages, zero retries, and no other provider endpoint.
- Published a 25-code provider catalog, 13,110 normalized observations, 9,939 canonical evidence records, and a logical completion marker after schema/count/fingerprint/hash rereads. Reconciliation was 9,939 mapped plus 3,171 expected-unjoined with zero ambiguity, collision, malformed record, duplicate, or canonical conflict.
- Re-audited the unchanged legacy 1,864-member universe: 1,862 remain quarantine, VCX is the one authoritative exclusion, and AKAN is the one authoritative Broad candidate. Core remains 0 and Broad remains 1 because provider type does not establish issuer structure or domicile.
- Added logical completed-snapshot reads, a 99.9% linkage gate, exact request-attempt accounting, and nullable sanitized diagnostics for failures before reconciliation. Existing Instrument Master, identity, resolver, EOD, and legacy calculations were not modified.
- Deployed provisional disclosure release `2026-08-14T020535Z-ebb16015b7da` from clean source commit `ebb16015b7da259e68033ca442544def5a300d63`. The bundle retained the exact prior summary, movers, and Trading Activity Map payloads while adding the legacy/provisional label and material evidence warning.
- Verified root/login/dashboard/private-data/auth boundaries, remote checksums, active Nginx/Auth Service, localhost-only 8010, zero failed units, and no 8000/8001/5173 listener. No real user password was used.

## 2026-08-15

- Completed Phase B1A entirely offline. Read-only reconciliation found two duplicate-ticker groups (`BCPC`, `TPC`), each with one stable-ID resolved observation and one identifier-free excluded observation; old ticker fallback caused all four false ambiguities and a business-key conflict count of four.
- Split normalized Provider Security Observation V1 from canonical Provider Instrument Security Evidence V1, corrected linkage to 9,939/9,939 with 3,171 expected-unjoined observations, and added deterministic observation IDs plus canonical conflict handling.
- Added sanitized failed-run diagnostics outside completed evidence datasets. No Massive/SEC request, credential access, `/data` write, production snapshot, frontend deployment, or OCI access occurred.

- Selected Core U.S. Domestic Operating Equities as the future default and Broad U.S.-Listed Operating Equities as the future secondary view; production activation remains deferred.
- Implemented provider ticker-type catalog and point-in-time instrument security evidence contracts, bounded Massive ingestion, atomic Parquet persistence, and provisional Dashboard governance metadata.
- Ran one authorized Phase B1 sequence: 1 Ticker Types request plus 14 All Tickers pages, zero retries. The 13,110 raw records reconciled, but four ambiguous mappings, nonzero mapped business-key conflicts, and an initially incorrect identity-link denominator failed hard gates.
- Published no evidence partition, generated no production snapshot, and made no OCI deployment. Corrected the identity-link denominator and retained the production stop pending a separately authorized rerun.

- Accepted ADR 0015 and implemented provider-neutral, effective-dated Security Classification V1 with separate security form, issuer structure, listing scope, evidence, status, and disposition.
- Completed the read-only Phase A audit: 9,939 Instrument Master records, 9,889 comparable records, 5,360 explicit ETFs, 4,527 unknown/quarantined non-ETF records, one excluded VCX closed-end fund, and one Broad candidate AKAN foreign ordinary share.
- Computed non-production Phase A Core and Broad candidates of 0 and 1. Production remains on the legacy 1,864-member universe pending evidence remediation; the later product-policy decision does not make these evidence-limited counts production-ready.
- Added deterministic contract, override, point-in-time, reconciliation, funnel, and pollution tests. No Massive call, credential access, `/data` modification, snapshot generation, frontend change, or OCI deployment occurred.

- Accepted the integrity-verified 2026-08-14 Instrument Master, provider identity, and ticker resolver logical snapshot as `accepted_with_provenance_exception`; original request and pagination provenance remains unknown, and the snapshot must not be requested again or overwritten.
- Accepted ADR 0014 and implemented an offline XNYS market-session calendar with injectable time, expected-versus-actual session lag, and separate file-consistency and calendar-freshness statuses.
- Executed exactly one authorized Massive Grouped Daily request for 2026-08-14 with `adjusted=false` and no retry; all hard gates passed and 9,912 canonical EOD bars were published without raw payload persistence.
- Generated a current 2026-08-14 / previous 2026-08-13 private snapshot with XNYS lag zero and freshness `fresh`, then deployed release `2026-08-14T224306Z-21d0e7fda749` from source commit `21d0e7fda749e3afec7edc9a884eb6408663004f`.
- Verified root login, compatibility redirect, unauthenticated Dashboard redirect, private-data/status protection, external internal-auth denial, remote checksums, active services, and localhost-only Auth listener. No authentication credential or policy changed.

- Upgraded Dashboard V1.1 Market Overview with SPY/QQQ/IWM/DIA benchmark strip, equal-weight universe benchmark, Sector ETF relative-to-SPY performance, conservative data freshness wording, top-50 Trading Activity Map default, improved map labels/search/detail panel, and categorized Data Details.
- Completed read-only SNDK review against canonical 2026-08-12 and 2026-08-13 data: identity and OHLC are internally consistent, but corporate-action/adjustment evidence is insufficient; canonical `/data` was not modified.
- Did not call Massive, read Massive credentials, modify `/data`, change authentication/password/session behavior, or alter market-data canonical partitions.
- Deployed private Dashboard Market Overview release `2026-08-13T214820Z-32fed3a8b17b` from source commit `32fed3a8b17b020e00c33f839d2a12e9de50d855`; unauthenticated root/login/dashboard/private-data protection checks passed.

- Recorded user-completed production acceptance for root session login, Dashboard data loading, Logout, and WH Alpha password rotation without recording any password or hash.
- Accepted ADR 0013 and implemented Dashboard V1.1 professional universe cleanup with `Tradable U.S. Equities` as the default view.
- Added Sector Benchmark ETFs as a separate fixed benchmark module and renamed the filtered treemap UI to Trading Activity Map.
- Moved broad engineering/session details into collapsible Data Details and categorized quality flags instead of showing a single large warning count.

- Repaired the OCI password rotation helper after the first real run failed during immediate listener verification; current password version is marked unknown until the user reruns the repaired interactive rotation.
- Hardened listener parsing, bounded readiness polling, and post-replacement rollback status output; password minimum is now a hard 10 characters with longer unique passwords recommended.

- Deployed root-login release `2026-08-13T135949Z-92819ed17316` from source commit `92819ed17316c567c40b440f5c2e8487f9db4b53`; made `https://whalpha.com/` the official branded WH Alpha session-login entry and changed `/login/` to a compatibility redirect to `/`.
- Added a minimal `/auth/status` check for root-entry session detection; it returns only 204 or 401 with no session details.
- Updated Dashboard unauthenticated redirects to `/?next=/dashboard/` while keeping `/private-data/` protected with 401 JSON.
- Added and deployed the OCI-only password rotation helper for interactive user-run rotation; it does not accept or print passwords or hashes.
- Did not call Massive, read Massive credentials, modify `/data`, or change Dashboard analytics, numeric formatting, or Liquidity Map behavior.

- Fixed the production login form submission contract so Sign In uses same-origin JSON `POST /auth/login` instead of native navigation; deployed release `2026-08-15T133119Z-137f244e8508`.
- Repaired the OCI `/login/` route verification by mapping the login path explicitly to the release artifact and requiring branded-login body markers during deployment; deployed release `2026-08-15T130949Z-78eedc071786`.
- Deployed private Dashboard session-login release `2026-08-15T125517Z-0fa5cac89847` and replaced browser-native Basic Auth with a branded `/login/` page and localhost-only server-side session Auth Service.
- Added secure session cookies, logout, wrong-password safe failure behavior, and Nginx `auth_request` protection for `/dashboard/` and `/private-data/`.
- Fixed Dashboard presentation formatting for long Decimal ratios, percentages, compact volume, compact currency, and metric/card overflow.
- Did not read or output the Dashboard password/hash, call Massive, read Massive credentials, modify `/data`, or change Liquidity Map algorithms.

- Provisioned a dedicated `dell5820` to OCI deployment SSH key while retaining the existing WSL OCI key.
- Regenerated the private Dashboard snapshot and OCI bundle from clean source commit `987b5289a7835316ef6aae4aa326aff46de58896`.
- Deployed private Dashboard release `2026-08-13T120220Z-987b5289a783` to OCI as the initial Basic Auth-protected release; it was later superseded by the session-login release.
- Verified public `/` remains the data-free placeholder and unauthenticated `/dashboard/` plus `/private-data/v1/manifest.json` return 401.
- Did not read or output the Dashboard password/hash, call Massive, read Massive credentials, modify `/data`, deploy raw/Parquet data, or access another OCI instance.

- Accepted ADR 0011 for authenticated static private dashboard snapshots.
- Implemented the private Dashboard JSON snapshot exporter and manifest/hash validation.
- Added frontend `snapshot` mode for `/dashboard/` static deployment and `/private-data/` JSON snapshots.
- Added a versioned OCI dashboard bundle builder, Nginx template, dry-run deployment script, and private access runbook.
- Completed read-only OCI preflight without creating credentials, uploading files, reloading Nginx, modifying whalpha.com, accessing Massive, or changing `/data`.

- Implemented the first local React Market Dashboard V1 using the private Market Summary, Movers, and Liquidity Map APIs.
- Added explicit API and synthetic demo modes; API mode does not fall back to demo fixtures on failure.
- Rendered Market Pulse, Market Breadth, Up/Down Volume, liquidity-screened movers, Liquidity Map V1, and Data Quality / Session Metadata.
- Added frontend unit/component tests with Vitest, React Testing Library, jsdom, and mocked ECharts initialization/disposal.
- Verified frontend production build locally; no Massive request, credential access, `/data` write, OCI access, or deployment was introduced.

- Published the 2026-08-12 Massive Instrument Master, provider identity, provider ticker resolver, and canonical EOD Price Bar datasets through the existing bounded pipelines.
- Implemented provider-neutral close-to-close EOD return analytics across the completed 2026-08-12 and 2026-08-13 sessions.
- Added Market Summary V1, liquidity-screened movers, paginated returns, and Liquidity Map V1 private API response contracts.
- Documented that Liquidity Map V1 is not market-cap weighted, not sector grouped, and not a fund-flow or money-flow map.
- No frontend change, OCI access, deployment, database, raw payload persistence, or system service change was introduced.


- Implemented the first canonical EOD read repository for completed Parquet sessions with manifest, schema, fingerprint, and identity snapshot validation.
- Added a paginated provider-neutral EOD query service and private FastAPI response contracts with Decimal values serialized as strings.
- Added default-disabled private EOD market-data routes gated by `TIP_ENABLE_PRIVATE_MARKET_DATA_ROUTES`; default OpenAPI does not show the private routes.
- Verified the completed 2026-08-13 production session read path locally without modifying `/data`, reading credentials, calling Massive, changing frontend code, or deploying OCI.

## 2026-08-14

- Accepted ADR 0010 to represent aggregate EOD volume as exact non-negative Decimal while keeping trade count and timestamps integer-semantic.
- Updated EOD Price Bar V1, Massive mapping, Grouped Daily inspection/ingestion, Arrow schema, Parquet persistence, fingerprints, and tests for Decimal volume.
- Re-ran the authorized 2026-08-13 Massive Grouped Daily request once with `adjusted=false`; all V1 gates passed and 9,901 canonical EOD bars were published.
- Recorded 11,208 fractional-volume records, 4 isolated conflicting duplicate records, 4 missing optional VWAP values, 4 missing optional trade-count values, and 4 zero-volume records as quality warnings.
- No raw provider payload, Dashboard data flow, OCI access, database, scheduler, or system change was introduced.

- Hardened Massive Grouped Daily numeric parsing for JSON int, finite float, Decimal, and numeric string inputs while rejecting bool, non-finite values, malformed strings, and fractional integer-semantic fields.
- Fixed Grouped Daily processing so identity classification is counted before numeric validation and remains independent from OHLCV parse failures.
- Changed low-ratio conflicting duplicate bars from a hard session failure to isolated quality warnings, while preserving a hard gate above the accepted ratio.
- Re-ran the authorized 2026-08-13 Grouped Daily request once; identity coverage passed, but numeric conversion failures and canonical bar count gates blocked publication.
- No raw payload, EOD Parquet partition, Dashboard data flow, OCI access, or system change was introduced.

- Added a controlled Massive Grouped Daily publication entrypoint for the completed 2026-08-13 session using the completed point-in-time ticker resolver.
- Executed one authorized Grouped Daily request with `adjusted=false`; access succeeded but quality gates blocked publication.
- Recorded conflicting duplicate bars, numeric conversion failures, low identity coverage, and insufficient canonical bar count as the exact blockers.
- No raw payload, EOD Parquet partition, Dashboard data flow, OCI access, or system change was introduced.

- Refined Massive Instrument Master snapshot quality classification to separate eligible records, expected exclusions, malformed records, ticker ambiguity, and stable-ID collisions.
- Added Provider Ticker Resolver V1 and included it in the logical Instrument Master snapshot completion marker.
- Re-ran the authorized 2026-08-13 Massive All Tickers pagination once; corrected quality gates passed and published 9,932 canonical instruments, 13,106 provider identity records, and 9,932 resolver entries.
- No raw Massive payload, Grouped Daily call, Dashboard data flow, OCI access, or system change was introduced.

- Added Provider Instrument Identity V1 as a Python contract and data-contract document.
- Accepted ADR 0009 for stable provider identifiers and deterministic UUIDv5 canonical instrument identity.
- Implemented bounded Massive All Tickers point-in-time Instrument Master snapshot ingestion with fixed-interval pagination.
- Implemented Instrument Master and provider identity Parquet snapshot repositories with logical completion marker semantics.
- Executed one live Massive All Tickers snapshot attempt for 2026-08-13; pagination completed, but quality gates blocked publication.
- No raw provider payload, completed Instrument Master snapshot, Grouped Daily publication, Dashboard data flow, OCI access, or system change was introduced.

- Added a safe one-request Massive Grouped Daily inspection tool.
- Executed one read-only Grouped Daily inspection for 2026-08-13 with `adjusted=false`.
- Verified Grouped Daily access and payload structure without saving raw or canonical data.
- Confirmed production publication is blocked pending Instrument Master identity coverage.
- No Parquet write, `/data` write, repository publish, second Massive request, Dashboard data flow, OCI access, or provider-backed deployment was introduced.
- Accepted partitioned Parquet as the initial canonical EOD Price Bar persistence format.
- Implemented a one-session provider-neutral EOD ingestion service for mocked fixtures.
- Implemented an explicit PyArrow EOD Price Bar V1 Parquet repository, manifest, deterministic content fingerprint, atomic publish, idempotency, and conflict/corruption checks.
- Added mocked-fixture ingestion and Parquet persistence tests.
- No Massive API call, credential access, production `/data` write, scheduler, historical backfill, analytics, database, Dashboard API, or OCI deployment was introduced.
- Implemented the protected Massive credential-file loader.
- Implemented a minimal standard-library HTTPS transport using Authorization bearer headers.
- Added local security tests for credential parsing, transport behavior, error mapping, redirect handling, and network prohibition.
- Verified one read-only Massive Stocks reference smoke test without outputting raw data or credentials.
- No ingestion, Grouped Daily download, persistence, Dashboard data flow, OCI deployment, or public provider-backed access was introduced.
- Implemented the Massive Stocks configuration and credential boundary.
- Added a mocked-only Massive adapter skeleton for Instrument Master and EOD Price Bars.
- Added deterministic mocked HTTP response tests for Massive mapping, error handling, pagination, and credential redaction.
- No real API key, Massive API call, market-data download, persistence, provider-backed deployment, or access-control change was introduced.
- Evaluated Massive Stocks Basic using official public documentation.
- Accepted Massive Stocks Basic as the first private EOD development provider.
- Documented public-display and Derived Works restrictions for provider-backed data.
- Accepted the public placeholder, public data-free demo, and private real-data dashboard boundary.
- No account, credential, adapter, API request, data ingestion, deployment, or access-control change was introduced.
- Implemented the synchronous provider-neutral MarketDataProvider Protocol.
- Added provider capabilities and query models for Instrument Master and EOD Price Bars.
- Added explicit provider error taxonomy.
- Added deterministic in-memory provider contract test fake.
- No real provider, network access, credentials, ingestion, persistence, database, or Dashboard implementation was introduced.

## 2026-08-13

- Expanded workstation root LV from 100 GiB to 150 GiB.
- Created 700 GiB ext4 data LV mounted at `/data`.
- Created `/data/trading-intelligence-platform`.
- Retained approximately 100.82 GiB VG free.
- Verified `/data` persisted across a controlled reboot.
- Confirmed zero failed systemd units after reboot.
- Documented the accepted application technology stack.
- Documented the target application architecture.
- Added the documentation checkpoint policy for future material changes.
- Created the minimal FastAPI backend scaffold.
- Created the minimal React/Vite frontend scaffold.
- Introduced the versioned Health API contract.
- Added local development scripts and documentation.
- Installed backend dependencies in the project virtualenv and verified backend tests.
- Verified the Health API locally on `127.0.0.1:8000`.
- Frontend dependency installation and build were not verified because Node.js and npm were unavailable.
- Prepared guarded Node.js 24 LTS provisioning script and operations document.
- Completed Node.js 24 LTS provisioning and verified npm.
- Corrected provisioning script GPG behavior to avoid interactive overwrite prompts.
- Locked frontend dependencies with npm-generated `package-lock.json`.
- Verified frontend production build.
- Verified local Vite server and Vite-to-FastAPI proxy.
- Revalidated backend tests and the direct Health API endpoint.
- No market data provider, database, production deployment, or Dashboard V1 implementation was introduced.
- Accepted the Initial EOD Universe boundary.
- Accepted the three-layer classification model for Sector/Industry, Theme, and Analytical Groups.
- Accepted five normalized EOD logical contracts.
- Documented point-in-time membership and revision principles.
- No provider, data ingestion, physical schema, database, or Dashboard implementation was introduced.
- Implemented the Instrument Master V1 Pydantic contract.
- Implemented the EOD Price Bar V1 Pydantic contract.
- Added validation and serialization tests for the two implemented contracts.
- No provider adapter, persistence, real market data, database, or Dashboard implementation was introduced.

## 2026-08-12

- Completed workstation and OCI infrastructure audits.
- Removed obsolete projects and services.
- Replaced old public trading console with static placeholder.
- Separated workstation and OCI SSH identities.
- Established initial product, architecture, and Dashboard V1 decisions.
- Created project documentation foundation.
# 2026-08-25 — Explicit Production review deployment contract

- Added `production-review-deployment/1.0`, narrowly bound to analysis and
  actual session 2026-08-24, expected session 2026-08-25, lag one, and an
  explicit acknowledgement. Normal publications still require lag zero.
- Bound review metadata through Market Intelligence candidate/manifest/plan,
  active reader/API, Snapshot 1.5 candidate/manifest/plan, and both English and
  Chinese first-screen banners. The payload remains language neutral.
- Added fail-closed checks for missing/wrong acknowledgement, changed session,
  expected date or lag, plus focused and full regressions. No generic
  `--allow-stale` was introduced.

# 2026-08-25 — Dashboard Snapshot 1.5 frontend contract compatibility

- Added typed, fail-closed Snapshot 1.5 manifest validation to the existing
  static Dashboard loader, including Dashboard 2.2, Market Intelligence,
  Funnel, and exact stale-review bindings.
- Kept the embedded Dashboard overview on its defined 2.1 response contract;
  unknown snapshot versions, Dashboard contracts, and data-status values remain
  rejected instead of being converted to empty or synthetic data.
