# Candidate Continuation Facts Formal Audit — 2026-08-28

## Result

`COMPLETED_SHADOW_ONLY`

The descriptive Continuation Facts stage is now formally reproducible from the
completed 2026-08-26 Dell audit chain. It remains research evidence only and is
not a Strategy Preview, Snapshot, Dashboard, or Production input.

## Formal output

| Field | Verified value |
| --- | --- |
| Output | `/tmp/whalpha-candidate-continuation-facts-20260826` |
| Audit contract | `candidate-continuation-facts-audit/1.0` |
| Audit logical fingerprint | `3e1226c676f19d95876c8bda96a4739ec551d4be83cfe83cbc1854cf5fafe976` |
| Primary fact-batch fingerprint | `4e4bba5af663a7b5d1306cdb1663f676f4f5f2087a843a9f66fef15fac2e30cb` |
| Secondary fact-batch fingerprint | `94a411fdb576417f1cd2b73376d2456434490b4589bfdcc71f1722fbce861990` |
| Assessed / unavailable | 3,543 / 0 |
| Oracle mismatch | 0 |
| Input permutation | exact match |
| Network / Production writes | 0 / 0 |
| Filesystem custody | directory `0700`; four files `0400`; no partial residue |

The formal reader revalidated the completed output independently after the
write. A second calculation path produced the same audit and fact-batch logical
fingerprints.

## Runtime evidence

| Stage | Before bounded-read optimization | After optimization |
| --- | ---: | ---: |
| Current Candidate projection | 16.48 s | 7.16 s |
| Entry Geometry reread | 1.01 s | 1.00 s |
| Panel-cache reread | 8.90 s | 8.83 s |
| Facts plus independent Oracle | 6.69 s | 6.65 s |
| Audit write plus formal reread | 0.52 s | 0.52 s |
| Total | 33.59 s | 24.15 s |

The total improved by about 28%. The optimization removed a duplicate
canonical re-encoding of the already hash-verified 196 MB Candidate history;
it did not weaken selected-row typed validation or source lineage.

## Decision from the profile

Do not change the Candidate main-audit schema merely to save the remaining
seven-second current projection. The panel read is now the largest stage, and
facts plus an entirely independent recomputation are intentionally substantive
work. Keep measuring real daily executions and introduce a current-batch shard
only if repeated end-to-end evidence justifies the upstream compatibility cost.

The slower first output generated during measurement was moved to the system
trash. The optimized, formally reread output retains the canonical path above
and can be recovered independently from its immutable source audits.
