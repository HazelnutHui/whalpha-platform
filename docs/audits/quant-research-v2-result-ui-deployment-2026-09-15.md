# Factor Discovery V2 Result UI Deployment Audit — 2026-09-15

## Verdict

Deployed and independently verified, pending only the user's manual visual and
password-login check.

## Release

- Release: `2026-09-15T215904Z-286334f`
- Source: `286334f256d52675fd0cffa6432e3cffcbff8f12`
- Bundle logical fingerprint:
  `7651ebc543be096cc6b5b7c2b97992d91bcb905c98e2c83b1e3eb933d580fc0a`
- Manifest SHA-256:
  `5a3363719839cd772b95e578b47cf498309861a1dab3511fd96104befcc247bd`
- Checksums SHA-256:
  `64e8276440a506e2de63d5a23bda1c033140f0708959a81502c38dcb6db14c42`
- Remote-state fingerprint:
  `fdc8b37074b6024b6e3f7590583cca7fe6ef6a793b00b3a4841bac1040074a36`

## Change boundary

This was a UI-only release over the existing immutable Snapshot
`2026-09-11T211340Z-26cab64fabda` and Market Intelligence publication
`2026-09-11T205429Z-26cab64fabda`. It changed no `/data`, analytics,
Candidate calculation, Universe, Session capability, provider input, or
research result.

The public entry dossier and protected Quant Research Lab now agree that V2 is
closed with four rejected candidate-Alpha trials, two qualified-but-unselected
risk guards, an exact replay, 14 cumulative trials, zero model inputs, and a
new unregistered Factor Discovery design boundary. English, Chinese, and
Spanish carry the same meaning.

## Verification

- deployment dry-run matched the exact prior release;
- target bundle and remote checksums matched;
- Nginx and the localhost-only Auth Service are active and enabled;
- guest Session and protected routes passed;
- guest and credential route policies remain identical;
- no failed release, staging residue, failed system unit, or unexpected private
  listener remains; and
- password login and final appearance were not automated and remain manual
  checks.

