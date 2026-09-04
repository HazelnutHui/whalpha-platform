# Candidate Pipeline Performance and Execution Boundary

## Authority and scope

Candidate calculation, historical replay, Oracle validation, audit generation,
and future daily automation run on `dell5820`. Canonical and historical data
remain under `/data/trading-intelligence-platform` on Dell. OCI receives only
separately approved bounded publication artifacts and must not run Candidate
analytics or become a historical-data store.

Provider acquisition retains its request and rate-limit gates. CPU-bound local
calculation may use deterministic process parallelism after a serial reference
path proves exact equivalence. Browser, Windows, and future Mac clients are
remote work interfaces, not compute or data authorities.

## Canonical local runner

Use the repository-aware Python runner from the current checkout:

```bash
scripts/dev/run-project-python.sh -m pytest apps/api/tests
```

Linked Codex worktrees may reuse the main Dell checkout's virtual environment,
but the runner places the current worktree's `apps/api/src` first on
`PYTHONPATH`. This prevents a worktree command from silently importing the main
checkout's source. `TIP_PYTHON_BIN` may select another compatible interpreter.

Run a full offline Candidate audit through:

```bash
scripts/admin/calculate-opportunity-candidates-offline.sh \
  --as-of-session YYYY-MM-DD \
  --data-root /data/trading-intelligence-platform \
  --phase1b-audit /tmp/<exact-completed-phase1b-audit> \
  --output-dir /tmp/<new-empty-candidate-audit-directory>
```

The command is socket-guarded, writes no Production state, and requires an
owner-controlled new `/tmp` target. Publication and deployment remain separate
approval-bound operations.

Phase 1a and the downstream daily analytics may share an explicit Dell-local
panel cache:

```bash
scripts/admin/calculate-market-regime-offline.sh \
  --as-of-session YYYY-MM-DD \
  --universe-id provider_classified_common_shares_v1 \
  --universe-id provider_classified_common_shares_plus_adrs_v1 \
  --data-root /data/trading-intelligence-platform \
  --panel-cache-root /tmp/<owner-controlled-panel-cache> \
  --output-dir /tmp/<new-empty-phase1a-audit> \
  --sector-rotation-output-dir /tmp/<new-empty-sector-rotation-audit>

scripts/admin/calculate-opportunity-candidates-offline.sh \
  --as-of-session YYYY-MM-DD \
  --data-root /data/trading-intelligence-platform \
  --phase1b-audit /tmp/<exact-completed-phase1b-audit> \
  --prior-candidate-audit /tmp/<immediately-prior-candidate-audit> \
  --panel-cache-root /tmp/<same-owner-controlled-panel-cache> \
  --validation-tier daily \
  --audit-work-dir /tmp/<new-owner-controlled-candidate-work-directory> \
  --output-dir /tmp/<new-empty-incremental-candidate-audit>
```

The cache is optional and content-addressed by the exact 26-session EOD,
Identity, Activation, and ordered-Universe source ledger. An absent exact
entry invokes the unchanged formal reader and populates the cache. A present
unsafe, malformed, or mismatched entry fails closed. The cache has no `latest`
pointer, never belongs in OCI, and does not authorize `/data` writes.

Entry Geometry and ETF Relationships receive the same cache root from the
daily executor. Entry selects its exact entry from the formally reread current
Candidate source panel; ETF Relationships selects it from the formally reread
Phase 1a input manifest. Both retain the formal cold-reader fallback and must
prove exact source-boundary equality before using or populating a missing
entry. Entry also uses the finalized current-Candidate and governed state
projections rather than reconstructing the complete cumulative Candidate
audit before reading the same histories again.

The Phase 1a command also calculates and independently checks Sector ETF
Rotation from the same in-memory panel. It formally binds the second audit to
the completed Phase 1a audit and reports `source_panel_load_count=1`; it must
not perform another canonical-history scan. Both audit targets must be
distinct, new direct children of `/tmp`.

`--audit-work-dir` enables exact restart and memory-separated finalization. It
must be a distinct, new, owner-controlled direct child of `/tmp`. Completed
artifact prefixes are reused only after physical, canonical, logical, source,
typed-record, Oracle, and equivalence bindings pass. Unknown files, gaps,
changed inputs, or corruption fail closed. A fully prepared interrupted audit
is finalized before any Phase 1b, panel, Candidate, or `/data` source is read.

