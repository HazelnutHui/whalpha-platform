# Private Dashboard Publication

## Purpose

This document records the static publication boundary for the private provider-backed Market Dashboard.

## Status

Deployed pending manual authenticated browser verification.

Implemented locally:

- private dashboard JSON snapshot contract
- snapshot exporter
- frontend `snapshot` mode
- versioned OCI bundle builder
- Nginx configuration template
- deployment script with dry-run and reviewed apply mode
- dedicated dell5820-to-OCI deployment SSH key
- deployed OCI release `2026-08-13T120220Z-987b5289a783`

Not implemented:

- authenticated browser verification
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
  /             public placeholder
  /dashboard/   authenticated static dashboard
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

`manifest.json` records contract version, release ID, generation time, session dates, file names, SHA-256 hashes, node counts, warning count, and private access classification.

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

`/dashboard/` and `/private-data/` must be protected by the same authentication boundary. `/private-data/` must not fall back to the SPA index. Public `/` remains the data-free placeholder.

Nginx Basic Auth is acceptable for this personal prototype only after TLS, password provisioning, and config review are complete.

The first deployment verified that public `/` remains unauthenticated and data-free, while `/dashboard/` and `/private-data/` return unauthenticated 401 responses. Authenticated visual verification must be performed by the user in a browser; Codex does not know or handle the password.
