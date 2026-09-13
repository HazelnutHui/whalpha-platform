# ADR 0232: Extract Form 25 Structure Without Inferring Terminal Dates

- Status: Accepted
- Date: 2026-09-13

## Context

The content census found 64 Form 25-NSE documents across 62 first-strategy
instruments. All 64 expose consistent HTML table fields for issuer, CIK,
exchange, Commission file number, security class, selected rule provision, and
signature date. Those fields can be extracted without narrative matching.

Form 25 is a notice concerning exchange listing or registration. Its filing,
signature, and rule code do not by themselves prove the last tradable date,
effective delisting date, reason, successor, consideration, OTC continuation,
or terminal return needed by the historical research database.

## Decision

1. Extract only the standardized table fields from all 64 Form 25-NSE source
   documents. Require complete one-to-one recovery; one malformed or ambiguous
   document rejects the whole report.
2. Require the issuer-link CIK to equal the plan CIK and the signature date to
   equal the plan filing date. Retain duplicate instruments as separate filing
   evidence rather than merging them.
3. Read checkbox state from the HTML control itself. Do not infer the selected
   rule from surrounding text.
4. Treat issuer name, exchange, class, CIK, Commission file number, selected
   rule, acceptance time, and signature date as structured source candidates.
   They remain partial candidates for three field families, not complete
   lifecycle facts.
5. Keep last-trade, effective-delisting, termination-reason, successor,
   consideration, and OTC/liquidation values explicitly null. Keep all eight
   complete field-support counts at zero.
6. Bind the report to the immutable plan, source package, and content census;
   prohibit network access and all canonical/research/Production authority.

## Consequences

- The direct exchange-notice population is structured without brittle broad
  regex or legal effective-date assumptions.
- The two instruments with multiple Form 25 filings remain available for
  later conflict and class-level review.
- Narrative 8-K, Form 15, tender, and proxy evidence remains a separate stage.

## Rejected alternatives

### Add a fixed number of days to the filing date

Rejected because the exact effective status and last tradable session require
governed rule semantics and corroborating exchange/market evidence.

### Collapse multiple notices per stable instrument

Rejected because notices may concern different securities, exchanges, or
revisions; early merging would hide evidence.
