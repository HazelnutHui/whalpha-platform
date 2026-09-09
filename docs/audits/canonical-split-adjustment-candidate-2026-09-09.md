# 2026-09-09 Canonical Split Adjustment Candidate Audit

## Result

The clean-revision Dell build completed the ADR 0177 sparse, affected-path
candidate. It did not write canonical data, contact an external service, or
change analytics, Snapshot, bundle, scheduler, or Production state.

The candidate is bound to source revision
`0c57560d44489c4170675cee086527d25e6daef4`, canonical split-action
publication `76f017a1547e20b997e40cd1e61497b71c749a94e88a8632a3898fe84c106218`,
and EOD family evidence
`923f27a8fa4e85c6d20b5c8ac0804f17dbab7437b350f02d54fea2ed5293aeb1`.
Its explicit basis is 2026-09-04.

## Candidate evidence

| Field | Verified value |
| --- | --- |
| Candidate root | `/tmp/whalpha-canonical-split-adjustment-candidate-20260909T000848Z` |
| Candidate manifest SHA-256 | `4ebd9d705bb2dd7d08e6aede968dfb50a26f955efb56e187dbca674835429ef4` |
| Publication fingerprint | `7e08b8a8ee364cf215c1459645f76240368b50cc3d2cb4bc77db86d3ca7c3c2a` |
| Row logical fingerprint | `ac8d42893d19bb0c84ce159eb0cf1dcdbb69c60271b0212179f497ba61df318a` |
| Parquet SHA-256 / bytes | `945c3b71bd71b5043ac38be3af647c60faabc116ddd8dc3d8303e827c2592e63` / 77,637 |
| Selected stable IDs / EOD rows | 622 / 175,033 |
| Sparse rows | 101,321 |
| Clear rows / stable IDs | 98,291 / 575 |
| Quarantined rows / stable IDs | 3,030 / 31 |
| Candidate custody | directory `0700`; both files `0400`; exact two-file inventory |

All 622 selected stable IDs had canonical EOD observations. Clear rows contain
140 distinct price factors. The observed range is 0.04 through 62,500 and the
maximum price/volume reciprocal-product error is
`0.000000000000011096`, far inside the established
`0.0000005` reconciliation tolerance. This is fixed-scale Decimal rounding,
not binary floating-point math.

The 285 clear rows with a net factor of one are not neutral placeholders. They
belong to three stable IDs whose crossed canonical action paths contain an
earlier split and a later exact reciprocal reverse split, so their composed
factor cancels. The 62,500 maximum belongs to one stable ID with two distinct
1:250 reverse splits on 2025-08-04 and 2025-09-22. Both cases trace to distinct
active canonical actions and exact action-set fingerprints.

Quarantine remained explicit. All 3,030 rows preserve sparse/outcome-only,
bounded-source, unavailable-total-return, and absent-row-nonneutrality flags.
Of these, 123 cross the canonical multiple-action group and 2,907 cross an
unresolved possible-impact path. Quarantined rows carry no adjustment factors.

## Idempotency and unchanged-state proof

An exact second full derivation with the same source revision, inputs,
calculation time, and output root returned `already_present`. Counts, Parquet
bytes, manifest SHA-256, and publication fingerprint were unchanged. External
request and canonical write counts remained zero.

The network-prohibited postflight report passed with full active-source reread:

- repository `main` clean at the exact source revision;
- `/data` unchanged at 4,202 files / 2,151,599,005 bytes with fingerprint
  `6d6ef7c214087130290ae151a53b7f8b7be018ffcd1cb42c9912bbcf4c843915`;
- zero symlinks and zero publication residue; and
- Production unchanged at release `2026-09-08T171914Z-ca2d34d50692`.

The formal report therefore continues to show the Adjustment Ledger as absent,
research status `data_blocked`, and performance claims unauthorized. A
separate inventory-bound Plan/Apply boundary is required before these candidate
bytes may enter canonical `/data` custody.
