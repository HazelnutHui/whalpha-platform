# Deployment Boundary

## Confirmed

The development source of truth is the workstation. No desktop folder or manual copy should become authoritative.

The public GitHub repository
`https://github.com/HazelnutHui/whalpha-platform` is the versioned code,
documentation, test, schema, and compact research-evidence mirror. It is not a
data store, computation authority, credential store, deployment target, or
substitute for workstation custody. Only reviewed Git-tracked content may be
pushed. Provider source data, canonical datasets, database files, model
artifacts, caches, local configuration, credentials, private keys, and other
restricted or machine-local state remain outside Git.

The workstation uses a repository-specific GitHub authentication identity.
Never reuse the OCI deployment identity for GitHub and never document or copy
private-key material into the repository. Before every public push, require a
clean worktree and inspect both current tracked content and Git history for
credentials, private keys, disallowed datasets, and oversized artifacts.

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
