# Deployment Boundary

## Confirmed

The development source of truth is the workstation. No desktop folder or manual copy should become authoritative.

OCI is a deployment target, not a development source of truth. Nginx/HTTPS currently exist and can later proxy to a lightweight application.

Application data should not be committed to Git. Secrets must use environment/configuration outside Git.

## Proposed

Deployment should be reproducible, simple, and compatible with the OCI memory constraint.

## Provider-Backed Data Boundary

The public placeholder may remain data-free. Any provider-backed content, including derived heatmaps, analytics, research, API responses, or static exports based on restricted provider data, requires the [Data Access Boundary](data-access-boundary.md) pre-deployment gate before deployment.

No deployment, whalpha.com, OCI, Nginx, Cloudflare, or access-control change is performed by this documentation update.

## Unknown

No deployment approach has yet been selected. The exact private access-control mechanism for provider-backed data remains undecided.
