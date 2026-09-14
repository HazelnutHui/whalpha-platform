# Strong-Leader Pullback Corrected Listed Reference and Gap V3 Audit

Date: 2026-09-14

## Scope

Complete the SCS/HNI listed-reference step without network access, `/data`
writes, holder-election inference, terminal outcomes, or research admission;
then extend the immutable terminal-gap worklist without rewriting V2.

## Evidence result

- HNI source/SEC/canonical identity gate: `strict_stable_security_match`
- assigned stable ID: `8bde034d-a7f8-5dce-a432-134c583eb9ac`
- valuation session: 2025-12-10
- HNI unadjusted close: 42.5400000000 USD
- cash alternative: 16.2282860000000000 USD
- mixed/default alternative: 16.5247680000000000 USD
- stock alternative: 16.7607600000000000 USD
- sensitivity range: 0.5324740000000000 USD
- actual holder election: unknown
- adjustment/proration mechanics: unresolved

The listed-reference report is at
`historical-evidence/strong-leader-pullback-terminal-population-listed-reference/adjudication=20260914-v1`.
Its implementation revision is
`cdf38e85f7fc86e5391a2882f31fbad73db3588f`, SHA-256 is
`86221d53e36b4ff8b2b56f1c7d6eefd893681ac66c4b62c92ca8ae2974f5e71e`,
and logical fingerprint is
`df154b5086d10527e1367c73d7980bf5ef5801d67d65d513829b49edf2b201b4`.

Terminal-gap census V3 is at
`historical-evidence/strong-leader-pullback-terminal-gap-census-v3/census=20260914-v3`.
Its implementation revision is
`f44e69df2dff68e91fcc026c8fd06acbf7f59062`, SHA-256 is
`8c3f4f960218eaded49fabf3503865a24a885eb118b0e96ab2aeddfa51288462`,
and logical fingerprint is
`d94b5f22397df2b1fe49ac2c2c12e5f04d8617b076c8b95fb2e8127c886aa57e`.

The corrected population remains 65 securities / 302 five-session paths.
Documented references are now 43 securities / 197 paths; 22 / 105 remain.
Only the SCS stable-ID decision changed from V2.

## Verification

- four direct listed-reference tests passed;
- 21 linked terminal tests passed;
- the complete API suite passed 2,778 tests with two unchanged dependency
  warnings in 270.98 seconds;
- ten V2/V3/reference focused tests passed after the V3 extension;
- both formal packages replayed as `already_present`;
- package/report modes are `0700/0400` with no symlink or partial residue; and
- network requests, canonical writes, terminal outcomes, Historical Coverage,
  research admission, Candidate, publication, deployment, and scheduler
  changes are zero.

## Next gate

Use V3 as the terminal worklist. Address the nine cessation-timing cases and
three legacy exceptional cases before CVR, remaining election/proration, and
unlisted-unit policies. A daily reference is not yet a strategy outcome.
