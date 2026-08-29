# ETF Relationship Explanation Deployment — 2026-08-29

## Scope and authorization

After reviewing the repository-only relationship persistence/acceleration and
state-timeline work, the user approved continuing with the proposed deployment.
The authorization covered one fresh Snapshot, one matching OCI bundle, and one
deployment of these UI/interpretation changes. It did not cover new EOD data,
analytics recomputation, scheduler activation, rollback, credentials, or any
other infrastructure change.

## Preflight correction

The first write-free Snapshot candidate reached prior-active-Snapshot reread
and failed because the backend response model incorrectly required the new
additive fields on old Snapshot bytes. It created no approval plan, `/data`
target, pointer change, OCI request, or Production change. Its exact 31 MB
`/tmp` candidate was inspected for symlinks and removed.

Repository commit `1490b37f25b3cc48c80fcf0a79c091767eff69ad` makes both
additive fields optional for prior Snapshot reads while the current service
still constructs and strictly validates both fields. A regression test and a
formal reread of the active old Snapshot passed. The full backend suite passed
1,656 tests; the frontend suite passed 96 tests and its Production build passed.

## Snapshot and bundle

- Market Intelligence remained
  `2026-08-29T080431Z-785ab49dfedd`, analysis session 2026-08-28.
- Fresh Plan 2.4 SHA-256:
  `49d98548c8b67ceb00598de16cc646c45594be06e5ac38498e900e061747b446`.
- Prior Snapshot pointer fingerprint:
  `a3ab05d42f11421540cc3b702078c33f6cf15f25a9392f81851a86f9d321d00b`.
- Activated Snapshot:
  `2026-08-29T133847Z-1490b37f25b3`, Snapshot 1.9 / Dashboard 2.6.
- New Snapshot pointer fingerprint:
  `76f499d976b3e1e87a5b84dd6cad0875d9baadf555b0e2c6d81d42d99e9d7a60`.
- Both Universe records contain all 16 change summaries and all 16 bounded
  timelines; every timeline exposes 10 of 21 retained relationship sessions.
- The matching OCI bundle contains 48 payload files plus deployment manifest
  and checksum inventory, 50 files on disk. It declares no credentials, raw
  provider data, Parquet, demo data, or role difference.

## OCI deployment and postflight

The dry-run proved expected current release
`2026-08-29T080928Z-785ab49dfedd`, clean remote preconditions, and valid Nginx
configuration. One Apply switched `/srv/whalpha/current` to
`2026-08-29T133847Z-1490b37f25b3`.

The first independent inspector invocation exposed only a remote Python
compatibility error: `datetime.UTC` was unavailable. The read-only script was
changed to `datetime.timezone.utc`, regression-tested, and rerun without a
redeployment. The final report proved:

- remote manifest SHA-256
  `e6ac6de7ec1c16f3feeaf1468aa81e14ffedee60172f9451e711a1a6a6bb7c4b`;
- remote checksum-inventory SHA-256
  `7f076e3a4eca909813e86ecc8ec2c53918b545cc7a5e7323bdcab411f01a690e`;
- bundle logical fingerprint
  `467166c28f7f78f8f2f5072d01f007d8910e18386333b26043a1477871975a74`;
- Nginx and Session Auth active and enabled, Auth listener localhost-only,
  protected routes correct, temporary guest Session successful, and guest /
  credential route policy identical;
- zero failed system units, staging releases, failed releases, or unexpected
  private listeners; and
- state fingerprint
  `9385e063a8f1b1cb166c38dcd2b375e7e91aae81721e8a9750e9bdf5fca8f47b`.

Password-based login and human visual acceptance were not performed and remain
manual. No credential or cookie content was printed or retained.

## Final Dell state

The credential-free full-source report reread aligned Identity/EOD, active MI,
and the new active Snapshot. `/data` now contains 485 files / 299,111,361 bytes
at inventory fingerprint
`3daa2dcd66d607769f10320cfb99f4fd92dbcb0979d927fe03acef4b4a7da269`,
with zero symlinks and zero publication residue. No EOD, Identity, analytics,
Activation, scheduler, email, rollback, password, DNS, firewall, or unrelated
service changed.
