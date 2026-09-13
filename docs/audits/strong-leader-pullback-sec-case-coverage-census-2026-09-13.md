# Strong-Leader Pullback SEC Case Coverage Census Audit — 2026-09-13

## Verdict

The frozen Form 25, Form 15, and transaction candidate packages were joined
to the exact 64-case first-strategy lifecycle population by stable
`instrument_id`. The resulting census is complete for candidate-document
coverage, but field adjudication has not started. All 512 case/field results
remain `unsupported`, and no lifecycle or terminal-outcome fact was created.

## Bound inputs

- implementation revision:
  `42295c127c85c9efb09e95c10259e9a6288d8bdb`;
- source-acceptance sample: 64 lifecycle cases;
- Form 25 candidates: 64 documents across 62 cases;
- Form 15 candidates: 66 documents across 62 cases;
- transaction candidates: 89 documents across 63 cases;
- total candidate documents: 219; and
- evaluation time: `2026-09-13T16:46:26Z`.

The builder required exact agreement across the frozen plan, source manifest,
content census, and 64-case population bindings. It performed no network
request.

## Case evidence profiles

| Profile | Cases |
| --- | ---: |
| Structured transaction scope | 61 |
| Notice only; no transaction document | 1 |
| Completion exhibit referenced but body missing | 1 |
| No registered transaction-completion scope | 1 |

Candidate presence by required lifecycle field is:

| Required field | Cases with candidate material |
| --- | ---: |
| Bankruptcy, liquidation, or OTC continuation | 0 |
| Cash and stock consideration | 61 |
| First and last tradable dates | 0 |
| Predecessor, successor, and acquirer | 59 |
| Source availability and revision history | 64 |
| Stable security and listing identifiers | 64 |
| Suspension and delisting status/effective dates | 63 |
| Termination reason | 56 |

These counts mean only that retained primary documents contain candidate
material. Presence is not a matched field, and absence from the retained
documents is not proof that an event or fact is absent.

## Artifact and reread

The owner-only output is:

`/home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-sec-case-coverage-census/census=20260913-v1`

- report SHA-256:
  `77b81064c1a494275029a2c667bac7ef2cb99c83d446aa491c2be29a3fe1e09a`;
- logical fingerprint:
  `98d9c5d3da4d02316c020f0705ce1e8714a8b4086ead1a897a9e3a5511f7c1b9`;
- directory/file modes: `0700/0400`; and
- symlinks, partial files, staging files, and temporary residue: zero.

An exact second invocation returned `already_present` with the same identities.

## Verification and authority

- three focused case-census tests passed after the final readability edit;
- before that behavior-neutral edit, the complete API suite passed 2,661 tests
  with two unchanged dependency warnings;
- wrapper syntax and repository diff checks passed; and
- adjudicated fields, matched/absent/ambiguous/conflicting/irrelevant results,
  lifecycle facts, terminal outcomes, network requests, `/data` writes,
  Historical Coverage writes, research admissions, Candidate writes,
  publications, deployments, and scheduler changes: zero.

## Next gate

Adjudicate typed candidate values case by case, beginning with the 61
structured transaction cases, while preserving document identity, security
identity, issuer-event semantics, and source availability as separate claims.
Freeze the exact residual field gap before testing any commercial source.