Append one session from an immediately prior verified Candidate audit with:

```bash
scripts/admin/calculate-opportunity-candidates-offline.sh \
  --as-of-session YYYY-MM-DD \
  --data-root /data/trading-intelligence-platform \
  --phase1b-audit /tmp/<corrected-stable-prefix-phase1b-audit> \
  --prior-candidate-audit /tmp/<immediately-prior-candidate-audit> \
  --validation-tier daily \
  --output-dir /tmp/<new-empty-incremental-candidate-audit>
```

The prior audit must be the preceding XNYS session and use compatible
calculation, parameter, Activation, membership, and stable-prefix Phase 1b
sources. A mismatch fails closed and requires a corrected cold replay.

Build and compare the periodic cold reference explicitly:

```bash
scripts/admin/calculate-opportunity-candidates-offline.sh \
  --as-of-session YYYY-MM-DD \
  --data-root /data/trading-intelligence-platform \
  --phase1b-audit /tmp/<exact-completed-phase1b-audit> \
  --validation-tier periodic \
  --max-workers 4 \
  --audit-work-dir /tmp/<new-cold-reference-work-directory> \
  --output-dir /tmp/<new-cold-reference-audit>

scripts/admin/calculate-opportunity-candidates-offline.sh \
  --as-of-session YYYY-MM-DD \
  --data-root /data/trading-intelligence-platform \
  --phase1b-audit /tmp/<exact-completed-phase1b-audit> \
  --output-dir /tmp/<completed-daily-incremental-audit> \
  --verify-output \
  --validation-tier periodic \
  --reference-audit /tmp/<completed-cold-reference-audit>
```

## 2026-08-27 Dell baseline and first optimization

Both runs used the same 2026-08-26 formal inputs, all four calculable Candidate
sessions, full independent Oracle, and replay-equivalence gates. Both produced
logical fingerprint
`34e97758863658bfd710e74b312481e5d9f0d170396882dcf2b9c5c63f7eb6d7`
with zero Oracle mismatch.

| Stage | Instrumented baseline | Shared-read/indexed state |
| --- | ---: | ---: |
| Total before audit writer | 1840.44 s | 461.88 s |
| Formal panel load/validation | 837.98 s | 226.57 s |
| Candidate state update | 773.19 s | 4.50 s |
| Candidate score calculation | 46.13 s | 45.47 s |
| Independent Oracle | 117.64 s | 118.25 s |
| Replay equivalence | 10.90 s | 10.88 s |
| Process character reads | 733,872,101 | 220,768,515 |
| Pre-writer peak RSS sample | 3,157,624 KiB | 2,113,360 KiB |

The optimized full calculation is about four times faster before audit writing.
It reads each immutable source session once across overlapping 26-session
panels and builds one stable-ID bar index per panel. It does not skip content,
Identity, Activation, Oracle, or replay checks and does not change Candidate
formulas, ranks, states, or fingerprints.

The original manifest memory sample was taken before the audit writer. A
baseline run was separately observed near 6.3 GiB RSS during large JSON
serialization; the streaming/resume result below replaces that open item.

## 2026-08-27 immutable panel reuse result

The final V1.0.1 2026-08-26 Candidate append was run once without a cache and
once against the exact Phase 1a-populated cache. Formal current-panel loading
fell from 217.409 to 8.837 seconds. Total time before audit writing fell from
310.008 to 101.792 seconds, a 67.2% reduction. Process character reads fell
from 684,039,139 to 521,493,089.

The source manifest, raw facts, normalization ledger, score history, state
history, transition ledger, current risk results, parameter contract, and
independent Oracle report were byte-identical across both paths. Both Oracles
reported zero mismatch. The aggregate audit fingerprint differs by design
because cache evidence and physical runtime evidence are recorded separately
from the unchanged business artifacts. These were `/tmp` development audits;
Production and `/data` were unchanged.

The remaining roughly 102 seconds before writing are dominated by formal
prior-Candidate reread (46.393 seconds), the independent current-session Oracle
(29.296 seconds), and score calculation (11.144 seconds). Large cumulative
JSON writing and final formal reread add further wall time outside the
pre-writer metric.

