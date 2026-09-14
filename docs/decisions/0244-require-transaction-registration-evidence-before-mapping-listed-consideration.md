# ADR 0244: Require Transaction-Registration Evidence before Mapping Listed Consideration

## Status

Accepted.

## Context

Twelve non-election terminal-payoff cases have a listed-equity ratio and
matched cessation timing. Transaction documents provide agreement-party names
and share-class language, while the point-in-time canonical Instrument Master
contains plausible common-stock candidates. SEC Submissions also associates
candidate CIKs with current ticker and exchange metadata.

That alignment is not yet sufficient identity proof. Party names such as
Rocket, Compass, Columbia, and Rayonier have multiple market-name candidates,
and ticker/name matching alone cannot grant a stable-ID assignment. The
Vivmark transaction also crosses an `EQR` to `VMRK` name/ticker transition
while retaining one candidate stable identity.

## Decision

Freeze exactly one transaction-registration 424B3 source document for each of
the 12 cases. The plan must bind the exact agreement-party literal, candidate
CIK, SEC Submissions filing row, point-in-time common-stock identity, source
identity key, EOD/Identity fingerprints, and immutable archive URL.

Keep every stable `instrument_id` as a proposed candidate only. A later
adjudicator may assign it only after the retained 424B3 content independently
matches the target transaction, ordinary/common consideration class, and
registered exchange ratio. Names and tickers remain locators, never positive
identity authority.

Do not expand this into a global issuer or entity master. Elections and other
complex payoff states remain outside the 12-case plan.

## Consequences

The next source acquisition is bounded to 12 exact public SEC documents rather
than an undirected issuer search. False name/ticker joins fail closed, and the
event-time `EQR`/later `VMRK` transition remains visible without breaking the
candidate stable identity.

The plan makes no network request and creates no identity assignment,
terminal value, canonical lifecycle fact, strategy label, `/data` write,
Historical Coverage write, research admission, publication, deployment, or
scheduler change.
