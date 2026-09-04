# Historical Identity Source Apply V1

## Purpose

This boundary publishes one explicitly approved
`historical-identity-source-apply-plan/1.0` into immutable canonical source
partitions. It adds no new business facts: every target byte is already bound
by the plan.

## Inputs

- exact plan path and whole-file SHA-256;
- exact plan logical fingerprint;
- exact expected whole-`/data` pre-state fingerprint;
- approved Dell data root; and
- explicit ordinary Apply or `verify_then_complete` recovery mode.

The operation refuses unpinned or changed plans, changed candidate bytes,
wrong operation/provider/counts, non-Dell roots, symlinks, and unexpected path
shapes.

## Publication and recovery

Each session directory is staged beside its target, contains exactly
`manifest.json` and `part-00000.parquet`, uses canonical read-only file modes,
and becomes visible through one atomic rename. Existing targets are never
replaced.

Ordinary Apply requires all targets absent and exact equality with the planned
canonical pre-state. Recovery allows a mix of exact completed and absent
targets, requires the inventory outside all planned targets to remain equal to
that same pre-state, skips completed partitions, and publishes only the absent
ones. Partial, changed, symlinked, writable, or extra-file targets block.

After publication, every canonical partition is formally parsed and
reconciled with its plan session. Completion reports the number reused and
published, bytes published, and the post-state inventory fingerprint.

## Non-authority

The executor cannot fetch data, modify the candidate, overwrite or delete
canonical partitions, create membership, publish Historical Coverage, run
research, change Production, deploy, or enable scheduling. Repository and
`/tmp` proof do not themselves authorize the real `/data` invocation.