## 2026-08-27 streaming and resumable audit result

ADR 0026 retains Candidate audit schemas 1.0/1.1 and completed file bytes while
streaming canonical JSON, physical hashes, and logical hashes. Formal reread no
longer retains raw artifact bytes plus a second full canonical encoding. An
explicit recovery journal binds the exact final path and all artifact, typed-
record, source, Oracle, equivalence, and prior-audit identities. Final delivery
is an atomic work-directory rename after one formal completed-audit reread.

The final real 2026-08-26 verified-prior run used the immutable panel cache and
an explicit recovery directory. Time before writing was 111.636 seconds; the
ten artifacts streamed in 17.921 seconds. The process peak recorded in the
completed manifest was 3,343,112 KiB. The observed work-directory creation to
atomic-delivery boundary was approximately 164 seconds; the earlier
non-released streamed attempt took 366.38 seconds and peaked at 6,232,876 KiB.
The final design therefore removed roughly 46% of that measured peak and more
than halved that run's elapsed time by releasing calculation objects before
the one final formal reread and removing duplicate validation.

All nine source/business/Oracle files were byte-identical to the earlier
panel-cache audit. The additive incremental validation ledger was byte-
identical to the preceding streamed implementation. The final logical audit
fingerprint was
`0e9db80894a56c0ddd3180975a99237e84159846a1ac5ff7195978d82f887a63`,
all four equivalence gates were true, Oracle mismatch was zero, and external
request and Production-write counts were zero. These are Dell `/tmp`
development results; `/data` and Production were unchanged.

## Next performance sequence

1. Measure the next complete daily run with ADRs 0125 and 0126 active. Do not
   infer the full end-to-end saving from isolated stage replays.
2. Attribute the remaining time separately across Candidate, Strategy
   Channels, Candidate Visual Context, MI plan/Apply, and Snapshot
   source-product construction before changing another calculation or
   contract.
3. Keep the daily inner Oracle serial unless a new workload measurement proves
   deterministic process parallelism is faster.

## 2026-09-04 downstream finalized-evidence reuse

ADR 0126 extends the existing ADR 0025 panel cache and ADR 0117 finalized-
Candidate boundary; it does not create another cache or weaken formal source
validation. All measurements used the unchanged 2026-09-03 Dell inputs and
wrote development audits only under `/tmp`.

| Stage/read | Prior evidence | Optimized replay | Result |
| --- | ---: | ---: | --- |
| Phase 1a pre-write | 621.184 s | 164.447 s after ADR 0125 | same composites, raw metrics, Oracle, and logical fingerprint |
| Current Candidate batches + governed state ledger | complete reconstruction followed by duplicate history reads | 34.410 s | 2 exact current batches, 35,490 typed states, unchanged Candidate audit fingerprint |
| Entry Geometry end-to-end | roughly 19-minute uninstrumented stage interval | 49.67 s outer / 48.335 s instrumented | all 3 business artifacts byte-identical; same logical fingerprint; zero Oracle mismatch |
| ETF panel load | 148.666 s after ADR 0125 | 8.423 s | exact cache hit bound to Phase 1a input evidence |
| ETF pre-write | 154.178 s after ADR 0125 | 14.193 s | all 8 business artifacts byte-identical; same audit/history fingerprints and zero Oracle mismatch |
| ETF outer process | 155.34 s after ADR 0125 | 15.36 s | no network or Production write |

The original Entry stage did not record internal timings, so its prior value is
an audit-directory timestamp interval rather than an exact process timer. The
new CLI reports Candidate/state reread, panel load, calculation/Oracle, audit
write/reread, total elapsed, cache status, and peak RSS in its physical stdout
summary. Runtime evidence remains outside business logical fingerprints.

## 2026-09-04 bounded Strategy input result

ADR 0127 applies the existing finalized current-Candidate projection to
Strategy Channels, which consumes only the two batches for its requested
session. On the unchanged 2026-09-03 audit, the prior complete Candidate read
alone took 225.978 seconds and peaked at 8,737,108 KiB RSS while reconstructing
20 batches, 35,490 states, 18,269 raw rows, and 35,408 normalization rows.

