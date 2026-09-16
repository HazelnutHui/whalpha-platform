# Campaign Three Result Production Deployment Audit — 2026-09-16

## Scope

Deploy the already tested, committed Campaign Three result projection without
refreshing EOD, canonical data, Market Intelligence, or the Dashboard Snapshot.

## Immutable bindings

| Field | Value |
| --- | --- |
| Source revision | `250f423b01cbea7ac6ec1f16a43dcecb82b678ac` |
| OCI release | `2026-09-16T141001Z-250f423b01cb` |
| Dashboard Snapshot | `2026-09-11T211340Z-26cab64fabda` |
| Snapshot / Dashboard contract | 1.11 / 2.8 |
| Market Intelligence publication | `2026-09-11T205429Z-26cab64fabda` |
| Market Intelligence contract | 1.3 |
| Bundle file count | 63 |

## Execution and verification

The workstation bundle build completed from a clean `main` worktree. The OCI
deployment dry-run passed its remote preflight and Nginx configuration check.
The apply then completed its upload, checksum verification, atomic active
pointer switch, Nginx validation, and route checks.

An independent read-only inspection at `2026-09-16T14:11:04Z` verified:

- active release and source revision match the immutable bindings above;
- manifest SHA-256 is
  `cb09b665ac054defbaa7f908acf59de49fd4eb9c3432fc4588232c14f0d4ae64`;
- checksums SHA-256 is
  `462c7e7b945b06b3b984f1e9649f06b7963bcf052be208ab96a4368896d2cdca`;
- bundle logical fingerprint is
  `bc77ba3c30f7fa10d4403404de0094cead422571b1744c4874a058ef84cb94f8`;
- Nginx and authentication services are active and enabled;
- the authentication listener is localhost-only with no unexpected private
  listener;
- protected routes and a temporary guest Session pass;
- guest and credential routes retain identical policy; and
- no failed release, staging release, or failed system unit remains.

Password login was not exercised because the read-only inspector does not read
credentials. Final browser appearance remains a human visual check. No EOD,
Identity, canonical data, Snapshot, Market Intelligence, scheduler, or research
result was changed by this deployment.
