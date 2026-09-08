# Corporate-Action Repeat-Diff Audit — 2026-09-08

## Scope

This audit records one later, identical-scope observation of the complete
2025-06-23 through 2026-09-04 Massive V1 split and dividend endpoints and the
two ADR 0171 content comparisons against the first retained observation.

Acquisition and comparison used clean Dell main revision
`1f07c53893aa31366f057fd440ed82f9ed49ef87`. The later source is retained at
`/tmp/whalpha-corporate-actions-repeat-20260908T093845Z`; the two diff outputs
are `/tmp/whalpha-corporate-action-repeat-diff-20260908T094238Z-split` and
`/tmp/whalpha-corporate-action-repeat-diff-20260908T094238Z-dividend`.

## Result

| Evidence | Split | Dividend |
| --- | ---: | ---: |
| Baseline rows | 1,949 | 68,150 |
| Repeat rows | 1,949 | 68,150 |
| Unchanged payloads | 1,949 | 68,150 |
| Same-ID changed payloads | 0 | 0 |
| Added provider action IDs | 0 | 0 |
| Removed provider action IDs | 0 | 0 |
| Effective-date changes | 0 | 0 |
| Provider-ticker changes | 0 | 0 |
| Pagination-shape change | no | no |

Both later packages again had zero invalid dates, duplicate provider action
IDs, and unexpected fields. Every provider action ID and canonical JSON source
payload was identical to its baseline observation. Source package manifests
and page hashes differ because their observation timestamps are intentionally
new; the page/order-independent content fingerprints match exactly.

## Observation and evidence bindings

| Evidence | Split | Dividend |
| --- | --- | --- |
| Baseline observed | 08:26:32–08:26:33 UTC | 08:26:42–08:29:58 UTC |
| Repeat observed | 09:39:00–09:39:01 UTC | 09:39:12–09:42:28 UTC |
| Baseline manifest SHA-256 | `536235ba0c2e56b2975b32901f0175fb2a63ff0ced01cfbc2e39bdaeac9fc790` | `a53aa90c79a77d455cb6cc97668535799106c47560d874706d30b53f8c8ce1cc` |
| Repeat manifest SHA-256 | `ad6d433aa9e977a5b99622362b4ee1f32195bc4099af1e05131420f5246dc432` | `dc3ef380b2daf71ee829ceb3d97ea0cd2bd5e786330d241876a5341df5e97a72` |
| Content fingerprint, both observations | `bb4ca2e88b2a727f269969f3facb1b213cffdbd050996df70bbc6a8fb7968ec6` | `d743d4d069e5fc391d6b2a1e29c7d2d186a82cd14ff72989d4f845c2fab6ee3d` |
| Diff manifest SHA-256 | `cde373245253b263e04b90a37ef3db75b397e959dba156e58b2b8d2d62667521` | `2c97770ac4c634306512382e82552571a37e2f542946644290b0da6536d72b54` |
| Diff logical fingerprint | `53a3cb304c320a4be226b07346675a0ace706348627e92bb43f8f9522d29650d` | `5f9839cd7216a0f5676caab4f14c55216020b835d71a19d27a0279ee0c562372` |

Separate formal rereads passed for both later source packages and both diff
outputs. The source tree has 19 regular files / 24,489,297 bytes and three
directories. Each diff tree has two regular files and one directory, using
2,514 and 2,522 bytes respectively. All files are mode `0400`, all directories
are mode `0700`, and no symlink is present.

## Interpretation and next gate

The result proves source content stability only across the approximately
69–73 minute intervals observed on 2026-09-08. It does not prove that the
provider never revised older records, supply a historical availability time,
or turn local observation order into provider revision numbers. It also does
not establish that every action's financial semantics are correct.

The observed zero-delta result is sufficient to stop waiting and proceed to
append-only revision-policy design plus semantic and cross-event conflict
review. Future acquisitions can use the same comparator to detect later
changes. Added, removed, or changed rows must remain observed deltas until
separately interpreted; they cannot silently overwrite a prior observation.

The post-run network-prohibited current-context report passed on clean main
`1f07c53893aa31366f057fd440ed82f9ed49ef87`. `/data` remained exactly 4,060
files / 2,009,699,645 bytes with inventory fingerprint
`16033737d18cd8d34de3e8401ee0f3e5d195a49470a2cda384a604ed6f29db1e`,
zero symlinks, and zero publication residue. No canonical Corporate Action,
Adjustment Ledger, analytics, Snapshot, bundle, OCI deployment, scheduler, or
website transition occurred.
