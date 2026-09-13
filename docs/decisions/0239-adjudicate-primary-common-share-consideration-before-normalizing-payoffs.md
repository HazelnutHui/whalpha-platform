# ADR 0239: Adjudicate Primary Common-Share Consideration before Normalizing Payoffs

## Status

Accepted.

## Context

The first-strategy SEC sample has 61 matched common-equity identities, typed
transaction-completion events, and listing-termination reasons. The same
filings also discuss options, restricted awards, preferred stock, debt,
fractional-share settlement, and financing. A broad cash-or-stock keyword scan
therefore overstates ordinary-share consideration and can corrupt terminal
return research.

## Decision

Adjudicate the primary clause governing issued or outstanding ordinary/common
shares in the already bounded transaction scope. Prefer an explicit tender-
offer price for all outstanding common shares; otherwise use the first explicit
merger-conversion clause for ordinary/common shares.

Classify only these structures:

- cash only;
- stock only;
- fixed cash and listed stock;
- cash plus a contingent value right;
- holder election between cash and listed stock; or
- holder election between cash and cash plus an unlisted equity unit.

Cash paid only instead of fractional shares is retained as an adjustment and
does not turn stock-only consideration into cash-and-stock consideration.
Options, RSUs, other awards, preferred stock, debt, and financing are excluded.

The exact clause is retained with offsets and a digest, but numeric payoff terms
are not normalized in this stage. Party relations, tradability, terminal
outcomes, canonical lifecycle facts, and research admission remain separate.

## Consequences

The sample can resolve the evidence field describing ordinary-share
consideration without pretending that a terminal payoff or return is ready.
Later numeric normalization must remain traceable to the retained clause and
must separately model elections, CVRs, non-listed units, and fractional-share
cash.
