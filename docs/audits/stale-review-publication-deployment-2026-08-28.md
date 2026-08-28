# 2026-08-28 Stale-Review Publication and OCI Deployment

## Scope and authorization

The user explicitly authorized the exact review tuple: analysis/actual session
2026-08-26, expected session 2026-08-27, lag one, and acknowledgement
`I_ACKNOWLEDGE_2026_08_26_STALE_REVIEW_LAG_1`. This authorized one bounded
review publication and deployment. It did not authorize provider acquisition,
claim 2026-08-27 EOD completeness, or create standing stale-publication
authority.

## Source and verification

- Dell source-of-truth `main` was clean at
  `eeccc2242a3414aba3b761915c4e146022b3b9fe`.
- The full backend regression passed: 1,555 tests, two existing deprecation
  warnings, 247.69 seconds.
- MI source custody retained the exact Phase 1a history fingerprint
  `ebb3a7ef9fc2faf68b355929a08af77e91183d5821b1fec07219febcff88fb5a`
  and preview fingerprint
  `740e50acc7e30fb817e70ae7300c062af3126d9d136cf40cb5c76f2bfdc9ade6`.
- Publication-time MI source validation fell from 53.74 to 2.98 seconds after
  removing repeated completed calculation replay; the byte-custody and
  Production-state compare-and-swap gates remain mandatory.

## Market Intelligence

- Plan 1.2 SHA-256:
  `c8c0d30edd2704815c089ad76e8b13c5e5b8dde8d3587f8dca470c0aa2e78708`.
- Plan completed in 77.98 seconds with zero Production writes.
- Apply completed in 124.50 seconds.
- Active publication: `2026-08-28T131700Z-eeccc22`.
- Contract: `market-intelligence-publication/1.2`.
- Active pointer fingerprint:
  `e4b387c8e41f78da53d05b7ebfc94b126ee0b9209712cbd6fd77bdb25ad03a40`.
- Candidate publication identity remained
  `286d4eebcb2e0489f33b03894bec8c7c58c1641f113719a014f296db42c2f07a`
  with 496 Primary and 532 Secondary records.

## Dashboard Snapshot

- Plan 2.4 SHA-256:
  `0a039eca5e3ccdb4642346e50bc300e5c5c9b1192501c9e49a28b804fe928dbc`.
- Plan completed in 205.30 seconds with zero Production writes.
- Apply completed in 129.96 seconds.
- Active release: `2026-08-28T132100Z-eeccc22`.
- Contracts: Snapshot 1.9 / Dashboard 2.6.
- Active pointer fingerprint:
  `e2b52f319894786d2e6fc628472bfdecd2078e85bbbec3e02be223a4ba9b0203`.
- The release includes the 1.49 MB first-load Candidate summary, 32 detail
  shards, and the 195,211-byte strategy-channel product with logical
  fingerprint
  `45bad6eb7fd014c0cc36b1244be7274dc98b92d23fa57d9ddcabe10b271ca3cd`.
- The prior Snapshot 1.7 / Dashboard 2.4 release remains the rollback target.

## OCI bundle and deployment

- The 50-file bundle was built in 6.46 seconds from the exact source commit and
  active MI/Snapshot identities. It contains no credentials, raw provider
  payload, or canonical Parquet.
- Remote dry-run completed in 3.83 seconds with successful Nginx preflight.
- Atomic Apply completed in 20.62 seconds for release
  `2026-08-28T132100Z-eeccc22`.
- Postflight passed HTTPS redirect/protection rules, Nginx/service health,
  localhost-only Auth listener, release checksums, temporary guest login,
  Candidate summary/detail access, strategy-product lineage and decision
  boundaries, logout, and post-logout protection.
- Guest and credential Sessions remain role-free and capability-identical by
  contract. Password-based login and human visual acceptance were not tested,
  because no password or credential content was read.

## Post-deployment reconciliation

The network-free project report reread active custody and contracts. It found
390 files / 202,875,231 bytes under `/data`, inventory fingerprint
`7d66bc02fe88410a4ed6f000f74875aa135e11d10318ff010a148d03ba08a0de`,
zero symlinks, and zero publication residue. Latest EOD remains 2026-08-26;
latest Identity is 2026-08-27 and therefore one session ahead of EOD. The
active payload correctly reports `stale_review` rather than freshness.

No Massive/SEC request, EOD or Identity update, scheduler change, credential
read, rollback, or unrelated service action occurred.
