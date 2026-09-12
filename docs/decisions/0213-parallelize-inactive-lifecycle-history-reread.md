# ADR 0213: Parallelize Inactive-Lifecycle History Reread

- Status: Accepted
- Date: 2026-09-12

## Context

The first inactive-lifecycle resolution shadow formally reread 303 canonical
Instrument snapshots serially and took roughly seven minutes. Re-resolving the
same retained inactive source against the completed five-year Identity history
requires about four times as many snapshots. Repeating the serial design would
delay a bounded evidence census without improving its semantics.

A naive per-session process design would transfer more than ten million raw
rows back to the parent and create avoidable memory pressure. Linux `fork`
from the existing multithreaded Python environment also carries a deadlock
risk.

## Decision

Read the canonical Instrument history in at most eight default and 32 maximum
spawned worker processes. Partition the ordered session list into deterministic
contiguous blocks. Each worker formally inspects every assigned snapshot and
returns only:

- its ordered manifest inventory bindings;
- the total Instrument row count; and
- one aggregate first date, last date, and ticker set per stable
  `instrument_id`.

The parent merges blocks in deterministic order, verifies the complete session
sequence, and computes the unchanged canonical-history fingerprint from the
same ordered inventory fields as the serial implementation. Worker count is an
operational input only and cannot affect the shadow contract or fingerprint.
The CLI exposes an explicit bounded worker option.

Use the `spawn` multiprocessing context so workers do not inherit incidental
threads or mutable parent runtime state. Any worker, merge, coverage, type,
hash, or formal snapshot failure stops the complete shadow before publication.

This decision changes only disconnected shadow construction. It does not write
canonical data, acquire new provider data, promote lifecycle facts, create
Historical Coverage, authorize research, or change Production.

## Consequences

- Raw cross-section rows are reduced inside each worker rather than copied in
  full between processes.
- Tests prove exact serial/parallel `_CanonicalHistory` equality and reject
  zero, boolean, and above-limit worker counts.
- The existing one-to-one observation, quarantine, and lifecycle limitation
  semantics remain unchanged.
