# Strong-Leader Pullback SEC Document Content Census Audit — 2026-09-13

## Verdict

All 219 frozen SEC primary documents were deterministically decoded, parsed,
and localized against the eight registered lifecycle field-marker families.
The complete result was rebuilt and reread with zero network access and an
identical hash. It is a lexical candidate census only; zero lifecycle or
terminal fact was created.

## Bound evidence

| Field | Value |
| --- | --- |
| Implementation revision | `5845a32dc9c768d1e653c3a1d1d65bcc059eea53` |
| Evaluated at | `2026-09-13T14:36:14Z` |
| Plan SHA-256 | `bb79ec052e7296b1a7234f83d5c91a11097bdb54f9215e8c806e5159ab0d41f7` |
| Source manifest SHA-256 | `38d7cf826769e4f3541ba5e22b4066b3f9a8779e56c770f81e7c2b5fc0833bb5` |
| Source artifact binding | `abf6f8ebcde8a5690768bca09504c56854823da3ff2c0e3bd8a4929cbba63a42` |
| Marker ruleset | `f1f5e251fea187e70c975f129458620cfbe5d6d3c7c6d08bea1dbe7408f3100d` |

## Parse results

- 219 / 219 documents parsed from 5,430,894 source bytes into 1,539,034
  normalized text characters.
- All 219 decoded as UTF-8.
- Markup profiles were 64 ordinary HTML, 93 SEC SGML-wrapped HTML, and 62
  inline-XBRL XHTML documents.
- The 1,339,529-byte report has SHA-256
  `a566d966236fb046a88e662dacbcfa35ff93d57f319b86a218ef0f0ddde46869`
  and logical fingerprint
  `d22f5436aaeabeee3fe8bee8061594b42f479f25b8ad9f575fab81f3e781e77a`.
- Formal identical rerun returned `already_present`; modes are `0700/0400`,
  with zero symlink or staging residue.

## Lexical candidate distribution

| Registered field family | Documents with marker | Occurrences |
| --- | ---: | ---: |
| Bankruptcy, liquidation, or OTC continuation | 1 | 2 |
| Cash and stock consideration | 140 | 591 |
| First and last tradable dates | 9 | 9 |
| Predecessor, successor, and acquirer | 70 | 378 |
| Source availability and revision history | 93 | 904 |
| Stable security and listing identifiers | 217 | 461 |
| Suspension/delisting status and dates | 209 | 496 |
| Termination reason | 119 | 2,948 |

These are intentionally not coverage percentages. Repeated boilerplate and
proposed events can create many occurrences, while a zero marker count does
not prove that an event is absent.

## Verification and remaining boundary

Fourteen focused tests and the complete 2,649-test API suite passed with two
unchanged dependency deprecation warnings. Network, credentials, full-text
duplication, security identity assignment, lifecycle/terminal facts, strategy
outcomes, `/data`, Historical Coverage, research admission, Candidate,
publication, deployment, and scheduler changes remained zero.

The next bounded stage is form-aware candidate-value extraction and
cross-document reconciliation. It must preserve proposed/completed/amended
state and cannot turn CIK or ticker text into a listed-security assignment.
