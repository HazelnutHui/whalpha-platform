# Deployment Boundary

## Confirmed

The development source of truth is the workstation. No desktop folder or manual copy should become authoritative.

OCI is a deployment target, not a development source of truth. Nginx/HTTPS currently exist and can later proxy to a lightweight application.

Application data should not be committed to Git. Secrets must use environment/configuration outside Git.

## Proposed

Deployment should be reproducible, simple, and compatible with the OCI memory constraint.

## Unknown

No deployment approach has yet been selected.
