# OCI Private Dashboard Deployment

## Purpose

This runbook records the reviewed deployment package and future deployment flow for the private static Market Dashboard.

## Status

Deployed pending manual session-login verification.

The active release `2026-08-15T125517Z-0fa5cac89847` was deployed from source commit `0fa5cac8984789f8b88ce25b5c1f43567aae5911` on 2026-08-15. It replaces browser-native Basic Auth with a branded login page and server-side sessions.

## Local Build Steps

```bash
scripts/admin/build-private-dashboard-snapshot.sh
scripts/admin/build-oci-dashboard-bundle.sh --snapshot-release <release-id>
scripts/admin/deploy-private-dashboard-oci.sh --bundle-release <release-id> --dry-run
scripts/admin/deploy-private-dashboard-oci.sh --bundle-release <release-id> --apply
```

The snapshot exporter reads completed canonical datasets from `/data/trading-intelligence-platform` and writes ignored artifacts under `build/private-dashboard/`.

The bundle builder creates ignored artifacts under `build/oci-dashboard/`.

## Apply Flow

The apply deployment:

1. Verify local host, repo, branch, clean tree, and bundle checksums.
2. Verify remote host and user through `whalpha-oci`.
3. Verify Nginx, TLS, auth file, and target release paths.
4. Upload to a new staging release directory.
5. Verify remote checksums.
6. Atomically move the release into place.
7. Atomically switch `/srv/whalpha/current`.
8. Tests Nginx config before reload.
9. Reloads Nginx only after config test passes.
10. Verifies public placeholder remains public, login is public, Dashboard redirects unauthenticated users to login, and private JSON returns 401.

Automatic verification does not use or request the Dashboard password. Authenticated browser verification remains a manual user step.

## Session Auth Boundary

- `/login/` is public and contains no real market data.
- `/auth/login` and `/auth/logout` proxy to the localhost-only Auth Service.
- `/auth/internal-verify` is an Nginx internal location.
- `/dashboard/` and `/private-data/` use the same `auth_request` session check.
- The Auth Service listens on `127.0.0.1:8010` only.
- Wrong-password deployment verification uses a known invalid password and does not reveal whether the username or password failed.
- No successful login is automated because Codex does not know the password.

## 2026-08-15 Deployment Result

- workstation source commit: `987b5289a7835316ef6aae4aa326aff46de58896`
- deployed release: `2026-08-13T120220Z-987b5289a783`
- current session: 2026-08-13
- previous session: 2026-08-12
- deployment status: `superseded_by_session_login_release`
- public `/`: HTTPS 200 and still serves the data-free WH Alpha placeholder
- `/dashboard/`: unauthenticated HTTPS 401 with Basic Auth challenge
- `/private-data/v1/manifest.json`: unauthenticated HTTPS 401 with Basic Auth challenge
- HTTP `/`: redirects to HTTPS
- private JSON cache policy: private no-store
- source/raw provider payloads: not uploaded
- canonical Parquet: not uploaded
- Massive credential: not uploaded

## 2026-08-15 Session Login Deployment Result

- active release: `2026-08-15T125517Z-0fa5cac89847`
- source commit: `0fa5cac8984789f8b88ce25b5c1f43567aae5911`
- current session: 2026-08-13
- previous session: 2026-08-12
- browser Basic Auth popup: replaced
- branded `/login/` page: deployed and public
- server-side in-memory sessions: deployed on localhost-only port 8010
- logout endpoint and Dashboard Logout button: deployed
- numeric presentation rules: updated to bounded percent, ratio, volume, and currency formatting
- public `/`: HTTPS 200 and still serves the data-free WH Alpha placeholder
- `/dashboard/`: unauthenticated HTTPS 302 to `/login/?next=/dashboard/`
- `/private-data/v1/manifest.json`: unauthenticated HTTPS 401 JSON with `Cache-Control: private, no-store`
- `/auth/internal-verify`: external HTTPS 404; usable only as an Nginx internal subrequest
- security headers: present on login, dashboard redirect, and private-data unauthenticated responses
- deployment status: `deployed_pending_manual_session_login_verification`

Earlier same-source deployment attempts failed post-switch validation before this release. They were retained as failed release directories for audit and are not the active `current` release.

## OCI Read-Only Preflight on 2026-08-15

Observed without modifying OCI:

- hostname: `hui`
- user: `ubuntu`
- OS: Ubuntu 22.04.5 LTS
- memory: about 956 MiB
- swap: none
- root disk: about 45G with about 40G free
- Nginx: active and enabled, version 1.18.0
- Nginx config test: successful
- certbot timer: present
- current public HTTP: 301 to HTTPS
- current public HTTPS: 200 placeholder
- listeners: 22, 80, 443, system DNS/RPC only
- failed systemd units: none
- `/srv/whalpha` now exists with versioned Dashboard releases
- `/etc/nginx/auth/whalpha-dashboard.htpasswd` exists with restricted metadata
- `openssl` present
- `htpasswd` command not found for the unprivileged check

Public HTTPS is verified. Direct unprivileged file tests for `/etc/letsencrypt/live/whalpha.com/...` did not confirm certificate path accessibility, so deployment should recheck with the required privilege boundary before apply.

## Non-Goals

- changing DNS, Cloudflare, TLS, firewall, SSH, or system services
- reading or outputting the Dashboard password or password hash
- authenticated browser verification by Codex
