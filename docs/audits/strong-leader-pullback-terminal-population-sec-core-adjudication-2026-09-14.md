# Strong-Leader Pullback Terminal-Population SEC Core Adjudication Audit

Date: 2026-09-14

## Scope

Apply the established point-in-time cover, transaction-completion, Item 3.01
termination-reason, and ordinary-share consideration rules to the one SCS
case. No historical case decision was imported. The operation was zero-network
and did not read credentials, write `/data`, create a canonical lifecycle fact
or terminal outcome, change research admission, publish Candidate data, deploy,
or modify a scheduler.

## Result

- output: `adjudication=20260914-v1/core-adjudication.json`
- implementation revision: `4aa6ff0a60019a6eea4ec27419a320c5818670bb`
- evaluated at: `2026-09-14T07:30:24Z`
- boundary-local identity interval: 2025-12-09 through 2025-12-11,
  represented with exclusive end 2025-12-12
- identity interval is full lifecycle: false
- report bytes: 12,100
- report SHA-256:
  `aa37836aa161ee21f96c5a8920e09ae780fc454455d22c85703c9538377f7321`
- logical fingerprint:
  `773ba35192f1d722412c1e1bea2fc98c8988722335f664eb2b5dcf9656054698`

The 8-K cover contains one matched `Class A Common Stock` row for CIK
`0001050825`, ticker locator `SCS`, and XNYS. The Form 25, Form 15, cover, and
stable-ID chain agree on CIK, Commission file `001-13873`, common-equity class,
and exchange. Ticker alone grants no authority.

The selected issuer transaction-completion date is 2025-12-10 under the
highest-priority unique named-closing-date rule. One bounded Item 3.01 section
links merger/acquisition completion to trading halt, delisting, Form 25 request,
and no-longer-listed actions. The termination reason is matched as
`merger_or_acquisition`.

The primary common-share clause is matched as
`holder_election_cash_or_stock`, with cash and listed-equity components plus a
separate fractional-share cash adjustment. Numeric payoff terms remain in
source evidence and are not normalized or valued.

## Preserved limitations

- the Form 25 notice/signature date is not an effective delisting date;
- the Form 15 certification date is not a trading-cessation date;
- first/last tradability and legal delisting effectiveness remain unsupported;
- acquirer payoff-security identity, election, proration, normalized terms,
  terminal reference value, strategy return, and terminal outcome remain
  absent; and
- terminal-gap census V2 remains 42 / 65 securities and 196 / 302 five-session
  paths with reference evidence.

## Verification

- exact replay returned `already_present` with zero network requests;
- custody and output directory modes are `0700`, report mode is `0400`;
- no symlink, partial, or staging residue was found;
- 29 focused/linked tests passed;
- the complete API suite passed 2,765 tests with two unchanged dependency
  deprecation warnings; and
- lifecycle fact, terminal outcome, performance, admission, canonical-write,
  publication, deployment, and scheduler counters remain zero.

## Next bounded gate

Adjudicate the source-stated SCS trading-cessation boundary against formal
stable-ID EOD presence, then establish a separate policy for the holder-
election/proration consideration before any terminal reference value.
