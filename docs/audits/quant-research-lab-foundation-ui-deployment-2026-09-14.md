# Quant Research Lab Foundation UI Deployment Audit — 2026-09-14

## Scope

This audit records the UI-only publication of the trilingual research-
foundation snapshot and corrected Strong-Leader Pullback next-decision record.
It contains no credential, Session material, provider response, private-key
path, or server address.

The deployment reused the immutable 2026-09-11 Dashboard Snapshot and Market
Intelligence publication. It did not fetch or Apply data, rebuild analytics,
publish a Snapshot, open research outcomes, select a parameter, activate a
Candidate model, or change the equal guest/credential capability policy.

## Local release evidence

- Clean source revision:
  `70438696e33c9d7a3302a272ff13846a5f38b249`.
- Release:
  `2026-09-14T234322Z-70438696e33c`.
- Immutable source Snapshot:
  `2026-09-11T211340Z-26cab64fabda`, Snapshot 1.11 / Dashboard 2.8.
- Market Intelligence publication:
  `2026-09-11T205429Z-26cab64fabda`, contract 1.3.
- Serving Bundle logical fingerprint:
  `4772aaa692392b4a0cadee6e0a4e4f7b3ed009e4baf5e1c0e1e8e604e1c77c25`.
- Source Snapshot manifest SHA-256:
  `3d968480754e07a589ebc467848db19a74e95ac442598e964726146f3d112e3c`.
- The completed bundle contains 63 regular files and passed its complete
  checksum inventory. Forbidden credential, key, Parquet, environment, source-
  map, and raw-provider patterns were absent.

The local implementation had already passed all 2,825 backend tests, all 126
frontend tests, and a clean bounded production build. The checked-in Lab model
record exactly matched the canonical Python projection.

## Freshness boundary

The credential-free deployment review at 2026-09-14T23:42:13Z found both
Canonical EOD and the active Snapshot at 2026-09-11 while the latest completed
XNYS session was 2026-09-14. Freshness was therefore `stale` with a one-session
lag. This UI-only release preserves that fact; it does not relabel the data as
current or create a review Snapshot.

## Remote preflight and Apply

The independent preflight found the prior release
`2026-09-11T211340Z-26cab64fabda` active, the target absent, protected routes
and a temporary guest Session valid, Nginx and the localhost-only Auth Service
healthy, and zero staging releases, failed releases, failed units, or
unexpected private listeners. Its state fingerprint was
`df45f6293570c383bd9e7ac86aa609ed155a40d96b572e00e6b9382b838cff69`.

The deployment dry-run then rechecked the exact current release, host/user,
bundle revision, checksum inventory, Nginx configuration, service state,
listener boundary, and residue before mutation. Apply uploaded to a new staging
path, verified checksums, promoted the immutable release, switched the current
pointer atomically, retested Nginx, and completed the bounded guest-flow checks.
The prior release remains the immediate rollback candidate.

## Independent postflight

The postflight at 2026-09-14T23:44:48Z verified:

- current release and deployed source match the intended target;
- Serving Bundle logical fingerprint:
  `4772aaa692392b4a0cadee6e0a4e4f7b3ed009e4baf5e1c0e1e8e604e1c77c25`;
- deployment-manifest SHA-256:
  `f8e8e94f245ffc67bb2eb914498c015eca8ba7263257816a6b3fe14a838a6860`;
- checksums-file SHA-256:
  `2c8ed7bfe7b94c236e77b46ca72569cd96864994663d0e2f949d3a2028a1ed94`;
- Nginx and the Auth Service are active and enabled;
- the Auth Service listener remains localhost-only;
- unauthenticated protected-route behavior remains correct;
- a bounded guest Session read the Dashboard and exact private manifest, then
  logged out successfully;
- guest and credential route policy remains identical; and
- no staging release, failed release, failed unit, or unexpected private
  listener remains.

The final remote-state fingerprint is
`28e418b0c43c74f93658e99ba4af8be030b2fedf875ece6ee8d340ed88d8cfbb`.
Credential login was not tested and final appearance remains a manual browser
check by the user.
