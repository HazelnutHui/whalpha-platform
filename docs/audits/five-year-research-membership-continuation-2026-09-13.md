# Five-Year Research Membership Continuation — 2026-09-13

## Result

The rolling five-year reconstructed Universe Membership family now retains
1,213 research-only sessions. Together with the three physically separate
signal-eligible sessions, formal coverage is 1,216 / 1,255 XNYS sessions from
2021-09-13 through 2026-09-11, with 20,701,026 decisions.

This is a coverage and missingness milestone, not a point-in-time or
performance-ready Membership result. The research family remains
`reconstructed_latest_vintage`, `not_as_operated`, and unavailable to signals,
validation, holdout, performance, Candidate, Production, or web publication.

## Frozen plan and execution

The immutable continuation plan was bound to:

- implementation revision:
  `187c42549e0d0796158453d874e424fb9dfad8c5`;
- evaluated time: `2026-09-13T09:30:00Z`;
- provider catalog date: 2026-08-14;
- target: 1,255 sessions, 2021-09-13 through 2026-09-11;
- initial Membership: 300 research-only plus three signal-eligible sessions;
- intended continuation: 950 source-available sessions in 192 adjacent
  batches of no more than five;
- target-session fingerprint:
  `5cce850e36bc506ddcacbba0213ab07451f0979e4504c5302cdf23e2f403826f`;
  and
- plan logical fingerprint:
  `79a0339f0244f9494c1f2a366472c20bc0e1547ba3ecb9a87066c10b1d55a59b`.

A three-session pilot passed before the full four-process candidate build.
Under the unchanged evidence-quality policy, 913 sessions completed and 37
were rejected by `identity_join_ratio_below_gate`. The completed 913-session
candidate contained 15,069,980 decisions.

The research archive then applied all 913 completed sessions and formally
reread every Parquet row. Archive result:

| Measure | Result |
| --- | ---: |
| Candidate / applied sessions | 913 / 913 |
| New decisions | 15,069,980 |
| Reused / failed sessions | 0 / 0 |
| Overwritten / deleted partitions | 0 / 0 |
| External requests | 0 |
| Performance / Production authorization | false / false |

The archive used the governed workspace
`historical-backfill/five-year-2021-09-09--2026-09-09` and the frozen creation
time `2026-09-13T11:52:00Z`. Completion was observed before
`2026-09-13T12:23:34Z`; no exact monotonic archive duration was retained.

## Explicit missing sessions and quality evidence

Two target sessions have no retained Identity source observation and were
never candidates: 2026-08-13 and 2026-08-19.

The other 37 missing sessions are:

```text
2022-08-01  2022-10-31  2023-06-07  2023-08-28  2024-03-04
2024-10-02  2024-12-04  2024-12-05  2024-12-06  2024-12-09
2024-12-10  2024-12-11  2024-12-12  2024-12-13  2024-12-16
2024-12-17  2024-12-18  2024-12-19  2024-12-20  2024-12-23
2024-12-24  2024-12-26  2024-12-27  2024-12-30  2024-12-31
2025-01-02  2025-01-03  2025-01-06  2025-01-07  2025-01-08
2025-01-10  2025-01-13  2025-01-14  2025-01-15  2025-01-16
2025-01-21  2025-01-22
```

An outcome-free, four-process read-only census of the then-missing 139
source-available sessions found:

- 64 sessions with no evidence failure;
- 38 sessions with only `stable_identifier_collision_nonzero`, which is
  explicitly localizable and whose join ratio still passed;
- 37 sessions with both `stable_identifier_collision_nonzero` and
  `identity_join_ratio_below_gate`;
- 102 join-gate passes and 37 rejections;
- zero ambiguous rows and 264 malformed rows across the rejected sessions;
- collision counts from 10 through 66; and
- linkage ratios from 0.9922589725545391 through 0.9988058275614998.

The quality-census row fingerprint is
`04bcfb58ed84f9eadc162ebf38d695a95378179b82de0b264b9540948f6025aa`.
This evidence does not authorize lowering the 0.999 gate. It identified the
bounded question resolved later by ADR 0227: a research-only complete
cross-section may retain a session only when the entire ratio shortfall is
proven collision-derived and every collision is classified as involving a
quarantined canonical candidate or as confined to noncanonical Identity
references. Signal-eligible Membership and Production are outside that rule.

## Interruption and recovery

The first full candidate run was stopped after contiguous evidence failures
made the quality pattern clear. Only the known parent and four exact worker
processes were terminated. One incomplete staging directory for 2025-01-31
was inspected, contained only the expected manifest and Parquet artifacts,
and was removed by an exact-path depth-first delete after the execution
environment rejected direct recursive removal. No unrelated process or valid
completed partition was touched. The unchanged-plan continuation then
completed normally.

## Independent verification

Postflight found exactly 1,213 research partitions, zero staging/partial
directories, zero symlinks, and zero residual archive processes. The fresh
five-year census returned:

- Membership: 1,216 / 1,255 sessions, 39 missing, 20,701,026 decisions;
- quarantined Membership decisions: 840,791;
- census logical fingerprint:
  `71c78262c0e3be33c7f1ba3676ffb35f5301002f846728b0b9f0b45af564a89c`;
- status: `quarantined`; and
- performance claims authorized: false.

The credential-free, network-disabled current-context report subsequently
verified 20,914 canonical files / 7,382,699,983 bytes, zero symlinks, and
inventory fingerprint
`b7e0789db07fcb69165723fa6b537ba70379ec836085c8f934ce1812fbeb5f9c`.

The five-year database remains `data_blocked`: reconstructed Membership is
not historical as-operated evidence, and lifecycle/terminal outcomes,
complete action/adjustment semantics, calibrated costs, and final Historical
Coverage remain unresolved.
