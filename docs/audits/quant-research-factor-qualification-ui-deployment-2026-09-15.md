# Quant Research Factor Qualification UI Deployment Audit — 2026-09-15

## Scope

This audit records the UI-only deployment that synchronized Quant Research Lab
with the completed outcome-blind Factor Qualification V1 report. The page now
shows the current three-layer direction, evidence boundary, qualification
counts, factor roles, all 12 exact formulas, point-in-time timing, missingness
policy, limitations, and reproduction identities in English, Simplified
Chinese, and professional neutral Spanish.

The deployment reused the immutable 2026-09-11 Dashboard Snapshot and Market
Intelligence publication. It did not fetch or Apply market data, rebuild
analytics, read an outcome, admit a factor, construct a model, define a
strategy expression, activate Stock Candidates, change access capability, or
change any broker/order boundary.

## Local evidence

- Clean source revision:
  `bfcd55bae038313169d9b9bf88d9d8b59645f1ff`.
- Release: `2026-09-15T101225Z-bfcd55bae038`.
- Immutable source Snapshot:
  `2026-09-11T211340Z-26cab64fabda`, Snapshot 1.11 / Dashboard 2.8.
- Market Intelligence publication:
  `2026-09-11T205429Z-26cab64fabda`, contract 1.3.
- Serving Bundle logical fingerprint:
  `4851ce296f6c295e80e2dced561023e9e84cdc19e66bc04827fbb63c1548b9ed`.
- Source Snapshot manifest SHA-256:
  `3d968480754e07a589ebc467848db19a74e95ac442598e964726146f3d112e3c`.
- Completed bundle: 63 regular files; deployment-manifest SHA-256
  `10e662aa7d9b0a22a1cbba15842093eaad2286525f0440736067e046aa928e08`;
  checksums-file SHA-256
  `b1109734a75383ab23c745400212a4fbc898ab4d3e8e5630ef6d9d051ca06d6b`.

Before bundling, the implementation passed all 2,922 backend tests, all 126
frontend tests, the production TypeScript/Vite build, local Markdown target
validation, exact catalog-to-public-record comparison, exact private-report-
to-public-summary comparison, and a full independent 287-session diagnostics
replay. The Lab lazy chunk remains 21.70 kB gzip; the new disclosure did not
move its content into the login or initial application bundle.

## Preflight and Apply

The independent preflight at 2026-09-15T10:12:38Z found the prior release
`2026-09-15T083410Z-45b1d4dfedca` active, the target absent, protected routes
and a bounded guest Session valid, Nginx and the localhost-only Auth Service
healthy, and zero staging releases, failed releases, failed units, or
unexpected private listeners. State fingerprint:
`ac21fd4c728eace6e576011d2f4daf82063992591ea94ae1b86af123ebd4d7c9`.

The deployment dry-run rechecked the exact current release, clean source,
bundle revision and checksums, Nginx configuration, authentication boundary,
and residue before mutation. Apply uploaded to a new staging path, verified
the complete checksum inventory, promoted the immutable release, switched the
current pointer atomically, retested Nginx, and completed the guarded guest-
Session flow. The prior release remains the immediate rollback candidate.

## Independent postflight

The postflight at 2026-09-15T10:13:46Z verified:

- current release and deployed source match the intended target;
- the remote manifest, checksums, and bundle logical fingerprint match Dell;
- Nginx and the Auth Service are active and enabled;
- the Auth Service listener remains localhost-only;
- unauthenticated Dashboard and private-data protection is correct;
- a bounded guest Session read the Dashboard and exact private manifest, then
  logged out successfully;
- guest and credential route policy remains identical; and
- no staging release, failed release, failed unit, or unexpected private
  listener remains.

Final remote-state fingerprint:
`2bfaeb489eb395097a38c1034a132ea3be7750158ee210a8e67b8418bd490a41`.
Credential login was not tested and final appearance remains a manual browser
check by the user.
