# Historical Identity Source Apply and Recovery Audit — 2026-09-04

## Result

ADR 0139's canonical writer, formal reader, recovery path, and explicit CLI
are implemented and proven against disposable `/tmp` canonical roots. The
proof covers both a clean ordinary Apply and a process interruption after one
partition has become atomically visible.

The real 279-session plan was not invoked. No file was written to `/data`, no
canonical historical Identity source partition exists, and research readiness
did not change.

Subsequent same-day status: after this implementation-only proof was committed,
the exact plan was separately directed, applied, and independently reread. See
the [canonical Apply audit](historical-identity-source-canonical-apply-2026-09-04.md).
The statements above remain the historical boundary of this earlier proof.

## Exact real plan retained for separate review

| Binding | Value |
| --- | --- |
| Plan path | `/tmp/whalpha-historical-identity-source-apply-plan-20260904.json` |
| Plan SHA-256 | `97e22c62bc8554f1229a41925970a365d189a5ad05bbf802e984fc9f3885c1a0` |
| Logical fingerprint | `6310b845d83ead27e949d66bae158c021be010ccd7565b724f55e5a20d20f87d` |
| Expected `/data` pre-state | `2928d804ea48cf076b0a589d09b0e150cf07810dc4dd0cef503121d53d95d794` |
| Sessions / files / bytes | 279 / 558 / 258,394,518 |
| Plan status | `ready_for_separate_review` |
| Plan self-authorization | false |

These facts identify a prospective action; they do not authorize or prove its
execution.

After the implementation commit, the new reader revalidated that real plan,
all 558 candidate artifacts, all 279 absent targets, and the exact current
pre-state in 4.76 seconds at 122% CPU with 153,408 KiB peak RSS. It again
returned `ready_for_separate_review` and `apply_authorized=false`.

## Implemented boundary

- The executor requires the exact plan path, file SHA-256, logical
  fingerprint, expected pre-state fingerprint, and approved Dell root.
- It rereads and rehashes the complete plan and source candidate before and
  after acquiring the shared daily-publication lock.
- It prohibits network access during publication.
- Each session is copied into a same-parent staging directory, assigned
  canonical `0755`/`0644` modes, fsynced, rehashed, and made visible by one
  atomic directory rename.
- Existing targets are never overwritten, merged, or deleted.
- Ordinary mode requires every target absent and the complete inventory equal
  to the plan pre-state.
- `verify_then_complete` accepts only an exact complete target or an absent
  target. It excludes only the planned target partitions from the base
  inventory comparison, reuses exact completed partitions, and writes only
  absent ones.
- Every target is parsed through the canonical typed reader and reconciled to
  the plan before success is returned. Formal reread supports one to four
  local processes.

## Disposable-root fault proof

The tests generated real typed Parquet candidates and plans below `/tmp`, then
verified:

1. clean ordinary publication, target modes, hashes, source preservation, and
   canonical typed reread;
2. CLI enforcement and reporting of the exact execution binding;
3. rejection of unrelated pre-state inventory drift before any target write;
4. an injected failure immediately after an atomic partition rename;
5. recovery that reuses that exact completed partition and publishes the next
   absent partition;
6. refusal to treat an existing target as an ordinary replay;
7. rejection and preservation of a partial target; and
8. rejection and preservation of staging residue.

The focused historical-Identity suite passed 32 tests. The complete backend
suite passed 2,041 tests with the same two pre-existing dependency warnings.

## Explicit non-authority

This stage does not authorize the real Apply, cleanup, rollback, source-gap
acquisition, Universe Membership publication, Historical Coverage,
strategy-performance claims, scheduler changes, Production publication, or
OCI deployment. A real invocation must first revalidate the pinned plan and
current `/data` pre-state; any mismatch requires a new plan rather than an
override.
