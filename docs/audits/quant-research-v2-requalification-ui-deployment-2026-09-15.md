# Factor Catalog V2 Requalification UI Deployment Audit

## Scope

This audit records the UI-only release that synchronized the public landing
dossier and protected Quant Research Lab with the ADR 0280 requalification.
It changed no market analytics, Baseline V1 calculation, research result,
canonical data, access capability, or trading boundary.

## Local evidence

- Source: `188c7ae00193e75c0386515a48bda32faca94457` on clean `main`.
- Release: `2026-09-15T164234Z-188c7ae00193`.
- Reused immutable Dashboard Snapshot:
  `2026-09-11T211340Z-26cab64fabda`, Snapshot 1.11 / Dashboard 2.8.
- Reused Market Intelligence publication:
  `2026-09-11T205429Z-26cab64fabda`, contract 1.3.
- Bundle logical fingerprint:
  `cf02ee34d310754a770325ee2c2205478f02e952b924067691111cb6f0dea28a`.
- Snapshot manifest SHA-256:
  `3d968480754e07a589ebc467848db19a74e95ac442598e964726146f3d112e3c`.
- Completed bundle: 63 regular files; deployment-manifest SHA-256
  `2dbf5208cc6343a8cad8d81fc2304a8ecf8c53b475cc9de89b3e0c273949edab`;
  checksums-file SHA-256
  `c835bb9e286c594c164cebafc2a32c84f1f84ef4ba5283a077d6f1be913d9ebf`.
- All 126 frontend tests and the TypeScript/Vite Production build passed.

## Deployment evidence

The independent preflight found prior release
`2026-09-15T142104Z-99b4467c0379` active, the target absent, all protected and
guest routes healthy, zero failed system units, no unexpected listener, and no
staging or failed-release residue. Its state fingerprint was
`f2ed93f86842ce524c6160ae23025aca690ea9eb21cb4ed6d859c8af463c5036`.

Dry-run verified the exact current release, clean source, target bundle,
checksums, Nginx configuration, authentication boundary, and residue. Apply
uploaded and checked the immutable target, promoted it, atomically switched the
current pointer, and retained the prior release as rollback.

The 2026-09-15T16:44:25Z independent postflight verified the intended release,
source revision, manifest, checksums, bundle fingerprint, Nginx, localhost-only
Auth Service, protected routes, equal-capability guest Session, logout, zero
failed units, and zero staging/failed residue. Its state fingerprint was
`d203dda6b08cf08bd639616f1946ad8d772795083560163b7b566635b40cafcb`.
The live public assets were also read back with the English, Chinese, and
Spanish qualification-pass copy. Password login and final visual appearance
remain manual checks.

## Research boundary

The UI reports 98.59% data qualification and eight definitions eligible for
screening-protocol review. It also states that no Alpha factor or model is
admitted. Model Construction, Strategy Expression, Validation, Holdout,
Candidate activation, option-performance claims, and trading remain locked.
