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

Phase 1a and the daily Candidate append may share an explicit Dell-local panel
cache:

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

1. Measure the next complete daily run with ADR 0125 active. Do not infer the
   full end-to-end saving from the isolated control-path benchmark below.
2. Attribute the remaining time separately across Phase 1a, Candidate, Entry
   Geometry, ETF Relationships, MI plan/Apply, and Snapshot source-product
   construction before changing another calculation or contract.
3. Keep the daily inner Oracle serial unless a new workload measurement proves
   deterministic process parallelism is faster.

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
