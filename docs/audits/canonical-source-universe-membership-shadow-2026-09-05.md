# Canonical-Source Universe Membership Shadow Audit — 2026-09-05

## Scope

This audit replaces temporary retained packages as the normal input to the
historical Universe Membership shadow. It uses the 301 canonical normalized
Identity source-observation partitions on the Dell workstation and preserves
the retained-package path only for compatibility comparison.

All Membership outputs are below `/tmp`. No provider request, credential read,
`/data` write, active-pointer change, Historical Coverage publication,
Production build, OCI deployment, or scheduler change occurred.

## Implementation and regression evidence

ADR 0144 introduces methodology
`provider-form-complete-base-point-in-time-v3`. Each session formally rereads
the normalized source manifest and Parquet, rebuilds all three accepted
Identity families under the manifest-bound profile, and includes the canonical
source custody fingerprint in downstream lineage. The existing complete-base
decision implementation is shared with V2.

The implementation is bound to clean-main commit
`af415a44389c319d0ce7ab189c3a9bd8713dd0ab`. All 2,066 backend tests passed;
the only warnings were the two existing third-party deprecation notices.

For 2026-09-03, V2 and V3 each produced 19,958 Membership rows over 9,979
stable IDs. After excluding only methodology version, source-lineage set, and
execution timestamp, every row matched on Universe, instrument, session,
origin, disposition, membership state, reason codes, evaluated-base
fingerprint, source cutoff, and quality status.

## Measured runtime correction

The initial V3 single-session run took about 100 seconds. Profiling found that
PyArrow repeatedly searched for the unavailable optional `pytz` module while
converting UTC values: one 9,956-row EOD partition produced 49,826 failed import
requests, and a full 21-partition run produced about 1.35 million searches.

After declaring and installing the bounded runtime dependency, the same single
session completed in 59.53 seconds with a 1,144,680 KiB peak. Its logical
fingerprint and Parquet SHA-256 remained exactly
`6b90fb6d7e220d33b66dbacfe6d3c7860d487f81803e2b7c0ac9b59ddaab40e4`
and
`5136bec3fb2dfe946d33956fcb48bd0e5c294f651e45a922c56c21dd32140f95`.
The five-session boundary completed in 135.53 seconds with a 1,373,124 KiB
peak, versus the prior V2 boundary's 195.04 seconds.

## All-session source preflight

A network-disabled four-process preflight evaluated all 303 canonical EOD
sessions before broad Membership work:

| Result | Sessions |
| --- | ---: |
| Eligible canonical source and evidence gates | 300 |
| Canonical normalized source absent | 2 |
| Non-localizable evidence gate failed | 1 |

The absent dates are exactly 2026-08-13 and 2026-08-19. Their later provider
packages remain non-equivalent to the accepted same-day Identity and were not
silently substituted.

The only evidence-gate failure is 2026-08-31. Its normalized source exactly
rebuilds accepted Identity, but 10 stable-identifier collisions leave 9,957 of
9,967 join-eligible observations mapped. The resulting linkage ratio is
0.998996689074, below the unchanged 0.999 whole-session gate. The batch now
reports `identity_join_ratio_below_gate` rather than a generic failure. This
audit does not lower the gate.

## Full disconnected shadow

The 300 eligible sessions were split into 62 adjacent batches of at most five
sessions. Four Dell-local worker processes used independent batch roots and a
shared formally read type catalog. The run started at
2026-09-05T07:15:09.920773Z and the calculation plus subsequent physical audit
completed within 36 minutes 52 seconds.

| Evidence | Value |
| --- | --- |
| Completed / failed sessions | 300 / 0 |
| Membership decision rows | 5,571,154 |
| Published temporary partitions | 300 |
| Aggregate batch fingerprint | `f53c8aaa555faec258382275b68eb781fb65637536cf5a88b0e644d24fb86f74` |
| Output root | `/tmp/whalpha-canonical-membership-full-shadow-af415a4` |
| External requests / canonical writes | 0 / 0 |

The physical census found 300 manifests and 300 Parquet files totaling
129,736,636 bytes. Dates are unique and span 2025-06-23 through 2026-09-03;
none of the three blocked sessions is present. Inventory fingerprint is
`8afa4e188d006e5ac732447d0ca1042b6797b2af51bd3a3547a87a5167e886cf`.
The owner-only root is mode 0700; internal repository paths retain the project
defaults behind that boundary. Symlink and staging/partial residue counts are
zero.

Formal sample rereads passed for the first and last dates, the 2025-09-09/10
profile boundary, both sides of the two absent-source dates, 2026-08-28,
2026-09-01, and 2026-09-03. Repeating the first five-session batch with the
same evaluation timestamp returned five `already_present` results with the
same logical and physical fingerprints.

## Remaining boundary

This completes the disconnected mechanics shadow for every currently eligible
session; it does not complete canonical daily Membership. Sampled records all
correctly report a source cutoff after their represented session. The source
layer is therefore retrospective outcome-reconciliation evidence, not proof of
what was knowable at the historical decision time.

Research readiness remains `data_blocked`. Before any canonical Membership or
Historical Coverage publication, a separate decision must address:

- the two exact source gaps without projecting present facts backward;
- the 2026-08-31 linkage-gate result without changing a threshold to fit one
  observed date;
- historical knowledge-time and revision semantics;
- lifecycle, corporate actions, adjustments, costs, chronological evaluation,
  and sealed holdout evidence.
