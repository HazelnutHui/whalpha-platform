# OCI Private Dashboard Deployment

## Purpose

This runbook records the reviewed deployment package and future deployment flow for the private static Market Dashboard.

## Status

Deployed pending manual session-login verification.

The active release is managed through the deployment script and should be verified from the current release symlink after each apply. The root path `/` is the branded WH Alpha session-login entry; `/login/` is retained only as a compatibility redirect to `/`.

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
10. Verifies `/` serves the branded login page, `/login/` redirects to `/`, Dashboard redirects unauthenticated users to `/?next=/dashboard/`, and private JSON returns 401.
11. Uploads the non-secret password rotation helper to `/srv/whalpha/admin/rotate-whalpha-dashboard-password.sh`.

Automatic verification does not use or request the Dashboard password. Authenticated browser verification remains a manual user step.

## Session Auth Boundary

- `/` is public and contains the branded login page with no real market data.
- `/login/` is a compatibility redirect to `/`.
- `/auth/login` and `/auth/logout` proxy to the localhost-only Auth Service.
- `/auth/status` returns only authenticated/not-authenticated status and no sensitive body.
- `/auth/internal-verify` is an Nginx internal location.
- `/dashboard/` and `/private-data/` use the same `auth_request` session check.
- The Auth Service listens on `127.0.0.1:8010` only.
- Wrong-password deployment verification uses a known invalid password and does not reveal whether the username or password failed.
- No successful login is automated because Codex does not know the password.

## Password Rotation Helper

The deployment installs `/srv/whalpha/admin/rotate-whalpha-dashboard-password.sh`. It defaults to dry-run and only rotates on `--apply` with an interactive TTY. It never accepts a password through command arguments, environment variables, files, or piped stdin. On success it restarts the Auth Service to invalidate all existing sessions.

The real password must be entered by the user directly on OCI. Do not paste it into chat or Git.

The helper enforces a hard minimum length of 10 characters. Longer unique passwords are recommended, but passwords meeting the 10-character minimum are accepted.

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

- superseded release: `2026-08-15T125517Z-0fa5cac89847`
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


## 2026-08-15 Login Route Repair

- active release: `2026-08-15T130949Z-78eedc071786`
- source commit: `78eedc071786c39e6bdebbf4d2a8d0e35fe84804`
- defect: prior deployment verification treated `/login/` HTTP 200 as success and did not verify that the body was the branded login page rather than the public placeholder.
- root cause: the automated deployment gate was status-only for `/login/`; it did not assert branded-login markers or reject the public placeholder marker. The Nginx login location also used an `alias`/`$uri` mapping that was less explicit than the intended release-root mapping.
- repair: `/login/` now maps through `root /srv/whalpha/current` to the release login artifact, and deployment verification checks body markers for both public `/` and `/login/`.
- production `/`: HTTPS 200, contains `New platform under development.`, and does not contain the login form.
- production `/login/`: HTTPS 200, contains `Quantitative Market Structure`, username/password fields, and `Sign In`; does not contain `New platform under development.`
- production `/dashboard/`: unauthenticated HTTPS 302 to `/login/?next=/dashboard/`.
- production `/private-data/v1/manifest.json`: unauthenticated HTTPS 401 JSON with no private payload exposed.
- `/auth/internal-verify`: external HTTPS 404.
- Auth Service: active and listening only on `127.0.0.1:8010`.
- deployment status: `deployed_pending_manual_session_login_verification`.


## 2026-08-15 Login Submission Repair

- active release: `2026-08-15T133119Z-137f244e8508`
- source commit: `137f244e850890dba29ee55f3a16c92923416497`
- user-observed defect: submitting the login form navigated the browser to `/auth/login` and displayed `{"error":"invalid_request"}`.
- root cause: `login.js` attached a submit listener but did not call `event.preventDefault()` or submit through the frontend client. The browser therefore performed a native form POST to `/auth/login`, while the intended session-login flow required an AJAX JSON contract and client-side handling of success/failure.
- repair: the login page now intercepts submit, POSTs JSON to relative `/auth/login`, uses `credentials: same-origin`, validates `next`, clears the password on failure, and displays a generic error without navigation.
- Auth Service contract: `POST /auth/login` with `Content-Type: application/json`, fields `username`, `password`, and `next`; success returns JSON with a Set-Cookie session, failure returns a generic JSON authentication error with no Set-Cookie.
- deployment verification now checks `/login/login.js` and `/login/login.css` status and Content-Type, and performs one controlled invalid JSON login using only fictitious credentials.
- controlled invalid-login production result: HTTP 401, generic `invalid_credentials`, no session cookie, no submitted values leaked, and not `invalid_request`.
- real successful login remains a manual browser verification step for the user.

## 2026-08-15 Root Login Entry and Rotation Helper

- active release: `2026-08-13T135949Z-92819ed17316`
- source commit: `92819ed17316c567c40b440f5c2e8487f9db4b53`
- root `/`: HTTPS 200 and serves the WH Alpha branded login page.
- `/login/`: HTTPS 302 compatibility redirect to `/`.
- `/dashboard/`: unauthenticated HTTPS 302 to `/?next=/dashboard/`.
- `/private-data/v1/manifest.json`: unauthenticated HTTPS 401 JSON with no private payload exposed.
- `/auth/status`: unauthenticated HTTPS 401, no response body, `Cache-Control: private, no-store`.
- `/auth/internal-verify`: external HTTPS 404.
- Auth Service: active and listening only on `127.0.0.1:8010`.
- password rotation helper: deployed at `/srv/whalpha/admin/rotate-whalpha-dashboard-password.sh`.
- deployment status: `deployed_pending_manual_password_rotation_and_login_verification`.

## 2026-08-15 Password Rotation Script Repair

The first real password rotation attempt failed after user input with `auth service must listen only on 127.0.0.1:8010`. Read-only diagnostics found:

- Auth Service active.
- Nginx active.
- `8010` listening only on `127.0.0.1:8010`.
- one root-owned backup file from the failed rotation.
- no safe way to determine whether the active htpasswd file contains the old or newly entered password.

The repaired admin helper:

- extracts only the `ss` local-address field;
- accepts exactly one `127.0.0.1:8010` listener;
- rejects wildcard, IPv6 wildcard, public-address, multiple, and absent listeners;
- waits briefly and repeatedly for service readiness after restart;
- performs atomic rollback from the run backup if post-replacement validation fails;
- prints fixed non-sensitive status keys for `rotation_failed`, `rollback_attempted`, `rollback_succeeded`, or `rollback_failed`;
- reports `password_rotation=completed`, `sessions_invalidated=true`, `auth_service=active`, and `listener=127.0.0.1:8010` on success.

The user must run one new repaired `--apply` rotation to establish a known final password state.

Several same-source candidate releases failed post-switch validation while strengthening deployment assertions. The deployment script rolled back after each failure; failed release directories were retained for audit and are not the active `current` release.

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
