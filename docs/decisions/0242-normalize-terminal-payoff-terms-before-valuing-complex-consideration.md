# ADR 0242: Normalize Terminal-Payoff Terms before Valuing Complex Consideration

## Status

Accepted.

## Context

The first-strategy sample has 61 typed common-share consideration clauses and
a bounded comparison between SEC trading-stop timing and canonical EOD
presence. The clauses contain par values, preferred-security terms, employee
awards, fractional-share cash, CVRs, holder elections, and multiple exchange
ratios. Treating every number as ordinary-share terminal value would create
false payoffs and biased research labels.

Fixed cash can be mechanically normalized from exact source literals. Listed
stock requires a point-in-time consideration-security identity and market
value. CVRs require realization or a separately governed valuation policy.
Elections and proration do not define one universal holder outcome. An
unlisted unit cannot be valued from an exchange close.

## Decision

Create one finite, source-fingerprint-bound term registry for the exact 61
cases. Preserve each selected literal, offset, digest, economic kind, and
normalized decimal value. Normalize USD cash to cents and listed-equity or
unit ratios to six decimal places without binary floats.

Keep these payoff profiles separate:

- fully specified fixed cash;
- listed-equity market value required;
- contingent value right unvalued;
- holder election unresolved; and
- unlisted-unit election unresolved.

For elections, retain each alternative, the source terms belonging to it,
whether it is the stated default, and whether proration applies. Source-local
consideration-issuer names are locators only and never global stable IDs. Cash
in lieu of fractional shares remains a separate adjustment.

The term report may identify fixed-cash cases whose cessation timing is ready
for a later terminal-outcome calculation. It does not itself create a terminal
outcome or a canonical lifecycle fact.

## Consequences

The next step can calculate only the bounded fixed-cash outcomes with matched
timing, while listed-security, CVR, election, unlisted-unit, and timing
residuals remain explicit. No complex component is silently valued at zero,
and a named source amount that is not numeric in the selected clause remains
unresolved.

The operation is network-disabled and writes only one immutable owner-only
private evidence report. It does not write `/data`, publish Historical
Coverage, admit research, or change Production.
