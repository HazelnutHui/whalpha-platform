# China A-Share Market Selector Deployment Audit — 2026-09-17

## Scope

Deploy a dedicated, explicitly unadmitted China A-share option in the protected
Market / Universe selector. The release adds separate A-share Lab and
Model-Driven Selection readiness pages, prevents U.S.-only workspaces and rows
from rendering under A-share, and moves the prior A-share status dossier out
of the U.S. Lab. It does not refresh EOD, mutate `/data`, publish A-share
row-level records, or open research or Product authority.

## Immutable bindings

| Field | Value |
| --- | --- |
| Source revision | `a3bd55bff60d673573fa766fe7146ec28958d3d0` |
| OCI release | `2026-09-17T054505Z-a3bd55bff60d` |
| Dashboard Snapshot | `2026-09-11T211340Z-26cab64fabda` |
| Snapshot / Dashboard contract | 1.11 / 2.8 |
| Market Intelligence publication | `2026-09-11T205429Z-26cab64fabda` |
| Market Intelligence contract | 1.3 |
| Bundle file count | 64 |

## Product boundary

The A-share Lab surface displays completed pilot evidence and the current
adjustment-versus-corporate-action gate. It explicitly models A-share-specific
T+1 inventory timing, effective-dated price limits, locked-limit fill
uncertainty, suspension/resumption, listing age, lot and account eligibility,
long-only constraints, separate execution/adjusted/total-return layers,
point-in-time Universe decisions, market-state conditioning, cross-sectional
normalization, horizon-specific tests, and disclosure availability time.

The A-share selection-readiness view reports zero admitted Universe, zero
rankings, and zero models. The six SSE/SZSE pilot securities are evidence
anchors rather than an investable stock pool. U.S. market tools are disabled
under the A-share selection, direct A-share/free-tool URLs normalize to the
A-share Lab, and no U.S. Candidate page is rendered.

## Verification

All 135 frontend tests and the Production frontend build passed before bundle
creation. The deployment dry-run passed remote preflight and Nginx validation.
The apply completed checksum verification, atomic release switch, Nginx
validation, and route checks.

Independent read-only inspection at `2026-09-17T05:45:58Z` verified:

- active release and source revision match the bindings above;
- manifest SHA-256 is
  `019c7b02cde660a0b007934a55798f0199aab0c3670094dba1f0e964f114b2a9`;
- checksums SHA-256 is
  `3d32456299a9c22f8f3b723387ee04139d08ebca47daca18768239a157fe773e`;
- bundle logical fingerprint is
  `79a66d0501eef6d0f36358268c91f08e8a75c548b404695c868f5166126bf24c`;
- Nginx and authentication services are active and enabled;
- the authentication listener is localhost-only with no unexpected private
  listener;
- protected routes and a temporary guest Session pass;
- guest and credential routes retain identical policy; and
- no failed release, staging release, or failed system unit remains.

Password login was not exercised because the inspector does not read
credentials. Final browser appearance remains a manual visual check. The
release changes only presentation and routing authority; it grants no A-share
backtest, Alpha, model, ranking, strategy, Product publication, or trading
authority.
