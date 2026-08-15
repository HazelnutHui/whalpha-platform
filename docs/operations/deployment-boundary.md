# Deployment Boundary

## Confirmed

The development source of truth is the workstation. No desktop folder or manual copy should become authoritative.

OCI is a deployment target, not a development source of truth. Nginx/HTTPS currently exist and can later proxy to a lightweight application.

Application data should not be committed to Git. Secrets must use environment/configuration outside Git.

## Proposed

Deployment should be reproducible, simple, and compatible with the OCI memory constraint.

## Provider-Backed Data Boundary

The public placeholder may remain data-free. Any provider-backed content, including derived heatmaps, analytics, research, API responses, or static exports based on restricted provider data, requires the [Data Access Boundary](data-access-boundary.md) pre-deployment gate before deployment.

The first private static Dashboard release is deployed to OCI behind Basic Auth. Public `/` remains the data-free placeholder. `/dashboard/` and `/private-data/` are protected by the same server-side authentication boundary.


## Unknown

Nginx Basic Auth is the accepted V1 personal-prototype access boundary for the static Dashboard. It is not the final identity model for a public or multi-user product.
