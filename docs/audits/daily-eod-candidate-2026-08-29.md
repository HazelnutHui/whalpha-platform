# 2026-08-27 Daily Candidate — 2026-08-29

## Scope

The one-transition coordinator executed only the Dell-local
`calculate_candidate_daily` action for 2026-08-27. It consumed the corrected
current Phase 1b audit, the immediately preceding verified-prior Candidate
audit, and the immutable Phase 1a panel cache. It wrote only a new audit below
`/tmp`. It made no external request or Production write and did not run Entry
Geometry, publication, Snapshot, bundle, deployment, notification, or
scheduler work.

## Exact inputs and custody

- pre-plan fingerprint:
  `1d1440d1be6a66969a29e511a8eb94b722e0ca3a818990ffdaf5045ea46cb3f7`
- Phase 1b fingerprint:
  `6a3a530280dbe9eea6617d76e980ed453b47e087d9e35fe588e8f7b6fe630801`
- prior Candidate fingerprint:
  `0e9db80894a56c0ddd3180975a99237e84159846a1ac5ff7195978d82f887a63`
- panel-cache status / fingerprint: hit /
  `6ada4d2830d7e7ac0b52f5860769863e02a56a01198f262897345434ba0f0e23`
- output: `/tmp/whalpha-candidate-phase5c-20260827`
- audit fingerprint:
  `0fa85ae742ef47e7278c444c12f05f2082e38a5071068a5787655a11271eb4e4`
- manifest SHA-256:
  `3a6dfb21f7e9c7597c2249f149e22c3151f91d9d5a83c70b610cc650444069af`

The audit is `verified_prior_incremental`, completed, and publication-custody
reread passes. The daily validation ledger confirms exact Candidate and state
prefixes, compatible Phase 1b, unchanged Activation and membership, formally
validated current panel, input permutation, restart, and future-prefix
equivalence. The independent current-session Oracle has zero mismatch.

## Current-session result

The current score batches contain 1,714 Primary and 1,827 Secondary comparable
securities. The complete state ledger retains all 1,718 / 1,831 active members;
four in each Universe are unavailable. Seventeen records in each Universe are
marked anomaly or quarantine.

| Universe | Watch | Prepare | Enter | Invalidated | No stage |
| --- | ---: | ---: | ---: | ---: | ---: |
| Primary | 1,082 | 365 | 106 | 76 | 89 |
| Secondary | 1,156 | 390 | 111 | 86 | 88 |

Risk-mode ranking remains bounded by the fixed contract:

| Universe | Conservative | Balanced | Aggressive |
| --- | ---: | ---: | ---: |
| Primary | 25 / 1,714 | 50 / 1,714 | 100 / 1,714 |
| Secondary | 25 / 1,827 | 50 / 1,827 | 100 / 1,827 |

These are deterministic research states and within-mode review lists, not
validated returns, automatic trade instructions, or option-return claims.

## Performance finding

The business increment reused four Candidate sessions and calculated one new
session across two Universe batches. Its measured stages were:

- prior Candidate full audit read/validate: 89.223149 seconds;
- current panel cache load/validate: 9.465801 seconds;
- Candidate incremental calculation: 63.697092 seconds;
- independent current-session Oracle: 35.060944 seconds, included within the
  incremental calculation;
- total before audit write: 152.944168 seconds;
- streamed audit write: 22.201208 seconds;
- journaled action from `action_started` to `action_succeeded`: 576.027031
  seconds.

The eleven-file cumulative audit is 422,786,554 bytes. Its largest files are
Candidate score history (245,333,199 bytes), state history (73,091,084 bytes),
and raw facts (69,306,390 bytes). The audit manifest records peak memory
4,063,784 KiB; read-only process observation during the later post-plan full
reread reached about 6.1 GB RSS.

The coordinator path also performs full formal planning before the executor,
the executor repeats the plan under its lock, Candidate calculation formally
rereads its prior append input, audit finalization rereads its output, and the
postcondition plan rereads the new output. These checks are safe but their
current evidence level is unnecessarily repetitive for planner/postcondition
roles. The separate publication-evidence custody reader rehashed this completed
audit in 1.8 seconds and passed all gates without rebuilding historical typed
rows. The next engineering slice should remove redundant full business-row
reconstruction while retaining one full append-input validation, exact hashes,
typed current-session validation, locked plan identity, and fail-closed
postconditions. It must not weaken Candidate calculation or Oracle semantics.

## Postflight

Journal event 19 is `action_succeeded`, fingerprint
`24b0f9bdbda5e3a131d57bfa9b1a87093feb67d8a182d8e898f67cfa1a0da545`.
No unresolved action remains. The post-plan fingerprint is
`eb19d7790605fae6d2467f6996b9411fb5fc6653f28f27b6e60c9fdd6b41811f`
and its sole next operational action is `calculate_entry_geometry`.

The `/data` boundary remains exactly 392 files / 203,931,663 bytes at inventory
fingerprint
`ddbe1ab03d5b945e9c3e2be975218c830f10e1ca615571e9616e131c847c7749`,
with zero symlink, staging, or partial residue. The resumable work directory
was atomically finalized and is absent. The related Candidate/planner/executor/
coordinator suite passed all 135 tests.
