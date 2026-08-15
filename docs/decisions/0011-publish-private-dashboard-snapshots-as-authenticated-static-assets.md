# ADR 0011: Publish Private Dashboard Snapshots as Authenticated Static Assets

## Status

Accepted

## Date

2026-08-15

## Context

The workstation is the source of truth for canonical Parquet data, market analytics, and frontend builds. OCI is a lightweight public web-serving boundary with limited memory. Provider-backed market data and derived works must remain private until an access-control and provider-display boundary is accepted and implemented.

The current local React Market Dashboard V1 can consume private API responses, but running a backend on OCI is not required for the first private prototype deployment.

## Decision

Publish the private dashboard as versioned authenticated static assets.

The workstation produces:

```text
Canonical Parquet
-> Market Analytics
-> Private Dashboard JSON Snapshot
-> React production build
-> Versioned deployment bundle
```

OCI serves:

- public data-free placeholder at `/`
- private authenticated dashboard at `/dashboard/`
- private authenticated JSON snapshots at `/private-data/`

`/dashboard/` and `/private-data/` must use the same authentication boundary. Nginx Basic Auth is accepted as the V1 access-control mechanism for the personal prototype, with TLS as a mandatory prerequisite. Basic Auth is not a final multi-user identity system.

Massive credentials never leave the workstation. OCI receives only minimal dashboard-ready derived JSON, never raw provider payloads, canonical Parquet, API credentials, or provider account details.

Deployment uses versioned releases and an atomic `current` symlink switch. Rollback is a future symlink switch to a previous release. Password hashes and credentials must never enter Git, docs, chat, command arguments, or logs.

## Consequences

- OCI does not need a backend runtime or database for Dashboard V1.
- Static snapshots are suitable for the current low-resource OCI host.
- Public placeholder and private provider-backed dashboard remain separated.
- Public real-data display remains prohibited without separate authorization.
- A deployment bundle can be reviewed locally before any OCI write occurs.

## Alternatives Considered

- Run FastAPI on OCI: deferred because static snapshots are simpler and fit the current single-user EOD use case.
- Browser calls the workstation API: rejected for the current deployment boundary because OCI should not proxy unrestricted private provider-backed APIs to the workstation.
- Public static dashboard with real data: rejected under the accepted data-access boundary.

## Non-Goals

- creating the Basic Auth password
- uploading a bundle to OCI
- activating Nginx config
- deploying whalpha.com changes
- automatic daily publication
- Cloudflare Access or OIDC
- multi-user access control
- raw data or Parquet replication to OCI
