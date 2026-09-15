# Renewable Factor Discovery Cycle UI Deployment Audit — 2026-09-15

## Verdict

Deployed and independently verified, pending only manual visual and password-
login checks.

## Release

- Release: `2026-09-15T222626Z-9ef8bff`
- Source: `9ef8bff3107afb2abc8ddaad16a32c137d959cd0`
- Bundle logical fingerprint:
  `c5fa82692b77d8cb460542e22953d6b2fc27c8ca2f655019c6d644bfe0c6f2b0`
- Manifest SHA-256:
  `8615242d9682d5ef1bc6225078daf2d7570f5cbeadd3b75b72ab2cfc0848672d`
- Checksums SHA-256:
  `7240238ac8303517dd8faca8b9c052f2773d647d9642835a1c0c33ce985f5392`
- Remote-state fingerprint:
  `1ffe69bf4b490fd59701ecf4f40bb204be031d89df9f146b50a1579c8a39979d`

## Change boundary

This UI-only release reuses the existing immutable Snapshot and Market
Intelligence publication. It adds the trilingual renewable Factor Discovery
control panel and changes no `/data`, analytics, Candidate calculation,
Universe, research outcome, Session capability, or provider input.

## Verification

- frontend: 126 tests passed and the production build stayed within enforced
  JavaScript and stylesheet budgets;
- backend: 2,996 tests passed;
- deployment dry-run matched the exact prior release;
- remote bundle, manifest, and checksum identities reconcile;
- guest Session and protected routes passed with guest/credential parity;
- Nginx and the localhost-only Auth Service are active and enabled; and
- no failed release, staging residue, failed unit, or unexpected private
  listener remains.

