# ADR 0028: Parallelize Only Independent Cold-Replay Oracle Sessions

## Status

Accepted

## Date

2026-08-27

## Context

Dell has 8 physical cores / 16 threads, while Candidate calculation remained
serial. The independent Oracle is the clearest CPU-only boundary: it does not
write data, call providers, or mutate shared model state. Not every apparent
subdivision is beneficial, however. Large typed panels and batches must cross
a safe process boundary, and process overhead can exceed the calculation saved.

## Decision

Keep scoring, state recursion, risk ranking, ordering, comparison, aggregate
fingerprinting, and audit writing in the deterministic parent process. Add an
explicit bounded `--max-workers` value from 1 through 8, defaulting to 4 on the
Dell runner.

For cold periodic and code/model-change replay, construct one complete Oracle
job per ordered Candidate session after all serial score/state dependencies are
available. Run those mutually independent session jobs in an isolated Python
`forkserver` process pool. Each worker disables network sockets and DNS; only
local Unix process-control IPC is allowed. The parent consumes results in the
original session order and performs the unchanged `_combine_oracles` operation,
so output ordering and fingerprints are independent of worker completion order.
Worker exceptions propagate and fail the run; there is no silent serial
fallback.

The daily verified-prior append has exactly one new-session Oracle, so its
effective worker count remains 1 even when 4 is requested. A tested prototype
that split one daily Oracle into Universe and permutation jobs was rejected:
safe process startup and large-input transfer made it slower than serial.

Runtime evidence records requested workers, effective workers, and session-job
count. These are physical fields excluded from logical fingerprints. The
serial `max_workers=1` path remains the reference.

## Evidence

On the same 2026-08-26 four-session cold replay, 4 session workers reduced the
Oracle stage from 117.09 to 76.23 seconds and pre-writer time from 459.05 to
420.18 seconds. End-to-end elapsed time fell from 597.70 to 560.02 seconds.
All nine business/Oracle artifacts were byte-identical; aggregate logical and
Oracle fingerprints were identical and Oracle mismatch was zero.

The rejected daily prototypes were also byte-identical but slower: 1 worker
took 277.81 seconds end to end, 2 workers 286.99 seconds, and 4 workers 291.22
seconds. Daily therefore remains one effective worker.

## Consequences

- Heavy cold validation uses multiple Dell cores with exact serial equivalence.
- Daily latency is not made worse merely to claim multicore usage.
- Safe process isolation adds serialization cost, so future parallel stages
  require their own measured serial/parallel comparison.
- This does not parallelize provider requests, data publication, state
  recursion, final ordering, or audit custody.
- Production, `/data`, OCI, scheduler, and model formulas remain unchanged.

## Alternatives Considered

### Fork the already multithreaded parent

Rejected because Python warns that direct `fork` from a multithreaded process
may deadlock. The isolated `forkserver` boundary is mandatory.

### Split the daily Oracle by Universe

Rejected by real measurement because large-input process transfer outweighed
the two-Universe CPU benefit.

### Parallelize state recursion or parent merge

Rejected because those boundaries carry chronological or canonical-order
semantics and provide less independent work than session-level cold Oracles.
