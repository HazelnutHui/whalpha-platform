# OCI Private Dashboard Deployment

## Purpose

This runbook records the reviewed deployment package and future deployment flow for the private static Market Dashboard.

## Status

Deployed pending manual authenticated browser verification.

The release `2026-08-13T120220Z-987b5289a783` was deployed from source commit `987b5289a7835316ef6aae4aa326aff46de58896` on 2026-08-15.

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
10. Verifies public placeholder remains public and dashboard/data require auth.

Automatic verification does not use or request the Dashboard password. Authenticated browser verification remains a manual user step.

## 2026-08-15 Deployment Result

- workstation source commit: `987b5289a7835316ef6aae4aa326aff46de58896`
- deployed release: `2026-08-13T120220Z-987b5289a783`
- current session: 2026-08-13
- previous session: 2026-08-12
- deployment status: `deployed_pending_manual_authenticated_verification`
- public `/`: HTTPS 200 and still serves the data-free WH Alpha placeholder
- `/dashboard/`: unauthenticated HTTPS 401 with Basic Auth challenge
- `/private-data/v1/manifest.json`: unauthenticated HTTPS 401 with Basic Auth challenge
- HTTP `/`: redirects to HTTPS
- private JSON cache policy: private no-store
- source/raw provider payloads: not uploaded
- canonical Parquet: not uploaded
- Massive credential: not uploaded

Two earlier same-source deployment attempts failed post-switch validation before this release. They were retained as failed release directories for audit and are not the active `current` release.

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
