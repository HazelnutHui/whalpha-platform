# Current Historical Family-Evidence Canonical Apply Audit — 2026-09-08

## Scope

Publish only the two immutable ADR 0165 evidence manifests for current
canonical EOD Price Bar and point-in-time Identity history. This operation did
not publish final Historical Coverage, change research readiness, run a model,
modify analytics, build a Snapshot or bundle, deploy OCI, or change a scheduler.

## Preflight

- Host/user: `dell5820` / `hui`.
- Source: clean `main` at
  `1d30cb69d26225a456374513f887fcbe1d9a0794`.
- Plan: owner `hui`, mode 0400, 677,689 bytes, file SHA-256
  `dced91a98cf4a71fe28748c241f83aa31dcdb588a9f322245a9b14de6d4511ae`.
- Plan logical fingerprint:
  `6ae6738181012b6f9364d5b624d7edaa81d992b7be623e6bd6b58c2854d5e663`.
- Family-set fingerprint:
  `be67c6ec924809eca63dacf1130ec19d9df0d673f65b403a416de1f2be812377`.
- Coverage: 304 sessions from 2025-06-23 through 2026-09-04.
- Pre-state: 4,058 files / 2,009,024,076 bytes; inventory fingerprint
  `d7ddbace6669c1870e86d79fd48aa86ff99d276699d23b84939983f950b236b4`;
  zero symlinks and zero staging/partial residue.
- Exact-SHA plan verification formally reread every bound source and confirmed
  both targets absent before mutation.

## Apply result

The shared-lock, network-prohibited executor published EOD first and Identity
second. It added exactly two files / 675,569 bytes and formally reread both
families. The outside-target inventory fingerprint remained
`d7ddbace6669c1870e86d79fd48aa86ff99d276699d23b84939983f950b236b4`
before and after the critical section. External requests, overwrites, and
deletions were all zero.

| Family | Manifest bytes | Manifest SHA-256 | Directory/file mode |
| --- | ---: | --- | --- |
| `eod_price_bar` | 177,268 | `ba652cb4ed21a0bfce1ce0cbd690c933cb8ae98de3f39231e282ea8f22789593` | 0755 / 0644 |
| `point_in_time_identity` | 498,301 | `5046dd6b3b1f8dd028528636a9caf989bcbb53040082ca0060016b07a49d67a2` | 0755 / 0644 |

Each target is owned by `hui` and contains exactly `manifest.json`.

## Recovery postflight

An independent `verify_then_complete` invocation with the same exact bindings
classified both targets as completed, reused both families, formally reread
both, and published zero files / zero bytes. The full post-state fingerprint
remained
`16033737d18cd8d34de3e8401ee0f3e5d195a49470a2cda384a604ed6f29db1e`.

## Authoritative post-state

Current-context report 1.6 completed network-free from clean main:

- `/data`: 4,060 files / 2,009,699,645 bytes;
- inventory fingerprint:
  `16033737d18cd8d34de3e8401ee0f3e5d195a49470a2cda384a604ed6f29db1e`;
- zero symlinks and zero staging/partial residue;
- two `historical_coverage_evidence` partitions/manifests observed;
- final `historical_coverage` remains absent;
- research readiness remains `data_blocked`;
- strategy-development review and performance claims remain unauthorized.

The EOD/Identity source facts did not change: 304 aligned sessions through
2026-09-04, with 9,962 rows in the latest EOD partition. The two family
evidence objects establish immutable transitive custody for those acquired
families only; they do not satisfy Membership, lifecycle, corporate-action,
adjustment, cost/liquidity, revision-lineage, chronological-evaluation, or
sealed-holdout requirements.
