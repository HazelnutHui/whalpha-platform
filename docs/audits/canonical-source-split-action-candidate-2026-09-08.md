# 2026-09-08 Canonical-Source Split Action Candidate Audit

## Scope

This audit records the first real ADR 0175 candidate built on Dell from the
formal ADR 0174 source publication. The operation was network-prohibited and
wrote only one owner-only `/tmp` artifact. It did not publish canonical data,
run analytics, build a Snapshot or bundle, deploy, or change the scheduler.

## Exact lineage

| Evidence | Value |
| --- | --- |
| Clean implementation revision | `c46cc3f4ee883ed7ef4c850ca146b6e3807f87bb` |
| Source publication fingerprint | `7b13691e22b7e815a773ed1d575ed580bbee897eb0dbf10c41e4e0862a95b1d1` |
| Source range / basis | 2025-06-23 through 2026-09-04 / 2026-09-04 |
| Candidate logical fingerprint | `026e9087ad4ef7ec891036cbe84ee4b3bde47cb1b1349fa858fc2e090b74f132` |
| Candidate file SHA-256 | `8ef0f95dce94a041be7e5c18d69bb959ae037e52e6f22d41c2401ab92f160c83` |
| Candidate file size | 602,491 bytes |
| Custody | directory `0700`; file `0400` |

The artifact is below
`/tmp/whalpha-canonical-split-action-candidate-20260908T224456Z` and passed a
separate formal reread.

## Reconciliation

| Measure | Result |
| --- | ---: |
| Split-like source observations | 1,949 |
| Resolved active source observations | 709 |
| Quarantined source observations | 1,240 |
| Stable-ID/effective-date event groups | 708 |
| Single-action clear candidates | 707 |
| Multiple-action quarantined groups | 1 |
| Possible-impact stable IDs from unresolved tickers | 43 |

After removing only the new ledger-admission field, the ordered event payload
hash exactly matched the ADR 0172 temporary candidate. The ordered unresolved-
impact payload hash also matched exactly. Therefore the lineage change did not
alter event math, stable-ID resolution, or quarantine membership.

The one quarantined event group is the TTSH 2025-12-16 reciprocal `1:3000` and
`3000:1` pair. Its diagnostic composed factor is one, but it is not treated as
a clear event or a proved neutral adjustment.

## Postflight

The network-free current-context report passed at contract 1.7 on clean main.
`/data` remained 4,200 files / 2,151,480,413 bytes with fingerprint
`f3117ceaab4ea25ea60c23886d171373ae15dfcee30cff6ac784af02b7e1670b`,
zero symlinks, and zero publication residue. Canonical Corporate Actions and
the Adjustment Ledger remain absent; formal research status remains
`data_blocked` and performance claims remain unauthorized.

## Next boundary

The next phase may design an exact canonical split-action Plan/Apply around the
707 clear candidates while retaining the one multiple-event group and 43
possible-impact stable IDs as explicit quarantine evidence. It must not infer
neutral factors for instruments without an event. A bounded ledger projection
follows canonical split actions and applies only to an exact admitted EOD panel
and basis.
