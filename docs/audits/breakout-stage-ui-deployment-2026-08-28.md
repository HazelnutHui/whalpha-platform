# Breakout Stage UI Deployment — 2026-08-28

## Scope

The user authorized deployment after implementation and review. This release
changes the Momentum Breakout presentation and deploys the previously
repository-complete strategy-method explanation. It reuses the already active,
explicitly stale-review Snapshot 1.9 / Dashboard 2.6 payload. It does not
create or modify Market Intelligence, Snapshot, EOD, Identity, Activation, or
any `/data` content.

## Source and verification

- Source commit:
  `2737f8171c3c47247568fc8de818b005a2355697`.
- Backend: 1,568 tests passed with two existing deprecation warnings.
- Frontend: 94 tests passed; Snapshot-mode Production build passed.
- The independent Continuation Facts 1.1 audit formally reread with 3,543
  assessed rows, zero unavailable, zero Oracle mismatch, and exact input
  permutation equivalence.

## Bundle and deployment

- OCI release: `2026-08-28T162136Z-2737f81`.
- Bundle: 50 files, no credentials, Parquet, or raw provider data.
- Bound Market Intelligence publication:
  `2026-08-28T131700Z-eeccc22`.
- Bound payload: Snapshot 1.9 / Dashboard 2.6 for 2026-08-26,
  `stale_review`, expected 2026-08-27, lag one.
- Remote dry-run passed Nginx, service, host, path, credential-metadata, and
  listener preflight.
- Atomic Apply and the deployment tool's temporary equal-capability guest
  Session postflight passed.

## Post-deployment checks

- `/srv/whalpha/current` resolves to the exact new release.
- Nginx and `whalpha-dashboard-auth.service` are active and enabled.
- Expected listeners are public 80/443 and localhost-only
  `127.0.0.1:8010`; no private 8000/8001 backend is exposed.
- Public `/` returns 200, unauthenticated `/dashboard/` redirects, and
  unauthenticated private Snapshot data returns 401.
- No remote staging or partial release residue was found.
- The built asset contains both English and Chinese breakout-stage copy.

Password-based login and human visual acceptance remain manual checks. No
credential content was read or printed.