The optimized complete Strategy process took 33.82 seconds and peaked at
2,538,356 KiB. Its current-Candidate projection took 12.588 seconds, Entry
reread 0.771 seconds, calculation plus independent Oracle 9.884 seconds, and
audit write plus reread 9.360 seconds. All four Strategy business artifacts
were byte-identical, audit logical fingerprint
`440fb9db9d1d3b09bf53a5ba5677f2461c881c45642ccc94720c107c82096e28`
was unchanged, Oracle mismatch was zero, and permutation passed.

Candidate Visual Context was measured rather than modified. It completed in
51.11 seconds: governed Candidate/state reread 34.208 seconds, exact panel
cache reread 8.719 seconds, calculation plus Oracle 4.573 seconds, and audit
write plus reread 1.178 seconds. Both business artifacts were byte-identical
to the prior audit and logical fingerprint remained unchanged. This bounded
path is not a current optimization target.

## 2026-09-04 daily Candidate finalization result

ADR 0128 separates the daily commit gate from the periodic semantic audit.
The writer still validates the full cumulative typed evidence, source and
prefix lineage, parameters, transition/equivalence gates, and independent
current-session Oracle before it prepares the completed manifest. Daily
finalization then rehashes every immutable artifact and validates exact files,
ownership, modes, sizes, manifest identity, parameters, session, Universe,
equivalence, and zero-Oracle gates before the atomic directory rename.
`periodic`, `code_change`, and the direct finalizer default retain the complete
post-write semantic reconstruction.

On unchanged 2026-09-03 inputs, the prior daily replay took 521.21 seconds and
peaked at 8,886,376 KiB. The daily-scope replay took 294.99 seconds and peaked
at 7,534,432 KiB, saving 226.22 seconds or 43.4%. The baseline recorded 95.365
seconds before audit write and 44.104 seconds for stream write; the daily-scope
run recorded comparable 94.770- and 44.095-second stages. All ten business
artifacts were byte-identical to the prior audit; logical fingerprint
`b6945f58b4766fd2e110415a7fa45816447205a61caf1085f9fe759c2d89f12f`
was unchanged and Oracle mismatch remained zero.

The bounded physical completion reader alone took 1.595 seconds and peaked at
152,816 KiB. A separate full semantic reread of the delivered fast audit then
passed in 228.285 seconds with 8,737,080 KiB peak RSS, the same logical
fingerprint, zero Oracle mismatches, and completed status. Roughly 154 seconds
of the fast process remain outside the current named calculation, stream-write,
and physical-completion measurements; that interval must be profiled before
further Candidate changes rather than attributed by inference. These were
Dell `/tmp` replays only. No `/data`, Production, scheduler, publication,
Snapshot, bundle, OCI, formula, parameter, rank, contract, or Universe changed.

A follow-up instrumented replay completed in 294.30 seconds and narrowed the
remaining cost. The complete audit writer occupied 193.525 seconds, while the
daily finalizer occupied 1.739 seconds and explicit garbage collection only
0.061 seconds. Nested inside the writer, all logical-fingerprint calls totaled
88.528 seconds, the incremental-prefix validator 45.918 seconds, external-
record normalization/sorting 17.569 seconds, and the ten artifact logical-
fingerprint wrappers 38.963 seconds. These nested counters overlap and must not
be summed as independent stages.

The prefix validator was then decomposed against the exact completed output.
Reading its source took 34.715 seconds; the already matching 18-batch prefix
used 7.387 seconds for model projection and 20.463 seconds for its aggregate
fingerprint, while the matching 31,941-state, 16,445-raw-row, and 31,873-
normalization-row fingerprints took 8.759, 5.009, and 1.225 seconds. All four
matched their bound prior evidence. The next optimization is therefore not
finalization, garbage collection, or indiscriminate multicore execution. The
remaining scaling cost is canonical projection and re-fingerprinting of a
self-contained cumulative audit. A segmented or delta custody design may
address that growth, but it requires a separate architecture decision and
must preserve byte-logical prefix proof, recovery, retention, and periodic
cold comparison rather than silently weakening those gates.

## 2026-09-04 MI and Snapshot plan attribution

