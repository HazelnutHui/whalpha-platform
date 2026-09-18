# ADR 0314: Rotate Codex Tasks at Verified Project Checkpoints

## Status

Accepted

## Date

2026-09-18

## Context

The project is long-lived, multi-market, and evidence-heavy. A single Codex
task can be compacted repeatedly as its conversation grows. Conversation
history is useful for collaboration, but it is not a durable source of truth
for code, data custody, research authority, running processes, Git state, or
Production state. Copying the full chat into the repository would preserve
noise, duplicate superseded direction, and risk retaining sensitive material.

The repository already has the correct durable layers: `AGENTS.md`, compact
current context/status/work controls, ADRs, contracts, operations, audits, and
the changelog. Those layers need an explicit task-rotation procedure.

## Decision

1. Rotate to a fresh Codex task after a material, independently verified
   checkpoint rather than using one task indefinitely or rotating during an
   unrecorded background run.
2. Conversation memory is never authoritative. Confirmed rules live in
   `AGENTS.md`; current facts live in the three current project documents;
   durable decisions live in ADRs; execution evidence lives in immutable data
   packages and dated audits.
3. Do not preserve full chat transcripts in Git. Extract only confirmed,
   non-secret decisions or unresolved questions and route them to the proper
   authoritative document.
4. Before rotation, reconcile Git, owner-only data packages, active processes,
   current documents, website release identity, deployment state, and the next
   bounded gate. A running process must either finish or have its exact owner,
   command, checkpoint, restart semantics, and stop conditions recorded.
5. The new task begins read-only. It reads the required recovery chain, verifies
   the actual repository and workstation state, and reports discrepancies
   before any mutation, network acquisition, publication, deployment, or push.
6. A task switch alone never mutates workstation data, the public website, or
   GitHub. Those systems change only through their existing explicit,
   independently verified workflows.
7. Public Git remains code/document/test custody only. Credentials, raw private
   evidence, large workstation data, private keys, Session material, and local
   runtime state remain excluded and are checked before push.

## Consequences

The current task should rotate only after the 2026-09-18 U.S. source-engineering
and A-share warning-acquisition results are integrated, tested, committed, and
deployed or explicitly recorded as not deployed. The next task must perform the
read-only checklist in the linked operation before continuing either market.

This approach intentionally keeps `current-context.md` compact. Dated execution
detail stays in audits and immutable packages rather than accumulating in the
default recovery path.

The operational checklist is
[Codex Task Rotation and Recovery](../operations/codex-task-rotation-and-recovery.md).
