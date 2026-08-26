# Deployment Boundary

## Confirmed

The development source of truth is the workstation. No desktop folder or manual copy should become authoritative.

OCI is a deployment target, not a development source of truth. It serves the
versioned static Dashboard through Nginx and a localhost-only Session Auth
Service; no production market-data API runs there.

Application data should not be committed to Git. Secrets must use environment/configuration outside Git.

Deployment must remain reproducible, simple, and compatible with the OCI memory
constraint.

## Provider-Backed Data Boundary

The public branded login must remain data-free. Any provider-backed content,
including derived heatmaps, analytics, research, API responses, or static
exports based on restricted provider data, requires the
[Data Access Boundary](data-access-boundary.md) pre-deployment gate.

The static Dashboard is deployed behind the branded Session entry.
Public `/` contains no market data. `/dashboard/` and `/private-data/` are
protected by the same server-side Session boundary.

Equal-capability guest entry is implemented through the same role-free Session
as credential login. A public/multi-user identity model, per-user private state,
and role-dependent product access are not implemented or authorized.