The current 2026-09-03 Market Intelligence candidate plus approval-plan path
completed in 53.84 seconds and peaked at 2,563,512 KiB. Its publication build
took 20.327 seconds, approval-plan construction 15.843 seconds, and formal
input validation the remainder. The resulting MI 1.3 payload reproduced the
active logical fingerprint
`8db1d95b97bad6d34ebd3dad9a102a26907f2294bede33025fcf9b114945de74`,
the exact Candidate analytics binding, and the exact Sector Rotation product
binding. The older approximately 9-minute journal interval therefore does not
describe the current code path and is not an optimization target.

The current Snapshot 1.11 / Dashboard 2.8 candidate plus Plan 2.6 path first
measured 135.00 seconds and 994,996 KiB peak RSS. Its largest independent
inputs were the formal active Activation read at 48.782 seconds and Snapshot
product construction at 44.977 seconds. Approval-plan construction took
30.743 seconds because it fully reread the active Snapshot once for rollback
and again for the expected current-state fingerprint.

ADR 0129 binds rollback and CAS to the same formal active-state observation;
Apply retains a new current-state read. The exact replay then completed in
121.57 seconds with 994,052 KiB peak RSS, saving 13.43 seconds or 9.9%. All 42
Snapshot files totaling 43,406,568 bytes were byte-identical. The plans differed
only in their temporary candidate path and derived plan-content fingerprint;
all business, rollback, CAS, target-pointer, aggregate, and manifest bindings
matched. Both runs were `/tmp` dry runs with `production_writes=0`; `/data` and
Production did not change.

After bounded current-code measurement, the largest known daily stages are the
294.99-second cumulative Candidate path, the approximately 164-second Phase 1a
pre-write path, and the 121.57-second Snapshot path. MI (53.84 seconds), Visual
Context (51.11 seconds), Entry (49.67 seconds), Strategy (33.82 seconds), and
ETF Relationships (15.36 seconds) are bounded and are not immediate
optimization targets. A complete same-session chain measurement remains
necessary because isolated times do not capture orchestration overhead.

## 2026-09-04 segmented Candidate shadow proof

The last three V1 Candidate audits contain 674,868,781, 758,853,957, and
842,945,142 bytes, an observed increase of approximately 84 MB per Candidate
session. Extending the self-contained format to 303 Candidate sessions would
put the latest audit near 25.5 GB; retaining every cumulative daily version
would approach 3.9 TB. The more immediate problem is repeated projection,
fingerprinting, writing, and parsing, not Dell capacity.

ADR 0130 adds a default-disconnected segmented shadow. The real 2026-09-03 V1
audit converted into ten immutable session files totaling 840,642,650 bytes
plus a 17,534-byte manifest. Conversion, complete typed reread, and exact
eight-projection comparison took 548.57 seconds and 11,008,352 KiB peak RSS.
The shadow logical fingerprint is
`f2f253f14deeca3ee4d8eebb60c1ee0b1edbbaab82934cadde7b35ed71e4fc8e`;
its source is the unchanged V1 fingerprint
`b6945f58b4766fd2e110415a7fa45816447205a61caf1085f9fe759c2d89f12f`.

The first real reconstruction failed closed only on the raw-fact projection:
V1 sorts those records canonically across the entire history, so concatenating
date segments changed order. The accepted shadow records exact V1 source
ordinals and restores that order; all eight projections then matched without
using unordered or approximate equality.

The bounded current-checkpoint reader rehashes every immutable segment but
parses typed records only from the latest 86,537,118-byte segment. It completed
in 16.53 seconds with 855,712 KiB peak RSS and returned the exact two current
Candidate batches, 3,549 state rows, and six risk results. This compares with
228.285 seconds and 8,737,080 KiB for a complete V1 semantic reread. The result
justifies a later append-input prototype; it does not yet replace V1 or prove
O(current-session) calculation, write, recovery, or publication.

A separate full-V1 versus current-checkpoint comparison completed in 257.46
seconds and 8,737,524 KiB peak RSS. Source panel, current batches, 3,549 current
states, and six risks were exact. The Primary 1,718- and Secondary 1,831-row
prior support sets were also exact, including prior stage, confirmation count,
and source state-record fingerprint. Only the cumulative V1 state-history
fingerprint differed. That value does not affect component scores or the state
runtime, but it is part of the Candidate batch's logical evidence. A fast
append therefore requires an explicit versioned state-chain identity; changing
the V1 meaning in place is prohibited.

