# Reconciled EOD Family-Evidence Publication Plan Audit — 2026-09-12

## Boundary

Build and independently reread one immutable, edition-specific publication
plan for the two unpublished Historical Dataset Coverage Evidence candidates
validated in ADR 0210. The run was offline and wrote only the owner-readable
plan in direct `/tmp` custody. It did not publish either evidence manifest,
write `/data`, create Historical Coverage, authorize research, or change
Production.

The implementation is governed by ADR 0211 and source revision
`b279a04abf1dcf5e011d31439cc17c06937f2a7e`.

## Exact source binding

- Reconciled EOD edition:
  `reconciled-eod-v12-20210913-20260812-c798e58`;
- interval-manifest fingerprint:
  `098ff756a463c0bf142d9ce597375e3a0574db02ca641fcdcef9b6e72cb6b5e3`;
- interval: 1,234 sessions from 2021-09-13 through 2026-08-12;
- EOD evidence: 10,376,263 records, 1 artifact, 2,469 bound source files,
  logical fingerprint
  `b65ee35bb65796dab501d4e59df132bffc566452c713bb18e8659401b632b0a5`;
- Identity evidence: 10,472,243 instrument-snapshot records, 1,234 artifacts,
  8,638 bound source files, logical fingerprint
  `faaa73bceace816d91a5a2483714055d20c48091fe4fc8bfbcde8c27d8b647db`.

Both exact canonical target paths were absent and had no staging residue. The
plan allows an inventory change of exactly two files and 2,673,980 bytes.

## Plan identity and verification

- contract:
  `reconciled-eod-historical-family-evidence-publication-plan/1.0`;
- operation: `publish_reconciled_eod_historical_family_evidence`;
- plan path:
  `/tmp/whalpha-reconciled-eod-family-evidence-plan-20260912.json`;
- plan file SHA-256:
  `d328f1725dc4a74a6237d30e1ccdad6fa8c64765d45210a8cc7a76d6492f9168`;
- plan logical fingerprint:
  `443d80c7347b794b7f105c2d8b5dc8e57fbc4d4dd67442773983647d69d0fcfc`;
- family-set fingerprint:
  `30722680a6d2f8448db0e895fed7e060ca8a81f2d5faebca3b4d23fbba2b0d8e`.

The eight-worker source validation and plan build completed in 379.53 seconds.
An independent exact-SHA reread completed in 9.82 seconds and reproduced every
source, evidence, plan, family-set, target-state, count, and byte binding.
The complete API suite passed 2,531 tests with only the two existing dependency
deprecation warnings.

## Result and next boundary

The plan remains `ready_for_separate_review` with
`apply_authorized=false`, `canonical_data_write_count=0`,
`historical_coverage_authorized=false`, and both research authority fields
false. No canonical evidence publication occurred.

ADR 0212 subsequently extended the existing recoverable Apply path to recognize
this distinct contract and operation. Its complete API regression passed, but
the real plan was not executed. Executing it still requires separate approval
bound to this exact plan SHA, logical fingerprint, and family-set fingerprint.
Membership, lifecycle, actions, adjustments, final Historical Coverage,
research, and Production remain later independent gates.
