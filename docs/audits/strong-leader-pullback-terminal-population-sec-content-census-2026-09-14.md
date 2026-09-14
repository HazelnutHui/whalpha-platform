# Strong-Leader Pullback Terminal-Population SEC Content Census Audit

Date: 2026-09-14

## Scope

Parse only the three primary SEC files in authoritative corrected-population
source V2. The operation was zero-network and did not read credentials, write
`/data`, adjudicate lifecycle fields, calculate outcomes, change research
admission, publish Candidate data, deploy, or modify a scheduler.

## Authoritative inputs

- plan: `plan=20260914-v2`
- plan SHA-256:
  `6986c5e1f2b5c9eb863f1db6284c65a47d25edb977dddee2633b8b34547a27f5`
- plan logical fingerprint:
  `3acbd745b320301c3aeb52db89e06ac58b07e64511ed13f348f5f1f0e61ab84a`
- source: `source=20260914-v2`
- source manifest SHA-256:
  `f0f2ab15129bd3acf4d8ef7d88ca04edf6df84cf625964aa8ab401d23fe96188`
- source logical fingerprint:
  `62e4d1d01cf9cd8215267e980fb8694820f51880cdcd2f176d5336e32f4b81b1`
- source artifact-binding fingerprint:
  `4a962b4a8c7eaed0e4148a2f5046047e98c0e64685a5896d4e58eaa89643ab9f`

## Result

- output: `census=20260914-v1/content-census.json`
- implementation revision: `6d373f679ecd058b8fed1339a88a0cb0982a1993`
- evaluated at: `2026-09-14T07:00:56Z`
- parsed documents: 3 / 3
- forms: one 25-NSE, one 8-K, and one 15-12G
- decoding: three UTF-8
- markup: one HTML, one SEC-SGML HTML, and one inline-XBRL XHTML
- physical bytes: 73,520
- normalized text characters: 20,343
- report bytes: 18,067
- report SHA-256:
  `0431de1dd61646ebc67c69f53a50db48ba91fbd8c741c9c99514e1345f3cbf87`
- logical fingerprint:
  `972ef6dd9aa83a7e8d04edfca24bbebff3d9fc70ff209976e1a7369561b39a2d`

Lexical marker document/occurrence counts are:

| Field family | Documents | Occurrences |
| --- | ---: | ---: |
| bankruptcy/liquidation/OTC continuation | 0 | 0 |
| cash and stock consideration | 0 | 0 |
| first and last tradable dates | 0 | 0 |
| predecessor/successor/acquirer | 0 | 0 |
| source time and revision history | 1 | 4 |
| stable security and listing identifiers | 3 | 7 |
| suspension/delisting effective status | 3 | 5 |
| termination reason | 2 | 52 |

These counts are navigation evidence only. A zero is not proof of absence and
a hit is not a matched fact.

## Verification

- exact replay returned `already_present` with zero network requests;
- custody and report directory modes are `0700`, report mode is `0400`;
- no symlink, partial, or staging residue was found;
- 10 focused/linked tests passed;
- the complete API suite passed 2,761 tests with two unchanged dependency
  deprecation warnings; and
- all fact, outcome, performance, admission, canonical-write, publication,
  deployment, and scheduler counters remain zero.

## Next bounded gate

Perform form-aware SCS extraction and stable-ID-bound field adjudication. Raw
bytes and lexical contexts must not be reused as an outcome or borrowed from
the historical 64-case sample.
