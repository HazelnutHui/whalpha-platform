# Reusable Research Inputs and Guest Counter Deployment Audit — 2026-09-15

## Verdict

Deployed and independently verified, pending only manual visual and password-
login checks.

## Release

- Release: `2026-09-15T234025Z-30b0f10`
- Source: `30b0f101bceaaf8b80df760c9b4f8b3df31ba45a`
- Bundle logical fingerprint:
  `343b86edb1c36d6d079b9ff57162841ba51ed10ee4721559e4ecaa8bcfbbe403`
- Manifest SHA-256:
  `4e2b65f5e7b37c541e223f01089da04b58d46d727eb44ce444ae0ec3d4a0c837`
- Checksums SHA-256:
  `cfae1658c4d4a60c7204b3490c4e5b4166d0f6325e31d2cafabe69bc421948ed`
- Remote-state fingerprint:
  `7fee36c825f73421fe0dbf95da5be95bc0b51c22d4a3bc801848d2bd85a9ba68`

## Change boundary

The release reuses the existing immutable 2026-09-11 Snapshot and Market
Intelligence publication. It adds the reusable-input registry projection,
research-submission link, cumulative guest-entry endpoint/state, and footer.
It changes no canonical `/data`, analytics, Candidate calculation, Universe,
factor outcome, model authority, or guest/credential capability.

## Verification

- backend: 3,007 tests passed;
- frontend: 129 tests passed and the production build remained within enforced
  JavaScript and stylesheet budgets;
- deployment dry-run matched the exact prior release;
- Apply validated Auth Service state-file custody before switching current;
- independent postflight reconciled the release, source, bundle, manifest, and
  checksum identities;
- guest Session and protected routes passed with equal guest/credential policy;
- Nginx and the localhost-only Auth Service are active and enabled; and
- no failed release, staging residue, failed unit, or unexpected private
  listener remains.

The deployment guest check intentionally did not call `/auth/visit`, so it did
not consume the first real guest workspace entry. Password login and final
visual appearance remain manual checks.
