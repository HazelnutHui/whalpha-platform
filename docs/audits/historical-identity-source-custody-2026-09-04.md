# Historical Identity Source Custody Audit — 2026-09-04

## Result

The 279 profile-bound historical Identity packages now have a complete,
deterministic normalized custody candidate below `/tmp`. Every candidate
partition formally rereads, preserves the full audited result field set, and
independently reconstructs the accepted same-day Instrument Master, Provider
Identity, and Provider Resolver fingerprints under its bound profile.

A combined census and prospective Apply plan also formally rereads. It binds
all 558 candidate files, all 279 absent target partitions, and the unchanged
whole-`/data` pre-state. At the time of this proof no Apply executor existed,
and no canonical write was performed.

Subsequent same-day status: ADR 0139 later implemented and tested the executor
only against disposable roots. The no-write result recorded by this audit and
the unapplied real plan remain unchanged; see the separate
[Apply/recovery audit](historical-identity-source-apply-recovery-2026-09-04.md).

## Audited source boundary

- Explicit package roots: 12
- Profile-bound packages and unique sessions: 279
- Current-profile sessions: 58
- `pre_etv_governance_v1` sessions: 221
- Unbound physical gaps: 24, unchanged
- Source response artifacts: 3,536
- Source result records: 3,399,877
- Response bytes represented by the normalized custody: 1,006,791,465
- Complete retained result-field union: `active`, `cik`, `composite_figi`,
  `currency_name`, `last_updated_utc`, `locale`, `market`, `name`,
  `primary_exchange`, `share_class_figi`, `ticker`, `type`

Response URLs, request IDs, response bodies, credentials, and Authorization
material are excluded. Per-page hash, byte count, row count, reported count,
bounded status, and pagination-presence evidence remain in each manifest.

## Complete candidate proof

Candidate root:

```text
/tmp/whalpha-identity-source-custody-full-20260904
```

The four-process real run completed 279/279 sessions in 26:11.52 at 399% CPU
with peak RSS 486,728 KiB. The writer performed zero external requests, zero
canonical writes, and zero membership writes.

Physical census:

| Measure | Result |
| --- | ---: |
| Partitions | 279 |
| Parquet files | 279 |
| Manifest files | 279 |
| Total files | 558 |
| Parquet bytes | 256,647,407 |
| Manifest bytes | 1,747,111 |
| Total candidate bytes | 258,394,518 |
| Parquet/source-response ratio | 25.4916% |
| Symlinks | 0 |
| Staging residue | 0 |
| Non-`0700` directories | 0 |
| Non-`0400` candidate files | 0 |

A separate four-process formal-reader pass revalidated all 279 partitions and
all 3,399,877 normalized rows. It found one materialization timestamp, one
profile-map fingerprint, the exact 58/221 profile split, and zero forbidden
authority or retention flags. Its aggregate session-evidence fingerprint is
`886e835c5e082b1353ae1f35f25152d80c9b896c98cacd9333b0ea883bc20641`.

The 2025-09-09 current-profile and 2025-09-10 legacy-profile partitions are
byte-identical to both prior independent proof roots, for both Parquet and
manifest bytes.

## No-write Apply-plan proof

Plan paths:

```text
/tmp/whalpha-historical-identity-source-apply-plan-20260904.json
/tmp/whalpha-historical-identity-source-apply-plan-20260904-parallel.json
```

The second path is an independent performance/equivalence repeat. Both files
are 639,375 bytes, mode `0600`, and byte-identical.

| Binding | Value |
| --- | --- |
| Plan SHA-256 | `97e22c62bc8554f1229a41925970a365d189a5ad05bbf802e984fc9f3885c1a0` |
| Plan logical fingerprint | `6310b845d83ead27e949d66bae158c021be010ccd7565b724f55e5a20d20f87d` |
| Candidate inventory fingerprint | `a75a421ce8daf3b4170dfa06e61b86c2200ce3d371de9e37f36a89a19cd69881` |
| Session index fingerprint | `86fd522d46a41e7a949fb4c90086a4b1dbf838376a4a9434afb4a5a5df51d373` |
| Profile-map fingerprint | `20e8b8f5b360d8a4ad4a78f0add69fb5eb88e1bc3ab5c6059dd87ca1035e0028` |
| Expected `/data` inventory | `2928d804ea48cf076b0a589d09b0e150cf07810dc4dd0cef503121d53d95d794` |
| Planned files / bytes | 558 / 258,394,518 |
| Target partitions absent | 279/279 |
| Status | `ready_for_separate_review` |
| Apply authorized | false |

The initial serial plan took 5:17.38 at 102% CPU with peak RSS 334,948 KiB.
The exact four-process implementation took 1:30.46 at 379% CPU with peak RSS
282,852 KiB, a 71.5% wall-time reduction. Worker count is not plan content;
the resulting logical and physical plan bytes stayed identical.

## Boundaries and next gate

- `/data`, Production, Universes, analytics, formulas, active pointers,
  scheduler state, publication, deployment, and research readiness did not
  change.
- The candidate is still temporary. ADR 0139 subsequently supplied and tested
  the bulk Apply/recovery boundary, but durable custody still requires a
  separately reviewed real invocation using this pinned plan.
- The 24 missing sessions remain a separate source-resolution queue. No
  current-universe replay or silent gap fill is allowed.
- Daily point-in-time Universe Membership reconstruction and Historical
  Coverage remain later, independent gates.
- Twenty-four related focused tests and all 2,033 backend tests passed with
  the two unchanged dependency warnings.
