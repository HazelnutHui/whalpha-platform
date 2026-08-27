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

Append one session from an immediately prior verified Candidate audit with:

```bash
scripts/admin/calculate-opportunity-candidates-offline.sh \
  --as-of-session YYYY-MM-DD \
  --data-root /data/trading-intelligence-platform \
  --phase1b-audit /tmp/<corrected-stable-prefix-phase1b-audit> \
  --prior-candidate-audit /tmp/<immediately-prior-candidate-audit> \
  --output-dir /tmp/<new-empty-incremental-candidate-audit>
```

The prior audit must be the preceding XNYS session and use compatible
calculation, parameter, Activation, membership, and stable-prefix Phase 1b
sources. A mismatch fails closed and requires a corrected cold replay.

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

The current manifest memory sample is taken before the audit writer. A baseline
run was separately observed near 6.3 GiB RSS during large JSON serialization,
so writer streaming and peak-memory instrumentation remain open work.

## Next performance sequence

1. Cache or content-address formally validated immutable EOD panel inputs so a
   daily Candidate run does not reread 25 unchanged partitions.
2. Separate daily, periodic, and code/model-change validation tiers without
   weakening the full reference audit.
3. Add content-addressed resumable stages with explicit input/output
   fingerprints and failure locations.
4. Process-parallelize only independent CPU work using stable `instrument_id`
   shards; merge and fingerprint in one deterministic parent order.
5. Split Candidate public summary and on-demand detail payloads. This changes
   neither guest/credential capability parity nor the Dell/OCI boundary.

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
the prior Candidate audit. The result is logically complete but not yet the
target daily latency; immutable-panel reuse and streaming audit output remain
necessary.
