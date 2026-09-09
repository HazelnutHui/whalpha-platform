# 2026-09-09 Canonical Split Adjustment Publication Audit

## Result

The ADR 0178 Plan/Apply published the exact independently reconciled ADR 0177
candidate into canonical Dell custody. The operation added only the two planned
files, and an exact second Apply verified zero-write recovery.

This publication is sparse split-only outcome reconciliation. It does not
authorize a neutral factor for an omitted row, total return, full adjustment
coverage, Historical Coverage, research performance, analytics, Snapshot,
bundle, deployment, or scheduler work.

## Exact plan

| Field | Verified value |
| --- | --- |
| Planner revision | `bdb027a293a167962c24f4a8ec0bb28746e53b8e` |
| Candidate revision | `0c57560d44489c4170675cee086527d25e6daef4` |
| Candidate publication | `7e08b8a8ee364cf215c1459645f76240368b50cc3d2cb4bc77db86d3ca7c3c2a` |
| Plan path | `/tmp/whalpha-canonical-split-adjustment-publication-plan-20260909T005017Z.json` |
| Plan SHA-256 | `fef31be98d8ae6ebbae2a55e043a2eb7f210770acae1204a0972141fefdbaf06` |
| Plan logical fingerprint | `99d657c78694db98659a6d4537f2a3192a308f774994279fba7234d3a8ce132c` |
| Expected `/data` fingerprint | `6d6ef7c214087130290ae151a53b7f8b7be018ffcd1cb42c9912bbcf4c843915` |
| Planned change | 2 files / 80,308 bytes |
| Planned rows | 101,321 = 98,291 clear + 3,030 quarantined |

The plan file was owner-only `0400`, 5,223 bytes, and independently reread with
its approved SHA-256. Formal review fully rederived the candidate from the
exact canonical split-action and EOD family evidence. Both candidate artifacts
matched their planned bytes and hashes, the content-addressed target was
absent, the repository was clean, and every authority field was false.

## Apply and recovery

The shared-lock, network-prohibited Apply published:

- `part-00000.parquet`: 77,637 bytes, SHA-256
  `945c3b71bd71b5043ac38be3af647c60faabc116ddd8dc3d8303e827c2592e63`;
- `manifest.json`: 2,671 bytes, SHA-256
  `4ebd9d705bb2dd7d08e6aede968dfb50a26f955efb56e187dbca674835429ef4`.

The canonical directory is:

```text
/data/trading-intelligence-platform/market-data/adjustment-ledger/
  schema_version=1/
  methodology_version=canonical-split-ratio-to-basis-v1/
  basis_session=2026-09-04/
  coverage_id=7e08b8a8ee364cf215c1459645f76240368b50cc3d2cb4bc77db86d3ca7c3c2a/
```

The directory is `0755`; both files are owner-matched regular files at `0644`.
The first Apply reported `applied`, two files / 80,308 bytes, zero overwrite,
zero deletion, zero external requests, and an outside-target fingerprint equal
to the exact pre-state. The post-state fingerprint is
`af06b692cf1f9708e75cf44defd198cb25317b65403a2adbc503d9e03e1fa71f`.

The exact second Apply reported `verified_existing`, zero files / zero bytes,
two reused files, the same post-state, and the same outside-target pre-state.

## Postflight

Current-context contract 1.9 passed with active-source reread on clean `main`.
It formally read the full canonical ledger and reported:

- custody `canonical_sparse_split_only_outcome_reconciliation`;
- 101,321 rows: 98,291 clear and 3,030 quarantined;
- 575 clear and 31 quarantined stable IDs;
- explicit 2026-09-04 basis and affected-path-only row scope;
- false absent-row neutrality, total return, full coverage, Historical
  Coverage, and research authority; and
- blocker `adjustment_ledger_reconciliation_incomplete`, status
  `data_blocked`, and performance claims unauthorized.

`/data` contains 4,204 files / 2,151,679,313 bytes with the exact post-state
fingerprint, zero symlinks, and zero publication residue. No matching process
remained. EOD, Identity, Activation, Market Intelligence, and Snapshot were not
changed. No deployment action was executed; the local deployment evidence
continues to reference OCI release `2026-09-08T171914Z-ca2d34d50692`.
Remote serving was not re-inspected in this data-only operation.
