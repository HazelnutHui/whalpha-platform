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
  `/srv/whalpha/releases/2026-08-26T151600Z-1f3eb5512eb0`;
- the release is built from source commit
  `1f3eb5512eb0d1ba67112395450c2783221596da`;
- it binds Market Intelligence `2026-08-24T142500Z-1f3eb5512eb0` and
  Snapshot `2026-08-24T144500Z-1f3eb5512eb0`;
- it serves Snapshot 1.6 / Dashboard 2.3, the bounded Stock Candidate
  workspace, `en` and `zh`, English by default, and the exact one-session-lag
  `stale_review` payload;
- the deployment manifest declares no credentials, raw payload, or Parquet;
- Nginx and `whalpha-dashboard-auth.service` are active and enabled;
- the Auth Service listens only on `127.0.0.1:8010`;
- an unauthenticated loopback HTTPS check returns 200 for `/`, redirects
  `/dashboard/` to `/?next=/dashboard/`, returns 401 for private data and
  `/auth/status`, and returns 404 for external `/auth/internal-verify`;
- deployment postflight creates a temporary guest Session, verifies the same
  Dashboard and Snapshot 1.6 Candidate payload are readable, logs out, and
  removes the local cookie jar without printing it;
- no staging or partial release residue exists; and
- the current release, prior releases `2026-08-26T103119Z-f344a589a8c9` and
  `2026-08-26T094339Z-f9711d5403f6`, and deliberate older selectable-Universe
  fallback `2026-08-19T083341Z-7ed7fdc21686` are retained.

Authenticated browser behavior was not tested because the verification did not
read or use the user's password.

## Immutable bundle boundary

The builder requires an explicit immutable Snapshot path and Market
Intelligence publication. It accepts only the exact Snapshot 1.5 / Dashboard
2.2 through Snapshot 1.8 / Dashboard 2.5 supported pairs and rejects identity mismatch,
missing analytics, or fewer than 16 registered relationships. For 1.6 it also
freezes and validates Candidate audit/parameter/display bindings and the
underlying-stock/price-proxy disclosure boundaries. It freezes locales `en`
and `zh`, default locale `en`, and the analytics checksum and logical identity.
For 1.7 it additionally validates Candidate publication 1.1, embedded entry
geometry, fixed lane order/counts, entry audit/parameter lineage, preserved
leadership rank, and the reference-support-not-stop-price boundary.
For 1.8 it additionally validates the summary fingerprint, ordered detail
shards, full-Candidate identity, and guest access to both the summary and one
declared detail shard.

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
6. verify the entry page, compatibility redirect, unauthenticated Dashboard
   redirect, protected JSON, auth status, and internal-only verification route;
7. create a bounded guest Session, prove it opens both Dashboard and the same
   private Snapshot, log it out, and prove the asset is protected again;
8. leave password-based browser login as a manual user check; and
9. retain the prior reviewed rollback release until a later exact cleanup.

Deployment, rollback, password rotation, publication, Snapshot creation, and
bundle creation are separate explicit approvals.

## Session boundary

- `/` is the public, data-free branded Session entry page.
- `/login/` is a compatibility redirect to `/`.
- `/auth/login`, `/auth/guest`, and `/auth/logout` proxy to the localhost-only
  Auth Service.
- Credential and guest entry create the same role-free Session; neither Nginx
  nor the Dashboard receives a capability distinction.
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
- adding unprotected provider-data routes or role-dependent product access.
