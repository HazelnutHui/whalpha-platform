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

1. Add an incremental path that binds a verified prior Candidate audit and
   calculates only the new session while preserving a cold full-replay mode.
2. Separate daily, periodic, and code/model-change validation tiers without
   weakening the full reference audit.
3. Add content-addressed resumable stages with explicit input/output
   fingerprints and failure locations.
4. Process-parallelize only independent CPU work using stable `instrument_id`
   shards; merge and fingerprint in one deterministic parent order.
5. Split Candidate public summary and on-demand detail payloads. This changes
   neither guest/credential capability parity nor the Dell/OCI boundary.
