# OCI Private Dashboard Deployment

## Purpose

This runbook records the reviewed deployment package and future deployment flow for the private static Market Dashboard.

## Status

Prepared — dry-run only. No OCI files were modified and no deployment was performed.

## Local Build Steps

```bash
scripts/admin/build-private-dashboard-snapshot.sh
scripts/admin/build-oci-dashboard-bundle.sh --snapshot-release <release-id>
scripts/admin/deploy-private-dashboard-oci.sh --bundle-release <release-id> --dry-run
```

The snapshot exporter reads completed canonical datasets from `/data/trading-intelligence-platform` and writes ignored artifacts under `build/private-dashboard/`.

The bundle builder creates ignored artifacts under `build/oci-dashboard/`.

## Future Apply Flow

A future apply deployment must:

1. Verify local host, repo, branch, clean tree, and bundle checksums.
2. Verify remote host and user through `whalpha-oci`.
3. Verify Nginx, TLS, auth file, and target release paths.
4. Upload to a new staging release directory.
5. Verify remote checksums.
6. Atomically move the release into place.
7. Atomically switch `/srv/whalpha/current`.
8. Test Nginx config before reload.
9. Reload Nginx only after config test passes.
10. Verify public placeholder remains public and dashboard/data require auth.

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
- `/srv` exists; `/srv/whalpha` not yet present
- `/etc/nginx/auth` not yet present
- `openssl` present
- `htpasswd` command not found for the unprivileged check

Public HTTPS is verified. Direct unprivileged file tests for `/etc/letsencrypt/live/whalpha.com/...` did not confirm certificate path accessibility, so deployment should recheck with the required privilege boundary before apply.

## Non-Goals This Round

- creating htpasswd credentials
- creating `/srv/whalpha` directories
- uploading bundles
- enabling Nginx config
- reloading Nginx
- changing DNS, Cloudflare, TLS, firewall, SSH, or system services
