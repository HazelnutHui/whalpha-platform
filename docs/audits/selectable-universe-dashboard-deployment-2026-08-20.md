# Selectable Universe Dashboard Deployment Audit — 2026-08-20

## Result

`deployed_pending_manual_authenticated_universe_verification`

Release `2026-08-19T083341Z-7ed7fdc21686` was built from Git commit `7ed7fdc21686...` using the completed 2026-08-19 activation. The private snapshot is contract 1.3 and contains full Common Shares and Common Shares + ADRs Dashboard payloads, with Common Shares as default.

The bundle contained 13 checksummed files: static Dashboard assets, branded login assets, deployment metadata, and five private snapshot files. It contained no Parquet, source map, credential, private key, `.env`, raw payload, or `node_modules` content. Deployment dry-run passed before apply. Apply passed Nginx checks and selected the new versioned release while retaining prior releases.

Unauthenticated verification passed:

- `/`: 200 branded WH Alpha login page;
- `/login/`: 302 to `/`;
- `/dashboard/`: 302 to `/?next=/dashboard/`;
- `/private-data/v1/manifest.json`: 401 JSON with `private, no-store`;
- `/auth/status`: 401, empty body, `private, no-store`;
- `/auth/internal-verify`: 404.

On OCI, `whalpha-dashboard-auth.service` and Nginx were active, Nginx configuration tested successfully, and Auth Service listened only on `127.0.0.1:8010`. Ports 8000, 8001, and 5173 had no listener. Automated verification used no real password; authenticated selector and visual verification remain a user task. Restarting the Auth Service may invalidate the previous browser session, so the user may need to sign in again.

No Massive, SEC, provider, credential, canonical-data, scheduler, EOD/backfill, firewall, TLS, SSH, password, or storage operation occurred.
