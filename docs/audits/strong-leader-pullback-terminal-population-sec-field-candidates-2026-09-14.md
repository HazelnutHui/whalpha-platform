# Strong-Leader Pullback Terminal-Population SEC Field Candidates Audit

Date: 2026-09-14

## Scope

Apply the established form-aware extractors to the authoritative three-file
SCS source package. No historical 64-case decision was imported. The operation
was zero-network and did not read credentials, write `/data`, adjudicate a
lifecycle fact, calculate an outcome, change research admission, publish
Candidate data, deploy, or modify a scheduler.

## Result

- output: `extraction=20260914-v1/field-candidates.json`
- implementation revision: `4b5f44524e235ae0426dc602e1ca504d97739823`
- evaluated at: `2026-09-14T07:15:45Z`
- one stable `instrument_id` and three source documents
- forms: one 25-NSE, one 8-K, and one 15-12G
- 8-K structure: `8k_item_2_01_candidate_scope`
- report bytes: 17,883
- report SHA-256:
  `f64a9df580409e426b31032cce602c1d14ff077f1d7e887736ea8812c09c41fd`
- logical fingerprint:
  `c351199c90fb5016900980841a776eb61dbdef7a0d24887c8c0ea78e208ff5a3`

The Form 25 candidate contains CIK `0001050825`, Commission file number
`001-13873`, issuer `STEELCASE INC`, `NEW YORK STOCK EXCHANGE LLC`, `Class A
Common Stock`, rule `17 CFR 240.12d2-2(a)(3)`, and signature date 2025-12-10.

The Form 15 candidate contains the same CIK and Commission file number,
`Class A Common Stock`, `5.125% Senior Notes due 2029`, certification date
2025-12-22, and selected Rules 12g-4(a)(1) and 12h-3(b)(1)(i).

The structured 8-K candidate contains transaction-scope candidates for
consideration, party/successor relations, suspension/delisting, completion,
and effective time. Its bounded date candidates include 2025-12-10. All are
candidate locations rather than adjudicated values.

## Verification

- exact replay returned `already_present` with zero network requests;
- custody and output directory modes are `0700`, report mode is `0400`;
- no symlink, partial, or staging residue was found;
- 14 focused/linked tests passed;
- the complete API suite passed 2,763 tests with two unchanged dependency
  deprecation warnings; and
- all complete lifecycle-field support, fact, outcome, performance, admission,
  canonical-write, publication, deployment, and scheduler counters remain
  zero.

## Next bounded gate

Adjudicate cover identity and transaction fields from the exact source chain.
Form fields and candidate contexts cannot be promoted by presence alone.
