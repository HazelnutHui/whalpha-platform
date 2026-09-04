# Private Dashboard Publication

## Current deployed boundary

The [Dashboard Snapshot V2 contract](../data-contracts/dashboard-snapshot-v2.md)
and [operations boundary](../operations/dashboard-snapshot-publication.md)
define the formal Universe Funnel, immutable releases,
approval-plan-bound atomic publication, active-pointer compatibility fallback,
verify-then-link recovery, separate rollback, and lock-time XNYS freshness
gate. Production supports the additive Snapshot 1.11 / Dashboard 2.8 boundary;
exact active release, source bindings and health evidence belong in
[current context](../project/current-context.md).

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
- Serving Bundle 1.0 whole-file reader and daily local construction custody
- Nginx configuration template using session `auth_request`
- deployment script with dry-run and reviewed apply mode
- dedicated dell5820-to-OCI deployment SSH key
- versioned OCI releases bound to exact clean source commits
- branded credential-or-guest `/` entry, `/login/` compatibility redirect, and
  localhost-only Auth Service

Not implemented:

- automatic daily publication and deployment

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
  market-overview.json
  market-summary.json
  movers.json
  liquidity-map.json
  market-regime-overviews.json
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
  favicon.png
  dashboard/
    index.html
    favicon.png
    assets/...
  private-data/v1/
    manifest.json
    market-overview.json
    market-summary.json
    movers.json
    liquidity-map.json
    market-regime-overviews.json
  deployment-manifest.json
  checksums.sha256
```

The bundle excludes source maps, credentials, `.env`, raw payloads, Parquet files, backend virtualenvs, `node_modules`, and database files.

## Security Boundary

`/dashboard/` and `/private-data/` must be protected by the same server-side session boundary. `/private-data/` must not fall back to the SPA index. Public `/` is the branded Session entry and must not expose provider-backed market data before a Session exists.

The existing htpasswd file remains the server-side credential store for the owner login. Browser-native Basic Auth is replaced by a branded entry page, opaque in-memory Sessions, and an HttpOnly `__Host-whalpha_session` cookie. `POST /auth/guest` creates the same role-free Session without accepting a credential; guest and credential Sessions have no data or capability difference.

The deployment verifies that public `/` remains data-free, public
`/favicon.png` is a valid PNG, `/login/` redirects to `/`, unauthenticated
`/dashboard/` redirects to `/?next=/dashboard/`, and unauthenticated
`/private-data/` returns 401. It also creates a temporary guest Session, reads
the same Dashboard and private Snapshot through it, logs it out, and removes
the local cookie jar without printing the token. Password-based visual
verification remains a user browser check; Codex does not know or handle the
password.

## Login Route Verification

The deployment gate is content-aware: public `/` must contain branded entry markers, username/password fields, `Sign In`, and the guest control, and must not contain the retired placeholder marker. `/login/` must redirect to `/`. HTTP 200 alone is not accepted as proof of correct routing.

## Login Submission Boundary

Login form submission is part of the deployment boundary. The static login page must prevent native form navigation and submit JSON to same-origin `/auth/login`; deployment verification checks login JavaScript and CSS assets plus one controlled invalid-login request using fictitious credentials.
