# Strong-Leader Pullback SEC Transaction Candidate Audit — 2026-09-13

## Verdict

All 89 remaining transaction-adjacent primary documents in the frozen first-
strategy package were formally reread, classified by form structure, and
indexed through bounded candidate contexts. The package is complete for its
declared extraction contract. It creates zero transaction-completion,
lifecycle, terminal-outcome, or research facts.

## Bound inputs

- implementation revision:
  `591585ef3d26d40d524313c932ded9303c74697e`
- document plan SHA-256:
  `bb79ec052e7296b1a7234f83d5c91a11097bdb54f9215e8c806e5159ab0d41f7`
- source manifest SHA-256:
  `38d7cf826769e4f3541ba5e22b4066b3f9a8779e56c770f81e7c2b5fc0833bb5`
- content-census SHA-256:
  `a566d966236fb046a88e662dacbcfa35ff93d57f319b86a218ef0f0ddde46869`
- evaluation time: `2026-09-13T16:28:34Z`

The builder recomputed each document and normalized-text identity, required
exact agreement with the content census, and prohibited network access.

## Population and structure

- 89 documents across 63 stable-ID locators;
- 62 Form 8-K, 12 Schedule TO amendments, 12 Schedule 14D-9 amendments, two
  DEFA14A documents, and one Form 6-K;
- 61 exact 8-K Item 2.01 candidate scopes;
- one 8-K without Item 2.01, retained separately rather than treated as
  sampled-common-equity completion evidence;
- 24 tender-amendment primary documents;
- one 6-K whose primary document references a completion exhibit but does not
  contain that exhibit body; and
- two proxy-material primary documents with no registered completion scope.

Fourteen stable IDs have more than one document; the maximum is three. The
high-recall source plan intentionally preserved related, repeated, and
ultimately irrelevant issuer filings.

## Candidate coverage

Eighty-six primary documents contain at least one registered candidate marker.
Document/occurrence counts are:

| Candidate family | Documents | Occurrences |
| --- | ---: | ---: |
| Cash/stock consideration | 86 | 827 |
| Predecessor/successor/acquirer | 78 | 179 |
| Suspension/delisting status | 79 | 182 |
| Tender acceptance/expiration | 37 | 88 |
| Transaction completion/closing | 74 | 234 |
| Transaction effective time | 78 | 798 |

At most three bounded, hashed contexts per family and their local date tokens
are retained. High occurrence counts reflect repeated legal text and embedded
transaction materials; they are not independent facts.

Partial lifecycle-family candidate counts are 86 consideration, 78 party
relationship, 79 suspension/delisting, 74 termination reason, and all 89 for
source/revision and locator evidence. First/last tradable date and bankruptcy/
liquidation/OTC continuation support remain zero. Every complete field-support
count remains zero.

## Artifact and reread

The owner-only output is:

`/home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-sec-transaction-candidates/extraction=20260913-v1`

- report bytes: 917,859;
- report SHA-256:
  `fbaf9116fc23e00dcdeeb21075c7bdfb196b6d178b588d76fb549b27d8d790ae`;
- logical fingerprint:
  `15ecfe9c5e737aa4090ed144de822b916040390a7a513f36b09715ecf25b9d2b`;
- directory/file modes: `0700/0400`;
- symlinks, partial files, and temporary residue: zero.

An exact second invocation returned `already_present` with the same identities.

## Verification and authority

- three focused transaction tests passed;
- the complete API suite passed 2,658 tests with two unchanged dependency
  warnings;
- wrapper syntax and repository diff checks passed;
- network requests, transaction facts, security assignments, lifecycle facts,
  terminal outcomes, `/data` writes, Historical Coverage writes, research
  admissions, Candidate writes, publications, deployments, and scheduler
  changes: zero.

## Next gate

Reconcile the Form 25, Form 15, and transaction candidate packages at the
stable-ID case level. The reconciliation must distinguish matched, absent from
source, referenced-but-unavailable, unsupported, ambiguous, conflicting, and
irrelevant issuer evidence. No date, amount, party, class, or status becomes a
fact until security-level identity and cross-document semantics are proven.
