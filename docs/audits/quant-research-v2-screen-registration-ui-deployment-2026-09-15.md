# Factor Catalog V2 Screen-Registration UI Deployment Audit

## Scope

This audit records the UI-only release that synchronized the public landing
dossier and protected Quant Research Lab with the frozen ADR 0281 Development
screen and cumulative ledger V2. It changed no factor outcome, market analytic,
Baseline V1 calculation, canonical data, access capability, or trading boundary.

## Local evidence

- Source: `d774d87f37a20c402bf57d31f0d82acc105ef1ec` on clean `main`.
- Release: `2026-09-15T170757Z-d774d87f37a2`.
- Reused immutable Dashboard Snapshot:
  `2026-09-11T211340Z-26cab64fabda`, Snapshot 1.11 / Dashboard 2.8.
- Reused Market Intelligence publication:
  `2026-09-11T205429Z-26cab64fabda`, contract 1.3.
- Bundle logical fingerprint:
  `599caa5818b6cf84f860369099ce208112e08a6ae7766ed0f5bcf699d09db9ff`.
- Completed bundle: 63 regular files; deployment-manifest SHA-256
  `9b4f295d6181e1869b39128eace8c37819fd175fdce3fe2dcf6337de46b62db7`;
  checksums-file SHA-256
  `ca9fd1a1b03d5d03189ca05cce090b76f94bb7788f44391db49cde6d520114d2`.
- All 126 frontend tests and the TypeScript/Vite Production build passed.

## Deployment evidence

The independent preflight found prior release
`2026-09-15T164234Z-188c7ae00193` active, the target absent, all protected and
guest routes healthy, zero failed system units, no unexpected listener, and no
staging or failed-release residue. Its state fingerprint was
`3ea2af7f66e07e4977ea00ef045e5a45905e36c5629f838c8a3fc3866d386903`.

Dry-run verified the exact current release, source-bound bundle, checksums,
Nginx configuration, authentication boundary, and residue. Apply uploaded and
checked the immutable target, promoted it, and atomically switched the current
pointer while retaining the prior release for rollback.

The 2026-09-15T17:09:12Z independent postflight verified the intended release,
source revision, manifest, checksums, bundle fingerprint, Nginx,
localhost-only Auth Service, protected routes, equal-capability guest Session,
zero failed units, and zero staging/failed residue. Its state fingerprint was
`f47a674c22770295e3d9a45498c2dc96f731490d0be042fdeb7d3eee2c4f3a49`.
Live public assets were read back with the English, Chinese, and Spanish
screen-registered/outcomes-unread copy. Password login and final visual
appearance remain manual checks.

## Research boundary

The UI now reports the exact registered scope: four candidate-Alpha and two
risk-guard trials, 14 cumulative trials, 106 Development sessions, 167,860
declared paths, a three-session primary horizon, one- and five-session decay,
and zero read V2 outcomes. Registration authorizes only exact implementation,
one immutable Development report, and one exact replay. Model Construction,
Strategy Expression, Validation, Holdout, Candidate activation, options,
performance claims, and trading remain locked.
