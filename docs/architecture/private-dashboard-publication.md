# Private Dashboard Publication

## Snapshot 1.4 / Dashboard 2.1 offline readiness

The [Dashboard Snapshot V2 contract](../data-contracts/dashboard-snapshot-v2.md) and [operations boundary](../operations/dashboard-snapshot-publication.md) add the formal 20-record Universe Funnel, immutable releases, approval-plan-bound atomic publication, active-pointer compatibility fallback, verify-then-link recovery, separate rollback, and a lock-time XNYS freshness gate. The production release remains contract 1.3 and unchanged. With canonical EOD at 2026-08-19 and expected latest at 2026-08-21, the offline candidate is `stale` with lag two and cannot create a production approval package.

## Classification Phase Boundary

Phase A audits do not produce a private snapshot or bundle. A later snapshot contract must carry the selected universe definition ID, version, as-of date, taxonomy fingerprint, and ruleset fingerprint so Pulse, Breadth, Movers, and Trading Activity Map reconcile to identical membership.

Snapshot contract 1.3 carries the completed activation catalog and full Primary/Secondary Dashboard payloads. Provider security-form evidence can be complete while issuer structure and domicile remain provisional.

## Purpose

This document records the static publication boundary for the private provider-backed Market Dashboard.

## Status

Deployed and manually authenticated by the user for the personal prototype.

Implemented locally:

- private dashboard JSON snapshot contract
- snapshot exporter
- frontend `snapshot` mode
- versioned OCI bundle builder
- Nginx configuration template using session `auth_request`
- deployment script with dry-run and reviewed apply mode
- dedicated dell5820-to-OCI deployment SSH key
- deployed OCI session-login release `2026-08-15T133119Z-137f244e8508`
- deployed OCI fresh Market Overview release `2026-08-14T224306Z-21d0e7fda749`, built from source commit `21d0e7fda749e3afec7edc9a884eb6408663004f`
- branded `/login/` page and localhost-only Auth Service

Not implemented:

- automatic daily publication

## Architecture

```text
dell5820
  Canonical Parquet
  -> Market Analytics
  -> Private Dashboard JSON Snapshot
  -> React production build
  -> Versioned deployment bundle

OCI
  /             public branded credential/guest Session entry page
  /login/        compatibility redirect to /
  /dashboard/    authenticated static dashboard
  /private-data/ authenticated JSON snapshots
```

The dashboard never connects to Massive. Provider credentials remain on the workstation and are not included in the bundle.

## Snapshot Contract

Each bundle contains:

```text
private-data/v1/
  manifest.json
  market-summary.json
  movers.json
  liquidity-map.json
```

`manifest.json` records contract version, release ID, generation time, activation fingerprint/catalog/default, session dates, freshness, file names, SHA-256 hashes, per-Universe node counts, warning count, and private access classification. Dashboard Overview JSON contains complete payloads for both activated universes. File consistency validation and calendar freshness are distinct.

The manifest explicitly records:

- `is_real_provider_backed=true`
- `access_classification=private`
- `contains_raw_provider_data=false`
- `contains_credentials=false`

It must not contain source filesystem paths, raw provider manifests, provider request IDs, account identifiers, credentials, headers, Parquet metadata, or full returns universe exports.

## Frontend Snapshot Mode

`VITE_MARKET_DATA_MODE=snapshot` reads static JSON from absolute same-origin paths under `/private-data/v1/`.

The production dashboard is built with `VITE_DASHBOARD_BASE=/dashboard/` so hashed assets load from `/dashboard/assets/...`.

API mode remains the default for workstation local development. Demo mode remains synthetic and clearly labeled.

## Bundle Layout

```text
build/oci-dashboard/<release-id>/
  dashboard/
    index.html
    assets/...
  private-data/v1/
    manifest.json
    market-summary.json
    movers.json
    liquidity-map.json
  deployment-manifest.json
  checksums.sha256
```

The bundle excludes source maps, credentials, `.env`, raw payloads, Parquet files, backend virtualenvs, `node_modules`, and database files.

## Security Boundary

`/dashboard/` and `/private-data/` must be protected by the same server-side session boundary. `/private-data/` must not fall back to the SPA index. Public `/` is the branded Session entry and must not expose provider-backed market data before a Session exists.

The existing htpasswd file remains the server-side credential store for the owner login. Browser-native Basic Auth is replaced by a branded entry page, opaque in-memory Sessions, and an HttpOnly `__Host-whalpha_session` cookie. `POST /auth/guest` creates the same role-free Session without accepting a credential; guest and credential Sessions have no data or capability difference.

The deployment verifies that public `/` remains data-free, `/login/` redirects to `/`, unauthenticated `/dashboard/` redirects to `/?next=/dashboard/`, and unauthenticated `/private-data/` returns 401. It also creates a temporary guest Session, reads the same Dashboard and private Snapshot through it, logs it out, and removes the local cookie jar without printing the token. Password-based visual verification remains a user browser check; Codex does not know or handle the password.

## Login Route Verification

The deployment gate is content-aware: public `/` must contain branded entry markers, username/password fields, `Sign In`, and the guest control, and must not contain the retired placeholder marker. `/login/` must redirect to `/`. HTTP 200 alone is not accepted as proof of correct routing.

## Login Submission Boundary

Login form submission is part of the deployment boundary. The static login page must prevent native form navigation and submit JSON to same-origin `/auth/login`; deployment verification checks login JavaScript and CSS assets plus one controlled invalid-login request using fictitious credentials.