## 2026-09-04 session-discovery validation tiers

ADR 0125 extends ADR 0118's completion-index boundary to operational paths
that need only completed dates, current-session selection, freshness, or a
bounded-window presence check. It does not change `list_sessions()` itself.
Explicit descriptor APIs and research evidence builders retain the deep reader,
and every partition consumed by calculation is still fully validated.

On the unchanged 303-session Dell state:

| Read | Elapsed | Validation scope |
| --- | ---: | --- |
| Pre-change current-context report | about 443 s | all historical partitions, latest/current artifacts, whole inventory |
| Pre-change report without inventory fingerprint | 478.23 s | all historical partitions and latest/current artifacts |
| Whole `/data` inventory fingerprint alone | 3.77 s | all 3,356 files / 1.60 GB |
| Completion index plus latest EOD inspection alone | 2.14 s | all completion manifests and full latest partition |
| ADR 0125 default current-context report | 27.65 s | completion index, full latest partition, current artifacts, whole inventory |
| ADR 0125 explicit full-history report without inventory fingerprint | 478.01 s | every completed EOD partition and current artifacts |

Run-to-run cache effects make the two pre-change measurements unsuitable for
subtraction, but both show that whole-history reconstruction dominates. The
new default report was about 94% faster than the observed 443-second default
baseline. It reproduced the same EOD, Identity, Activation, Market
Intelligence, Snapshot, inventory, symlink, and residue facts. Report contract
1.2 adds `history_validation_scope`; `--full-history-validation` preserves the
old all-partition proof explicitly.

The same date-only selection rule now covers MI plan/Apply freshness, Snapshot
Apply freshness, Candidate available-session discovery, normal Market Regime
window presence, application activation selection, and latest-session return
analytics. No end-to-end saving is claimed for those stages until the next real
daily chain is measured.

## 2026-09-01 finalized-evidence reuse result

ADR 0117 separates immutable prior-audit reuse from audit creation and periodic
validation. The daily append first rehashes the exact completed manifest and
all artifacts, verifies custody and completion gates, then parses the verified
bytes once for typed append inputs. It no longer repeats canonical JSON
serialization or re-derives every finalized historical fingerprint.

On the real 2026-08-31 prior audit, the measured read fell from the manifest's
133.871-second stage to 28.18 seconds, about 79% faster. The result preserved
the exact audit logical fingerprint, 14 Candidate batches, 24,843 state rows,
12,793 raw rows and 24,795 normalization rows. A more conservative first
prototype that retained the redundant derivations took 103.22 seconds and was
rejected.

Snapshot validation now reuses each decoded, contract-validated value for its
cross-file bindings and removes the immediately redundant validation after
write. Staging and post-rename full validations, file-set checks, checksums and
all contract bindings remain. A read-only full validation of the active
Snapshot 1.11 / Dashboard 2.8 release with 32 detail shards took 5.40 seconds.
These measurements changed no `/data` or Production state.

## 2026-09-01 Snapshot completion-index result

ADR 0118 removes two full historical Parquet scans that were used only to
discover the latest completed session dates. The canonical completion index
still verifies each partition's bounded directory, completion manifest,
session/schema/status fields, symlink boundary, and required files. The chosen
current and previous partitions are then read and validated in full by the
unchanged Dashboard calculation.

On the exact same 2026-08-31 Activation, active Market Intelligence, Strategy
Channel, and Visual Context inputs, deployed source `44b052419be8` completed
Snapshot candidate plus approval-plan construction in 251.79 seconds. The
indexed path completed in 121.43 seconds, a 130.36-second or 51.8% reduction.
All business payloads were byte-identical; Market Overview also matched after
excluding its deliberately different generation/freshness timestamps.

A separately measured same-process Activation reuse prototype reached 119.65
seconds, only 1.5% beyond the indexed result. It was removed because that small
gain did not justify coupling the Activation and MI formal readers. No
Production state changed during any benchmark.

## 2026-08-27 deterministic process-parallel result

