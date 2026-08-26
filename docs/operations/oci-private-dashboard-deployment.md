# OCI Private Dashboard Deployment

## Purpose

This runbook records the current private static Dashboard deployment boundary
and the reviewed build, apply, verification, rollback, and retention flow.
Historical release-by-release troubleshooting belongs in Git history and the
project changelog, not in this current runbook.

## Live-verified state

Verified through the `whalpha-oci` SSH alias and deployment postflight on
2026-08-26 without reading credentials:

- `/srv/whalpha/current` resolves to
  `/srv/whalpha/releases/2026-08-26T094339Z-f9711d5403f6`;
- the release is built from source commit
  `f9711d5403f60cd70a93b50ee314ab38a6af24a2`;
- it binds Market Intelligence `2026-08-24T043223Z-aee1a6ab0f67` and
  Snapshot `2026-08-24T045652Z-aee1a6ab0f67`;
- it serves Snapshot 1.5 / Dashboard 2.2, `en` and `zh`, English by default,
  and the exact one-session-lag `stale_review` payload;
- the deployment manifest declares no credentials, raw payload, or Parquet;
- Nginx and `whalpha-dashboard-auth.service` are active and enabled;
- the Auth Service listens only on `127.0.0.1:8010`;
- an unauthenticated loopback HTTPS check returns 200 for `/`, redirects
  `/dashboard/` to `/?next=/dashboard/`, returns 401 for private data and
  `/auth/status`, and returns 404 for external `/auth/internal-verify`;
- no staging or partial release residue exists; and
- the current release, immediate rollback `2026-08-26T062038Z-895a073769ad`,
  and older reviewed rollback `2026-08-19T083341Z-7ed7fdc21686` are retained
  temporarily pending authenticated visual verification and exact cleanup.

Authenticated browser behavior was not tested because the verification did not
read or use the user's password.

## Immutable bundle boundary

The builder requires an explicit immutable Snapshot path and Market
Intelligence publication. It rejects a contract other than Snapshot 1.5 /
Dashboard 2.2, identity mismatch, missing analytics, or fewer than 16 registered
relationships. It freezes locales `en` and `zh`, default locale `en`, and the
analytics checksum and logical identity.

The production React graph contains no static dependency on the synthetic
Dashboard fixture. Development demo mode loads it lazily only behind the Vite
development guard. API and Snapshot failures fail closed. Production build and
candidate review reject emitted assets containing the known demo markers.

Production bundles must not contain credentials, canonical Parquet, raw
provider payload, or unrestricted source data.

## Local build flow

```bash
scripts/admin/build-private-dashboard-snapshot.sh
scripts/admin/build-oci-dashboard-bundle.sh \
  --snapshot-path <immutable-snapshot-absolute-path> \
  --market-intelligence-publication <publication-id> \
  --bundle-release <release-id>
scripts/admin/deploy-private-dashboard-oci.sh \
  --bundle-release <release-id> --dry-run
scripts/admin/deploy-private-dashboard-oci.sh \
  --bundle-release <release-id> --apply
```

The snapshot exporter and bundle builder write ignored artifacts beneath
`build/private-dashboard/` and `build/oci-dashboard/`. Follow the
[build and release retention policy](local-build-artifact-retention.md).

## Apply flow

An authorized apply must:

1. verify local host, source-of-truth repository, branch, clean tree, and bundle
   checksum inventory;
2. verify remote host/user, exact target paths, service state, TLS, and auth-file
   metadata without reading credential content;
3. upload to a new staging directory and verify remote checksums;
4. atomically promote the release and switch `/srv/whalpha/current`;
5. test Nginx configuration before reload;
6. verify the login page, compatibility redirect, unauthenticated Dashboard
   redirect, protected JSON, auth status, and internal-only verification route;
7. leave authenticated login as a manual user check; and
8. retain the prior reviewed rollback release until a later exact cleanup.

Deployment, rollback, password rotation, publication, Snapshot creation, and
bundle creation are separate explicit approvals.

## Session boundary

- `/` is the public, data-free branded Session login page.
- `/login/` is a compatibility redirect to `/`.
- `/auth/login` and `/auth/logout` proxy to the localhost-only Auth Service.
- `/auth/status` exposes only authentication state.
- `/auth/internal-verify` is an Nginx internal location.
- `/dashboard/` and `/private-data/` use the same `auth_request` check.
- The session cookie is secure, HttpOnly, SameSite=Lax, host-only, and scoped to
  `/`; an Auth Service restart invalidates in-memory sessions.

## Password rotation

The deployed helper is:

```bash
sudo /srv/whalpha/admin/rotate-whalpha-dashboard-password.sh
sudo /srv/whalpha/admin/rotate-whalpha-dashboard-password.sh --apply
```

It defaults to dry-run and accepts a real password only through an interactive
hidden TTY prompt. The password, hash, session token, and credential file
contents must never enter chat, Git, command arguments, environment output, or
logs. See [Private Dashboard Access](private-dashboard-access.md).

## Non-goals

- changing DNS, Cloudflare, TLS, firewall, SSH, or unrelated system services;
- reading or outputting passwords, hashes, cookies, or private keys;
- treating unauthenticated probes as authenticated browser verification; or
- converting the personal Session boundary into public provider-data access.
