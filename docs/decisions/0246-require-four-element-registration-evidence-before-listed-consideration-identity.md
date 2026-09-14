# ADR 0246: Require Four-Element Registration Evidence before Listed-Consideration Identity

## Status

Accepted.

## Context

The 12 frozen 424B3 files are now in complete, formally reread custody. A filing
under a candidate issuer CIK is necessary but does not by itself prove that the
document registers the exact merger consideration security or the final
exchange terms.

Initial content inspection exposed two important residuals: a registration
document may describe a variable exchange-ratio formula without containing the
later final ratio, and a 424B3 filed by the expected issuer may concern an
unrelated debt offering rather than the merger. Filing form, company name, and
ticker therefore cannot be treated as sufficient evidence.

## Decision

Adjudicate every frozen file against four source elements:

1. the same merger transaction and target common security;
2. the consideration security's ordinary/common share class;
3. the exact registered exchange ratio agreeing numerically with the retained
   terminal-payoff term; and
4. the plan's identifier chain from the SEC filer CIK to the event-time
   canonical common-security candidate and stable `instrument_id`.

Assign the proposed consideration stable ID only when all four elements match
in one deterministic decision. Names and tickers remain document locators and
transaction-language aids; they never independently grant identity.

Retain formula-only documents and non-transaction offering documents as typed
negative results. Do not infer the final ratio from a formula range, a later
price, or the fact that the expected issuer filed the document.

## Consequences

The adjudicator can admit a strict subset of the 12 candidate identities while
keeping every residual explicit. A later residual source plan may target only
the unresolved cases.

Identity adjudication does not value the consideration, create a terminal
outcome or strategy label, modify `/data` or Historical Coverage, admit
research, publish Candidate data, deploy, or change a scheduler.