ADR 0028 adds bounded 1–8 worker execution for independent full-session
Oracles in cold periodic and code-change replay. Workers use an isolated
`forkserver`, disable network and DNS, and return results to the parent in the
original session order. The parent retains state recursion, ordering,
comparison, aggregate fingerprints, and audit custody. A daily append has one
Oracle session and therefore remains one effective worker.

For a parallel Oracle stage, the recorded process CPU field covers the
coordinating parent, not total forkserver-worker CPU. Use stage wall time,
worker/job counters, and serial-equivalence evidence for performance decisions.

On the same four-session 2026-08-26 cold replay, 4 workers reduced the Oracle
stage from 117.09 to 76.23 seconds, pre-writer time from 459.05 to 420.18
seconds, and end-to-end time from 597.70 to 560.02 seconds. All nine
business/Oracle artifacts were byte-identical, logical and Oracle fingerprints
were exact, and Oracle mismatch was zero.

A one-session inner-Oracle prototype was rejected after measurement: serial,
2-worker, and 4-worker end-to-end times were 277.81, 286.99, and 291.22 seconds
respectively. Its outputs were exact, but safe process transfer cost exceeded
the available parallel work. Daily keeps the faster serial Oracle rather than
using cores performatively.

## 2026-08-27 explicit validation-tier result

ADR 0027 makes `daily`, `periodic`, and `code_change` executable CLI gates.
Daily requires the verified-prior append. Periodic and code/model change
require a cold full replay; periodic verification formally rereads both audits
and compares eight schema-neutral business projections rather than their
intentionally different incremental/cold containers and Oracle scopes.

The real 2026-08-26 cold periodic reference completed in 597.70 seconds with
3,516,264 KiB maximum RSS and zero Oracle mismatch. Formal comparison of the
final incremental audit with that same-version cold reference completed in
197.20 seconds with 3,506,364 KiB maximum RSS; all eight business projections
matched. External-request and Production-write counts were zero. These are
Dell `/tmp` development audits; `/data` and Production were unchanged.

## 2026-08-27 verified-prior Phase 1b result

Phase 1b audit schema 1.1 formally consumes the current Phase 1a audit and the
immediately prior corrected Phase 1b audit, then appends one state/explanation
row per Universe. It validates the immediate XNYS boundary, calculation and
parameter versions, Activation, membership, and all prior prefixes, and runs
an independent state append Oracle. The daily path does not reopen `/data`.

The final V1.0.1 real-data comparison used a cold 2026-08-25 audit as the
verified prefix and compared 2026-08-26 incremental with a separate 2026-08-26
cold replay. Cumulative state history, explanations, transition ledger,
current summary, and both Universe history fingerprints matched exactly. Both
paths had zero Oracle mismatch. Time before writing was 0.237 seconds
incremental versus 302.736 seconds cold; current Phase 1a reread took 0.007
seconds, prior Phase 1b reread 0.228 seconds, and append plus Oracle 0.002
seconds. These are `/tmp` development audits, not Production publications.

## 2026-08-27 corrected stable-prefix proof

The first real incremental attempt correctly failed because the legacy Phase
1b rolling window had changed historical confirmed states. ADR 0023 corrects
that upstream boundary. Corrected 2026-08-25 and 2026-08-26 Phase 1b
development audits retained 16/16 prior state rows exactly and added only the
two current Universe rows. This real-data equivalence rehearsal occurred before
the corrected calculation and parameter identifiers were frozen as V1.0.1;
the final versioned code is covered by the complete backend regression but no
new Production-bound analytics audit was created.

Using that corrected source, a 2026-08-25 cold Candidate audit was appended to
2026-08-26. The incremental and 2026-08-26 corrected cold audit matched every
source panel, raw fact, normalization record, Candidate batch, state row,
transition row, current risk result, and all corresponding business
fingerprints. Both Oracles had zero mismatch. The cold path took 461.67 seconds
before writing; incremental took 309.02 seconds. Of the incremental time,
216.57 seconds reread the 26-session panel and 46.35 seconds formally reread
the prior Candidate audit. That comparison established the panel-reuse target;
the immutable panel cache documented above now removes the repeated canonical
source read. Streaming audit output remains necessary.
