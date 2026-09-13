# Strong-Leader Pullback SEC Case Adjudication Audit — 2026-09-13

## Verdict

The first point-in-time field adjudication is complete. Sixty-one of the 64
frozen lifecycle cases now have a unique event-time link from the stable source
instrument to a common-equity SEC Form 8-K cover. Those 61
`stable_security_and_listing_identifiers` fields are `matched`; every other
case/field cell remains `unsupported`.

This is private evidence-layer progress. It creates no canonical identity,
lifecycle, terminal outcome, Historical Coverage, or research admission.

## Bound inputs

- implementation revision:
  `14c72854200efa48842aa1522c01358ba08fe03d`;
- 64-case source-acceptance sample;
- 219-request document plan and complete source package;
- 89-document transaction candidate report;
- 64-case coverage census; and
- evaluation time: `2026-09-13T21:09:35Z`.

The builder formally reread all 219 source documents with network access
disabled and required exact plan, source-manifest, transaction, sample, and
coverage identities.

## Cover population and decision

All 62 Form 8-K documents expose inline-XBRL registrant CIK, report date, and
context-aligned security title, ticker, and exchange facts. The covers contain
70 complete security rows:

- 61 target common-equity documents uniquely matched the source instrument by
  active CIK+ticker+exchange MIC and common-equity title;
- one later IPG Form 8-K concerns a debt exchange after the provider delist-
  date candidate. Its reused ticker was rejected outside the source identity
  window; and
- one TGI Purchase Rights context has no trading symbol. It is retained as one
  incomplete non-target context and was not merged into the common-stock row.

The matching window begins at first canonical observation and ends at the
provider delist-date candidate, inclusive. Ticker-only matching is prohibited.

The three cases without an in-window structured 8-K cover remain explicit:

| Ticker | Evidence profile | Identity-field result |
| --- | --- | --- |
| `LNW` | no registered transaction-completion scope | unsupported |
| `REVG` | Form 25/Form 15 notice only | unsupported |
| `SAND` | completion exhibit referenced but body absent | unsupported |

## Field results

| State | Case/field cells |
| --- | ---: |
| Matched | 61 |
| Unsupported | 451 |
| Absent / referenced-only / ambiguous / conflicting / irrelevant | 0 |

Only `stable_security_and_listing_identifiers` changed: 61 matched and three
unsupported. Transaction completion, first/last tradability, delisting
effective date, termination reason, parties, consideration, bankruptcy,
liquidation, OTC continuation, and terminal return remain unresolved.

## Artifact and reread

The owner-only output is:

`/home/hui/.local/state/trading-intelligence-platform/historical-evidence/strong-leader-pullback-sec-case-adjudication/adjudication=20260913-cover-v1`

- report SHA-256:
  `7f868b6f1d4471cd8690d4ff4f0daf2b439f0d51808021ba5aaa30de6cb1eb94`;
- logical fingerprint:
  `e15db9ddd43efaa489fc1542ca0d42daf7e410bae91440cdf0bcccaee3507bcd`;
- directory/file modes: `0700/0400`; and
- symlinks, partial files, staging files, and temporary residue: zero.

An exact second invocation returned `already_present` with the same identities.

## Verification and authority

- 26 focused adjudication, coverage, and SEC identity tests passed;
- the complete API suite passed 2,664 tests with two unchanged dependency
  warnings;
- wrapper syntax, module compilation, line-length, and repository diff checks
  passed; and
- network requests, canonical identity writes, lifecycle facts, terminal
  outcomes, `/data` writes, Historical Coverage writes, research admissions,
  Candidate writes, publications, deployments, and scheduler changes: zero.

## Next gate

On the 61 matched structured cases, extract and adjudicate issuer transaction
completion, event date, termination reason, consideration, and party relations
with exact document and context provenance. Last tradability and terminal
return remain separate market-status and pricing decisions. The three
unsupported cases stay quarantined while that work proceeds.
